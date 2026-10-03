import random

from warehouse import Agent, Task, Warehouse
from planner import SpaceTimeAStar
from simulation import Simulator, save_metrics
from visualize import (
    plot_experiment_results,
    plot_warehouse,
)


# =============================================================
# Configuration
# =============================================================

GRID_SIZE = 20

AGENT_COUNTS = [
    5,
    10,
    15,
    20,
]

DYNAMIC_OBSTACLE_DENSITIES = [
    0.00,
    0.05,
    0.10,
    0.15,
]

TRIALS = 5

BASE_SEED = 42


# =============================================================
# Warehouse generation
# =============================================================

def generate_obstacles(
    rows: int,
    cols: int,
    density: float,
    rng: random.Random,
):
    obstacles = set()

    total_cells = rows * cols

    target = int(
        total_cells * density
    )

    while len(obstacles) < target:

        position = (
            rng.randrange(rows),
            rng.randrange(cols),
        )

        obstacles.add(position)

    return obstacles


# =============================================================
# Agent generation
# =============================================================

def generate_agents(
    warehouse: Warehouse,
    num_agents: int,
    rng: random.Random,
):
    used = set()

    agents = []

    def random_free_position():

        for _ in range(10000):

            position = (
                rng.randrange(
                    warehouse.rows
                ),
                rng.randrange(
                    warehouse.cols
                ),
            )

            if (
                warehouse.is_free(position)
                and position not in used
            ):
                used.add(position)
                return position

        raise RuntimeError(
            "Unable to generate enough free positions."
        )

    for agent_id in range(
        1,
        num_agents + 1,
    ):

        start = random_free_position()
        pickup = random_free_position()
        delivery = random_free_position()

        agents.append(
            Agent(
                agent_id=agent_id,
                start=start,
                task=Task(
                    pickup=pickup,
                    delivery=delivery,
                ),
            )
        )

    return agents


# =============================================================
# Demo
# =============================================================

def run_demo():

    rng = random.Random(BASE_SEED)

    obstacles = generate_obstacles(
        GRID_SIZE,
        GRID_SIZE,
        density=0.10,
        rng=rng,
    )

    warehouse = Warehouse(
        rows=GRID_SIZE,
        cols=GRID_SIZE,
        static_obstacles=obstacles,
    )

    agents = generate_agents(
        warehouse,
        num_agents=5,
        rng=rng,
    )

    planner = SpaceTimeAStar(
        warehouse
    )

    simulator = Simulator(
        warehouse=warehouse,
        agents=agents,
        planner=planner,
        seed=BASE_SEED,
    )

    success = simulator.generate_initial_plans()

    if not success:
        print(
            "Could not generate initial plans."
        )
        return

    print("\nInitial plans")
    print("=" * 60)

    for agent in agents:

        print(
            f"Agent {agent.agent_id}: "
            f"{len(agent.path) - 1} steps"
        )

        print(agent.path)

    # ---------------------------------------------------------
    # Visualize initial state.
    # ---------------------------------------------------------

    plot_warehouse(
        warehouse,
        agents,
        time_step=0,
        save_path="results/initial_warehouse.png",
    )

    # ---------------------------------------------------------
    # Find a cell from Agent 1's future path and block it.
    # ---------------------------------------------------------

    agent = agents[0]

    disruption_time = min(
        5,
        len(agent.path) - 2,
    )

    disruption_position = agent.path[
        disruption_time
    ]

    print("\nDisruption")
    print("=" * 60)

    print(
        f"Time: {disruption_time}"
    )

    print(
        f"Blocked cell: {disruption_position}"
    )

    result = simulator.add_dynamic_obstacle(
        disruption_position
    )

    print("\nRepair result")
    print("=" * 60)

    print(
        f"Success: {result.success}"
    )

    print(
        f"Changed agents: "
        f"{result.changed_agents}"
    )

    print(
        f"Reason: {result.reason}"
    )

    # ---------------------------------------------------------
    # Run simulation from current time.
    # ---------------------------------------------------------

    metrics = simulator.run(
        max_steps=500
    )

    print("\nSimulation results")
    print("=" * 60)

    print(
        f"Makespan: "
        f"{metrics.makespan}"
    )

    print(
        f"Aggregate agent time: "
        f"{metrics.aggregate_time}"
    )

    print(
        f"Average changed agents: "
        f"{metrics.average_changed_agents:.2f}"
    )

    print(
        f"Average repair time: "
        f"{metrics.average_repair_time_ms:.3f} ms"
    )


# =============================================================
# Experiments
# =============================================================

def run_experiments():

    results = []

    print("\nRunning experiments...")
    print("=" * 60)

    for num_agents in AGENT_COUNTS:

        for density in DYNAMIC_OBSTACLE_DENSITIES:

            for trial in range(TRIALS):

                seed = (
                    BASE_SEED
                    + trial
                    + num_agents * 100
                    + int(density * 1000)
                )

                rng = random.Random(seed)

                # -------------------------------------------------
                # Static warehouse obstacles.
                # -------------------------------------------------

                static_obstacles = generate_obstacles(
                    GRID_SIZE,
                    GRID_SIZE,
                    density=0.10,
                    rng=rng,
                )

                warehouse = Warehouse(
                    rows=GRID_SIZE,
                    cols=GRID_SIZE,
                    static_obstacles=static_obstacles,
                )

                # -------------------------------------------------
                # Agents.
                # -------------------------------------------------

                agents = generate_agents(
                    warehouse,
                    num_agents=num_agents,
                    rng=rng,
                )

                planner = SpaceTimeAStar(
                    warehouse
                )

                simulator = Simulator(
                    warehouse=warehouse,
                    agents=agents,
                    planner=planner,
                    seed=seed,
                )

                # -------------------------------------------------
                # Initial MAPF.
                # -------------------------------------------------

                success = (
                    simulator.generate_initial_plans()
                )

                if not success:

                    print(
                        f"Initial planning failed: "
                        f"agents={num_agents}, "
                        f"density={density}, "
                        f"trial={trial}"
                    )

                    continue

                # -------------------------------------------------
                # Generate dynamic obstacles.
                #
                # We select free cells rather than placing
                # obstacles directly on agents' starting cells.
                # -------------------------------------------------

                disruption_schedule = {}

                num_dynamic = int(
                    GRID_SIZE
                    * GRID_SIZE
                    * density
                )

                candidate_cells = []

                for r in range(GRID_SIZE):
                    for c in range(GRID_SIZE):

                        position = (r, c)

                        if (
                            warehouse.is_free(position)
                        ):
                            candidate_cells.append(
                                position
                            )

                rng.shuffle(candidate_cells)

                # Spread disruptions over time.
                for i in range(
                    min(
                        num_dynamic,
                        len(candidate_cells),
                    )
                ):

                    position = candidate_cells[i]

                    time_step = 10 + i * 5

                    disruption_schedule[
                        time_step
                    ] = position

                # -------------------------------------------------
                # Run.
                # -------------------------------------------------

                metrics = simulator.run(
                    max_steps=500,
                    disruption_schedule=(
                        disruption_schedule
                    ),
                )

                results.append(
                    {
                        "num_agents": num_agents,
                        "dynamic_obstacle_density": density,
                        "trial": trial,
                        "makespan": metrics.makespan,
                        "aggregate_time": (
                            metrics.aggregate_time
                        ),
                        "disruptions": (
                            metrics.disruptions
                        ),
                        "successful_repairs": (
                            metrics.successful_repairs
                        ),
                        "failed_repairs": (
                            metrics.failed_repairs
                        ),
                        "average_changed_agents": (
                            metrics.average_changed_agents
                        ),
                        "average_repair_time_ms": (
                            metrics.average_repair_time_ms
                        ),
                    }
                )

                print(
                    f"agents={num_agents:2d} | "
                    f"density={density:.2f} | "
                    f"trial={trial} | "
                    f"makespan={metrics.makespan}"
                )

    save_metrics(
        results,
        "results/metrics.csv",
    )

    print(
        "\nExperiment data saved to "
        "results/metrics.csv"
    )

    plot_experiment_results(
        "results/metrics.csv",
        "results/plots",
    )


# =============================================================
# Entry point
# =============================================================

if __name__ == "__main__":

    run_demo()
    run_experiments()