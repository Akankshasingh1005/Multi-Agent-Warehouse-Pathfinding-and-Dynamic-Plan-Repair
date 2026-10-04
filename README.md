# Multi-Agent Warehouse Pathfinding Simulation with Dynamic Plan Repair

## Overview

This project simulates an automated warehouse with a team of robotic agents navigating a 2D grid map. Agents are assigned pickup-and-delivery tasks and use **Space-Time A\*** with **Cooperative A\*** for collision-free multi-agent pathfinding. The system handles dynamic disruptions (cell blockages, agent breakdowns, emergency tasks) through a **local plan repair algorithm** with neighbor negotiation — without re-invoking the full planner from scratch.

## Architecture

```
warehouse_simulation/
├── main.py            # Entry point with CLI arguments
├── grid.py            # 2D grid environment with obstacles
├── agent.py           # Agent class with tasks and path following
├── pathfinding.py     # Space-Time A*, Cooperative A*
├── plan_repair.py     # Plan repair with local replanning & negotiation
├── disruptions.py     # Disruption types and generator
├── simulation.py      # Simulation engine orchestrating everything
├── visualization.py   # Pygame + Matplotlib visualization
├── experiments.py     # Experiment runner and plot generator
├── requirements.txt   # Python dependencies
└── results/           # Generated plots and animations
```

## Algorithms

### Space-Time A* (STA*)
Extends A* to the 3D space-time graph `(x, y, t)`. Each agent plans paths that avoid both obstacles and cells reserved by other agents at specific timesteps. The heuristic uses Manhattan distance.

### Cooperative A* (CA*)
Plans agent paths sequentially using a shared **Reservation Table**. Each agent respects reservations made by previously planned agents. Includes edge-conflict detection to prevent swap collisions.

### Plan Repair Algorithm
When disruptions occur, the system:
1. **Identifies affected agents** — those whose future paths pass through disrupted cells
2. **Locally replans** each affected agent from its current position using STA*
3. **Negotiates with neighbors** if local replanning fails — temporarily clears a neighbor's reservations, replans both agents
4. **Minimizes impact** — only agents directly affected have their plans modified

### Disruption Types
- **Cell Blockage**: A grid cell becomes impassable
- **Agent Breakdown**: An agent stops functioning, becoming a static obstacle  
- **Emergency Task**: An agent receives a high-priority pickup-delivery task

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Quick Demo
```bash
python main.py --demo --no-viz
```

### Demo with Visualization
```bash
# Matplotlib animation (saved as GIF)
python main.py

# Pygame real-time visualization
python main.py --pygame
```

### Custom Configuration
```bash
python main.py --grid-size 20 --agents 8 --tasks 3 --obstacles 0.15 --disruptions 5
```

### Run Experiments
```bash
python main.py --experiments
```

This generates performance plots in the `results/` directory.

## Experiments

1. **Performance vs Number of Agents** — Measures completion time, plan repair impact, and task completion rate as agent count varies
2. **Performance vs Obstacle Density** — Evaluates how increasing obstacle density affects planning time and disruption handling
3. **Disruption Type Comparison** — Compares impact of different disruption types
4. **Impact of Number of Disruptions** — Shows how total disruption count affects overall performance

## Evaluation Metrics

| Metric | Description |
|--------|-------------|
| Total Time Steps | Total simulation steps until all agents complete tasks |
| Agents Modified per Disruption | Number of agents whose plans changed per disruption event |
| Completion Rate | Percentage of agents that finished all tasks |
| Initial Planning Time | Time to compute the initial cooperative plan |

## Key Design Decisions

- **No full replan**: Plan repair never re-invokes CA* from scratch — it only locally replans affected agents
- **Neighbor negotiation**: When local replan fails, agents negotiate with neighbors within a configurable radius
- **Reservation table**: Efficient O(1) collision checking using hash-based space-time reservations
- **Edge conflict detection**: Prevents two agents from swapping positions

## Controls (Pygame Visualization)

| Key | Action |
|-----|--------|
| SPACE | Play/Pause |
| ← / → | Step backward/forward |
| ↑ / ↓ | Speed up/down |
| R | Restart |
| ESC | Quit |
