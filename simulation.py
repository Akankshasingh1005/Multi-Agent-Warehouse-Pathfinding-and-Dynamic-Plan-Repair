import csv
import os
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from warehouse import Agent, Position, Warehouse
from planner import SpaceTimeAStar
from repair import PlanRepair, RepairResult


@dataclass
class SimulationMetrics:
    makespan: int = 0
    aggregate_time: int = 0

    disruptions: int = 0
    successful_repairs: int = 0
    failed_repairs: int = 0

    total_changed_agents: int = 0
    repair_events: int = 0

    total_repair_time_ms: float = 0.0

    @property
    def average_changed_agents(self) -> float:
        if self.repair_events == 0:
            return 0.0

        return (
            self.total_changed_agents
            / self.repair_events
        )

    @property
    def average_repair_time_ms(self) -> float:
        if self.repair_events == 0:
            return 0.0

        return (
            self.total_repair_time_ms
            / self.repair_events
        )


class Simulator:
    """
    Executes agents on their planned trajectories.

    The simulator operates in discrete time.
    """

    def __init__(
        self,
        warehouse: Warehouse,
        agents: List[Agent],
        planner: SpaceTimeAStar,
        seed: int = 42,
    ):
        self.warehouse = warehouse
        self.agents = agents
        self.planner = planner

        self.rng = random.Random(seed)

        self.repairer = PlanRepair(
            warehouse=warehouse,
            planner=planner,
        )

        self.time = 0

        self.metrics = SimulationMetrics()

        self.completed_times: Dict[int, int] = {}

        self.repair_history: List[RepairResult] = []

    # -------------------------------------------------------------
    # Planning
    # -------------------------------------------------------------

    def generate_initial_plans(self) -> bool:
        """
        Generate initial prioritized MAPF plans.

        This is the ONLY stage where all agents are planned
        together sequentially.

        Plan repair will NOT call this function again.
        """

        reserved_paths = []

        for agent in self.agents:

            pickup_path = self.planner.search(
                start=agent.start,
                goal=agent.pickup,
                start_time=0,
                reserved_paths=reserved_paths,
            )

            if pickup_path is None:
                return False

            delivery_path = self.planner.search(
                start=agent.pickup,
                goal=agent.delivery,
                start_time=len(pickup_path) - 1,
                reserved_paths=reserved_paths,
            )

            if delivery_path is None:
                return False

            agent.path = (
                pickup_path[:-1]
                + delivery_path
            )

            reserved_paths.append(
                agent.path
            )

        return True

    # -------------------------------------------------------------
    # State
    # -------------------------------------------------------------

    def get_agent_position(
        self,
        agent: Agent,
    ) -> Position:

        if not agent.path:
            return agent.start

        index = min(
            self.time,
            len(agent.path) - 1,
        )

        return agent.path[index]

    def all_completed(self) -> bool:
        for agent in self.agents:

            if not agent.path:
                return False

            if self.time < len(agent.path) - 1:
                return False

        return True

    # -------------------------------------------------------------
    # Collision checking
    # -------------------------------------------------------------

    def detect_vertex_collisions(self) -> List[Tuple[int, int]]:

        positions = {}

        collisions = []

        for agent in self.agents:

            position = self.get_agent_position(agent)

            if position in positions:
                collisions.append(
                    (
                        positions[position],
                        agent.agent_id,
                    )
                )
            else:
                positions[position] = agent.agent_id

        return collisions

    def detect_edge_collisions(self) -> List[Tuple[int, int]]:

        collisions = []

        current_positions = {}
        previous_positions = {}

        for agent in self.agents:

            current_positions[agent.agent_id] = (
                self.get_agent_position(agent)
            )

            if self.time == 0:
                previous_positions[agent.agent_id] = (
                    self.get_agent_position(agent)
                )
            else:
                index = min(
                    self.time - 1,
                    len(agent.path) - 1,
                )

                previous_positions[agent.agent_id] = (
                    agent.path[index]
                )

        ids = [
            agent.agent_id
            for agent in self.agents
        ]

        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):

                a = ids[i]
                b = ids[j]

                if (
                    previous_positions[a]
                    == current_positions[b]
                    and
                    previous_positions[b]
                    == current_positions[a]
                ):
                    collisions.append((a, b))

        return collisions

    # -------------------------------------------------------------
    # Dynamic disruption
    # -------------------------------------------------------------

    def add_dynamic_obstacle(
        self,
        position: Position,
    ) -> Optional[RepairResult]:

        self.warehouse.add_dynamic_obstacle(
            position
        )

        self.metrics.disruptions += 1

        start = time.perf_counter()

        result = self.repairer.repair(
            agents=self.agents,
            disruption=position,
            current_time=self.time,
        )

        elapsed = (
            time.perf_counter() - start
        ) * 1000

        self.metrics.total_repair_time_ms += elapsed
        self.metrics.repair_events += 1

        self.metrics.total_changed_agents += (
            len(result.changed_agents)
        )

        if result.success:
            self.metrics.successful_repairs += 1
        else:
            self.metrics.failed_repairs += 1

        self.repair_history.append(result)

        return result

    # -------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------

    def step(self) -> None:

        # Check whether agents have reached their final goals.
        for agent in self.agents:

            if agent.agent_id in self.completed_times:
                continue

            if (
                agent.path
                and self.time >= len(agent.path) - 1
            ):
                self.completed_times[
                    agent.agent_id
                ] = self.time

        self.time += 1

    def run(
        self,
        max_steps: int = 1000,
        disruption_schedule: Optional[
            Dict[int, Position]
        ] = None,
    ) -> SimulationMetrics:

        disruption_schedule = (
            disruption_schedule or {}
        )

        while (
            not self.all_completed()
            and self.time < max_steps
        ):

            # Inject scheduled disruption.
            if self.time in disruption_schedule:

                position = disruption_schedule[
                    self.time
                ]

                self.add_dynamic_obstacle(
                    position
                )

            self.step()

        # Record completion times for agents that
        # finished at the final simulation step.
        for agent in self.agents:

            if agent.agent_id not in self.completed_times:
                self.completed_times[
                    agent.agent_id
                ] = self.time

        self.metrics.makespan = (
            max(self.completed_times.values())
            if self.completed_times
            else self.time
        )

        self.metrics.aggregate_time = sum(
            self.completed_times.values()
        )

        return self.metrics


# -----------------------------------------------------------------
# Experiment helpers
# -----------------------------------------------------------------

def save_metrics(
    rows: List[dict],
    filename: str = "results/metrics.csv",
) -> None:

    os.makedirs(
        os.path.dirname(filename),
        exist_ok=True,
    )

    if not rows:
        return

    fieldnames = list(rows[0].keys())

    with open(
        filename,
        "w",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)