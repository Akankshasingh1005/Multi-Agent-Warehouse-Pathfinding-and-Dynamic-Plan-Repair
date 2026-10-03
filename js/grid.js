/**
 * Grid class representing the 2D warehouse floor.
 * Manages static obstacles, dynamic blockages, and walkability queries.
 */
class Grid {
    /**
     * @param {number} width - Grid width (columns)
     * @param {number} height - Grid height (rows)
     */
    constructor(width, height) {
        this.width = width;
        this.height = height;
        // 0 = empty, 1 = static obstacle
        this.cells = Array.from({ length: height }, () => new Array(width).fill(0));
        // Dynamic blockages: Set of "x,y" strings
        this.blockedCells = new Set();
    }

    /**
     * Check if (x,y) is within grid bounds.
     */
    isInBounds(x, y) {
        return x >= 0 && x < this.width && y >= 0 && y < this.height;
    }

    /**
     * Check if (x,y) is walkable (in bounds, not obstacle, not blocked).
     */
    isWalkable(x, y) {
        if (!this.isInBounds(x, y)) return false;
        if (this.cells[y][x] === 1) return false;
        if (this.blockedCells.has(`${x},${y}`)) return false;
        return true;
    }

    /**
     * Add a static obstacle at (x,y).
     */
    addObstacle(x, y) {
        if (this.isInBounds(x, y)) {
            this.cells[y][x] = 1;
        }
    }

    /**
     * Remove a static obstacle at (x,y).
     */
    removeObstacle(x, y) {
        if (this.isInBounds(x, y)) {
            this.cells[y][x] = 0;
        }
    }

    /**
     * Dynamically block a cell (e.g., sudden obstruction).
     */
    blockCell(x, y) {
        if (this.isInBounds(x, y)) {
            this.blockedCells.add(`${x},${y}`);
        }
    }

    /**
     * Remove dynamic blockage from a cell.
     */
    unblockCell(x, y) {
        this.blockedCells.delete(`${x},${y}`);
    }

    /**
     * Get walkable neighbor cells of (x,y).
     * Returns array of {x, y} objects.
     */
    getNeighbors(x, y) {
        const neighbors = [];
        const dirs = [
            { dx: 1, dy: 0 },   // right
            { dx: -1, dy: 0 },  // left
            { dx: 0, dy: 1 },   // down
            { dx: 0, dy: -1 },  // up
        ];
        for (const d of dirs) {
            const nx = x + d.dx;
            const ny = y + d.dy;
            if (this.isWalkable(nx, ny)) {
                neighbors.push({ x: nx, y: ny });
            }
        }
        return neighbors;
    }

    /**
     * Generate random static obstacles with given density.
     * @param {number} density - Fraction of cells to be obstacles (0 to 1)
     * @param {Array} excludePositions - Array of {x,y} to exclude from obstacles
     */
    generateRandomObstacles(density, excludePositions = []) {
        // Clear existing obstacles
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                this.cells[y][x] = 0;
            }
        }

        const excludeSet = new Set(excludePositions.map(p => `${p.x},${p.y}`));
        const totalCells = this.width * this.height;
        const numObstacles = Math.floor(totalCells * density);
        let placed = 0;

        // Random placement with connectivity check
        const candidates = [];
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                if (!excludeSet.has(`${x},${y}`)) {
                    candidates.push({ x, y });
                }
            }
        }

        // Shuffle candidates
        for (let i = candidates.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [candidates[i], candidates[j]] = [candidates[j], candidates[i]];
        }

        for (const pos of candidates) {
            if (placed >= numObstacles) break;
            this.cells[pos.y][pos.x] = 1;
            // Verify connectivity of free cells with BFS
            if (this._isConnected(excludePositions)) {
                placed++;
            } else {
                // Undo if it breaks connectivity
                this.cells[pos.y][pos.x] = 0;
            }
        }
    }

    /**
     * Check if all positions in the list are connected via walkable cells.
     * Uses BFS from the first position.
     */
    _isConnected(positions) {
        if (positions.length <= 1) return true;

        const freeCells = positions.filter(p => this.isWalkable(p.x, p.y));
        if (freeCells.length === 0) return false;

        const visited = new Set();
        const queue = [freeCells[0]];
        visited.add(`${freeCells[0].x},${freeCells[0].y}`);

        while (queue.length > 0) {
            const curr = queue.shift();
            const dirs = [
                { dx: 1, dy: 0 }, { dx: -1, dy: 0 },
                { dx: 0, dy: 1 }, { dx: 0, dy: -1 },
            ];
            for (const d of dirs) {
                const nx = curr.x + d.dx;
                const ny = curr.y + d.dy;
                const key = `${nx},${ny}`;
                if (this.isWalkable(nx, ny) && !visited.has(key)) {
                    visited.add(key);
                    queue.push({ x: nx, y: ny });
                }
            }
        }

        // Check all required positions are reachable
        return freeCells.every(p => visited.has(`${p.x},${p.y}`));
    }

    /**
     * Get a random free cell (not obstacle, not blocked, not in exclude set).
     */
    getRandomFreeCell(excludeSet = new Set()) {
        const freeCells = [];
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                if (this.isWalkable(x, y) && !excludeSet.has(`${x},${y}`)) {
                    freeCells.push({ x, y });
                }
            }
        }
        if (freeCells.length === 0) return null;
        return freeCells[Math.floor(Math.random() * freeCells.length)];
    }

    /**
     * Create a deep copy of the grid.
     */
    clone() {
        const copy = new Grid(this.width, this.height);
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                copy.cells[y][x] = this.cells[y][x];
            }
        }
        for (const key of this.blockedCells) {
            copy.blockedCells.add(key);
        }
        return copy;
    }
}
