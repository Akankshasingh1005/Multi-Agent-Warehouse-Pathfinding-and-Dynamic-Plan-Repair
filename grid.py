"""
grid.py - Warehouse Grid Environment

Manages the 2D grid map for the warehouse simulation.
Supports static obstacles, dynamic blockages, and grid queries.
"""

import random
import copy


class Grid:
    """2D grid representing the warehouse floor."""

    def __init__(self, width, height, obstacle_density=0.2, seed=None):
        """
        Initialize the warehouse grid.

        Args:
            width: Number of columns in the grid.
            height: Number of rows in the grid.
            obstacle_density: Fraction of cells that are static obstacles.
            seed: Random seed for reproducibility.
        """
        self.width = width
        self.height = height
        self.obstacle_density = obstacle_density

        if seed is not None:
            random.seed(seed)

        # Static obstacles (walls, shelves, etc.) - set of (x, y)
        self.static_obstacles = set()
        # Dynamic obstacles (blockages that appear at runtime) - dict of (x,y) -> time_added
        self.dynamic_obstacles = {}

        self._generate_obstacles()

    def _generate_obstacles(self):
        """Generate static obstacles on the grid."""
        all_cells = [(x, y) for x in range(self.width) for y in range(self.height)]
        num_obstacles = int(len(all_cells) * self.obstacle_density)

        # Shuffle and pick obstacle cells
        random.shuffle(all_cells)
        for cell in all_cells[:num_obstacles]:
            self.static_obstacles.add(cell)

    def is_valid(self, x, y):
        """Check if a cell is within grid bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def is_free(self, x, y, time_step=None):
        """
        Check if a cell is free (not an obstacle).

        Args:
            x, y: Grid coordinates.
            time_step: If provided, also checks dynamic obstacles.
        """
        if not self.is_valid(x, y):
            return False
        if (x, y) in self.static_obstacles:
            return False
        if (x, y) in self.dynamic_obstacles:
            return True if time_step is not None and time_step < self.dynamic_obstacles[(x, y)] else (
                False if (x, y) in self.dynamic_obstacles else True
            )
        return True

    def is_blocked(self, x, y):
        """Check if a cell is blocked by any obstacle (static or dynamic)."""
        if not self.is_valid(x, y):
            return True
        if (x, y) in self.static_obstacles:
            return True
        if (x, y) in self.dynamic_obstacles:
            return True
        return False

    def add_dynamic_obstacle(self, x, y, time_step=0):
        """Add a dynamic obstacle (blockage) at the given cell."""
        self.dynamic_obstacles[(x, y)] = time_step

    def remove_dynamic_obstacle(self, x, y):
        """Remove a dynamic obstacle."""
        if (x, y) in self.dynamic_obstacles:
            del self.dynamic_obstacles[(x, y)]

    def get_neighbors(self, x, y):
        """
        Get valid neighboring cells (4-connected: up, down, left, right).
        Also includes the wait action (staying in place).

        Returns:
            List of (nx, ny) tuples for free neighboring cells + current cell.
        """
        neighbors = []
        # Wait action
        neighbors.append((x, y))
        # Cardinal directions
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if self.is_valid(nx, ny) and not self.is_blocked(nx, ny):
                neighbors.append((nx, ny))
        return neighbors

    def get_free_cells(self):
        """Get all currently free cells on the grid."""
        free = []
        for x in range(self.width):
            for y in range(self.height):
                if not self.is_blocked(x, y):
                    free.append((x, y))
        return free

    def clear_dynamic_obstacles(self):
        """Remove all dynamic obstacles."""
        self.dynamic_obstacles.clear()

    def copy(self):
        """Create a deep copy of the grid."""
        return copy.deepcopy(self)

    def __repr__(self):
        lines = []
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                if (x, y) in self.static_obstacles:
                    row += "█"
                elif (x, y) in self.dynamic_obstacles:
                    row += "X"
                else:
                    row += "."
            lines.append(row)
        return "\n".join(lines)
