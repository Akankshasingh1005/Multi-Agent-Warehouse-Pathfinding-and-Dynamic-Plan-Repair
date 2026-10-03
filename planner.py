import heapq
from typing import Dict, List, Optional, Set, Tuple

from warehouse import Position, Warehouse


State = Tuple[int, int, int]
Path = List[Position]


class SpaceTimeAStar:
    """
    Space-Time A* planner.

    A state is:
        (row, column, time)

    The planner considers:
        - four movement actions
        - WAIT action

    Existing agent paths are represented using vertex and edge
    reservations to prevent collisions.
    """

    def __init__(self, warehouse: Warehouse):
        self.warehouse = warehouse

    @staticmethod
    def heuristic(a: Position, b: Position) -> int:
        """Manhattan distance."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def edge(
        from_position: Position,
        to_position: Position,
    ) -> Tuple[Position, Position]:
        return from_position, to_position

    def build_reservations(
        self,
        paths: List[Path],
    ) -> Tuple[Set[Tuple[Position, int]], Set[Tuple[Position, Position, int]]]:
        """
        Build vertex and edge reservations from existing paths.

        Vertex reservation:
            (position, time)

        Edge reservation:
            (from_position, to_position, time)

        An edge reservation at time t means an agent moves from
        from_position at t to to_position at t+1.
        """

        vertex_reservations: Set[Tuple[Position, int]] = set()
        edge_reservations: Set[
            Tuple[Position, Position, int]
        ] = set()

        for path in paths:
            for t, position in enumerate(path):
                vertex_reservations.add((position, t))

                if t + 1 < len(path):
                    next_position = path[t + 1]

                    edge_reservations.add(
                        (position, next_position, t)
                    )

        return vertex_reservations, edge_reservations

    def is_valid_transition(
        self,
        current: Position,
        next_position: Position,
        next_time: int,
        vertex_reservations: Set[Tuple[Position, int]],
        edge_reservations: Set[Tuple[Position, Position, int]],
    ) -> bool:
        """
        Check whether moving current -> next_position is safe.
        """

        # Cannot enter a blocked cell.
        if not self.warehouse.is_free(next_position):
            return False

        # Vertex collision.
        if (next_position, next_time) in vertex_reservations:
            return False

        # Edge collision / swap collision.

        # Another agent moves:
        # next_position -> current
        #
        # while we move:
        # current -> next_position
        if (
            next_position,
            current,
            next_time - 1,
        ) in edge_reservations:
            return False

        return True

    def search(
        self,
        start: Position,
        goal: Position,
        start_time: int = 0,
        reserved_paths: Optional[List[Path]] = None,
        max_time: int = 500,
    ) -> Optional[Path]:
        """
        Find a collision-free path from start to goal.

        Parameters
        ----------
        start:
            Starting grid position.

        goal:
            Goal grid position.

        start_time:
            Time at which the agent starts planning.

        reserved_paths:
            Paths of already planned agents.

        max_time:
            Maximum number of time steps searched.

        Returns
        -------
        Path or None
        """

        if not self.warehouse.is_free(start):
            return None

        if not self.warehouse.is_free(goal):
            return None

        reserved_paths = reserved_paths or []

        (
            vertex_reservations,
            edge_reservations,
        ) = self.build_reservations(reserved_paths)

        start_state: State = (
            start[0],
            start[1],
            start_time,
        )

        # Priority queue:
        # (f_score, g_score, state)
        open_set = []

        start_h = self.heuristic(start, goal)

        heapq.heappush(
            open_set,
            (start_h, 0, start_state),
        )

        came_from: Dict[State, Optional[State]] = {
            start_state: None
        }

        g_score: Dict[State, int] = {
            start_state: 0
        }

        visited = set()

        while open_set:
            _, current_g, current_state = heapq.heappop(open_set)

            if current_state in visited:
                continue

            visited.add(current_state)

            r, c, current_time = current_state
            current_position = (r, c)

            # Goal reached.
            if current_position == goal:
                return self.reconstruct_path(
                    current_state,
                    came_from,
                )

            if current_time >= start_time + max_time:
                continue

            next_time = current_time + 1

            # Four movement actions + WAIT.
            candidates = self.warehouse.neighbours(
                current_position
            )

            # WAIT is important for multi-agent coordination.
            candidates.append(current_position)

            for next_position in candidates:

                if not self.is_valid_transition(
                    current_position,
                    next_position,
                    next_time,
                    vertex_reservations,
                    edge_reservations,
                ):
                    continue

                next_state: State = (
                    next_position[0],
                    next_position[1],
                    next_time,
                )

                new_g = current_g + 1

                if (
                    next_state not in g_score
                    or new_g < g_score[next_state]
                ):
                    g_score[next_state] = new_g

                    h = self.heuristic(
                        next_position,
                        goal,
                    )

                    f = new_g + h

                    came_from[next_state] = current_state

                    heapq.heappush(
                        open_set,
                        (f, new_g, next_state),
                    )

        return None

    @staticmethod
    def reconstruct_path(
        state: State,
        came_from: Dict[State, Optional[State]],
    ) -> Path:
        """Reconstruct position-only path from the search tree."""

        path = []

        current = state

        while current is not None:
            r, c, _ = current
            path.append((r, c))
            current = came_from[current]

        path.reverse()

        return path