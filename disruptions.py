"""
disruptions.py - Disruption Types and Generator

Defines different types of disruptions that can occur during simulation
and provides a generator to inject them at specified or random times.
"""

import random
from enum import Enum
from agent import Task


class DisruptionType(Enum):
    CELL_BLOCKAGE = "cell_blockage"
    AGENT_BREAKDOWN = "agent_breakdown"
    EMERGENCY_TASK = "emergency_task"


class Disruption:
    """Represents a single disruption event."""

    def __init__(self, disruption_type, time_step, **kwargs):
        """
        Args:
            disruption_type: DisruptionType enum value.
            time_step: When the disruption occurs.
            **kwargs: Type-specific parameters.
        """
        self.disruption_type = disruption_type
        self.time_step = time_step
        self.params = kwargs
        self.handled = False

    def __repr__(self):
        return f"Disruption({self.disruption_type.value}, t={self.time_step}, {self.params})"


class DisruptionGenerator:
    """Generates disruptions for simulation scenarios."""

    def __init__(self, grid, agents, seed=None):
        self.grid = grid
        self.agents = agents
        if seed is not None:
            random.seed(seed)

    def generate_cell_blockage(self, time_step, position=None):
        """
        Generate a cell blockage disruption.

        Args:
            time_step: When the blockage occurs.
            position: (x, y) of the blocked cell. Random if None.

        Returns:
            Disruption object.
        """
        if position is None:
            free_cells = self.grid.get_free_cells()
            # Avoid blocking agent start positions
            agent_positions = {a.position for a in self.agents}
            candidates = [c for c in free_cells if c not in agent_positions]
            if candidates:
                position = random.choice(candidates)
            else:
                return None

        return Disruption(
            DisruptionType.CELL_BLOCKAGE,
            time_step,
            position=position
        )

    def generate_agent_breakdown(self, time_step, agent_id=None):
        """
        Generate an agent breakdown disruption.

        Args:
            time_step: When the breakdown occurs.
            agent_id: ID of the agent that breaks down. Random if None.

        Returns:
            Disruption object.
        """
        if agent_id is None:
            active_agents = [a for a in self.agents
                           if a.status.value == "active" and not a.is_done()]
            if active_agents:
                agent_id = random.choice(active_agents).agent_id
            else:
                return None

        return Disruption(
            DisruptionType.AGENT_BREAKDOWN,
            time_step,
            agent_id=agent_id
        )

    def generate_emergency_task(self, time_step, agent_id=None, pickup=None, delivery=None):
        """
        Generate an emergency task disruption.

        Args:
            time_step: When the emergency task is assigned.
            agent_id: ID of the agent receiving the task. Random if None.
            pickup: (x, y) pickup location. Random if None.
            delivery: (x, y) delivery location. Random if None.

        Returns:
            Disruption object.
        """
        if agent_id is None:
            active_agents = [a for a in self.agents
                           if a.status.value == "active"]
            if active_agents:
                agent_id = random.choice(active_agents).agent_id
            else:
                return None

        free_cells = self.grid.get_free_cells()
        if pickup is None:
            pickup = random.choice(free_cells)
        if delivery is None:
            delivery = random.choice([c for c in free_cells if c != pickup])

        emergency_task = Task(
            pickup=pickup,
            delivery=delivery,
            priority=10,  # High priority
            task_id=f"emergency_{time_step}"
        )

        return Disruption(
            DisruptionType.EMERGENCY_TASK,
            time_step,
            agent_id=agent_id,
            task=emergency_task
        )

    def generate_random_disruptions(self, num_disruptions, time_range=(5, 50),
                                     types=None):
        """
        Generate a set of random disruptions.

        Args:
            num_disruptions: Number of disruptions to generate.
            time_range: (min_time, max_time) for disruption timing.
            types: List of DisruptionType values to choose from.

        Returns:
            List of Disruption objects sorted by time.
        """
        if types is None:
            types = [DisruptionType.CELL_BLOCKAGE, DisruptionType.AGENT_BREAKDOWN,
                     DisruptionType.EMERGENCY_TASK]

        disruptions = []
        for _ in range(num_disruptions):
            d_type = random.choice(types)
            t = random.randint(time_range[0], time_range[1])

            if d_type == DisruptionType.CELL_BLOCKAGE:
                d = self.generate_cell_blockage(t)
            elif d_type == DisruptionType.AGENT_BREAKDOWN:
                d = self.generate_agent_breakdown(t)
            else:
                d = self.generate_emergency_task(t)

            if d is not None:
                disruptions.append(d)

        disruptions.sort(key=lambda x: x.time_step)
        return disruptions
