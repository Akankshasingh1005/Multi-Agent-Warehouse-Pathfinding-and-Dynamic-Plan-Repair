#!/usr/bin/env python3
"""
main.py - Warehouse Multi-Agent Simulation Entry Point

Multi-Agent Pathfinding with Dynamic Plan Repair in an Automated Warehouse.

Usage:
    python main.py                    # Run demo simulation with visualization
    python main.py --experiments      # Run all experiments and generate plots
    python main.py --demo             # Run a quick demo scenario
    python main.py --pygame           # Use Pygame visualization (if installed)

    Options:
        --grid-size N       Grid dimensions (NxN), default=15
        --agents N          Number of agents, default=5
        --tasks N           Tasks per agent, default=2
        --obstacles F       Obstacle density (0.0-0.4), default=0.12
        --disruptions N     Number of disruptions, default=3
        --seed N            Random seed, default=42
        --no-viz            Skip visualization
"""

import argparse
import sys
import os

from simulation import Simulation
from visualization import (
    visualize_matplotlib,
    plot_static_snapshot,
    PygameVisualizer,
    PYGAME_AVAILABLE,
)
from experiments import run_all_experiments


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def print_banner():
    """Print a nice banner."""
    banner = """
+--------------------------------------------------------------+
|     Multi-Agent Warehouse Pathfinding Simulation             |
|     with Dynamic Plan Repair                                 |
|                                                              |
|     Algorithms: Space-Time A*, Cooperative A*,               |
|                 Local Plan Repair with Negotiation           |
+--------------------------------------------------------------+
"""
    print(banner)


def run_demo(args):
    """Run a demonstration simulation."""
    print_banner()

    print(f"Configuration:")
    print(f"  Grid Size:     {args.grid_size}x{args.grid_size}")
    print(f"  Agents:        {args.agents}")
    print(f"  Tasks/Agent:   {args.tasks}")
    print(f"  Obstacles:     {args.obstacles:.0%}")
    print(f"  Disruptions:   {args.disruptions}")
    print(f"  Seed:          {args.seed}")
    print()

    # Create and run simulation
    sim = Simulation(
        grid_width=args.grid_size,
        grid_height=args.grid_size,
        num_agents=args.agents,
        tasks_per_agent=args.tasks,
        obstacle_density=args.obstacles,
        num_disruptions=args.disruptions,
        seed=args.seed,
        max_time=300,
    )

    print("Planning initial paths (Cooperative A*)...")
    success = sim.plan_initial_paths()
    print(f"  Initial planning: {'SUCCESS' if success else 'PARTIAL (some agents could not plan)'}")
    print(f"  Planning time: {sim.metrics.initial_planning_time * 1000:.1f} ms")
    print()

    # Print agent info
    print("Agents:")
    for agent in sim.agents:
        targets = agent.get_remaining_targets()
        print(f"  Agent {agent.agent_id}: start={agent.start_pos}, "
              f"targets={targets}, path_len={len(agent.path)}")
    print()

    # Generate disruptions
    sim.generate_disruptions()
    print("Scheduled Disruptions:")
    for d in sim.disruptions:
        print(f"  t={d.time_step}: {d.disruption_type.value} - {d.params}")
    print()

    # Run simulation
    print("Running simulation...")
    print("-" * 50)
    metrics = sim.run(verbose=True)
    print("-" * 50)

    # Print detailed results
    print("\n" + "=" * 50)
    print("SIMULATION RESULTS")
    print("=" * 50)
    print(f"  Total Time Steps:     {metrics.total_time_steps}")
    print(f"  Agents Completed:     {metrics.agents_finished}/{metrics.total_agents}")
    print(f"  Disruptions Handled:  {metrics.disruptions_handled}")
    print(f"  Total Plans Modified: {metrics.total_agents_modified}")
    if metrics.agents_modified_per_disruption:
        print(f"  Per-Disruption Impact: {metrics.agents_modified_per_disruption}")
        avg = sum(metrics.agents_modified_per_disruption) / len(metrics.agents_modified_per_disruption)
        print(f"  Avg Modified/Disruption: {avg:.2f}")
    print()

    # Disruption log
    if sim.disruption_log:
        print("Disruption Details:")
        for entry in sim.disruption_log:
            print(f"  t={entry['time']}: {entry['type']}")
            print(f"    {entry['description']}")
            print(f"    Agents re-planned: {entry['agents_modified']}")
        print()

    # Print path changes
    print("Path Analysis:")
    for agent in sim.agents:
        orig_len = len(agent.original_path) if agent.original_path else 0
        new_len = len(agent.path)
        modified = "YES" if agent.plan_modified else "no"
        print(f"  Agent {agent.agent_id}: orig_path={orig_len} steps, "
              f"final_path={new_len} steps, modified={modified}, "
              f"status={agent.status.value}")

    return sim


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent Warehouse Simulation with Dynamic Plan Repair"
    )
    parser.add_argument("--grid-size", type=int, default=15,
                       help="Grid dimensions (NxN)")
    parser.add_argument("--agents", type=int, default=5,
                       help="Number of agents")
    parser.add_argument("--tasks", type=int, default=2,
                       help="Tasks per agent")
    parser.add_argument("--obstacles", type=float, default=0.12,
                       help="Obstacle density (0.0-0.4)")
    parser.add_argument("--disruptions", type=int, default=3,
                       help="Number of disruptions")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed")
    parser.add_argument("--experiments", action="store_true",
                       help="Run all experiments")
    parser.add_argument("--demo", action="store_true",
                       help="Run demo simulation")
    parser.add_argument("--pygame", action="store_true",
                       help="Use Pygame visualization")
    parser.add_argument("--no-viz", action="store_true",
                       help="Skip visualization")
    parser.add_argument("--save-animation", type=str, default=None,
                       help="Save animation to file (e.g., simulation.gif)")

    args = parser.parse_args()

    if args.experiments:
        # Run all experiments
        print_banner()
        output_dir = os.path.join(os.path.dirname(__file__), "results")
        run_all_experiments(output_dir=output_dir)
        return

    # Run demo
    sim = run_demo(args)

    if args.no_viz:
        return

    # Visualization
    if args.pygame and PYGAME_AVAILABLE:
        print("\nLaunching Pygame visualization...")
        viz = PygameVisualizer(sim, cell_size=36, fps=4)
        viz.run()
    else:
        if args.pygame and not PYGAME_AVAILABLE:
            print("\nPygame not installed. Falling back to Matplotlib.")
            print("Install Pygame with: pip install pygame")

        print("\nGenerating Matplotlib visualization...")

        # Save static snapshots
        output_dir = os.path.join(os.path.dirname(__file__), "results")
        os.makedirs(output_dir, exist_ok=True)

        plot_static_snapshot(sim, time_step=0,
                           save_path=os.path.join(output_dir, "snapshot_t0.png"))

        # Animated visualization
        save_path = args.save_animation
        if save_path is None:
            save_path = os.path.join(output_dir, "simulation.gif")

        visualize_matplotlib(sim, save_path=save_path, show=False, interval=250)
        print(f"\nAnimation saved to: {save_path}")


if __name__ == "__main__":
    main()
