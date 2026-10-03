/**
 * Agent class representing a robotic agent in the warehouse.
 * Each agent has a start position, a set of tasks, and a planned path.
 */

// Unique color palette for agents
const AGENT_COLORS = [
    '#e60000', // Solid Red
    '#0055ff', // Solid Blue
    '#00aa00', // Solid Green
    '#e6b800', // Solid Gold
    '#9900ee', // Solid Purple
    '#00bbcc', // Solid Cyan
    '#ff6600', // Solid Orange
    '#ff3399', // Solid Magenta
    '#778899', // Solid Slate
    '#00e676', // Solid Emerald
    '#3d5afe', // Solid Cobalt
    '#ff1744', // Solid Crimson
];

/**
 * Task status enumeration.
 */
const TaskStatus = {
    PENDING: 'pending',       // Not yet started — need to visit pickup
    PICKED_UP: 'picked_up',  // Item picked up — need to visit delivery
    DELIVERED: 'delivered',   // Task complete
};

/**
 * Agent status enumeration.
 */
const AgentStatus = {
    ACTIVE: 'active',
    BROKEN: 'broken',
    DONE: 'done',
    WAITING: 'waiting',
};

class Agent {
    /**
     * @param {number} id - Unique agent identifier
     * @param {number} startX - Starting X coordinate
     * @param {number} startY - Starting Y coordinate
     */
    constructor(id, startX, startY) {
        this.id = id;
        this.startX = startX;
        this.startY = startY;
        this.color = AGENT_COLORS[id % AGENT_COLORS.length];
        this.tasks = [];         // Array of task objects
        this.plan = [];          // Array of {x, y, t} — full planned path
        this.originalPlan = [];  // Backup of initial plan for comparison
        this.status = AgentStatus.ACTIVE;
        this.planModified = false;
    }

    /**
     * Add a pickup-delivery task.
     * @param {number} pickupX
     * @param {number} pickupY
     * @param {number} deliveryX
     * @param {number} deliveryY
     */
    addTask(pickupX, pickupY, deliveryX, deliveryY) {
        this.tasks.push({
            pickupX, pickupY,
            deliveryX, deliveryY,
            status: TaskStatus.PENDING,
            id: this.tasks.length,
        });
    }

    /**
     * Get agent position at a given timestep.
     * If timestep exceeds plan length, returns last position.
     */
    getPositionAtTime(t) {
        if (this.plan.length === 0) {
            return { x: this.startX, y: this.startY };
        }
        if (t < 0) t = 0;
        if (t >= this.plan.length) {
            return { x: this.plan[this.plan.length - 1].x, y: this.plan[this.plan.length - 1].y };
        }
        return { x: this.plan[t].x, y: this.plan[t].y };
    }

    /**
     * Get remaining goals (pickup/delivery locations not yet visited).
     * Returns an ordered list of {x, y, type, taskIndex}.
     */
    getRemainingGoals(currentTime) {
        const goals = [];
        for (let i = 0; i < this.tasks.length; i++) {
            const task = this.tasks[i];
            if (task.status === TaskStatus.PENDING) {
                goals.push({ x: task.pickupX, y: task.pickupY, type: 'pickup', taskIndex: i });
                goals.push({ x: task.deliveryX, y: task.deliveryY, type: 'delivery', taskIndex: i });
            } else if (task.status === TaskStatus.PICKED_UP) {
                goals.push({ x: task.deliveryX, y: task.deliveryY, type: 'delivery', taskIndex: i });
            }
            // DELIVERED tasks are skipped
        }
        return goals;
    }

    /**
     * Update the agent's plan from a given time onwards.
     * Keeps the plan up to `fromTime` and replaces the rest.
     * @param {Array} newPlanSegment - New path segment [{x, y, t}, ...]
     * @param {number} fromTime - Time from which to replace
     */
    updatePlan(newPlanSegment, fromTime) {
        // Keep plan up to fromTime
        const keptPlan = this.plan.filter(step => step.t < fromTime);
        this.plan = keptPlan.concat(newPlanSegment);
        this.planModified = true;
    }

    /**
     * Set the complete plan for the agent.
     */
    setFullPlan(plan) {
        this.plan = plan.map(step => ({ ...step }));
        this.originalPlan = plan.map(step => ({ ...step }));
        this.planModified = false;
    }

    /**
     * Update task statuses based on current time and plan.
     * Called at each simulation step to check if agent has reached
     * pickup or delivery locations.
     */
    updateTaskStatus(currentTime) {
        if (this.status === AgentStatus.BROKEN) return;
        const pos = this.getPositionAtTime(currentTime);

        for (const task of this.tasks) {
            if (task.status === TaskStatus.PENDING) {
                if (pos.x === task.pickupX && pos.y === task.pickupY) {
                    task.status = TaskStatus.PICKED_UP;
                }
                break; // Tasks are sequential — wait for current task
            } else if (task.status === TaskStatus.PICKED_UP) {
                if (pos.x === task.deliveryX && pos.y === task.deliveryY) {
                    task.status = TaskStatus.DELIVERED;
                }
                break;
            }
        }

        // Check if all tasks are done
        if (this.tasks.every(t => t.status === TaskStatus.DELIVERED)) {
            this.status = AgentStatus.DONE;
        }
    }

    /**
     * Check if the agent has completed all tasks.
     */
    isFinished() {
        return this.status === AgentStatus.DONE;
    }

    /**
     * Get the makespan (last timestep in plan).
     */
    getMakespan() {
        if (this.plan.length === 0) return 0;
        return this.plan[this.plan.length - 1].t;
    }

    /**
     * Check if the agent's future path passes through (x, y) at or after time t.
     */
    pathPassesThrough(x, y, afterTime) {
        return this.plan.some(step => step.t >= afterTime && step.x === x && step.y === y);
    }

    /**
     * Reset agent to initial state.
     */
    reset() {
        this.plan = [];
        this.originalPlan = [];
        this.status = AgentStatus.ACTIVE;
        this.planModified = false;
        for (const task of this.tasks) {
            task.status = TaskStatus.PENDING;
        }
    }
}
