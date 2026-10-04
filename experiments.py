"""
experiments.py - Experiment Runner and Report Generator

Runs systematic experiments to evaluate:
1. Total time steps vs number of agents
2. Impact of disruptions (agents modified per disruption)
3. Performance vs dynamic obstacle density
4. Comparison with and without plan repair

Generates plots and summary tables for the report.
"""

import os
import time
import random
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for saving plots
import numpy as np
from simulation import Simulation
from disruptions import DisruptionType


def run_single_experiment(grid_width, grid_height, num_agents, tasks_per_agent,
                          obstacle_density, num_disruptions, seed,
                          disruption_types=None, max_time=300, verbose=False):
    """
    Run a single simulation experiment and return metrics.

    Returns:
        dict with simulation results.
    """
    try:
        sim = Simulation(
            grid_width=grid_width,
            grid_height=grid_height,
            num_agents=num_agents,
            tasks_per_agent=tasks_per_agent,
            obstacle_density=obstacle_density,
            num_disruptions=num_disruptions,
            seed=seed,
            max_time=max_time,
        )
        sim.plan_initial_paths()
        sim.generate_disruptions(disruption_types=disruption_types)
        metrics = sim.run(verbose=verbose)
        return metrics.summary()
    except Exception as e:
        if verbose:
            print(f"  Experiment failed: {e}")
        return None


# ════════════════════════════════════════════════════════════════════
# Experiment 1: Performance vs Number of Agents
# ════════════════════════════════════════════════════════════════════

def experiment_vary_agents(output_dir, grid_size=20, obstacle_density=0.1,
                            tasks_per_agent=2, num_disruptions=3,
                            agent_counts=None, num_trials=5):
    """
    Measure how performance changes as the number of agents varies.
    """
    if agent_counts is None:
        agent_counts = [2, 3, 4, 5, 6, 8, 10]

    print("=" * 60)
    print("Experiment 1: Performance vs Number of Agents")
    print("=" * 60)

    results = {n: [] for n in agent_counts}

    for n_agents in agent_counts:
        print(f"\n  Testing with {n_agents} agents...")
        for trial in range(num_trials):
            seed = 42 + trial * 100 + n_agents
            res = run_single_experiment(
                grid_width=grid_size, grid_height=grid_size,
                num_agents=n_agents, tasks_per_agent=tasks_per_agent,
                obstacle_density=obstacle_density,
                num_disruptions=num_disruptions,
                seed=seed, max_time=400
            )
            if res:
                results[n_agents].append(res)
                print(f"    Trial {trial + 1}: steps={res['total_time_steps']}, "
                      f"modified={res['total_agents_modified']}")

    # ── Plot Results ──
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.patch.set_facecolor('#1a1a24')
    fig.suptitle("Performance vs Number of Agents", color='white',
                fontsize=16, fontweight='bold', y=1.02)

    valid_counts = [n for n in agent_counts if results[n]]

    # Plot 1: Total Time Steps
    ax = axes[0]
    ax.set_facecolor('#2a2a36')
    means = [np.mean([r['total_time_steps'] for r in results[n]]) for n in valid_counts]
    stds = [np.std([r['total_time_steps'] for r in results[n]]) for n in valid_counts]
    ax.errorbar(valid_counts, means, yerr=stds, marker='o', color='#42a5f5',
               capsize=5, linewidth=2, markeredgecolor='white', markeredgewidth=1)
    ax.set_xlabel("Number of Agents", color='#ccc', fontsize=11)
    ax.set_ylabel("Total Time Steps", color='#ccc', fontsize=11)
    ax.set_title("Completion Time", color='white', fontsize=12)
    ax.tick_params(colors='#999')
    ax.grid(True, alpha=0.2)

    # Plot 2: Avg Agents Modified per Disruption
    ax = axes[1]
    ax.set_facecolor('#2a2a36')
    means = [np.mean([r['avg_agents_modified_per_disruption'] for r in results[n]])
             for n in valid_counts]
    stds = [np.std([r['avg_agents_modified_per_disruption'] for r in results[n]])
            for n in valid_counts]
    ax.errorbar(valid_counts, means, yerr=stds, marker='s', color='#ef5350',
               capsize=5, linewidth=2, markeredgecolor='white', markeredgewidth=1)
    ax.set_xlabel("Number of Agents", color='#ccc', fontsize=11)
    ax.set_ylabel("Avg Agents Modified / Disruption", color='#ccc', fontsize=11)
    ax.set_title("Plan Repair Impact", color='white', fontsize=12)
    ax.tick_params(colors='#999')
    ax.grid(True, alpha=0.2)

    # Plot 3: Completion Rate
    ax = axes[2]
    ax.set_facecolor('#2a2a36')
    rates = [np.mean([r['agents_finished'] / r['total_agents'] * 100
                      for r in results[n]]) for n in valid_counts]
    ax.bar(valid_counts, rates, color='#66bb6a', edgecolor='white', linewidth=0.5,
          width=0.6)
    ax.set_xlabel("Number of Agents", color='#ccc', fontsize=11)
    ax.set_ylabel("Completion Rate (%)", color='#ccc', fontsize=11)
    ax.set_title("Task Completion Rate", color='white', fontsize=12)
    ax.set_ylim(0, 105)
    ax.tick_params(colors='#999')
    ax.grid(True, alpha=0.2, axis='y')

    plt.tight_layout()
    path = os.path.join(output_dir, "exp1_vary_agents.png")
    plt.savefig(path, dpi=150, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(f"\n  Plot saved: {path}")

    return results


# ════════════════════════════════════════════════════════════════════
# Experiment 2: Performance vs Dynamic Obstacle Density
# ════════════════════════════════════════════════════════════════════

def experiment_vary_obstacles(output_dir, grid_size=20, num_agents=5,
                               tasks_per_agent=2, num_disruptions=3,
                               densities=None, num_trials=5):
    """
    Measure how performance changes as static obstacle density varies.
    """
    if densities is None:
        densities = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]

    print("\n" + "=" * 60)
    print("Experiment 2: Performance vs Obstacle Density")
    print("=" * 60)

    results = {d: [] for d in densities}

    for density in densities:
        print(f"\n  Testing with {density:.0%} obstacle density...")
        for trial in range(num_trials):
            seed = 42 + trial * 100
            res = run_single_experiment(
                grid_width=grid_size, grid_height=grid_size,
                num_agents=num_agents, tasks_per_agent=tasks_per_agent,
                obstacle_density=density,
                num_disruptions=num_disruptions,
                seed=seed, max_time=400
            )
            if res:
                results[density].append(res)
                print(f"    Trial {trial + 1}: steps={res['total_time_steps']}, "
                      f"modified={res['total_agents_modified']}")

    # ── Plot Results ──
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.patch.set_facecolor('#1a1a24')
    fig.suptitle("Performance vs Obstacle Density", color='white',
                fontsize=16, fontweight='bold', y=1.02)

    valid_densities = [d for d in densities if results[d]]

    # Plot 1: Total Time Steps
    ax = axes[0]
    ax.set_facecolor('#2a2a36')
    means = [np.mean([r['total_time_steps'] for r in results[d]]) for d in valid_densities]
    stds = [np.std([r['total_time_steps'] for r in results[d]]) for d in valid_densities]
    labels = [f"{d:.0%}" for d in valid_densities]
    ax.errorbar(range(len(valid_densities)), means, yerr=stds, marker='o',
               color='#42a5f5', capsize=5, linewidth=2)
    ax.set_xticks(range(len(valid_densities)))
    ax.set_xticklabels(labels)
    ax.set_xlabel("Obstacle Density", color='#ccc', fontsize=11)
    ax.set_ylabel("Total Time Steps", color='#ccc', fontsize=11)
    ax.set_title("Completion Time", color='white', fontsize=12)
    ax.tick_params(colors='#999')
    ax.grid(True, alpha=0.2)

    # Plot 2: Avg Agents Modified
    ax = axes[1]
    ax.set_facecolor('#2a2a36')
    means = [np.mean([r['avg_agents_modified_per_disruption'] for r in results[d]])
             for d in valid_densities]
    stds = [np.std([r['avg_agents_modified_per_disruption'] for r in results[d]])
            for d in valid_densities]
    ax.errorbar(range(len(valid_densities)), means, yerr=stds, marker='s',
               color='#ef5350', capsize=5, linewidth=2)
    ax.set_xticks(range(len(valid_densities)))
    ax.set_xticklabels(labels)
    ax.set_xlabel("Obstacle Density", color='#ccc', fontsize=11)
    ax.set_ylabel("Avg Agents Modified / Disruption", color='#ccc', fontsize=11)
    ax.set_title("Plan Repair Impact", color='white', fontsize=12)
    ax.tick_params(colors='#999')
    ax.grid(True, alpha=0.2)

    # Plot 3: Planning Time
    ax = axes[2]
    ax.set_facecolor('#2a2a36')
    means = [np.mean([r['initial_planning_time_ms'] for r in results[d]])
             for d in valid_densities]
    ax.bar(range(len(valid_densities)), means, color='#ab47bc',
          edgecolor='white', linewidth=0.5)
    ax.set_xticks(range(len(valid_densities)))
    ax.set_xticklabels(labels)
    ax.set_xlabel("Obstacle Density", color='#ccc', fontsize=11)
    ax.set_ylabel("Planning Time (ms)", color='#ccc', fontsize=11)
    ax.set_title("Initial Planning Time", color='white', fontsize=12)
    ax.tick_params(colors='#999')
    ax.grid(True, alpha=0.2, axis='y')

    plt.tight_layout()
    path = os.path.join(output_dir, "exp2_vary_obstacles.png")
    plt.savefig(path, dpi=150, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(f"\n  Plot saved: {path}")

    return results


# ════════════════════════════════════════════════════════════════════
# Experiment 3: Disruption Type Comparison
# ════════════════════════════════════════════════════════════════════

def experiment_disruption_types(output_dir, grid_size=20, num_agents=5,
                                 tasks_per_agent=2, obstacle_density=0.1,
                                 num_disruptions=3, num_trials=5):
    """
    Compare the impact of different disruption types.
    """
    print("\n" + "=" * 60)
    print("Experiment 3: Disruption Type Comparison")
    print("=" * 60)

    disruption_configs = {
        'Cell Blockage': [DisruptionType.CELL_BLOCKAGE],
        'Agent Breakdown': [DisruptionType.AGENT_BREAKDOWN],
        'Emergency Task': [DisruptionType.EMERGENCY_TASK],
        'Mixed': None,  # All types
    }

    results = {name: [] for name in disruption_configs}

    for name, d_types in disruption_configs.items():
        print(f"\n  Testing disruption type: {name}...")
        for trial in range(num_trials):
            seed = 42 + trial * 100
            res = run_single_experiment(
                grid_width=grid_size, grid_height=grid_size,
                num_agents=num_agents, tasks_per_agent=tasks_per_agent,
                obstacle_density=obstacle_density,
                num_disruptions=num_disruptions,
                seed=seed, max_time=400,
                disruption_types=d_types
            )
            if res:
                results[name].append(res)

    # ── Plot Results ──
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor('#1a1a24')
    fig.suptitle("Impact of Different Disruption Types", color='white',
                fontsize=16, fontweight='bold', y=1.02)

    valid_names = [n for n in disruption_configs if results[n]]
    colors = ['#42a5f5', '#ef5350', '#66bb6a', '#ffa726']

    # Plot 1: Total Time Steps
    ax = axes[0]
    ax.set_facecolor('#2a2a36')
    means = [np.mean([r['total_time_steps'] for r in results[n]]) for n in valid_names]
    stds = [np.std([r['total_time_steps'] for r in results[n]]) for n in valid_names]
    bars = ax.bar(range(len(valid_names)), means, yerr=stds, color=colors[:len(valid_names)],
                 edgecolor='white', linewidth=0.5, capsize=5)
    ax.set_xticks(range(len(valid_names)))
    ax.set_xticklabels(valid_names, rotation=15, ha='right')
    ax.set_ylabel("Total Time Steps", color='#ccc', fontsize=11)
    ax.set_title("Completion Time by Disruption Type", color='white', fontsize=12)
    ax.tick_params(colors='#999')
    ax.grid(True, alpha=0.2, axis='y')

    # Plot 2: Agents Modified
    ax = axes[1]
    ax.set_facecolor('#2a2a36')
    means = [np.mean([r['avg_agents_modified_per_disruption'] for r in results[n]])
             for n in valid_names]
    stds = [np.std([r['avg_agents_modified_per_disruption'] for r in results[n]])
            for n in valid_names]
    ax.bar(range(len(valid_names)), means, yerr=stds, color=colors[:len(valid_names)],
          edgecolor='white', linewidth=0.5, capsize=5)
    ax.set_xticks(range(len(valid_names)))
    ax.set_xticklabels(valid_names, rotation=15, ha='right')
    ax.set_ylabel("Avg Agents Modified / Disruption", color='#ccc', fontsize=11)
    ax.set_title("Plan Repair Impact by Disruption Type", color='white', fontsize=12)
    ax.tick_params(colors='#999')
    ax.grid(True, alpha=0.2, axis='y')

    plt.tight_layout()
    path = os.path.join(output_dir, "exp3_disruption_types.png")
    plt.savefig(path, dpi=150, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(f"\n  Plot saved: {path}")

    return results


# ════════════════════════════════════════════════════════════════════
# Experiment 4: Number of Disruptions Impact
# ════════════════════════════════════════════════════════════════════

def experiment_vary_disruptions(output_dir, grid_size=20, num_agents=5,
                                  tasks_per_agent=2, obstacle_density=0.1,
                                  disruption_counts=None, num_trials=5):
    """
    Measure impact as number of disruptions increases.
    """
    if disruption_counts is None:
        disruption_counts = [0, 1, 2, 3, 5, 7, 10]

    print("\n" + "=" * 60)
    print("Experiment 4: Impact of Number of Disruptions")
    print("=" * 60)

    results = {n: [] for n in disruption_counts}

    for n_disrupt in disruption_counts:
        print(f"\n  Testing with {n_disrupt} disruptions...")
        for trial in range(num_trials):
            seed = 42 + trial * 100
            res = run_single_experiment(
                grid_width=grid_size, grid_height=grid_size,
                num_agents=num_agents, tasks_per_agent=tasks_per_agent,
                obstacle_density=obstacle_density,
                num_disruptions=n_disrupt,
                seed=seed, max_time=400
            )
            if res:
                results[n_disrupt].append(res)

    # ── Plot Results ──
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor('#1a1a24')
    fig.suptitle("Impact of Number of Disruptions", color='white',
                fontsize=16, fontweight='bold', y=1.02)

    valid_counts = [n for n in disruption_counts if results[n]]

    # Plot 1: Total Time Steps
    ax = axes[0]
    ax.set_facecolor('#2a2a36')
    means = [np.mean([r['total_time_steps'] for r in results[n]]) for n in valid_counts]
    stds = [np.std([r['total_time_steps'] for r in results[n]]) for n in valid_counts]
    ax.errorbar(valid_counts, means, yerr=stds, marker='o', color='#42a5f5',
               capsize=5, linewidth=2, markeredgecolor='white', markeredgewidth=1)
    ax.set_xlabel("Number of Disruptions", color='#ccc', fontsize=11)
    ax.set_ylabel("Total Time Steps", color='#ccc', fontsize=11)
    ax.set_title("Completion Time vs Disruptions", color='white', fontsize=12)
    ax.tick_params(colors='#999')
    ax.grid(True, alpha=0.2)

    # Plot 2: Total Agents Modified
    ax = axes[1]
    ax.set_facecolor('#2a2a36')
    means = [np.mean([r['total_agents_modified'] for r in results[n]]) for n in valid_counts]
    stds = [np.std([r['total_agents_modified'] for r in results[n]]) for n in valid_counts]
    ax.errorbar(valid_counts, means, yerr=stds, marker='s', color='#ef5350',
               capsize=5, linewidth=2, markeredgecolor='white', markeredgewidth=1)
    ax.set_xlabel("Number of Disruptions", color='#ccc', fontsize=11)
    ax.set_ylabel("Total Agents with Modified Plans", color='#ccc', fontsize=11)
    ax.set_title("Total Plan Modifications", color='white', fontsize=12)
    ax.tick_params(colors='#999')
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    path = os.path.join(output_dir, "exp4_vary_disruptions.png")
    plt.savefig(path, dpi=150, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(f"\n  Plot saved: {path}")

    return results


# ════════════════════════════════════════════════════════════════════
# Run All Experiments
# ════════════════════════════════════════════════════════════════════

def run_all_experiments(output_dir="results"):
    """Run all experiments and generate plots."""
    os.makedirs(output_dir, exist_ok=True)

    print("\n" + "=" * 60)
    print("  RUNNING ALL EXPERIMENTS")
    print("=" * 60)

    start = time.time()

    r1 = experiment_vary_agents(output_dir)
    r2 = experiment_vary_obstacles(output_dir)
    r3 = experiment_disruption_types(output_dir)
    r4 = experiment_vary_disruptions(output_dir)

    elapsed = time.time() - start
    print(f"\n\nAll experiments completed in {elapsed:.1f} seconds")
    print(f"Results saved to: {output_dir}/")

    return r1, r2, r3, r4


if __name__ == "__main__":
    run_all_experiments()
