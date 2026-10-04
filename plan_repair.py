"""
plan_repair.py - Plan Repair Algorithm

Implements local plan repair for handling dynamic disruptions without
re-invoking the full multi-agent planning algorithm from scratch.
Uses a windowed replanning approach with neighbor negotiation.
"""

from pathfinding import space_time_astar, plan_multi_target_path, manhattan_distance
from agent import AgentStatus


class PlanRepairResult:
    """Result of a plan repair operation."""

    def __init__(self):
        self.success = False
        self.agents_modified = []  # List of agent IDs whose plans were changed
        self.replanning_time_ms = 0
        self.description = ""


def find_affected_agents(agents, disruption_pos, current_time):
    """
    Identify agents whose future planned paths pass through the disrupted cell.

    Args:
        agents: List of Agent objects.
        disruption_pos: (x, y) position of the disruption.
        current_time: Current simulation time step.

    Returns:
        List of agents whose paths are affected.
    """
    affected = []
    for agent in agents:
        if agent.status == AgentStatus.BROKEN_DOWN:
            continue
        if agent.status == AgentStatus.FINISHED:
            continue

        # Check if the agent's future path passes through the disrupted cell
        for t in range(current_time, len(agent.path)):
            if agent.path[t] == disruption_pos:
                affected.append(agent)
                break

    return affected


def find_nearby_agents(agents, position, radius, exclude_ids=None):
    """
    Find agents within a certain radius of a position.

    Args:
        agents: List of Agent objects.
        position: (x, y) center position.
        radius: Search radius (Manhattan distance).
        exclude_ids: Set of agent IDs to exclude.

    Returns:
        List of nearby agents sorted by distance.
    """
    exclude_ids = exclude_ids or set()
    nearby = []
    for agent in agents:
        if agent.agent_id in exclude_ids:
            continue
        if agent.status == AgentStatus.BROKEN_DOWN:
            continue
        dist = manhattan_distance(agent.position, position)
        if dist <= radius:
            nearby.append((dist, agent))

    nearby.sort(key=lambda x: x[0])
    return [agent for _, agent in nearby]


def local_replan_agent(agent, grid, reservation_table, current_time, max_time=300):
    """
    Attempt to locally replan a single agent's path from its current position.

    Args:
        agent: The agent to replan for.
        grid: The warehouse Grid.
        reservation_table: Current reservation table.
        current_time: Current simulation time step.
        max_time: Maximum time horizon.

    Returns:
        New path segment (from current_time onwards) or None if failed.
    """
    targets = agent.get_remaining_targets()

    if not targets:
        return [agent.position]

    # Clear this agent's future reservations
    reservation_table.clear_agent_from_time(agent.agent_id, current_time)

    # Replan from current position
    new_path = plan_multi_target_path(
        grid, agent.position, targets, reservation_table, agent.agent_id,
        start_time=current_time, max_time=max_time
    )

    return new_path


def repair_plan_cell_blockage(grid, agents, reservation_table,
                              blocked_pos, current_time, max_time=300):
    """
    Repair plans when a cell becomes blocked.

    Strategy:
    1. Find directly affected agents (paths go through blocked cell).
    2. Try local replanning for each affected agent.
    3. If local replan fails, negotiate with nearby agents to yield space.

    Args:
        grid: The warehouse Grid.
        agents: List of all Agent objects.
        reservation_table: Current reservation table.
        blocked_pos: (x, y) of the newly blocked cell.
        current_time: Current simulation time step.
        max_time: Maximum planning time horizon.

    Returns:
        PlanRepairResult with details of the repair.
    """
    result = PlanRepairResult()

    # Add the dynamic obstacle to the grid
    grid.add_dynamic_obstacle(blocked_pos[0], blocked_pos[1], current_time)

    # Step 1: Find affected agents
    affected = find_affected_agents(agents, blocked_pos, current_time)

    if not affected:
        result.success = True
        result.description = "No agents affected by blockage."
        return result

    # Step 2: Try local replanning for each affected agent
    failed_agents = []
    for agent in affected:
        new_path = local_replan_agent(agent, grid, reservation_table, current_time, max_time)

        if new_path is not None:
            # Update the agent's path
            old_path_prefix = agent.path[:current_time]
            agent.path = old_path_prefix + new_path
            reservation_table.reserve_path(new_path, agent.agent_id, start_time=current_time)
            agent.plan_modified = True
            result.agents_modified.append(agent.agent_id)
        else:
            failed_agents.append(agent)

    # Step 3: If some agents failed, try negotiation with neighbors
    for agent in failed_agents:
        success = _negotiate_with_neighbors(
            agent, agents, grid, reservation_table, current_time, max_time
        )
        if success:
            agent.plan_modified = True
            result.agents_modified.append(agent.agent_id)
        else:
            # Last resort: agent waits at current position
            wait_path = [agent.position] * 10  # Wait for 10 steps
            agent.path = agent.path[:current_time] + wait_path
            reservation_table.reserve_path(wait_path, agent.agent_id, start_time=current_time)
            agent.plan_modified = True
            result.agents_modified.append(agent.agent_id)

    result.success = True
    result.description = f"Repaired {len(result.agents_modified)} agent plans for cell blockage at {blocked_pos}."
    return result


def repair_plan_agent_breakdown(grid, agents, reservation_table,
                                broken_agent_id, current_time, max_time=300):
    """
    Repair plans when an agent breaks down.

    The broken agent becomes a static obstacle. Nearby agents whose
    paths conflict with the broken agent's position must replan.

    Args:
        grid: The warehouse Grid.
        agents: List of all Agent objects.
        reservation_table: Current reservation table.
        broken_agent_id: ID of the broken agent.
        current_time: Current simulation time step.
        max_time: Maximum planning time horizon.

    Returns:
        PlanRepairResult.
    """
    result = PlanRepairResult()

    broken_agent = None
    for a in agents:
        if a.agent_id == broken_agent_id:
            broken_agent = a
            break

    if broken_agent is None:
        result.description = f"Agent {broken_agent_id} not found."
        return result

    # Mark agent as broken down
    broken_agent.breakdown()
    broken_pos = broken_agent.position

    # Clear the broken agent's future reservations and re-reserve as static
    reservation_table.clear_agent_from_time(broken_agent.agent_id, current_time)
    for t in range(current_time, current_time + max_time):
        reservation_table.reserve(broken_pos[0], broken_pos[1], t, broken_agent.agent_id)

    # Find agents affected by the breakdown
    affected = find_affected_agents(agents, broken_pos, current_time)

    # Remove the broken agent from affected list
    affected = [a for a in affected if a.agent_id != broken_agent_id]

    # Replan affected agents
    for agent in affected:
        new_path = local_replan_agent(agent, grid, reservation_table, current_time, max_time)

        if new_path is not None:
            old_path_prefix = agent.path[:current_time]
            agent.path = old_path_prefix + new_path
            reservation_table.reserve_path(new_path, agent.agent_id, start_time=current_time)
            agent.plan_modified = True
            result.agents_modified.append(agent.agent_id)
        else:
            # Negotiate with neighbors
            success = _negotiate_with_neighbors(
                agent, agents, grid, reservation_table, current_time, max_time
            )
            if success:
                agent.plan_modified = True
                result.agents_modified.append(agent.agent_id)

    result.success = True
    result.description = (f"Agent {broken_agent_id} broke down at {broken_pos}. "
                          f"Repaired {len(result.agents_modified)} agent plans.")
    return result


def repair_plan_emergency_task(grid, agents, reservation_table,
                               agent_id, emergency_task, current_time, max_time=300):
    """
    Repair plans when an agent receives a high-priority emergency task.

    The agent must abandon or postpone current tasks and handle
    the emergency task first.

    Args:
        grid: The warehouse Grid.
        agents: List of all Agent objects.
        reservation_table: Current reservation table.
        agent_id: ID of the agent receiving the emergency task.
        emergency_task: The emergency Task object.
        current_time: Current simulation time step.
        max_time: Maximum planning time horizon.

    Returns:
        PlanRepairResult.
    """
    result = PlanRepairResult()

    target_agent = None
    for a in agents:
        if a.agent_id == agent_id:
            target_agent = a
            break

    if target_agent is None:
        result.description = f"Agent {agent_id} not found."
        return result

    # Insert emergency task at the front of the task queue
    target_agent.tasks.insert(target_agent.current_task_index, emergency_task)
    target_agent.going_to_pickup = True
    target_agent._update_current_target()

    # Clear future reservations for this agent
    reservation_table.clear_agent_from_time(target_agent.agent_id, current_time)

    # Replan from current position with new task list
    targets = target_agent.get_remaining_targets()
    new_path = plan_multi_target_path(
        grid, target_agent.position, targets, reservation_table, target_agent.agent_id,
        start_time=current_time, max_time=max_time
    )

    if new_path is not None:
        old_path_prefix = target_agent.path[:current_time]
        target_agent.path = old_path_prefix + new_path
        reservation_table.reserve_path(new_path, target_agent.agent_id, start_time=current_time)
        target_agent.plan_modified = True
        result.agents_modified.append(target_agent.agent_id)

        # Check if the new path conflicts with other agents' future paths
        _resolve_new_conflicts(
            target_agent, agents, grid, reservation_table, current_time, max_time, result
        )
    else:
        # Try negotiation
        success = _negotiate_with_neighbors(
            target_agent, agents, grid, reservation_table, current_time, max_time
        )
        if success:
            target_agent.plan_modified = True
            result.agents_modified.append(target_agent.agent_id)

    result.success = True
    result.description = (f"Emergency task assigned to agent {agent_id}. "
                          f"Modified {len(result.agents_modified)} agent plans.")
    return result


def _negotiate_with_neighbors(agent, all_agents, grid, reservation_table,
                               current_time, max_time, radius=5):
    """
    Negotiate with nearby agents to find a viable path.

    Strategy: Ask nearby agents to yield (temporarily replan around)
    so the affected agent can find a path.

    Args:
        agent: The agent that needs a path.
        all_agents: List of all agents.
        grid: The warehouse Grid.
        reservation_table: Current reservation table.
        current_time: Current time step.
        max_time: Maximum time horizon.
        radius: Search radius for nearby agents.

    Returns:
        True if negotiation succeeded, False otherwise.
    """
    nearby = find_nearby_agents(
        all_agents, agent.position, radius,
        exclude_ids={agent.agent_id}
    )

    # Try removing each nearby agent's reservations one at a time
    # and see if the affected agent can find a path
    for neighbor in nearby:
        if neighbor.status == AgentStatus.BROKEN_DOWN:
            continue

        # Temporarily clear neighbor's future reservations
        saved_reservations = {}
        for key, val in list(reservation_table.cell_reservations.items()):
            if val == neighbor.agent_id and key[2] >= current_time:
                saved_reservations[key] = val

        reservation_table.clear_agent_from_time(neighbor.agent_id, current_time)

        # Try to replan the affected agent
        targets = agent.get_remaining_targets()
        new_path = plan_multi_target_path(
            grid, agent.position, targets, reservation_table, agent.agent_id,
            start_time=current_time, max_time=max_time
        )

        if new_path is not None:
            # Success! Now replan the neighbor too
            old_path_prefix = agent.path[:current_time]
            agent.path = old_path_prefix + new_path
            reservation_table.reserve_path(new_path, agent.agent_id, start_time=current_time)

            # Replan the neighbor around the affected agent's new path
            neighbor_targets = neighbor.get_remaining_targets()
            if neighbor_targets:
                neighbor_path = plan_multi_target_path(
                    grid, neighbor.position, neighbor_targets,
                    reservation_table, neighbor.agent_id,
                    start_time=current_time, max_time=max_time
                )
                if neighbor_path is not None:
                    old_prefix = neighbor.path[:current_time]
                    neighbor.path = old_prefix + neighbor_path
                    reservation_table.reserve_path(
                        neighbor_path, neighbor.agent_id, start_time=current_time
                    )
                    neighbor.plan_modified = True
                    return True

            # Restore neighbor's reservations if they couldn't replan
            for key, val in saved_reservations.items():
                reservation_table.cell_reservations[key] = val
            # Clear the affected agent's new path
            reservation_table.clear_agent_from_time(agent.agent_id, current_time)
        else:
            # Restore neighbor's reservations
            for key, val in saved_reservations.items():
                reservation_table.cell_reservations[key] = val

    return False


def _resolve_new_conflicts(agent, all_agents, grid, reservation_table,
                            current_time, max_time, result):
    """
    After replanning an agent, check if its new path conflicts with others
    and resolve those conflicts.
    """
    conflicting_agents = set()

    for t in range(current_time, len(agent.path)):
        pos = agent.path[t]
        reserved_agent = reservation_table.get_agent_at(pos[0], pos[1], t)
        if reserved_agent is not None and reserved_agent != agent.agent_id:
            conflicting_agents.add(reserved_agent)

    for conflict_id in conflicting_agents:
        conflict_agent = None
        for a in all_agents:
            if a.agent_id == conflict_id:
                conflict_agent = a
                break

        if conflict_agent is None:
            continue

        new_path = local_replan_agent(
            conflict_agent, grid, reservation_table, current_time, max_time
        )

        if new_path is not None:
            old_prefix = conflict_agent.path[:current_time]
            conflict_agent.path = old_prefix + new_path
            reservation_table.reserve_path(
                new_path, conflict_agent.agent_id, start_time=current_time
            )
            conflict_agent.plan_modified = True
            if conflict_agent.agent_id not in result.agents_modified:
                result.agents_modified.append(conflict_agent.agent_id)
