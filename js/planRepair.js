/**
 * Plan Repair Module.
 *
 * When a disruption occurs (agent breakdown, cell blockage, or emergency task),
 * this module repairs the affected agents' plans WITHOUT re-invoking the full
 * multi-agent planner from scratch.
 *
 * The repair process:
 *   1. Identifies agents whose future paths are invalidated
 *   2. Attempts to replan each affected agent locally
 *   3. If conflicts arise, negotiates with neighboring agents
 *   4. Minimizes the number of agents whose original plans are altered
 */

/**
 * Disruption types.
 */
const DisruptionType = {
    CELL_BLOCKAGE: 'cell_blockage',
    AGENT_BREAKDOWN: 'agent_breakdown',
    EMERGENCY_TASK: 'emergency_task',
};

/**
 * Identify agents whose future plans are affected by a disruption.
 *
 * @param {Array<Agent>} agents
 * @param {Object} disruption - {type, x, y, agentId, ...}
 * @param {number} currentTime
 * @returns {Array<Agent>} Affected agents
 */
function identifyAffectedAgents(agents, disruption, currentTime) {
    const affected = [];

    switch (disruption.type) {
        case DisruptionType.CELL_BLOCKAGE:
            // Agents whose future path passes through the blocked cell
            for (const agent of agents) {
                if (agent.status === AgentStatus.BROKEN || agent.status === AgentStatus.DONE) continue;
                if (agent.pathPassesThrough(disruption.x, disruption.y, currentTime)) {
                    affected.push(agent);
                }
            }
            break;

        case DisruptionType.AGENT_BREAKDOWN:
            // The broken agent itself, plus agents whose paths conflict with
            // the broken agent's stationary position
            const brokenAgent = agents.find(a => a.id === disruption.agentId);
            if (brokenAgent) {
                const brokenPos = brokenAgent.getPositionAtTime(currentTime);
                for (const agent of agents) {
                    if (agent.id === disruption.agentId) continue;
                    if (agent.status === AgentStatus.BROKEN || agent.status === AgentStatus.DONE) continue;
                    if (agent.pathPassesThrough(brokenPos.x, brokenPos.y, currentTime)) {
                        affected.push(agent);
                    }
                }
            }
            break;

        case DisruptionType.EMERGENCY_TASK:
            // The specific agent that receives the emergency task
            const emergencyAgent = agents.find(a => a.id === disruption.agentId);
            if (emergencyAgent && emergencyAgent.status === AgentStatus.ACTIVE) {
                affected.push(emergencyAgent);
            }
            break;
    }

    return affected;
}

/**
 * Repair plans after a disruption.
 *
 * Strategy:
 *   1. Remove future reservations for affected agents
 *   2. Replan each affected agent from its current position
 *   3. If conflicts with non-affected agents, negotiate (try to find
 *      alternative paths; if needed, replan neighbors too)
 *   4. Track and return the number of modified agents
 *
 * @param {Grid} grid
 * @param {Array<Agent>} agents
 * @param {Object} disruption
 * @param {number} currentTime
 * @param {ReservationTable} reservations
 * @param {number} maxTime
 * @returns {Object} {modifiedCount, modifiedAgentIds, success}
 */
function repairPlans(grid, agents, disruption, currentTime, reservations, maxTime) {
    const modifiedAgentIds = new Set();
    const activeAgents = agents.filter(a => a.status === AgentStatus.ACTIVE);

    // --- Step 0: Apply disruption effects ---
    if (disruption.type === DisruptionType.CELL_BLOCKAGE) {
        grid.blockCell(disruption.x, disruption.y);
    } else if (disruption.type === DisruptionType.AGENT_BREAKDOWN) {
        const brokenAgent = agents.find(a => a.id === disruption.agentId);
        if (brokenAgent) {
            brokenAgent.status = AgentStatus.BROKEN;
            const brokenPos = brokenAgent.getPositionAtTime(currentTime);
            // Remove broken agent's future reservations
            reservations.removeAgentReservations(brokenAgent.id, currentTime + 1);
            // Reserve broken agent's position as a static block for future timesteps
            for (let t = currentTime; t < maxTime + 50; t++) {
                reservations.reserve(brokenPos.x, brokenPos.y, t, brokenAgent.id);
            }
        }
    } else if (disruption.type === DisruptionType.EMERGENCY_TASK) {
        const emergencyAgent = agents.find(a => a.id === disruption.agentId);
        if (emergencyAgent) {
            // Insert emergency task at the front of remaining tasks
            emergencyAgent.tasks.unshift({
                pickupX: disruption.pickupX,
                pickupY: disruption.pickupY,
                deliveryX: disruption.deliveryX,
                deliveryY: disruption.deliveryY,
                status: TaskStatus.PENDING,
                id: -1, // Emergency marker
            });
        }
    }

    // --- Step 1: Identify affected agents ---
    const affectedAgents = identifyAffectedAgents(agents, disruption, currentTime);

    if (affectedAgents.length === 0 && disruption.type !== DisruptionType.EMERGENCY_TASK) {
        return { modifiedCount: 0, modifiedAgentIds: [], success: true };
    }

    // For emergency task, add the emergency agent if not already affected
    if (disruption.type === DisruptionType.EMERGENCY_TASK) {
        const ea = agents.find(a => a.id === disruption.agentId);
        if (ea && !affectedAgents.includes(ea)) {
            affectedAgents.push(ea);
        }
    }

    // --- Step 2: Remove future reservations for affected agents ---
    for (const agent of affectedAgents) {
        reservations.removeAgentReservations(agent.id, currentTime);
    }

    // --- Step 3: Replan each affected agent ---
    // Sort by priority: fewer remaining goals first (they're easier to replan)
    affectedAgents.sort((a, b) => {
        const goalsA = a.getRemainingGoals(currentTime).length;
        const goalsB = b.getRemainingGoals(currentTime).length;
        return goalsA - goalsB;
    });

    for (const agent of affectedAgents) {
        if (agent.status === AgentStatus.BROKEN) continue;

        const currentPos = agent.getPositionAtTime(currentTime);

        // Try replanning this agent
        const newPath = planAgentFullPath(grid, agent, currentPos, currentTime, reservations, maxTime);

        if (newPath !== null) {
            agent.updatePlan(newPath, currentTime);
            reservations.reservePath(newPath, agent.id, 30);
            modifiedAgentIds.add(agent.id);
        } else {
            // Replanning failed — negotiate with neighbors
            const negotiationResult = negotiateWithNeighbors(
                grid, agent, agents, currentPos, currentTime, reservations, maxTime
            );
            if (negotiationResult.success) {
                modifiedAgentIds.add(agent.id);
                for (const nid of negotiationResult.modifiedNeighbors) {
                    modifiedAgentIds.add(nid);
                }
            } else {
                // Last resort: agent waits at current position
                const waitPlan = [];
                for (let t = currentTime; t <= currentTime + 20; t++) {
                    waitPlan.push({ x: currentPos.x, y: currentPos.y, t });
                }
                agent.updatePlan(waitPlan, currentTime);
                reservations.reservePath(waitPlan, agent.id, 10);
                modifiedAgentIds.add(agent.id);
            }
        }
    }

    return {
        modifiedCount: modifiedAgentIds.size,
        modifiedAgentIds: [...modifiedAgentIds],
        success: true,
    };
}

/**
 * Negotiate with neighboring agents to find conflict-free paths.
 *
 * When an affected agent cannot replan without conflicting with
 * non-affected agents, this function temporarily removes the neighbor's
 * reservations, replans the affected agent, and then replans the neighbor.
 *
 * @param {Grid} grid
 * @param {Agent} agent - The agent that needs replanning
 * @param {Array<Agent>} allAgents - All agents
 * @param {{x,y}} currentPos - Agent's current position
 * @param {number} currentTime
 * @param {ReservationTable} reservations
 * @param {number} maxTime
 * @returns {{success: boolean, modifiedNeighbors: Array<number>}}
 */
function negotiateWithNeighbors(grid, agent, allAgents, currentPos, currentTime, reservations, maxTime) {
    const modifiedNeighbors = [];

    // Find neighboring agents: those within a certain distance or whose
    // paths intersect the agent's potential route area
    const neighbors = findNeighboringAgents(agent, allAgents, currentPos, currentTime, grid);

    for (const neighbor of neighbors) {
        if (neighbor.status !== AgentStatus.ACTIVE) continue;

        // Save neighbor's current reservations
        const neighborPos = neighbor.getPositionAtTime(currentTime);
        const neighborOldPlan = neighbor.plan.filter(s => s.t >= currentTime).map(s => ({ ...s }));

        // Temporarily remove neighbor's future reservations
        reservations.removeAgentReservations(neighbor.id, currentTime);

        // Try replanning the affected agent
        const agentNewPath = planAgentFullPath(grid, agent, currentPos, currentTime, reservations, maxTime);

        if (agentNewPath !== null) {
            // Reserve the agent's new path
            reservations.reservePath(agentNewPath, agent.id, 30);
            agent.updatePlan(agentNewPath, currentTime);

            // Now replan the neighbor around the agent's new path
            const neighborNewPath = planAgentFullPath(
                grid, neighbor, neighborPos, currentTime, reservations, maxTime
            );

            if (neighborNewPath !== null) {
                reservations.reservePath(neighborNewPath, neighbor.id, 30);
                neighbor.updatePlan(neighborNewPath, currentTime);
                modifiedNeighbors.push(neighbor.id);
                return { success: true, modifiedNeighbors };
            } else {
                // Neighbor can't replan — rollback
                reservations.removeAgentReservations(agent.id, currentTime);
                // Restore neighbor's old reservations
                for (const step of neighborOldPlan) {
                    reservations.reserve(step.x, step.y, step.t, neighbor.id);
                }
            }
        } else {
            // Agent still can't replan — restore neighbor's reservations
            for (const step of neighborOldPlan) {
                reservations.reserve(step.x, step.y, step.t, neighbor.id);
            }
        }
    }

    return { success: false, modifiedNeighbors: [] };
}

/**
 * Find neighboring agents based on spatial proximity.
 * Returns agents sorted by distance to the given position.
 */
function findNeighboringAgents(agent, allAgents, pos, currentTime, grid) {
    const neighbors = [];
    const searchRadius = Math.max(grid.width, grid.height); // Search whole grid if needed

    for (const other of allAgents) {
        if (other.id === agent.id) continue;
        if (other.status === AgentStatus.BROKEN || other.status === AgentStatus.DONE) continue;

        const otherPos = other.getPositionAtTime(currentTime);
        const dist = manhattan(pos, otherPos);

        if (dist <= searchRadius) {
            neighbors.push({ agent: other, distance: dist });
        }
    }

    // Sort by distance (closest first — more likely to have path conflicts)
    neighbors.sort((a, b) => a.distance - b.distance);
    return neighbors.map(n => n.agent);
}
