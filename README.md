# Multi-Agent Warehouse Pathfinding & Dynamic Plan Repair

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![HTML5 / Canvas](https://img.shields.io/badge/Web_GUI-HTML5_Canvas-E34F26?style=flat-square&logo=html5&logoColor=white)](index.html)
[![LaTeX](https://img.shields.io/badge/Report-LaTeX_Ready-008080?style=flat-square&logo=latex&logoColor=white)](report.tex)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

An academic and industrial-grade simulation of an **Automated Robotic Warehouse** operating on a 2D discrete grid. Robotic agents execute sequential pickup-and-delivery tasks using **Space-Time A<sup>*</sup> (STA\*)** with **Cooperative A<sup>*</sup> (CA\*)** collision avoidance. 

The system incorporates a decentralized **Local Plan Repair with Neighbor Negotiation** algorithm that handles runtime contingencies (cell blockages, robot breakdowns, and emergency orders) **without re-invoking the planner from scratch**, minimizing fleet plan modifications (&Delta;<sub>mod</sub> &lt; 1.0 on average).

---

## Visual Demos

### 1. Interactive Web Dashboard (Real-Time Simulation & Telemetry)
![Interactive Web Dashboard](results/web_gui_dashboard.png)
*The Web GUI displays color-coded robot trajectories, emerald green pickup diamonds (`P`), amber delivery squares (`D`), static storage shelves, and dynamic red blockages (`X`), accompanied by real-time analytics and controls.*

---

### 2. Animated Simulation Run
<p align="center">
  <img src="results/simulation.gif" alt="Simulation Animation" width="750px"/>
</p>
Multi-agent coordinated execution: robots collect parcels from pickup diamonds, navigate around storage racks, and transport payloads to delivery squares while dynamically recalculating paths when disruptions occur.

---

## Table of Contents
- [Key Features](#-key-features)
- [Architecture & Repository Structure](#-architecture--repository-structure)
- [Core Algorithms](#-core-algorithms)
  - [Space-Time A* (STA*)](#1-space-time-a-sta)
  - [Cooperative A* (CA*) with 3D Reservation Table](#2-cooperative-a-ca-with-3d-reservation-table)
  - [Local Plan Repair & Neighbor Negotiation](#3-local-plan-repair--neighbor-negotiation)
- [Dynamic Disruption Modalities](#-dynamic-disruption-modalities)
- [Experimental Benchmarks & Results](#-experimental-benchmarks--results)
- [Failure Analysis: Environmental Settings Where Agents Fail](#️-failure-analysis-environmental-settings-where-agents-fail)
- [Installation & Setup](#-installation--setup)
- [Quick Start Guide](#-quick-start-guide)
  - [1. Launch Interactive Web GUI](#1-interactive-browser-gui-recommended)
  - [2. Run Python Simulation & Pygame](#2-python-simulation--cli)
  - [3. Run Systematic Experiments](#3-run-benchmark-experiments)
- [Compiling the Academic Report (LaTeX)](#-compiling-the-academic-report-latex)
- [References](#-references)

---

## Key Features

* **3D Space-Time Pathfinding:** Complete avoidance of vertex collisions (cell sharing) and edge collisions (swapping transitions).
* **Multi-Target Pickup & Delivery:** Robots sequentially visit designated pickup stations and transport packages to fulfillment drop-offs.
* **Localized Plan Modification:** Contingencies are resolved by isolating affected agents, replanning only future path segments, and leaving untouched robots on their optimal schedules.
* **Peer-to-Peer Neighbor Negotiation:** When direct replanning is constrained, proximal agents within a 5-cell radius negotiate reservation concessions, yielding alternative escape corridors.
* **Dual Interface:**
  * **High-Performance Web GUI:** Zero-dependency HTML5 Canvas interface with playback controls, speed slider, live metrics, and manual disruption injection.
  * **Python Suite:** Matplotlib visualizer, GIF exporter, Pygame GUI, and automated Monte Carlo benchmark runner.

---

## Architecture & Repository Structure

```
Autonomous_System_Assignment1/
├── index.html            # Interactive Web GUI dashboard
├── css/
│   └── style.css         # Modern dark-mode styling and UI layout
├── js/
│   ├── agent.js          # JavaScript Agent class & task state machine
│   ├── grid.js           # 2D discrete grid & obstacle representation
│   ├── pathfinding.js    # Space-Time A* & Cooperative A* in JS
│   ├── planRepair.js     # Client-side local repair & neighbor negotiation
│   ├── simulation.js     # Real-time simulation controller & metrics
│   ├── visualization.js  # Canvas rendering (agents, diamonds, squares, paths)
│   ├── priorityQueue.js  # Min-heap priority queue implementation
│   ├── charts.js         # Canvas performance line and bar charts
│   └── app.js            # UI event bindings, sliders, and telemetry loop
├── main.py               # Python entry point with CLI parameters
├── grid.py               # Warehouse grid representation and static/dynamic obstacles
├── agent.py              # Robot agent kinematics, status tracking, and tasks
├── pathfinding.py        # Python Space-Time A* & 3D Reservation Table
├── plan_repair.py        # Local repair, affected agent isolation, and negotiation
├── disruptions.py        # Disruption generators (blockages, breakdowns, emergencies)
├── simulation.py         # Headless/steppable simulation orchestrator
├── visualization.py      # Pygame live visualizer & Matplotlib snapshot/GIF generator
├── experiments.py        # Automated Monte Carlo experiment runner & chart generator
├── report.tex            # Academic publication-ready LaTeX report
├── context.md            # In-depth file-by-file code architectural documentation
├── requirements.txt      # Python dependencies
└── results/              # Empirical plots, snapshots, and recordings
    ├── snapshot_t0.png
    ├── web_gui_dashboard.png
    ├── simulation.gif
    ├── exp1_vary_agents.png
    ├── exp2_vary_obstacles.png
    ├── exp3_disruption_types.png
    └── exp4_vary_disruptions.png
```

---

## Core Algorithms

### 1. Space-Time A<sup>*</sup> (STA\*)
Traditional A<sup>*</sup> plans across a spatial 2D grid (x, y). Space-Time A<sup>*</sup> expands search to the 3D space-time graph (x, y, t):
* **State Representation:** (x, y, t) where t ∈ [0, T<sub>max</sub>].
* **Actions:** Move {North, South, East, West} or Wait in place (cost = 1).
* **Heuristic:** Admissible Manhattan distance to the active target:
  h(x, y) = |x - x<sub>g</sub>| + |y - y<sub>g</sub>|
* **Evaluation Function:** f(x, y, t) = g(x, y, t) + h(x, y), where g(x, y, t) = t - t<sub>start</sub>.

### 2. Cooperative A<sup>*</sup> (CA\*) with 3D Reservation Table
Agents are planned sequentially in priority order. Avoidance is enforced via a global **3D Reservation Table** ℛ:
1. **Vertex Collision Constraint:** ℛ<sub>vertex</sub>(x, y, t) = ∅ (no two agents share a cell at time t).
2. **Edge Collision Constraint (Swapping):** ℛ<sub>edge</sub>((x', y'), (x, y), t) = ∅ (agents cannot cross the same edge in opposite directions at t → t+1).

### 3. Local Plan Repair & Neighbor Negotiation
When an unexpected disruption occurs at time t<sub>disrupt</sub>:
```
Disruption Occurs (Blockage, Breakdown, Emergency)
               │
               ▼
[Phase 1: Affected Agent Isolation]
Identify agents whose future path intersects the disrupted cell.
               │
      Is an agent affected?
      ├── No  ──► Maintain all current plans intact (0 plans modified).
      └── Yes ──► Clear ONLY that agent's future reservations in R.
                     │
                     ▼
          [Direct Local Replanning]
          Attempt Space-Time A* from current (x, y) to pending targets.
                     │
            Success? ├── Yes ──► Reserve new path in R (1 plan modified).
                     └── No
                          │
                          ▼
            [Phase 2: Neighbor Negotiation]
            Query nearby agents within Manhattan radius R <= 5.
            Candidate neighbor temporarily yields reservations.
            Affected agent attempts replanning in the freed corridor.
                          │
                 Both find paths?
                 ├── Yes ──► Commit exchange (<= 2 plans modified).
                 └── No  ──► Revert neighbor's reservations; query next neighbor.
                          │
                          ▼
            [Phase 3: Bounded Safe Waiting]
            If all fail, agent pauses in place for tau = 10 steps
            until moving congestion clears, then re-attempts STA*.
```

---

## Dynamic Disruption Modalities

| Disruption Type | Real-World Scenario | System Reaction |
|---|---|---|
| **Cell Blockage** | Dropped box, spill, or structural closure. | Cell (x, y) marked impassable. Intersecting robots locally reroute around the obstacle. |
| **Agent Breakdown** | Motor failure, depleted battery, hardware fault. | Broken agent freezes indefinitely; its final cell is reserved permanently as a static obstacle. |
| **Emergency Task** | Rush priority order or safety inspection. | Selected agent's current plan is preempted. Emergency pickup-delivery is inserted at the front of its task queue. |

---

## Experimental Benchmarks & Results

Empirical results obtained from systematic Monte Carlo trials (20 × 20 grid, 5 trials per configuration):

### Benchmark 1: Scalability vs. Number of Agents (N ∈ [2, 10])
![Experiment 1: Varying Agents](results/exp1_vary_agents.png)

| Agents (N) | Total Time Steps (Makespan) | Agents Modified / Disruption (Δ<sub>mod</sub>) | Task Completion Rate |
|:---:|:---:|:---:|:---:|
| **2** | 94.2 ± 66.8 | **0.40 ± 0.38** | 100% |
| **3** | 136.6 ± 133.5 | **0.33 ± 0.39** | 100% |
| **4** | 82.6 ± 11.7 | **0.53 ± 0.39** | 100% |
| **5** | 70.8 ± 12.3 | **0.27 ± 0.27** | 100% |
| **6** | 142.0 ± 129.5 | **0.60 ± 0.28** | 100% |
| **8** | 335.4 ± 129.2 | **0.93 ± 0.38** | 80% |
| **10** | 208.0 ± 156.8 | **0.80 ± 0.52** | 80% |

> **Key Finding:** Across all fleet sizes, the average number of altered plans per disruption remains **strictly below 1.0** (Δ<sub>mod</sub> ≤ 0.93). Compared to global replanning where all N agents must be recalculated, our localized negotiation yields an **>88% reduction in fleet plan disruptions**.

---

### Benchmark 2: Sensitivity to Obstacle Density (ρ ∈ [5%, 30%])
![Experiment 2: Varying Obstacle Density](results/exp2_vary_obstacles.png)

| Obstacle Density (ρ) | Total Time Steps | Agents Modified / Disruption | Initial Planning Runtime |
|:---:|:---:|:---:|:---:|
| **5%** | 142.2 ± 130.3 | 0.50 ± 0.37 | 3.4 ms |
| **10%** | 74.2 ± 17.5 | 0.27 ± 0.27 | 3.8 ms |
| **15%** | 77.0 ± 21.0 | 0.53 ± 0.39 | 4.2 ms |
| **20%** | 138.8 ± 131.2 | 0.53 ± 0.39 | 4.9 ms |
| **25%** | 280.2 ± 153.9 | 0.60 ± 0.44 | 5.6 ms |
| **30%** | 270.0 ± 159.2 | 0.23 ± 0.21 | 6.8 ms |

---

### Benchmark 3: Disruption Category Comparison
![Experiment 3: Disruption Types](results/exp3_disruption_types.png)

| Disruption Type | Total Time Steps | Agents Modified / Disruption | Impact Profile |
|:---|:---:|:---:|:---|
| **Cell Blockage** | 134.0 ± 133.0 | **0.20 ± 0.24** | Localized corridor detour |
| **Agent Breakdown** | 60.8 ± 11.2 | **0.50 ± 0.29** | Single permanent obstacle; workload halts |
| **Emergency Task** | 305.0 ± 134.1 | **1.00 ± 0.00** | High-priority preemption and dispatch |
| **Mixed (All 3)** | 74.2 ± 17.5 | **0.27 ± 0.27** | Composite realistic warehouse setting |

---

### Benchmark 4: Stress Testing Across Disruption Counts
![Experiment 4: Disruption Counts](results/exp4_vary_disruptions.png)

| Disruption Count | Total Time Steps | Cumulative Agents Modified |
|:---:|:---:|:---:|
| **0** | 69.0 ± 6.8 | 0.0 ± 0.0 |
| **1** | 77.2 ± 16.3 | 0.6 ± 0.5 |
| **3** | 74.2 ± 17.5 | 0.8 ± 0.8 |
| **5** | 159.2 ± 131.0 | 2.2 ± 1.2 |
| **10** | 148.0 ± 127.3 | 4.0 ± 1.4 |

---

## Failure Analysis: Environmental Settings Where Agents Fail

A rigorous evaluation of autonomous multi-agent systems requires isolating specific environmental settings and operational conditions under which pathfinding and dynamic plan repair **fail to complete assigned tasks** (or trigger simulation timeouts).

While the system reliably achieves a **100% completion rate** under moderate densities (N ≤ 6, ρ ≤ 20%), empirical stress testing reveals **four primary failure regimes**:

| Environmental Setting / Parameter | Physical Scenario | Algorithmic Failure Cause | Observable Impact | Architectural Remedy |
|---|---|---|---|---|
| **1. Dense Fleets in Narrow Corridors**<br>• N ≥ 8 agents on 20 × 20 grid<br>• Corridor width w = 1 cell | Two opposing robots enter a 1-tile wide aisle between static shelf racks. | **Symmetrical Head-to-Head Deadlock:** Neither agent can advance. Local peer negotiation fails because neither agent has a lateral escape cell without executing multi-step reverse egress. Both robots cycle into Phase 3 bounded wait states (τ<sub>wait</sub> = 10). | Completion rate drops to **80%** (Table 1); robots exceed the T<sub>max</sub> = 400 step horizon without finishing. | • Unidirectional flow corridors<br>• Periodic lateral pull-out alcoves<br>• Multi-step reverse evacuation protocol |
| **2. High Static Obstacle Density**<br>• ρ ≥ 25% - 30% static racks<br>• Choke points & articulation nodes | A dynamic cell blockage or breakdown occurs at a topological bridge (cut-vertex) on the grid. | **Topological Graph Disconnection:** The failure severs the grid graph into disconnected components (G → G₁ ∪ G₂). If an agent is in G₁ and its target is in G₂, Space-Time A* returns `FAIL` because no spatial path exists. | Robot freezes in place; task remains permanently uncompleted. | • Graph biconnectivity validation before placing blockages<br>• Redundant wide transit corridors |
| **3. Terminal Station Breakdowns**<br>• Agent breakdown on target tile<br>• Single-access pickup/delivery cells | An agent experiences a hardware breakdown directly on or in front of a pickup diamond (`P`) or delivery square (`D`). | **Target Cell Inaccessibility:** The disabled robot permanently blocks the goal tile. Any active agent assigned to collect or drop off parcels at that station can never satisfy the destination arrival condition (h(x, y) = 0). | Affected agent waits indefinitely; trial never reaches 100% mission completion. | • Multi-tile perimeter access for stations<br>• Dynamic task re-dispatch to alternate functional stations |
| **4. Compounding Disruption Cascades**<br>• High disruption frequency (k ≥ 7 events)<br>• Clustered arrival intervals | Multiple unexpected contingencies occur across tight spatial and temporal intervals. | **Time Horizon Expiry (t ≥ T<sub>max</sub>):** Although local rerouting succeeds geometrically, successive Phase 3 wait buffers (τ<sub>wait</sub> = 10) accumulate large execution delays, pushing total execution time past the hard cutoff (T<sub>max</sub> = 400). | Agents are functional and moving toward targets, but fail to finish before the global deadline expires. | • Dynamic deadline-aware priority boost<br>• Adaptive wait intervals based on remaining time budget |

### In-Depth Breakdown of Failure Mechanics

#### 1. Symmetrical Deadlocks in Single-Cell Aisles

In grid layouts with 1-cell wide aisles, cooperative space-time reservation prevents collisions by reserving future states (x, y, t). However, when an unexpected disruption forces an agent to dynamically replan into an already-occupied corridor, or when two agents are executing opposing legs of a pickup-delivery sequence:

- **Collision Rules:** Cell sharing (p<sub>i</sub>(t) = p<sub>j</sub>(t)) and edge swapping (p<sub>i</sub>(t) = p<sub>j</sub>(t + 1) ∧ p<sub>i</sub>(t + 1) = p<sub>j</sub>(t)) are strictly forbidden.
- **Negotiation Limitation:** Neighbor negotiation queries agents within R ≤ 5. While neighbor a<sub>j</sub> is willing to yield its reservation, a<sub>j</sub> cannot step sideways into an obstacle wall. Since the current protocol evaluates single-agent forward detours rather than synchronized multi-agent reverse maneuvers, atomic agreement cannot be reached.
- **Livelock Cycling:** Both agents fall back to Phase 3 waiting (τ<sub>wait</sub> = 10). After 10 steps, both simultaneously wake up, attempt replanning, detect the same opposing obstacle, and enter another wait cycle until the simulation times out at T<sub>max</sub> = 400.

#### 2. Graph Disconnection in Dense Topologies (ρ ≥ 25%)

When static rack density reaches ρ ≥ 25%, the free space forms long, labyrinthine bottlenecks. If a random dynamic cell blockage or agent breakdown is injected at an articulation vertex (a node whose removal increases the number of connected components), the warehouse floor is split. Space-Time A* explores all reachable states in the agent's component, exhausts the open list, and returns `FAIL`. Neighbor negotiation is powerless because the obstruction is a physical environmental wall rather than a negotiating robot.

#### 3. Station Gateway Ingress Obstruction

Each pickup diamond and delivery square occupies a specific coordinate. In layouts where storage racks restrict access to a station from only one orthogonal direction, an agent breakdown at that ingress coordinate permanently seals the station. Because the assignment model assumes fixed target assignments, the remaining agents cannot substitute alternate drop-off points, resulting in an unsolvable task state.

---


## Installation & Setup

### Prerequisites
* Python 3.8 or higher
* Any modern web browser (Chrome, Edge, Firefox, Safari)

### Install Dependencies
```bash
git clone https://github.com/Shweta30112005/Autonomous_System_Assignment1.git
cd Autonomous_System_Assignment1
pip install -r requirements.txt
```

---

## Quick Start Guide

### 1. Interactive Browser GUI (Recommended)
Launch a local HTTP server and open the web dashboard:
```bash
# Start local server
python -m http.server 8000
```
Open your browser to: **[http://localhost:8000](http://localhost:8000)**

* Click **`GENERATE`** to create random warehouse layouts, agents, and pickup/delivery targets.
* Click **`START`** or **`STEP`** to watch the robots navigate.
* Use the **`BLOCK CELL`**, **`BREAK AGENT`**, or **`EMERGENCY TASK`** buttons to inject real-time disruptions and observe instant plan repair in action!

---

### 2. Python Simulation & CLI
```bash
# Run headless demo simulation
python main.py --demo --no-viz

# Generate Matplotlib visualization and export animation
python main.py

# Launch interactive Pygame window (if Pygame is installed)
python main.py --pygame

# Custom warehouse configuration
python main.py --grid-size 20 --agents 6 --tasks 3 --obstacles 0.15 --disruptions 4
```

#### Pygame Visualizer Controls:
| Key | Action |
|:---:|:---|
| `SPACE` | Play / Pause simulation |
| `→` / `←` | Step forward / backward by 1 timestep |
| `↑` / `↓` | Increase / Decrease playback speed |
| `R` | Reset simulation to t = 0 |
| `ESC` | Exit visualizer |

---

### 3. Run Benchmark Experiments
To reproduce all empirical results and generate plots in `results/`:
```bash
python experiments.py
```
Or via `main.py`:
```bash
python main.py --experiments
```

---

 
## References
1. **Silver, D. (2005).** *Cooperative Pathfinding.* Proceedings of the AAAI Conference on Artificial Intelligence and Interactive Digital Entertainment (AIIDE), 1(1), 117–122.
2. **Sharon, G., Stern, R., Felner, A., & Sturtevant, N. R. (2015).** *Conflict-based search for optimal multi-agent pathfinding.* Artificial Intelligence, 219, 40–66.
3. **Standley, T. (2010).** *Finding optimal solutions to cooperative pathfinding problems.* Proceedings of the AAAI Conference on Artificial Intelligence, 24(1), 173–178.
4. **Wurm, K. M., Stachniss, C., & Burgard, W. (2010).** *Coordinating multi-robot teams using grid-based path planning.* IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS), 2842–2847.

---
*Developed for Autonomous Systems - Assignment 1: Multi-Agent Warehouse Pathfinding & Dynamic Plan Repair.*
