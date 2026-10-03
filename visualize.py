import os
from typing import Dict, List

import matplotlib.pyplot as plt
import pandas as pd

from warehouse import Agent, Warehouse


def plot_warehouse(
    warehouse: Warehouse,
    agents: List[Agent],
    time_step: int = 0,
    save_path: str | None = None,
):
    """
    Draw the warehouse and current robot positions.
    """

    fig, ax = plt.subplots(
        figsize=(8, 8)
    )

    # ---------------------------------------------------------
    # Static obstacles
    # ---------------------------------------------------------

    for r, c in warehouse.static_obstacles:

        ax.add_patch(
            plt.Rectangle(
                (c - 0.5, r - 0.5),
                1,
                1,
                fill=True,
                alpha=0.8,
            )
        )

    # ---------------------------------------------------------
    # Dynamic obstacles
    # ---------------------------------------------------------

    for r, c in warehouse.dynamic_obstacles:

        ax.add_patch(
            plt.Rectangle(
                (c - 0.5, r - 0.5),
                1,
                1,
                fill=True,
                alpha=0.4,
            )
        )

    # ---------------------------------------------------------
    # Agent paths
    # ---------------------------------------------------------

    for agent in agents:

        if not agent.path:
            continue

        xs = [
            p[1]
            for p in agent.path
        ]

        ys = [
            p[0]
            for p in agent.path
        ]

        ax.plot(
            xs,
            ys,
            linestyle="--",
            alpha=0.5,
        )

        index = min(
            time_step,
            len(agent.path) - 1,
        )

        r, c = agent.path[index]

        ax.scatter(
            c,
            r,
            s=100,
            label=f"Agent {agent.agent_id}",
        )

        # Pickup
        pr, pc = agent.pickup

        ax.scatter(
            pc,
            pr,
            marker="^",
            s=70,
        )

        # Delivery
        dr, dc = agent.delivery

        ax.scatter(
            dc,
            dr,
            marker="*",
            s=100,
        )

    # ---------------------------------------------------------
    # Formatting
    # ---------------------------------------------------------

    ax.set_xlim(
        -0.5,
        warehouse.cols - 0.5,
    )

    ax.set_ylim(
        warehouse.rows - 0.5,
        -0.5,
    )

    ax.set_xticks(range(warehouse.cols))
    ax.set_yticks(range(warehouse.rows))

    ax.grid(True, alpha=0.2)

    ax.set_title(
        f"Warehouse Simulation - t={time_step}"
    )

    ax.set_xlabel("Column")
    ax.set_ylabel("Row")

    ax.legend()

    plt.tight_layout()

    if save_path:
        os.makedirs(
            os.path.dirname(save_path),
            exist_ok=True,
        )

        plt.savefig(
            save_path,
            dpi=200,
        )

    return fig, ax


def plot_experiment_results(
    csv_path: str = "results/metrics.csv",
    output_dir: str = "results/plots",
):
    """
    Generate experiment plots from metrics.csv.
    """

    os.makedirs(
        output_dir,
        exist_ok=True,
    )

    df = pd.read_csv(csv_path)

    if df.empty:
        print("No experiment data found.")
        return

    # ---------------------------------------------------------
    # Agent count vs makespan
    # ---------------------------------------------------------

    if {
        "num_agents",
        "makespan",
    }.issubset(df.columns):

        grouped = (
            df.groupby("num_agents")["makespan"]
            .mean()
            .reset_index()
        )

        plt.figure(figsize=(8, 5))

        plt.plot(
            grouped["num_agents"],
            grouped["makespan"],
            marker="o",
        )

        plt.xlabel("Number of Agents")
        plt.ylabel("Average Makespan")
        plt.title(
            "Number of Agents vs Makespan"
        )

        plt.grid(alpha=0.2)

        plt.tight_layout()

        plt.savefig(
            os.path.join(
                output_dir,
                "agents_vs_makespan.png",
            ),
            dpi=200,
        )

        plt.close()

    # ---------------------------------------------------------
    # Agent count vs changed agents
    # ---------------------------------------------------------

    if {
        "num_agents",
        "average_changed_agents",
    }.issubset(df.columns):

        grouped = (
            df.groupby("num_agents")[
                "average_changed_agents"
            ]
            .mean()
            .reset_index()
        )

        plt.figure(figsize=(8, 5))

        plt.plot(
            grouped["num_agents"],
            grouped["average_changed_agents"],
            marker="o",
        )

        plt.xlabel("Number of Agents")
        plt.ylabel(
            "Average Number of Changed Agents"
        )

        plt.title(
            "Number of Agents vs Plan Changes"
        )

        plt.grid(alpha=0.2)

        plt.tight_layout()

        plt.savefig(
            os.path.join(
                output_dir,
                "agents_vs_changed_agents.png",
            ),
            dpi=200,
        )

        plt.close()

    # ---------------------------------------------------------
    # Obstacle density vs makespan
    # ---------------------------------------------------------

    if {
        "dynamic_obstacle_density",
        "makespan",
    }.issubset(df.columns):

        grouped = (
            df.groupby(
                "dynamic_obstacle_density"
            )["makespan"]
            .mean()
            .reset_index()
        )

        plt.figure(figsize=(8, 5))

        plt.plot(
            grouped[
                "dynamic_obstacle_density"
            ],
            grouped["makespan"],
            marker="o",
        )

        plt.xlabel(
            "Dynamic Obstacle Density"
        )

        plt.ylabel("Average Makespan")

        plt.title(
            "Dynamic Obstacle Density vs Makespan"
        )

        plt.grid(alpha=0.2)

        plt.tight_layout()

        plt.savefig(
            os.path.join(
                output_dir,
                "density_vs_makespan.png",
            ),
            dpi=200,
        )

        plt.close()

    # ---------------------------------------------------------
    # Obstacle density vs changed agents
    # ---------------------------------------------------------

    if {
        "dynamic_obstacle_density",
        "average_changed_agents",
    }.issubset(df.columns):

        grouped = (
            df.groupby(
                "dynamic_obstacle_density"
            )[
                "average_changed_agents"
            ]
            .mean()
            .reset_index()
        )

        plt.figure(figsize=(8, 5))

        plt.plot(
            grouped[
                "dynamic_obstacle_density"
            ],
            grouped["average_changed_agents"],
            marker="o",
        )

        plt.xlabel(
            "Dynamic Obstacle Density"
        )

        plt.ylabel(
            "Average Number of Changed Agents"
        )

        plt.title(
            "Dynamic Obstacle Density vs Plan Changes"
        )

        plt.grid(alpha=0.2)

        plt.tight_layout()

        plt.savefig(
            os.path.join(
                output_dir,
                "density_vs_changed_agents.png",
            ),
            dpi=200,
        )

        plt.close()

    print(
        f"Plots saved to {output_dir}"
    )