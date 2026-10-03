from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from warehouse import Agent, Position, Warehouse
from planner import SpaceTimeAStar, Path


@dataclass
class RepairResult:
    success: bool
    changed_agents: List[int]
    old_paths: Dict[int, Path]
    new_paths: Dict[int, Path]
    disruption_time: int
    reason: str = ""


class PlanRepair:
    """
    Local plan-repair mechanism.

    The repair process does NOT invoke the complete multi-agent
    planner from scratch.

    Instead, it:
        1. Identifies affected agents.
        2. Attempts local repair.
        3. Negotiates with nearby agents if required.
        4. Selects the repair that minimizes changed agents.
    """

    def __init__(
        self,
        warehouse: Warehouse,
        planner: SpaceTimeAStar,
        communication_radius: int = 8,
        max_repair_time: int = 100,
    ):
        self.warehouse = warehouse
        self.planner = planner
        self.communication_radius = communication_radius
        self.max_repair_time = max_repair_time

    @staticmethod
    def manhattan(a: Position, b: Position) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def nearest_path_distance(
        self,
        agent: Agent,
        disruption: Position,
        current_time: int,
    ) -> int:
        """
        Minimum spatial distance between the disruption and
        the agent's future path.
        """

        if not agent.path:
            return 10**9

        future_path = agent.path[current_time:]

        if not future_path:
            return 10**9

        return min(
            self.manhattan(position, disruption)
            for position in future_path
        )

    def is_agent_affected(
        self,
        agent: Agent,
        disruption: Position,
        current_time: int,
    ) -> bool:
        """
        An agent is directly affected if its future trajectory
        contains the disrupted cell.
        """

        if not agent.path:
            return False

        future_path = agent.path[current_time:]

        return disruption in future_path

    def find_neighbours(
        self,
        affected_agent: Agent,
        agents: List[Agent],
        current_time: int,
    ) -> List[Agent]:
        """
        Find agents that are spatially close to the affected
        agent's future trajectory.
        """

        candidates = []

        if not affected_agent.path:
            return candidates

        future_path = affected_agent.path[current_time:]

        for other in agents:

            if other.agent_id == affected_agent.agent_id:
                continue

            if not other.path:
                continue

            other_future = other.path[current_time:]

            if not other_future:
                continue

            minimum_distance = min(
                self.manhattan(a, b)
                for a in future_path
                for b in other_future
            )

            if minimum_distance <= self.communication_radius:
                candidates.append(other)

        return candidates

    def _future_path(
        self,
        path: Path,
        current_time: int,
    ) -> Path:
        """
        Extract the path from current simulation time onward.
        """

        if current_time >= len(path):
            return [path[-1]]

        return path[current_time:]

    def _plan_from_current_position(
        self,
        agent: Agent,
        current_position: Position,
        current_time: int,
        reserved_paths: List[Path],
    ) -> Optional[Path]:

        """
        Replan only the remaining portion of one agent's task.

        If the agent has not reached pickup:
            current -> pickup -> delivery

        Otherwise:
            current -> delivery
        """

        # Determine whether pickup has already been reached.
        pickup_reached = (
            current_position == agent.pickup
            or (
                agent.path
                and current_position == agent.pickup
                and current_time > 0
            )
        )

        if not pickup_reached:
            pickup_path = self.planner.search(
                start=current_position,
                goal=agent.pickup,
                start_time=current_time,
                reserved_paths=reserved_paths,
                max_time=self.max_repair_time,
            )

            if pickup_path is None:
                return None

            delivery_path = self.planner.search(
                start=agent.pickup,
                goal=agent.delivery,
                start_time=current_time + len(pickup_path) - 1,
                reserved_paths=reserved_paths,
                max_time=self.max_repair_time,
            )

            if delivery_path is None:
                return None

            return pickup_path[:-1] + delivery_path

        delivery_path = self.planner.search(
            start=current_position,
            goal=agent.delivery,
            start_time=current_time,
            reserved_paths=reserved_paths,
            max_time=self.max_repair_time,
        )

        return delivery_path

    def _path_has_disruption(
        self,
        path: Path,
        disruption: Position,
        current_time: int,
    ) -> bool:
        return disruption in path[current_time:]

    def _calculate_delay(
        self,
        old_path: Path,
        new_path: Path,
        current_time: int,
    ) -> int:

        old_remaining = max(
            0,
            len(old_path) - current_time - 1
        )

        new_remaining = max(
            0,
            len(new_path) - current_time - 1
        )

        return max(0, new_remaining - old_remaining)

    def repair(
        self,
        agents: List[Agent],
        disruption: Position,
        current_time: int,
    ) -> RepairResult:

        old_paths = {
            agent.agent_id: list(agent.path)
            for agent in agents
        }

        # ---------------------------------------------------------
        # 1. Find directly affected agents.
        # ---------------------------------------------------------

        affected = [
            agent
            for agent in agents
            if self.is_agent_affected(
                agent,
                disruption,
                current_time,
            )
        ]

        if not affected:
            return RepairResult(
                success=True,
                changed_agents=[],
                old_paths=old_paths,
                new_paths={},
                disruption_time=current_time,
                reason="No agent is affected.",
            )

        # ---------------------------------------------------------
        # 2. We currently repair one primary affected agent.
        #    If several are affected, choose the nearest one.
        # ---------------------------------------------------------

        affected.sort(
            key=lambda agent: self.nearest_path_distance(
                agent,
                disruption,
                current_time,
            )
        )

        primary = affected[0]

        # ---------------------------------------------------------
        # 3. Identify neighbouring agents.
        # ---------------------------------------------------------

        neighbours = self.find_neighbours(
            primary,
            agents,
            current_time,
        )

        # ---------------------------------------------------------
        # 4. Try changing ONLY the primary agent.
        # ---------------------------------------------------------

        other_paths = [
            list(agent.path)
            for agent in agents
            if agent.agent_id != primary.agent_id
        ]

        current_position = primary.path[
            min(current_time, len(primary.path) - 1)
        ]

        repaired_path = self._plan_from_current_position(
            primary,
            current_position,
            current_time,
            other_paths,
        )

        if repaired_path is not None:

            if not self._path_has_disruption(
                repaired_path,
                disruption,
                current_time,
            ):
                primary.path = (
                    primary.path[:current_time]
                    + repaired_path
                )

                return RepairResult(
                    success=True,
                    changed_agents=[primary.agent_id],
                    old_paths=old_paths,
                    new_paths={
                        primary.agent_id: primary.path
                    },
                    disruption_time=current_time,
                    reason=(
                        "Single-agent local repair succeeded."
                    ),
                )

        # ---------------------------------------------------------
        # 5. Single-agent repair failed.
        #
        #    Negotiate with neighbouring agents.
        # ---------------------------------------------------------

        candidate_results = []

        for neighbour in neighbours:

            # Candidate: primary + neighbour are allowed to
            # modify their remaining trajectories.

            protected_paths = [
                list(agent.path)
                for agent in agents
                if agent.agent_id not in {
                    primary.agent_id,
                    neighbour.agent_id,
                }
            ]

            primary_position = primary.path[
                min(
                    current_time,
                    len(primary.path) - 1
                )
            ]

            # First modify the neighbour.
            neighbour_position = neighbour.path[
                min(
                    current_time,
                    len(neighbour.path) - 1
                )
            ]

            neighbour_repair = self._plan_from_current_position(
                neighbour,
                neighbour_position,
                current_time,
                protected_paths,
            )

            if neighbour_repair is None:
                continue

            temporary_paths = protected_paths + [
                neighbour_repair
            ]

            primary_repair = self._plan_from_current_position(
                primary,
                primary_position,
                current_time,
                temporary_paths,
            )

            if primary_repair is None:
                continue

            if self._path_has_disruption(
                primary_repair,
                disruption,
                current_time,
            ):
                continue

            candidate_results.append(
                (
                    2,
                    self._calculate_delay(
                        primary.path,
                        primary_repair,
                        current_time,
                    )
                    +
                    self._calculate_delay(
                        neighbour.path,
                        neighbour_repair,
                        current_time,
                    ),
                    len(primary_repair)
                    + len(neighbour_repair),
                    neighbour,
                    primary_repair,
                    neighbour_repair,
                )
            )

        # ---------------------------------------------------------
        # 6. Select best negotiated candidate.
        # ---------------------------------------------------------

        if candidate_results:

            candidate_results.sort(
                key=lambda x: (
                    x[0],
                    x[1],
                    x[2],
                )
            )

            (
                _,
                _,
                _,
                neighbour,
                primary_repair,
                neighbour_repair,
            ) = candidate_results[0]

            primary.path = (
                primary.path[:current_time]
                + primary_repair
            )

            neighbour.path = (
                neighbour.path[:current_time]
                + neighbour_repair
            )

            return RepairResult(
                success=True,
                changed_agents=[
                    primary.agent_id,
                    neighbour.agent_id,
                ],
                old_paths=old_paths,
                new_paths={
                    primary.agent_id: primary.path,
                    neighbour.agent_id: neighbour.path,
                },
                disruption_time=current_time,
                reason=(
                    "Two-agent negotiated local repair succeeded."
                ),
            )

        # ---------------------------------------------------------
        # 7. No local repair possible.
        # ---------------------------------------------------------

        return RepairResult(
            success=False,
            changed_agents=[],
            old_paths=old_paths,
            new_paths={},
            disruption_time=current_time,
            reason=(
                "No feasible local repair was found."
            ),
        )