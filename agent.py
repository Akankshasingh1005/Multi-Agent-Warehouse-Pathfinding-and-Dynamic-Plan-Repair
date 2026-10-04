"""
agent.py - Robotic Agent

Represents a warehouse robot with tasks (pickup & delivery),
a planned path, and status tracking.
"""

from enum import Enum


class AgentStatus(Enum):
    ACTIVE = "active"
    BROKEN_DOWN = "broken_down"
    WAITING = "waiting"
    FINISHED = "finished"


class Task:
    """A pickup-and-delivery task for an agent."""

    def __init__(self, pickup, delivery, priority=0, task_id=None):
        """
        Args:
            pickup: (x, y) location to pick up the object.
            delivery: (x, y) location to deliver the object.
            priority: Higher values = higher priority.
            task_id: Unique identifier for this task.
        """
        self.pickup = pickup
        self.delivery = delivery
        self.priority = priority
        self.task_id = task_id
        self.picked_up = False
        self.delivered = False

    def __repr__(self):
        status = "delivered" if self.delivered else ("picked_up" if self.picked_up else "pending")
        return f"Task({self.pickup}->{self.delivery}, {status}, p={self.priority})"


class Agent:
    """A warehouse robotic agent."""

    def __init__(self, agent_id, start_pos, tasks=None):
        """
        Args:
            agent_id: Unique identifier for this agent.
            start_pos: (x, y) starting position on the grid.
            tasks: List of Task objects assigned to this agent.
        """
        self.agent_id = agent_id
        self.start_pos = start_pos
        self.position = start_pos  # Current position
        self.tasks = tasks if tasks is not None else []
        self.status = AgentStatus.ACTIVE

        # Path: list of (x, y) positions at each time step
        # path[t] = position at time step t
        self.path = [start_pos]
        self.original_path = None  # Store original for comparison

        # Track which task we're currently working on
        self.current_task_index = 0
        self.current_target = None  # Current navigation target
        self.going_to_pickup = True  # True = heading to pickup, False = heading to delivery

        # Metrics
        self.plan_modified = False
        self.total_wait_steps = 0

        self._update_current_target()

    def _update_current_target(self):
        """Update the current navigation target based on task progress."""
        if self.current_task_index >= len(self.tasks):
            self.current_target = None
            return

        task = self.tasks[self.current_task_index]
        if self.going_to_pickup and not task.picked_up:
            self.current_target = task.pickup
        elif not task.delivered:
            self.current_target = task.delivery
            self.going_to_pickup = False
        else:
            # Task is done, move to next
            self.current_task_index += 1
            self.going_to_pickup = True
            self._update_current_target()

    def get_remaining_targets(self):
        """
        Get the sequence of remaining targets the agent needs to visit.

        Returns:
            List of (x, y) positions: alternating pickup and delivery locations.
        """
        targets = []
        for i in range(self.current_task_index, len(self.tasks)):
            task = self.tasks[i]
            if i == self.current_task_index:
                if self.going_to_pickup and not task.picked_up:
                    targets.append(task.pickup)
                if not task.delivered:
                    targets.append(task.delivery)
            else:
                targets.append(task.pickup)
                targets.append(task.delivery)
        return targets

    def advance(self, time_step):
        """
        Advance the agent one time step along its planned path.

        Args:
            time_step: Current simulation time step.

        Returns:
            New position of the agent.
        """
        if self.status == AgentStatus.BROKEN_DOWN:
            return self.position

        if self.status == AgentStatus.FINISHED:
            return self.position

        if time_step < len(self.path):
            new_pos = self.path[time_step]
            if new_pos == self.position:
                self.total_wait_steps += 1
            self.position = new_pos
        # else: agent stays at last position in path

        # Check if we've reached current target
        self._check_target_reached()

        # Check if all tasks are done
        if self.current_task_index >= len(self.tasks):
            self.status = AgentStatus.FINISHED

        return self.position

    def _check_target_reached(self):
        """Check if the agent has reached its current target."""
        if self.current_target is None:
            return

        if self.position == self.current_target:
            if self.current_task_index < len(self.tasks):
                task = self.tasks[self.current_task_index]
                if self.going_to_pickup and not task.picked_up:
                    task.picked_up = True
                    self.going_to_pickup = False
                    self._update_current_target()
                elif not self.going_to_pickup and not task.delivered:
                    task.delivered = True
                    self.current_task_index += 1
                    self.going_to_pickup = True
                    self._update_current_target()

    def get_position_at(self, time_step):
        """Get the agent's planned position at a given time step."""
        if time_step < len(self.path):
            return self.path[time_step]
        elif len(self.path) > 0:
            return self.path[-1]
        return self.position

    def is_done(self):
        """Check if all tasks are completed."""
        return all(t.delivered for t in self.tasks)

    def breakdown(self):
        """Simulate agent breakdown."""
        self.status = AgentStatus.BROKEN_DOWN

    def repair(self):
        """Repair a broken-down agent."""
        self.status = AgentStatus.ACTIVE

    def save_original_path(self):
        """Save the current path as the original (before any repairs)."""
        self.original_path = list(self.path)

    def __repr__(self):
        return (f"Agent(id={self.agent_id}, pos={self.position}, "
                f"status={self.status.value}, tasks={len(self.tasks)}, "
                f"done={self.is_done()})")
