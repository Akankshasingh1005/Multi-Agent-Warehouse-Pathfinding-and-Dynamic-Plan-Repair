/**
 * Visualization Module.
 *
 * Renders the warehouse simulation on an HTML5 Canvas with:
 *   - Grid cells, obstacles, and dynamic blockages
 *   - Agents with color-coded paths
 *   - Pickup/delivery locations with visual markers
 *   - Smooth agent movement animation
 *   - Trail effects and path previews
 */

class Visualization {
    /**
     * @param {HTMLCanvasElement} canvas
     */
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.simulation = null;

        // Animation state
        this.animProgress = 0;       // 0.0 to 1.0 within each timestep
        this.animating = false;
        this.animSpeed = 400;        // ms per timestep
        this.animFrameId = null;
        this.lastFrameTime = 0;

        // Display options
        this.showPaths = true;
        this.showFuturePaths = true;
        this.showGrid = true;
        this.selectedAgent = null;

        // Interaction
        this.hoveredCell = null;
        this.cellSize = 30;
        this.offsetX = 0;
        this.offsetY = 0;

        // Particle effects
        this.particles = [];

        // Setup event listeners
        this._setupEvents();
    }

    /**
     * Link to a simulation instance.
     */
    setSimulation(sim) {
        this.simulation = sim;
        this._updateLayout();
    }

    /**
     * Recalculate cell size and offsets to fit canvas.
     */
    _updateLayout() {
        if (!this.simulation || !this.simulation.grid) return;

        const grid = this.simulation.grid;
        const padding = 20;
        const availW = this.canvas.width - 2 * padding;
        const availH = this.canvas.height - 2 * padding;

        this.cellSize = Math.floor(Math.min(availW / grid.width, availH / grid.height));
        this.offsetX = Math.floor((this.canvas.width - this.cellSize * grid.width) / 2);
        this.offsetY = Math.floor((this.canvas.height - this.cellSize * grid.height) / 2);
    }

    /**
     * Resize canvas to fit container.
     */
    resize(width, height) {
        this.canvas.width = width;
        this.canvas.height = height;
        this._updateLayout();
    }

    /**
     * Setup mouse event listeners for hover and click.
     */
    _setupEvents() {
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;

            const gx = Math.floor((mx - this.offsetX) / this.cellSize);
            const gy = Math.floor((my - this.offsetY) / this.cellSize);

            if (this.simulation && this.simulation.grid && this.simulation.grid.isInBounds(gx, gy)) {
                this.hoveredCell = { x: gx, y: gy };
            } else {
                this.hoveredCell = null;
            }
        });

        this.canvas.addEventListener('mouseleave', () => {
            this.hoveredCell = null;
        });
    }

    /**
     * Get grid coordinates from mouse event.
     */
    getGridCoords(e) {
        const rect = this.canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        return {
            x: Math.floor((mx - this.offsetX) / this.cellSize),
            y: Math.floor((my - this.offsetY) / this.cellSize),
        };
    }

    // ─── Drawing Methods ─────────────────────────────────────────

    /**
     * Full render of the current state.
     */
    render() {
        const ctx = this.ctx;
        const sim = this.simulation;
        if (!sim || !sim.grid) return;

        // Clear
        ctx.fillStyle = '#14171d';
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        this._drawGrid();
        this._drawObstacles();
        this._drawBlockedCells();
        this._drawTaskLocations();
        if (this.showPaths) this._drawPaths();
        if (this.showFuturePaths) this._drawFuturePaths();
        this._drawAgents();
        this._drawParticles();
        this._drawHoveredCell();
    }

    /**
     * Draw the grid lines.
     */
    _drawGrid() {
        const ctx = this.ctx;
        const grid = this.simulation.grid;

        for (let y = 0; y < grid.height; y++) {
            for (let x = 0; x < grid.width; x++) {
                const px = this.offsetX + x * this.cellSize;
                const py = this.offsetY + y * this.cellSize;

                // Cell background
                ctx.fillStyle = '#1a1e26';
                ctx.fillRect(px + 1, py + 1, this.cellSize - 2, this.cellSize - 2);

                // Cell border
                ctx.strokeStyle = '#2c3543';
                ctx.lineWidth = 0.5;
                ctx.strokeRect(px, py, this.cellSize, this.cellSize);
            }
        }
    }

    /**
     * Draw static obstacles.
     */
    _drawObstacles() {
        const ctx = this.ctx;
        const grid = this.simulation.grid;

        for (let y = 0; y < grid.height; y++) {
            for (let x = 0; x < grid.width; x++) {
                if (grid.cells[y][x] === 1) {
                    const px = this.offsetX + x * this.cellSize;
                    const py = this.offsetY + y * this.cellSize;

                    ctx.fillStyle = '#384152';
                    ctx.fillRect(px + 1, py + 1, this.cellSize - 2, this.cellSize - 2);

                    // Cross-hatch pattern
                    ctx.strokeStyle = '#222834';
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(px + 3, py + 3);
                    ctx.lineTo(px + this.cellSize - 3, py + this.cellSize - 3);
                    ctx.moveTo(px + this.cellSize - 3, py + 3);
                    ctx.lineTo(px + 3, py + this.cellSize - 3);
                    ctx.stroke();
                }
            }
        }
    }

    /**
     * Draw dynamically blocked cells with pulsing effect.
     */
    _drawBlockedCells() {
        const ctx = this.ctx;
        const grid = this.simulation.grid;

        for (const key of grid.blockedCells) {
            const [x, y] = key.split(',').map(Number);
            const px = this.offsetX + x * this.cellSize;
            const py = this.offsetY + y * this.cellSize;

            // Solid 2000s warning red
            ctx.fillStyle = '#cc0000';
            ctx.fillRect(px + 1, py + 1, this.cellSize - 2, this.cellSize - 2);

            // Bevel border
            ctx.strokeStyle = '#ff5555';
            ctx.lineWidth = 1;
            ctx.strokeRect(px + 1, py + 1, this.cellSize - 2, this.cellSize - 2);

            // Warning symbol - bold X in monospace
            ctx.fillStyle = '#ffffff';
            ctx.font = `bold ${Math.floor(this.cellSize * 0.55)}px Consolas, monospace`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('X', px + this.cellSize / 2, py + this.cellSize / 2);
        }
    }

    /**
     * Draw pickup and delivery locations for all agents.
     */
    _drawTaskLocations() {
        const ctx = this.ctx;
        const sim = this.simulation;

        for (const agent of sim.agents) {
            for (const task of agent.tasks) {
                const markerSize = this.cellSize * 0.35;

                // Pickup location (solid green diamond with black border)
                if (task.status === TaskStatus.PENDING) {
                    const px = this.offsetX + task.pickupX * this.cellSize + this.cellSize / 2;
                    const py = this.offsetY + task.pickupY * this.cellSize + this.cellSize / 2;

                    ctx.fillStyle = '#009900';
                    ctx.beginPath();
                    ctx.moveTo(px, py - markerSize);
                    ctx.lineTo(px + markerSize, py);
                    ctx.lineTo(px, py + markerSize);
                    ctx.lineTo(px - markerSize, py);
                    ctx.closePath();
                    ctx.fill();

                    ctx.strokeStyle = '#000000';
                    ctx.lineWidth = 1.5;
                    ctx.stroke();

                    // Label
                    ctx.fillStyle = '#ffffff';
                    ctx.font = `bold ${Math.floor(this.cellSize * 0.3)}px Consolas, monospace`;
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText('P', px, py);
                }

                // Delivery location (solid blue square with black border)
                if (task.status !== TaskStatus.DELIVERED) {
                    const dx = this.offsetX + task.deliveryX * this.cellSize + this.cellSize / 2;
                    const dy = this.offsetY + task.deliveryY * this.cellSize + this.cellSize / 2;

                    ctx.fillStyle = '#0055cc';
                    ctx.fillRect(dx - markerSize, dy - markerSize, markerSize * 2, markerSize * 2);

                    ctx.strokeStyle = '#000000';
                    ctx.lineWidth = 1.5;
                    ctx.strokeRect(dx - markerSize, dy - markerSize, markerSize * 2, markerSize * 2);

                    ctx.fillStyle = '#ffffff';
                    ctx.font = `bold ${Math.floor(this.cellSize * 0.3)}px Consolas, monospace`;
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText('D', dx, dy);
                }
            }
        }
    }

    /**
     * Draw completed path trails for each agent.
     */
    _drawPaths() {
        const ctx = this.ctx;
        const sim = this.simulation;
        const t = sim.currentTime;

        for (const agent of sim.agents) {
            if (agent.plan.length < 2) continue;

            ctx.strokeStyle = agent.color;
            ctx.globalAlpha = 0.7;
            ctx.lineWidth = 2;
            ctx.setLineDash([]);
            ctx.beginPath();

            let first = true;
            for (let i = 0; i < agent.plan.length && agent.plan[i].t <= t; i++) {
                const step = agent.plan[i];
                const px = this.offsetX + step.x * this.cellSize + this.cellSize / 2;
                const py = this.offsetY + step.y * this.cellSize + this.cellSize / 2;

                if (first) {
                    ctx.moveTo(px, py);
                    first = false;
                } else {
                    ctx.lineTo(px, py);
                }
            }
            ctx.stroke();
            ctx.globalAlpha = 1.0;
        }
    }

    /**
     * Draw future planned paths as dashed lines.
     */
    _drawFuturePaths() {
        const ctx = this.ctx;
        const sim = this.simulation;
        const t = sim.currentTime;

        for (const agent of sim.agents) {
            if (agent.status === AgentStatus.BROKEN) continue;
            if (agent.plan.length < 2) continue;

            ctx.strokeStyle = agent.color;
            ctx.globalAlpha = 0.35;
            ctx.lineWidth = 1.5;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();

            let first = true;
            for (const step of agent.plan) {
                if (step.t < t) continue;
                const px = this.offsetX + step.x * this.cellSize + this.cellSize / 2;
                const py = this.offsetY + step.y * this.cellSize + this.cellSize / 2;

                if (first) {
                    ctx.moveTo(px, py);
                    first = false;
                } else {
                    ctx.lineTo(px, py);
                }
            }
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.globalAlpha = 1.0;
        }
    }

    /**
     * Draw agent circles with smooth interpolation between timesteps.
     */
    _drawAgents() {
        const ctx = this.ctx;
        const sim = this.simulation;
        const t = sim.currentTime;
        const progress = this.animProgress;

        for (const agent of sim.agents) {
            const currPos = agent.getPositionAtTime(t);
            const nextPos = agent.getPositionAtTime(t + 1);

            // Interpolate position for smooth animation
            let drawX, drawY;
            if (this.animating && agent.status === AgentStatus.ACTIVE) {
                drawX = currPos.x + (nextPos.x - currPos.x) * progress;
                drawY = currPos.y + (nextPos.y - currPos.y) * progress;
            } else {
                drawX = currPos.x;
                drawY = currPos.y;
            }

            const px = this.offsetX + drawX * this.cellSize + this.cellSize / 2;
            const py = this.offsetY + drawY * this.cellSize + this.cellSize / 2;
            const radius = this.cellSize * 0.38;

            // Solid 2000s token - NO glow
            ctx.shadowBlur = 0;

            // Agent body
            ctx.beginPath();
            ctx.arc(px, py, radius, 0, Math.PI * 2);

            if (agent.status === AgentStatus.BROKEN) {
                ctx.fillStyle = '#555555';
            } else if (agent.status === AgentStatus.DONE) {
                ctx.fillStyle = '#006622';
            } else {
                ctx.fillStyle = agent.color;
            }
            ctx.fill();

            // 2000s beveled border (outer black, inner white ring)
            ctx.strokeStyle = '#000000';
            ctx.lineWidth = 2;
            ctx.stroke();

            ctx.beginPath();
            ctx.arc(px, py, radius - 2, 0, Math.PI * 2);
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 1;
            ctx.stroke();

            // Agent label (bold monospace ID)
            ctx.fillStyle = '#ffffff';
            ctx.font = `bold ${Math.floor(this.cellSize * 0.35)}px Consolas, monospace`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(agent.id.toString(), px, py);

            // Status indicator (classic 2000s text symbols: X, +, !)
            if (agent.status === AgentStatus.BROKEN) {
                ctx.fillStyle = '#ff2222';
                ctx.font = `bold ${Math.floor(this.cellSize * 0.42)}px Consolas, monospace`;
                ctx.fillText('X', px, py - radius - 6);
            } else if (agent.status === AgentStatus.DONE) {
                ctx.fillStyle = '#00ff66';
                ctx.font = `bold ${Math.floor(this.cellSize * 0.42)}px Consolas, monospace`;
                ctx.fillText('+', px, py - radius - 6);
            } else if (agent.planModified) {
                ctx.fillStyle = '#ffaa00';
                ctx.font = `bold ${Math.floor(this.cellSize * 0.38)}px Consolas, monospace`;
                ctx.fillText('!', px + radius + 4, py - radius - 2);
            }
        }
    }

    /**
     * Draw particle effects (for pickups and deliveries).
     */
    _drawParticles() {
        const ctx = this.ctx;
        const now = Date.now();

        this.particles = this.particles.filter(p => now - p.birth < p.lifetime);

        for (const p of this.particles) {
            const age = (now - p.birth) / p.lifetime;
            const alpha = 1 - age;
            const size = p.size * (1 - age * 0.5);

            // Retro solid square pixel sparks
            ctx.fillStyle = p.color;
            const px = p.x + p.vx * age * 25;
            const py = p.y + p.vy * age * 25 - age * 15;
            ctx.fillRect(px, py, 3, 3);
        }
    }

    /**
     * Spawn particles at a grid position.
     */
    spawnParticles(gx, gy, color, count = 8) {
        const px = this.offsetX + gx * this.cellSize + this.cellSize / 2;
        const py = this.offsetY + gy * this.cellSize + this.cellSize / 2;

        for (let i = 0; i < count; i++) {
            const angle = (Math.PI * 2 * i) / count + Math.random() * 0.5;
            this.particles.push({
                x: px,
                y: py,
                vx: Math.cos(angle) * (1 + Math.random()),
                vy: Math.sin(angle) * (1 + Math.random()),
                size: 2 + Math.random() * 3,
                color: color,
                birth: Date.now(),
                lifetime: 600 + Math.random() * 400,
            });
        }
    }

    /**
     * Draw hover highlight on the hovered cell.
     */
    _drawHoveredCell() {
        if (!this.hoveredCell) return;
        const ctx = this.ctx;
        const { x, y } = this.hoveredCell;

        const px = this.offsetX + x * this.cellSize;
        const py = this.offsetY + y * this.cellSize;

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.lineWidth = 2;
        ctx.strokeRect(px + 1, py + 1, this.cellSize - 2, this.cellSize - 2);
    }

    // ─── Animation Control ───────────────────────────────────────

    /**
     * Start the animation loop.
     */
    startAnimation(onTimestepComplete) {
        this.animating = true;
        this.animProgress = 0;
        this.lastFrameTime = performance.now();
        this._onTimestepComplete = onTimestepComplete;

        const loop = (timestamp) => {
            if (!this.animating) return;

            const dt = timestamp - this.lastFrameTime;
            this.lastFrameTime = timestamp;

            this.animProgress += dt / this.animSpeed;

            if (this.animProgress >= 1.0) {
                this.animProgress = 0;
                if (this._onTimestepComplete) {
                    const cont = this._onTimestepComplete();
                    if (!cont) {
                        this.animating = false;
                        this.render();
                        return;
                    }
                }
            }

            this.render();
            this.animFrameId = requestAnimationFrame(loop);
        };

        this.animFrameId = requestAnimationFrame(loop);
    }

    /**
     * Stop the animation loop.
     */
    stopAnimation() {
        this.animating = false;
        if (this.animFrameId) {
            cancelAnimationFrame(this.animFrameId);
            this.animFrameId = null;
        }
        this.animProgress = 0;
    }
}
