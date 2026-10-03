/**
 * Simulation Engine.
 *
 * Manages the simulation lifecycle:
 *   - Scenario generation (grid, agents, tasks)
 *   - Cooperative initial planning
 *   - Timestep-by-timestep execution
 *   - Disruption injection and plan repair
 *   - Metrics collection
 */

class Simulation {
    /**
     * @param {Object} config
     * @param {number} config.gridWidth
     * @param {number} config.gridHeight
     * @param {number} config.numAgents
     * @param {number} config.obstacleDensity - 0 to 1
     * @param {number} config.tasksPerAgent
     * @param {number} config.maxTime - Time horizon
     */
    constructor(config) {
        this.config = Object.assign({
            gridWidth: 20,
            gridHeight: 20,
            numAgents: 5,
            obstacleDensity: 0.15,
            tasksPerAgent: 2,
            maxTime: 300,
        }, config);

        this.grid = null;
        this.agents = [];
        this.reservations = null;
        this.currentTime = 0;
        this.isRunning = false;
        this.isPaused = false;
        this.isFinished = false;

        // Metrics
        this.metrics = {
            initialMakespan: 0,
            currentMakespan: 0,
            totalDisruptions: 0,
            disruptions: [],          // Array of disruption events
            planModifications: [],    // Array of {time, modifiedCount, modifiedIds}
            totalAgentsModified: 0,
        };

        // Event callbacks
        this.onStep = null;
        this.onDisruption = null;
        this.onFinished = null;
        this.onPlanRepaired = null;
    }

    /**
     * Initialize a new simulation scenario.
     * Generates grid, agents, tasks, and computes initial plans.
     */
    initialize() {
        this.currentTime = 0;
        this.isRunning = false;
        this.isPaused = false;
        this.isFinished = false;
        this.metrics = {
            initialMakespan: 0,
            currentMakespan: 0,
            totalDisruptions: 0,
            disruptions: [],
            planModifications: [],
            totalAgentsModified: 0,
        };

        // Create grid
        this.grid = new Grid(this.config.gridWidth, this.config.gridHeight);

        // Create agents with random start positions
        this.agents = [];
        const usedPositions = new Set();

        for (let i = 0; i < this.config.numAgents; i++) {
            const pos = this.grid.getRandomFreeCell(usedPositions);
            if (pos === null) {
                console.warn(`Cannot place agent ${i} — grid too crowded`);
                continue;
            }
            const agent = new Agent(i, pos.x, pos.y);
            this.agents.push(agent);
            usedPositions.add(`${pos.x},${pos.y}`);
        }

        // Generate random tasks for each agent
        for (const agent of this.agents) {
            for (let t = 0; t < this.config.tasksPerAgent; t++) {
                const pickup = this.grid.getRandomFreeCell(usedPositions);
                if (!pickup) continue;
                usedPositions.add(`${pickup.x},${pickup.y}`);

                const delivery = this.grid.getRandomFreeCell(usedPositions);
                if (!delivery) continue;
                usedPositions.add(`${delivery.x},${delivery.y}`);

                agent.addTask(pickup.x, pickup.y, delivery.x, delivery.y);
            }
        }

        // Generate obstacles AFTER placing agents and tasks
        // Collect all important positions to exclude from obstacles
        const excludePositions = [];
        for (const agent of this.agents) {
            excludePositions.push({ x: agent.startX, y: agent.startY });
            for (const task of agent.tasks) {
                excludePositions.push({ x: task.pickupX, y: task.pickupY });
                excludePositions.push({ x: task.deliveryX, y: task.deliveryY });
            }
        }
        this.grid.generateRandomObstacles(this.config.obstacleDensity, excludePositions);

        // Run cooperative pathfinding
        const result = cooperativePathfinding(this.grid, this.agents, this.config.maxTime);
        this.reservations = result.reservations;

        if (!result.success) {
            console.warn('Some agents failed initial planning:', result.failedAgents);
        }

        // Record initial makespan
        this.metrics.initialMakespan = this._computeMakespan();
        this.metrics.currentMakespan = this.metrics.initialMakespan;
    }

    /**
     * Advance simulation by one timestep.
     * @returns {boolean} true if simulation continues, false if finished
     */
    step() {
        if (this.isFinished) return false;

        this.currentTime++;

        // Update task statuses for all active agents
        for (const agent of this.agents) {
            agent.updateTaskStatus(this.currentTime);
        }

        // Check if all agents are done
        const allDone = this.agents.every(
            a => a.status === AgentStatus.DONE || a.status === AgentStatus.BROKEN
        );

        // Also check if we've exceeded max time
        if (allDone || this.currentTime >= this.config.maxTime) {
            this.isFinished = true;
            this.metrics.currentMakespan = this.currentTime;
            if (this.onFinished) this.onFinished();
            return false;
        }

        if (this.onStep) this.onStep(this.currentTime);
        return true;
    }

    /**
     * Inject a disruption into the simulation.
     * @param {Object} disruption - {type, x, y, agentId, pickupX, pickupY, deliveryX, deliveryY}
     * @returns {Object} Plan repair result
     */
    triggerDisruption(disruption) {
        disruption.time = this.currentTime;
        this.metrics.disruptions.push(disruption);
        this.metrics.totalDisruptions++;

        // Perform plan repair
        const result = repairPlans(
            this.grid, this.agents, disruption,
            this.currentTime, this.reservations, this.config.maxTime
        );

        // Record metrics
        this.metrics.planModifications.push({
            time: this.currentTime,
            disruptionType: disruption.type,
            modifiedCount: result.modifiedCount,
            modifiedIds: result.modifiedAgentIds,
        });
        this.metrics.totalAgentsModified += result.modifiedCount;
        this.metrics.currentMakespan = this._computeMakespan();

        if (this.onPlanRepaired) this.onPlanRepaired(result);
        if (this.onDisruption) this.onDisruption(disruption, result);

        return result;
    }

    /**
     * Trigger a random cell blockage.
     */
    triggerRandomBlockage() {
        // Find a free cell that's on some agent's future path
        const candidates = [];
        for (const agent of this.agents) {
            if (agent.status !== AgentStatus.ACTIVE) continue;
            for (const step of agent.plan) {
                if (step.t > this.currentTime + 2) {
                    const key = `${step.x},${step.y}`;
                    if (this.grid.isWalkable(step.x, step.y) && !candidates.some(c => `${c.x},${c.y}` === key)) {
                        candidates.push({ x: step.x, y: step.y });
                    }
                }
            }
        }

        if (candidates.length === 0) {
            // Fallback: block a random free cell
            const cell = this.grid.getRandomFreeCell();
            if (cell) {
                return this.triggerDisruption({
                    type: DisruptionType.CELL_BLOCKAGE,
                    x: cell.x,
                    y: cell.y,
                });
            }
            return null;
        }

        const target = candidates[Math.floor(Math.random() * candidates.length)];
        return this.triggerDisruption({
            type: DisruptionType.CELL_BLOCKAGE,
            x: target.x,
            y: target.y,
        });
    }

    /**
     * Trigger a random agent breakdown.
     */
    triggerRandomBreakdown() {
        const activeAgents = this.agents.filter(a => a.status === AgentStatus.ACTIVE);
        if (activeAgents.length === 0) return null;

        const target = activeAgents[Math.floor(Math.random() * activeAgents.length)];
        return this.triggerDisruption({
            type: DisruptionType.AGENT_BREAKDOWN,
            agentId: target.id,
        });
    }

    /**
     * Trigger a random emergency task for a random agent.
     */
    triggerRandomEmergency() {
        const activeAgents = this.agents.filter(a => a.status === AgentStatus.ACTIVE);
        if (activeAgents.length === 0) return null;

        const target = activeAgents[Math.floor(Math.random() * activeAgents.length)];
        const usedSet = new Set();
        // Exclude existing task positions
        for (const a of this.agents) {
            for (const t of a.tasks) {
                usedSet.add(`${t.pickupX},${t.pickupY}`);
                usedSet.add(`${t.deliveryX},${t.deliveryY}`);
            }
        }

        const pickup = this.grid.getRandomFreeCell(usedSet);
        if (!pickup) return null;
        usedSet.add(`${pickup.x},${pickup.y}`);

        const delivery = this.grid.getRandomFreeCell(usedSet);
        if (!delivery) return null;

        return this.triggerDisruption({
            type: DisruptionType.EMERGENCY_TASK,
            agentId: target.id,
            pickupX: pickup.x,
            pickupY: pickup.y,
            deliveryX: delivery.x,
            deliveryY: delivery.y,
        });
    }

    /**
     * Trigger a random disruption (any type).
     */
    triggerRandomDisruption() {
        const types = ['blockage', 'breakdown', 'emergency'];
        const choice = types[Math.floor(Math.random() * types.length)];
        switch (choice) {
            case 'blockage': return this.triggerRandomBlockage();
            case 'breakdown': return this.triggerRandomBreakdown();
            case 'emergency': return this.triggerRandomEmergency();
        }
    }

    /**
     * Compute makespan (maximum completion time across all agents).
     */
    _computeMakespan() {
        let maxTime = 0;
        for (const agent of this.agents) {
            if (agent.status === AgentStatus.BROKEN) continue;
            maxTime = Math.max(maxTime, agent.getMakespan());
        }
        return maxTime;
    }

    /**
     * Get comprehensive metrics summary.
     */
    getMetrics() {
        const agentsModifiedSet = new Set();
        for (const mod of this.metrics.planModifications) {
            for (const id of mod.modifiedIds) {
                agentsModifiedSet.add(id);
            }
        }

        return {
            gridSize: `${this.config.gridWidth}×${this.config.gridHeight}`,
            numAgents: this.config.numAgents,
            obstacleDensity: `${(this.config.obstacleDensity * 100).toFixed(0)}%`,
            tasksPerAgent: this.config.tasksPerAgent,
            currentTime: this.currentTime,
            initialMakespan: this.metrics.initialMakespan,
            currentMakespan: this._computeMakespan(),
            totalDisruptions: this.metrics.totalDisruptions,
            totalPlanModifications: this.metrics.planModifications.length,
            uniqueAgentsModified: agentsModifiedSet.size,
            avgModifiedPerDisruption: this.metrics.planModifications.length > 0
                ? (this.metrics.totalAgentsModified / this.metrics.planModifications.length).toFixed(2)
                : 'N/A',
            agentStatuses: this.agents.map(a => ({
                id: a.id,
                status: a.status,
                planModified: a.planModified,
                tasksCompleted: a.tasks.filter(t => t.status === TaskStatus.DELIVERED).length,
                totalTasks: a.tasks.length,
                makespan: a.getMakespan(),
            })),
            disruptions: this.metrics.disruptions,
            modifications: this.metrics.planModifications,
        };
    }
}
