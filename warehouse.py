from dataclasses import dataclass, field
from typing import List, Tuple, Set

Position = Tuple[int, int]


@dataclass
class Task:
    pickup: Position
    delivery: Position


@dataclass
class Agent:
    agent_id: int
    start: Position
    task: Task
    path: List[Position] = field(default_factory=list)

    @property
    def pickup(self) -> Position:
        return self.task.pickup

    @property
    def delivery(self) -> Position:
        return self.task.delivery


class Warehouse:
    """
    2D grid warehouse.

    Coordinates:
        (row, column)

    Static obstacles never change during execution.
    Dynamic obstacles can be added/removed during simulation.
    """

    def __init__(
        self,
        rows: int,
        cols: int,
        static_obstacles: Set[Position] | None = None,
    ):
        self.rows = rows
        self.cols = cols
        self.static_obstacles = static_obstacles or set()
        self.dynamic_obstacles: Set[Position] = set()

    def in_bounds(self, position: Position) -> bool:
        r, c = position
        return 0 <= r < self.rows and 0 <= c < self.cols

    def is_blocked(self, position: Position) -> bool:
        return (
            position in self.static_obstacles
            or position in self.dynamic_obstacles
        )

    def is_free(self, position: Position) -> bool:
        return self.in_bounds(position) and not self.is_blocked(position)

    def add_dynamic_obstacle(self, position: Position) -> None:
        if not self.in_bounds(position):
            raise ValueError(f"Position {position} is outside the warehouse.")

        if position in self.static_obstacles:
            raise ValueError(
                f"Position {position} is already a static obstacle."
            )

        self.dynamic_obstacles.add(position)

    def remove_dynamic_obstacle(self, position: Position) -> None:
        self.dynamic_obstacles.discard(position)

    def neighbours(self, position: Position) -> List[Position]:
        """
        Return all valid neighbouring cells.

        WAIT is not included here because the planner handles
        waiting explicitly.
        """
        r, c = position

        candidates = [
            (r - 1, c),  # UP
            (r + 1, c),  # DOWN
            (r, c - 1),  # LEFT
            (r, c + 1),  # RIGHT
        ]

        return [
            cell
            for cell in candidates
            if self.is_free(cell)
        ]