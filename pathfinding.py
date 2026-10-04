"""
pathfinding.py - Space-Time A* and Multi-Agent Pathfinding

Implements Space-Time A* (STA*) for single-agent pathfinding in the
space-time graph, and Cooperative A* (CA*) for multi-agent planning
using a shared reservation table.
"""

import heapq
from collections import defaultdict


class ReservationTable:
    """
    Tracks which cells are reserved by which agents at each time step.
    Used to prevent collisions between agents.
    """

    def __init__(self):
        # (x, y, t) -> agent_id
        self.cell_reservations = {}
        # ((x1,y1,x2,y2), t) -> agent_id  (edge reservations to prevent swaps)
        self.edge_reservations = {}
        self.max_time = 0

    def reserve(self, x, y, t, agent_id):
        """Reserve a cell at a specific time step for an agent."""
        self.cell_reservations[(x, y, t)] = agent_id
        self.max_time = max(self.max_time, t)

    def reserve_edge(self, x1, y1, x2, y2, t, agent_id):
        """Reserve an edge (movement from (x1,y1) to (x2,y2)) at time t."""
        self.edge_reservations[((x1, y1, x2, y2), t)] = agent_id

    def is_reserved(self, x, y, t, exclude_agent=None):
        """Check if a cell is reserved at time t (optionally excluding an agent)."""
        key = (x, y, t)
        if key in self.cell_reservations:
            if exclude_agent is not None and self.cell_reservations[key] == exclude_agent:
                return False
            return True
        return False

    def is_edge_reserved(self, x1, y1, x2, y2, t, exclude_agent=None):
        """Check if an edge has a conflicting reservation (swap conflict)."""
        # Check if another agent is moving from (x2,y2) to (x1,y1) at time t
        swap_key = ((x2, y2, x1, y1), t)
        if swap_key in self.edge_reservations:
            if exclude_agent is not None and self.edge_reservations[swap_key] == exclude_agent:
                return False
            return True
        return False

    def reserve_path(self, path, agent_id, start_time=0):
        """Reserve all cells and edges along a path for an agent."""
        for i, (x, y) in enumerate(path):
            t = start_time + i
            self.reserve(x, y, t, agent_id)
            if i > 0:
                px, py = path[i - 1]
                self.reserve_edge(px, py, x, y, t, agent_id)

        # Reserve the final position for future time steps (agent stays there)
        if path:
            final_x, final_y = path[-1]
            final_t = start_time + len(path) - 1
            for t in range(final_t + 1, final_t + 50):  # Reserve for a window
                self.reserve(final_x, final_y, t, agent_id)

    def clear_agent(self, agent_id):
        """Remove all reservations for a specific agent."""
        to_remove = [k for k, v in self.cell_reservations.items() if v == agent_id]
        for k in to_remove:
            del self.cell_reservations[k]

        to_remove = [k for k, v in self.edge_reservations.items() if v == agent_id]
        for k in to_remove:
            del self.edge_reservations[k]

    def clear_agent_from_time(self, agent_id, from_time):
        """Remove reservations for an agent from a specific time onwards."""
        to_remove = [k for k, v in self.cell_reservations.items()
                     if v == agent_id and k[2] >= from_time]
        for k in to_remove:
            del self.cell_reservations[k]

        to_remove = [k for k, v in self.edge_reservations.items()
                     if v == agent_id and k[1] >= from_time]
        for k in to_remove:
            del self.edge_reservations[k]

    def get_agent_at(self, x, y, t):
        """Get the agent ID reserving a cell at time t, or None."""
        return self.cell_reservations.get((x, y, t), None)

    def copy(self):
        """Create a copy of the reservation table."""
        new_rt = ReservationTable()
        new_rt.cell_reservations = dict(self.cell_reservations)
        new_rt.edge_reservations = dict(self.edge_reservations)
        new_rt.max_time = self.max_time
        return new_rt


def manhattan_distance(pos1, pos2):
    """Calculate Manhattan distance between two positions."""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


def space_time_astar(grid, start, goal, reservation_table, agent_id,
                     start_time=0, max_time=200):
    """
    Space-Time A* pathfinding algorithm.

    Plans a path from start to goal in the space-time graph,
    avoiding reserved cells and edges.

    Args:
        grid: The warehouse Grid object.
        start: (x, y) starting position.
        goal: (x, y) goal position.
        reservation_table: ReservationTable with existing reservations.
        agent_id: ID of the agent being planned for.
        start_time: Time step at which planning begins.
        max_time: Maximum time horizon for planning.

    Returns:
        List of (x, y) positions representing the path, or None if no path found.
    """
    if start == goal:
        return [start]

    # Priority queue: (f_score, counter, x, y, t)
    counter = 0
    open_set = []
    heapq.heappush(open_set, (manhattan_distance(start, goal), counter, start[0], start[1], start_time))
    counter += 1

    # g_score[state] = cost from start to state
    g_score = {(start[0], start[1], start_time): 0}
    # came_from[state] = previous state
    came_from = {}

    closed_set = set()

    while open_set:
        f, _, x, y, t = heapq.heappop(open_set)

        state = (x, y, t)

        if state in closed_set:
            continue
        closed_set.add(state)

        # Goal check
        if (x, y) == goal:
            # Reconstruct path
            path = []
            current = state
            while current in came_from:
                path.append((current[0], current[1]))
                current = came_from[current]
            path.append((current[0], current[1]))
            path.reverse()
            return path

        if t >= start_time + max_time:
            continue

        # Expand neighbors (including wait action)
        neighbors = grid.get_neighbors(x, y)

        for nx, ny in neighbors:
            nt = t + 1

            # Check cell reservation
            if reservation_table.is_reserved(nx, ny, nt, exclude_agent=agent_id):
                continue

            # Check edge reservation (swap conflict)
            if (nx, ny) != (x, y):  # Not a wait action
                if reservation_table.is_edge_reserved(x, y, nx, ny, nt, exclude_agent=agent_id):
                    continue

            new_state = (nx, ny, nt)
            if new_state in closed_set:
                continue

            # Cost: 1 for each time step
            tentative_g = g_score[state] + 1

            if new_state not in g_score or tentative_g < g_score[new_state]:
                g_score[new_state] = tentative_g
                f_score = tentative_g + manhattan_distance((nx, ny), goal)
                came_from[new_state] = state
                heapq.heappush(open_set, (f_score, counter, nx, ny, nt))
                counter += 1

    return None  # No path found


def plan_multi_target_path(grid, start, targets, reservation_table, agent_id,
                           start_time=0, max_time=300):
    """
    Plan a path visiting multiple targets in sequence.
    Used when an agent has multiple pickup/delivery locations.

    Args:
        grid: The warehouse Grid object.
        start: (x, y) starting position.
        targets: List of (x, y) positions to visit in order.
        reservation_table: ReservationTable.
        agent_id: Agent ID.
        start_time: Starting time step.
        max_time: Max time per segment.

    Returns:
        Complete path as list of (x, y), or None if any segment fails.
    """
    if not targets:
        return [start]

    full_path = []
    current_pos = start
    current_time = start_time

    for target in targets:
        segment = space_time_astar(
            grid, current_pos, target, reservation_table, agent_id,
            start_time=current_time, max_time=max_time
        )

        if segment is None:
            return None

        if full_path:
            # Don't duplicate the junction point
            full_path.extend(segment[1:])
        else:
            full_path.extend(segment)

        current_pos = target
        current_time = start_time + len(full_path) - 1

    return full_path


def cooperative_astar(grid, agents, max_time=300):
    """
    Cooperative A* (CA*) multi-agent pathfinding.

    Plans paths for all agents sequentially. Each agent plans its
    path respecting the reservations of previously planned agents.

    Args:
        grid: The warehouse Grid object.
        agents: List of Agent objects.
        max_time: Maximum time horizon.

    Returns:
        ReservationTable with all reservations, and success status.
    """
    reservation_table = ReservationTable()
    success = True

    # Sort agents by priority (agents with more tasks go first for better planning)
    sorted_agents = sorted(agents, key=lambda a: -len(a.tasks))

    for agent in sorted_agents:
        if agent.status.value == "broken_down":
            # Broken agents are static obstacles
            for t in range(max_time):
                reservation_table.reserve(agent.position[0], agent.position[1], t, agent.agent_id)
            continue

        targets = agent.get_remaining_targets()

        if not targets:
            # Agent has no tasks, reserve its position
            for t in range(max_time):
                reservation_table.reserve(agent.position[0], agent.position[1], t, agent.agent_id)
            agent.path = [agent.position]
            continue

        path = plan_multi_target_path(
            grid, agent.position, targets, reservation_table, agent.agent_id,
            start_time=0, max_time=max_time
        )

        if path is not None:
            agent.path = path
            reservation_table.reserve_path(path, agent.agent_id, start_time=0)
        else:
            # Fallback: just stay in place
            agent.path = [agent.position]
            reservation_table.reserve_path(agent.path, agent.agent_id, start_time=0)
            success = False

    return reservation_table, success
