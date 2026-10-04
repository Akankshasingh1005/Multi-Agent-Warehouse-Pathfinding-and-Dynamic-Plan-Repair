/**
 * Main Application Controller.
 *
 * Binds UI elements, manages simulation lifecycle,
 * handles user interactions, and runs benchmarks.
 */

// ─── Global State ────────────────────────────────────────────

let sim = null;
let vis = null;
let chart1 = null;
let chart2 = null;
let isPlaying = false;
let stepIntervalId = null;
let blockageMode = false;

// ─── Initialization ──────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // Setup canvas
    const canvas = document.getElementById('simCanvas');
    vis = new Visualization(canvas);

    // Chart canvases (if present)
    const chart1El = document.getElementById('chart1');
    const chart2El = document.getElementById('chart2');
    if (chart1El && typeof SimpleChart !== 'undefined') {
        chart1 = new SimpleChart(chart1El);
    }
    if (chart2El && typeof SimpleChart !== 'undefined') {
        chart2 = new SimpleChart(chart2El);
    }

    // Resize canvas to fit container
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    const container = document.getElementById('canvasContainer');
    if (window.ResizeObserver && container) {
        new ResizeObserver(() => resizeCanvas()).observe(container);
    }

    // Bind controls
    document.getElementById('btnGenerate').addEventListener('click', generateScenario);
    document.getElementById('btnStart').addEventListener('click', startSimulation);
    document.getElementById('btnPause').addEventListener('click', pauseSimulation);
    document.getElementById('btnStep').addEventListener('click', stepOnce);
    document.getElementById('btnReset').addEventListener('click', resetSimulation);

    // Disruption buttons
    document.getElementById('btnBlockCell').addEventListener('click', () => {
        if (!sim) return;
        blockageMode = !blockageMode;
        const btn = document.getElementById('btnBlockCell');
        if (blockageMode) {
            btn.classList.add('active');
            btn.textContent = '[ CLICK GRID TO BLOCK ]';
            addLog('Click on a grid cell to block it.', 'info');
        } else {
            btn.classList.remove('active');
            btn.textContent = 'BLOCK CELL';
        }
    });

    document.getElementById('btnBreakAgent').addEventListener('click', () => {
        if (!sim || sim.currentTime === 0) { addLog('Start simulation first.', 'warning'); return; }
        const result = sim.triggerRandomBreakdown();
        if (result) {
            addLog(`Agent breakdown! ${result.modifiedCount} plan(s) modified.`, 'disruption');
            updateMetricsPanel();
            vis.render();
        } else {
            addLog('No active agents to break down.', 'warning');
        }
    });

    document.getElementById('btnEmergency').addEventListener('click', () => {
        if (!sim || sim.currentTime === 0) { addLog('Start simulation first.', 'warning'); return; }
        const result = sim.triggerRandomEmergency();
        if (result) {
            addLog(`Emergency task assigned! ${result.modifiedCount} plan(s) modified.`, 'disruption');
            updateMetricsPanel();
            vis.render();
        } else {
            addLog('No active agents available.', 'warning');
        }
    });

    document.getElementById('btnRandomDisruption').addEventListener('click', () => {
        if (!sim || sim.currentTime === 0) { addLog('Start simulation first.', 'warning'); return; }
        const result = sim.triggerRandomDisruption();
        if (result) {
            addLog(`Random disruption! ${result.modifiedCount} plan(s) modified.`, 'disruption');
            updateMetricsPanel();
            vis.render();
        }
    });

    const btnBenchmark = document.getElementById('btnRunBenchmark');
    if (btnBenchmark) {
        btnBenchmark.addEventListener('click', runBenchmark);
    }

    // Canvas click for cell blockage
    canvas.addEventListener('click', (e) => {
        if (!blockageMode || !sim || !vis) return;
        if (sim.currentTime === 0) { addLog('Start simulation first.', 'warning'); return; }

        const coords = vis.getGridCoords(e);
        if (sim.grid.isInBounds(coords.x, coords.y) && sim.grid.isWalkable(coords.x, coords.y)) {
            const result = sim.triggerDisruption({
                type: DisruptionType.CELL_BLOCKAGE,
                x: coords.x,
                y: coords.y,
            });
            addLog(`Cell (${coords.x},${coords.y}) blocked! ${result.modifiedCount} plan(s) modified.`, 'disruption');
            updateMetricsPanel();
            vis.render();

            // Exit blockage mode
            blockageMode = false;
            const btn = document.getElementById('btnBlockCell');
            btn.classList.remove('active');
            btn.textContent = 'BLOCK CELL';
        }
    });

    // Speed control
    document.getElementById('speedSlider').addEventListener('input', (e) => {
        const speed = parseInt(e.target.value);
        if (vis) vis.animSpeed = 600 - speed; // Invert: higher slider = faster
        document.getElementById('speedValue').textContent = `${speed}`;
    });

    // Auto-generate on load
    generateScenario();
});

// ─── Canvas Resize ───────────────────────────────────────────

function resizeCanvas() {
    const container = document.getElementById('canvasContainer');
    const canvas = document.getElementById('simCanvas');
    if (!container || !canvas) return;
    if (container.clientWidth > 0 && container.clientHeight > 0) {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        if (vis) {
            vis.resize(canvas.width, canvas.height);
            vis.render();
        }
    }
}

// ─── Scenario Generation ─────────────────────────────────────

function generateScenario() {
    pauseSimulation();

    const config = {
        gridWidth: parseInt(document.getElementById('gridWidth').value) || 20,
        gridHeight: parseInt(document.getElementById('gridHeight').value) || 20,
        numAgents: parseInt(document.getElementById('numAgents').value) || 5,
        obstacleDensity: parseInt(document.getElementById('obstacleDensity').value) / 100 || 0.15,
        tasksPerAgent: parseInt(document.getElementById('tasksPerAgent').value) || 2,
        maxTime: 300,
    };

    sim = new Simulation(config);
    sim.initialize();
    vis.setSimulation(sim);
    vis.render();

    // Clear log
    document.getElementById('logContainer').innerHTML = '';
    addLog(`Scenario generated: ${config.numAgents} agents, ${config.gridWidth}×${config.gridHeight} grid, ${(config.obstacleDensity * 100).toFixed(0)}% obstacles`, 'info');
    addLog(`Initial makespan: ${sim.metrics.initialMakespan} timesteps`, 'info');

    updateMetricsPanel();
    updateAgentList();
}

// ─── Simulation Control ──────────────────────────────────────

function startSimulation() {
    if (!sim) { addLog('Generate a scenario first.', 'warning'); return; }
    if (sim.isFinished) { addLog('Simulation finished. Reset to restart.', 'warning'); return; }

    isPlaying = true;
    document.getElementById('btnStart').disabled = true;
    document.getElementById('btnPause').disabled = false;

    vis.startAnimation(() => {
        const cont = sim.step();
        updateMetricsPanel();
        updateAgentList();

        if (!cont) {
            isPlaying = false;
            document.getElementById('btnStart').disabled = false;
            document.getElementById('btnPause').disabled = true;
            addLog(`Simulation finished at timestep ${sim.currentTime}`, 'success');
            updateMetricsPanel();
        }
        return cont;
    });
}

function pauseSimulation() {
    isPlaying = false;
    if (vis) vis.stopAnimation();
    document.getElementById('btnStart').disabled = false;
    document.getElementById('btnPause').disabled = true;
    if (vis && sim) vis.render();
}

function stepOnce() {
    if (!sim) { addLog('Generate a scenario first.', 'warning'); return; }
    if (sim.isFinished) return;

    pauseSimulation();
    sim.step();
    vis.render();
    updateMetricsPanel();
    updateAgentList();

    if (sim.isFinished) {
        addLog(`Simulation finished at timestep ${sim.currentTime}`, 'success');
    }
}

function resetSimulation() {
    pauseSimulation();
    generateScenario();
}

// ─── UI Updates ──────────────────────────────────────────────

function updateMetricsPanel() {
    if (!sim) return;
    const m = sim.getMetrics();

    document.getElementById('metricTime').textContent = m.currentTime;
    document.getElementById('metricMakespan').textContent = m.currentMakespan;
    document.getElementById('metricInitMakespan').textContent = m.initialMakespan;
    document.getElementById('metricDisruptions').textContent = m.totalDisruptions;
    document.getElementById('metricModified').textContent = m.uniqueAgentsModified;
    document.getElementById('metricAvgModified').textContent = m.avgModifiedPerDisruption;
}

function updateAgentList() {
    if (!sim) return;
    const container = document.getElementById('agentList');
    container.innerHTML = '';

    for (const agent of sim.agents) {
        const pos = agent.getPositionAtTime(sim.currentTime);
        const completed = agent.tasks.filter(t => t.status === TaskStatus.DELIVERED).length;
        const total = agent.tasks.length;

        const div = document.createElement('div');
        div.className = `agent-item ${agent.status}`;
        div.innerHTML = `
            <span class="agent-dot" style="background:${agent.color}"></span>
            <span class="agent-id">Agent ${agent.id}</span>
            <span class="agent-status-badge ${agent.status}">${agent.status}</span>
            <span class="agent-tasks">${completed}/${total} tasks</span>
            ${agent.planModified ? '<span class="modified-badge">[MODIFIED]</span>' : ''}
        `;
        container.appendChild(div);
    }
}

function addLog(message, type = 'info') {
    const container = document.getElementById('logContainer');
    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;

    const time = sim ? `[t=${sim.currentTime}]` : '[--]';
    entry.innerHTML = `<span class="log-time">${time}</span> ${message}`;

    container.insertBefore(entry, container.firstChild);

    // Limit log entries
    while (container.children.length > 50) {
        container.removeChild(container.lastChild);
    }
}

// ─── Benchmark ───────────────────────────────────────────────

async function runBenchmark() {
    addLog('Running benchmark... This may take a moment.', 'info');
    document.getElementById('btnRunBenchmark').disabled = true;

    // Use setTimeout to allow UI to update
    await new Promise(r => setTimeout(r, 100));

    const results = {
        agentCounts: [],
        makespanByAgents: [],
        modifiedByAgents: [],
        densities: [],
        makespanByDensity: [],
        modifiedByDensity: [],
    };

    // --- Benchmark 1: Varying number of agents ---
    const agentCounts = [3, 5, 8, 10, 12];
    const trialsPerConfig = 3;

    for (const numAgents of agentCounts) {
        let totalMakespan = 0;
        let totalModified = 0;
        let validTrials = 0;

        for (let trial = 0; trial < trialsPerConfig; trial++) {
            try {
                const testSim = new Simulation({
                    gridWidth: 15,
                    gridHeight: 15,
                    numAgents: numAgents,
                    obstacleDensity: 0.1,
                    tasksPerAgent: 2,
                    maxTime: 250,
                });
                testSim.initialize();

                // Run to midpoint, then trigger a disruption
                const midpoint = Math.floor(testSim.metrics.initialMakespan / 3);
                for (let t = 0; t < midpoint && !testSim.isFinished; t++) {
                    testSim.step();
                }

                if (!testSim.isFinished) {
                    const result = testSim.triggerRandomBlockage();
                    if (result) {
                        totalModified += result.modifiedCount;
                    }
                }

                // Run to completion
                while (!testSim.isFinished) {
                    testSim.step();
                }

                totalMakespan += testSim.currentTime;
                validTrials++;
            } catch (e) {
                console.warn(`Benchmark trial failed:`, e);
            }
        }

        results.agentCounts.push(numAgents);
        results.makespanByAgents.push(validTrials > 0 ? totalMakespan / validTrials : 0);
        results.modifiedByAgents.push(validTrials > 0 ? totalModified / validTrials : 0);
    }

    // --- Benchmark 2: Varying obstacle density ---
    const densities = [5, 10, 15, 20, 25];

    for (const density of densities) {
        let totalMakespan = 0;
        let totalModified = 0;
        let validTrials = 0;

        for (let trial = 0; trial < trialsPerConfig; trial++) {
            try {
                const testSim = new Simulation({
                    gridWidth: 15,
                    gridHeight: 15,
                    numAgents: 5,
                    obstacleDensity: density / 100,
                    tasksPerAgent: 2,
                    maxTime: 300,
                });
                testSim.initialize();

                const midpoint = Math.floor(testSim.metrics.initialMakespan / 3);
                for (let t = 0; t < midpoint && !testSim.isFinished; t++) {
                    testSim.step();
                }

                if (!testSim.isFinished) {
                    const result = testSim.triggerRandomBlockage();
                    if (result) {
                        totalModified += result.modifiedCount;
                    }
                }

                while (!testSim.isFinished) {
                    testSim.step();
                }

                totalMakespan += testSim.currentTime;
                validTrials++;
            } catch (e) {
                console.warn(`Benchmark trial failed:`, e);
            }
        }

        results.densities.push(density);
        results.makespanByDensity.push(validTrials > 0 ? totalMakespan / validTrials : 0);
        results.modifiedByDensity.push(validTrials > 0 ? totalModified / validTrials : 0);
    }

    // --- Draw Charts ---

    chart1.drawLineChart({
        labels: results.agentCounts,
        series: [
            { name: 'Makespan', values: results.makespanByAgents, color: '#06b6d4' },
            { name: 'Plans Modified', values: results.modifiedByAgents, color: '#f59e0b' },
        ],
        title: 'Performance vs Number of Agents',
        xLabel: 'Number of Agents',
        yLabel: 'Value',
    });

    chart2.drawLineChart({
        labels: results.densities,
        series: [
            { name: 'Makespan', values: results.makespanByDensity, color: '#ec4899' },
            { name: 'Plans Modified', values: results.modifiedByDensity, color: '#84cc16' },
        ],
        title: 'Performance vs Obstacle Density (%)',
        xLabel: 'Obstacle Density (%)',
        yLabel: 'Value',
    });

    document.getElementById('btnRunBenchmark').disabled = false;
    addLog('Benchmark complete! See charts below.', 'success');

    // Show benchmark summary
    const summaryDiv = document.getElementById('benchmarkSummary');
    summaryDiv.innerHTML = `
        <h4>Benchmark Results Summary</h4>
        <table>
            <tr><th>Agents</th><th>Avg Makespan</th><th>Avg Plans Modified</th></tr>
            ${results.agentCounts.map((n, i) => `
                <tr>
                    <td>${n}</td>
                    <td>${results.makespanByAgents[i].toFixed(1)}</td>
                    <td>${results.modifiedByAgents[i].toFixed(2)}</td>
                </tr>
            `).join('')}
        </table>
        <table>
            <tr><th>Density (%)</th><th>Avg Makespan</th><th>Avg Plans Modified</th></tr>
            ${results.densities.map((d, i) => `
                <tr>
                    <td>${d}%</td>
                    <td>${results.makespanByDensity[i].toFixed(1)}</td>
                    <td>${results.modifiedByDensity[i].toFixed(2)}</td>
                </tr>
            `).join('')}
        </table>
    `;
}
