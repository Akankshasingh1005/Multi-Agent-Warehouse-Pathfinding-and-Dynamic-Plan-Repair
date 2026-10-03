/**
 * Space-Time A* pathfinding and Cooperative (Prioritized) Planning.
 *
 * Space-Time A* extends classical A* into the time dimension:
 *   - State: (x, y, t)
 *   - Actions: move up/down/left/right, or WAIT (stay in place)
 *   - Avoids vertex conflicts (two agents at same cell at same time)
 *   - Avoids edge/swap conflicts (two agents swapping positions)
 *
 * Cooperative pathfinding plans agents sequentially by priority.
 * Higher-priority agents plan first; lower-priority agents must
 * navigate around the reservations made by earlier agents.
 */

/**
 * Manhattan distance heuristic.
 */
function manhattan(a, b) {
    return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}

/**
 * Reservation Table: tracks which cells are occupied at which timesteps.
 * Key format: "x,y,t" → agentId
 */
class ReservationTable {
    constructor() {
        this.table = new Map();
    }

    /**
     * Reserve a cell at a specific time for an agent.
     */
    reserve(x, y, t, agentId) {
        this.table.set(`${x},${y},${t}`, agentId);
    }

    /**
     * Check if a cell is reserved at time t by a different agent.
     */
    isReserved(x, y, t, excludeAgentId = -1) {
        const key = `${x},${y},${t}`;
        if (!this.table.has(key)) return false;
        return this.table.get(key) !== excludeAgentId;
    }

    /**
     * Get the agent ID that reserved a cell at time t.
     */
    getReserver(x, y, t) {
        return this.table.get(`${x},${y},${t}`) ?? null;
    }

    /**
     * Remove all reservations for a specific agent after a given time.
     */
    removeAgentReservations(agentId, afterTime = 0) {
        const toRemove = [];
        for (const [key, id] of this.table) {
            if (id === agentId) {
                const parts = key.split(',');
                const t = parseInt(parts[2]);
                if (t >= afterTime) {
                    toRemove.push(key);
                }
            }
        }
        for (const key of toRemove) {
            this.table.delete(key);
        }
    }

    /**
     * Add reservations for an entire path.
     * Also reserves the final position for extra timesteps (goal parking).
     */
    reservePath(path, agentId, goalParkingSteps = 30) {
        for (const step of path) {
            this.reserve(step.x, step.y, step.t, agentId);
        }
        // Reserve goal position for extra steps to prevent future conflicts
        if (path.length > 0) {
            const last = path[path.length - 1];
            for (let dt = 1; dt <= goalParkingSteps; dt++) {
                this.reserve(last.x, last.y, last.t + dt, agentId);
            }
        }
    }

    /**
     * Check for swap/edge conflict: two agents swapping positions.
     */
    hasSwapConflict(fromX, fromY, toX, toY, t, excludeAgentId) {
        // Agent moves from (fromX, fromY) at t to (toX, toY) at t+1
        // Swap conflict if another agent is at (toX, toY) at t and
        // moves to (fromX, fromY) at t+1
        const agentAtDest = this.getReserver(toX, toY, t);
        if (agentAtDest !== null && agentAtDest !== excludeAgentId) {
            const agentAtOrigin = this.getReserver(fromX, fromY, t + 1);
            if (agentAtOrigin === agentAtDest) {
                return true; // Swap conflict detected
            }
        }
        return false;
    }

    /**
     * Clear all reservations.
     */
    clear() {
        this.table.clear();
    }

    /**
     * Clone the reservation table.
     */
    clone() {
        const copy = new ReservationTable();
        for (const [key, val] of this.table) {
            copy.table.set(key, val);
        }
        return copy;
    }
}

/**
 * Space-Time A* pathfinding algorithm.
 *
 * Finds a shortest path from start to goal in the space-time graph,
 * respecting the reservation table to avoid collisions.
 *
 * @param {Grid} grid - The warehouse grid
 * @param {{x,y}} start - Start position
 * @param {{x,y}} goal - Goal position
 * @param {number} startTime - Starting timestep
 * @param {ReservationTable} reservations - Current reservation table
 * @param {number} maxTime - Maximum time horizon
 * @param {number} agentId - ID of the planning agent
 * @returns {Array|null} Path as [{x, y, t}, ...] or null if no path found
 */
function spaceTimeAStar(grid, start, goal, startTime, reservations, maxTime, agentId) {
    const openSet = new PriorityQueue();
    const closedSet = new Set();
    const gScores = new Map();

    // 5 actions: wait, right, left, down, up
    const actions = [
        { dx: 0, dy: 0 },   // wait
        { dx: 1, dy: 0 },   // right
        { dx: -1, dy: 0 },  // left
        { dx: 0, dy: 1 },   // down
        { dx: 0, dy: -1 },  // up
    ];

    const startNode = {
        x: start.x,
        y: start.y,
        t: startTime,
        g: 0,
        h: manhattan(start, goal),
        parent: null,
    };
    startNode.f = startNode.g + startNode.h;

    const startKey = `${start.x},${start.y},${startTime}`;
    gScores.set(startKey, 0);
    openSet.push(startNode, startNode.f);

    let nodesExplored = 0;
    const MAX_NODES = 50000; // Safety limit

    while (!openSet.isEmpty()) {
        const current = openSet.pop();
        nodesExplored++;

        if (nodesExplored > MAX_NODES) {
            return null; // Search limit exceeded
        }

        // Goal reached
        if (current.x === goal.x && current.y === goal.y) {
            return _reconstructPath(current);
        }

        const currentKey = `${current.x},${current.y},${current.t}`;
        if (closedSet.has(currentKey)) continue;
        closedSet.add(currentKey);

        // Don't expand beyond time horizon
        if (current.t >= maxTime) continue;

        for (const action of actions) {
            const nx = current.x + action.dx;
            const ny = current.y + action.dy;
            const nt = current.t + 1;

            // Check grid bounds and walkability
            if (!grid.isWalkable(nx, ny)) continue;

            // Check vertex conflict: is (nx, ny) reserved at time nt?
            if (reservations.isReserved(nx, ny, nt, agentId)) continue;

            // Check edge/swap conflict
            if (action.dx !== 0 || action.dy !== 0) {
                if (reservations.hasSwapConflict(current.x, current.y, nx, ny, current.t, agentId)) {
                    continue;
                }
            }

            const neighborKey = `${nx},${ny},${nt}`;
            if (closedSet.has(neighborKey)) continue;

            const tentativeG = current.g + 1;
            const existingG = gScores.get(neighborKey);

            if (existingG !== undefined && tentativeG >= existingG) continue;

            gScores.set(neighborKey, tentativeG);
            const h = manhattan({ x: nx, y: ny }, goal);
            const neighbor = {
                x: nx,
                y: ny,
                t: nt,
                g: tentativeG,
                h: h,
                f: tentativeG + h,
                parent: current,
            };
            openSet.push(neighbor, neighbor.f);
        }
    }

    return null; // No path found
}

/**
 * Reconstruct path from goal node back to start.
 */
function _reconstructPath(node) {
    const path = [];
    let current = node;
    while (current !== null) {
        path.unshift({ x: current.x, y: current.y, t: current.t });
        current = current.parent;
    }
    return path;
}

/**
 * Plan a complete path for an agent through all its remaining goals.
 * Goals are visited sequentially: pickup1 → delivery1 → pickup2 → delivery2 → ...
 *
 * @param {Grid} grid
 * @param {Agent} agent
 * @param {{x,y}} currentPos - Agent's current position
 * @param {number} startTime - Current timestep
 * @param {ReservationTable} reservations
 * @param {number} maxTime
 * @returns {Array|null} Complete path or null if planning fails
 */
function planAgentFullPath(grid, agent, currentPos, startTime, reservations, maxTime) {
    const goals = agent.getRemainingGoals(startTime);
    if (goals.length === 0) return [{ x: currentPos.x, y: currentPos.y, t: startTime }];

    let fullPath = [];
    let pos = { x: currentPos.x, y: currentPos.y };
    let time = startTime;

    for (let i = 0; i < goals.length; i++) {
        const goal = goals[i];
        const segment = spaceTimeAStar(grid, pos, { x: goal.x, y: goal.y }, time, reservations, maxTime, agent.id);

        if (segment === null) {
            return null; // Cannot find path to this goal
        }

        // Concatenate segments (skip duplicate first element from segment 1+)
        if (fullPath.length > 0) {
            fullPath = fullPath.concat(segment.slice(1));
        } else {
            fullPath = segment;
        }

        // Temporarily reserve this segment so subsequent goals respect it
        for (const step of segment) {
            reservations.reserve(step.x, step.y, step.t, agent.id);
        }

        pos = { x: goal.x, y: goal.y };
        time = segment[segment.length - 1].t;
    }

    return fullPath;
}

/**
 * Cooperative Prioritized Planning.
 * Plans all agents sequentially — higher priority agents first.
 * Each agent must avoid cells reserved by previously planned agents.
 *
 * @param {Grid} grid
 * @param {Array<Agent>} agents
 * @param {number} maxTime - Time horizon
 * @returns {{success: boolean, reservations: ReservationTable, failedAgents: Array}}
 */
function cooperativePathfinding(grid, agents, maxTime = 200) {
    const reservations = new ReservationTable();
    const failedAgents = [];

    // Plan each agent in order of their ID (priority)
    for (const agent of agents) {
        if (agent.status === AgentStatus.BROKEN) continue;

        const startPos = { x: agent.startX, y: agent.startY };

        // Reserve start position at t=0
        // (will be overwritten by the full path reservation)

        const path = planAgentFullPath(grid, agent, startPos, 0, reservations, maxTime);

        if (path !== null) {
            agent.setFullPlan(path);
            // Reserve the full path including goal parking
            reservations.reservePath(path, agent.id, 30);
        } else {
            failedAgents.push(agent.id);
            // Agent gets a trivial plan (stay at start)
            agent.setFullPlan([{ x: agent.startX, y: agent.startY, t: 0 }]);
            reservations.reservePath(agent.plan, agent.id, maxTime);
        }
    }

    return {
        success: failedAgents.length === 0,
        reservations,
        failedAgents,
    };
}
