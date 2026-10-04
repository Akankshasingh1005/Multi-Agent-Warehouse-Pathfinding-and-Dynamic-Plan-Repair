"""
simulation.py - Simulation Engine

Orchestrates the multi-agent warehouse simulation:
- Initializes agents with tasks on the grid
- Runs initial cooperative pathfinding
- Executes time steps with disruption injection
- Invokes plan repair when disruptions occur
- Collects metrics throughout the simulation
"""

import random
import time
from grid import Grid
from agent import Agent, Task, AgentStatus
from pathfinding import cooperative_astar
from plan_repair import (
    repair_plan_cell_blockage,
    repair_plan_agent_breakdown,
    repair_plan_emergency_task,
    PlanRepairResult,
)
from disruptions import DisruptionGenerator, DisruptionType


class SimulationMetrics:
    """Collects and reports simulation performance metrics."""

    def __init__(self):
        self.total_time_steps = 0
        self.agents_finished = 0
        self.total_agents = 0
        self.disruptions_handled = 0
        self.total_agents_modified = 0  # Total plan modifications across all disruptions
        self.agents_modified_per_disruption = []  # List of counts
        self.initial_planning_time = 0
        self.repair_times = []
        self.task_completion_times = {}  # agent_id -> completion time

    def summary(self):
        """Return a summary dict of metrics."""
        avg_modified = (sum(self.agents_modified_per_disruption) /
                        len(self.agents_modified_per_disruption)
                        if self.agents_modified_per_disruption else 0)
        return {
            "total_time_steps": self.total_time_steps,
            "total_agents": self.total_agents,
            "agents_finished": self.agents_finished,
            "disruptions_handled": self.disruptions_handled,
            "avg_agents_modified_per_disruption": round(avg_modified, 2),
            "total_agents_modified": self.total_agents_modified,
            "agents_modified_per_disruption": self.agents_modified_per_disruption,
            "initial_planning_time_ms": round(self.initial_planning_time * 1000, 2),
        }

    def __repr__(self):
        s = self.summary()
        lines = ["=== Simulation Metrics ==="]
        for key, val in s.items():
            lines.append(f"  {key}: {val}")
        return "\n".join(lines)


class Simulation:
    """Main simulation engine for the warehouse."""

    def __init__(self, grid_width=20, grid_height=20, num_agents=5,
                 tasks_per_agent=2, obstacle_density=0.15,
                 num_disruptions=3, seed=42, max_time=300):
        """
        Initialize the simulation.

        Args:
            grid_width: Width of the warehouse grid.
            grid_height: Height of the warehouse grid.
            num_agents: Number of robotic agents.
            tasks_per_agent: Number of pickup/delivery tasks per agent.
            obstacle_density: Fraction of static obstacles.
            num_disruptions: Number of dynamic disruptions to inject.
            seed: Random seed for reproducibility.
            max_time: Maximum simulation time steps.
        """
        self.seed = seed
        self.max_time = max_time
        self.num_disruptions = num_disruptions

        random.seed(seed)

        # Create grid
        self.grid = Grid(grid_width, grid_height, obstacle_density, seed=seed)

        # Create agents with tasks
        self.agents = self._create_agents(num_agents, tasks_per_agent)

        # Reservation table (set after planning)
        self.reservation_table = None

        # Disruptions
        self.disruptions = []

        # Metrics
        self.metrics = SimulationMetrics()
        self.metrics.total_agents = num_agents

        # Simulation state
        self.current_time = 0
        self.history = []  # List of snapshots for visualization
        self.disruption_log = []  # Log of handled disruptions

    def _create_agents(self, num_agents, tasks_per_agent):
        """Create agents with random start positions and tasks."""
        free_cells = self.grid.get_free_cells()
        random.shuffle(free_cells)

        if len(free_cells) < num_agents * (1 + tasks_per_agent * 2):
            raise ValueError("Not enough free cells for agents and tasks. "
                             "Reduce obstacle density or agent/task count.")

        agents = []
        cell_idx = 0

        for i in range(num_agents):
            start_pos = free_cells[cell_idx]
            cell_idx += 1

            tasks = []
            for j in range(tasks_per_agent):
                pickup = free_cells[cell_idx]
                cell_idx += 1
                delivery = free_cells[cell_idx]
                cell_idx += 1
                tasks.append(Task(
                    pickup=pickup,
                    delivery=delivery,
                    priority=0,
                    task_id=f"task_{i}_{j}"
                ))

            agent = Agent(agent_id=i, start_pos=start_pos, tasks=tasks)
            agents.append(agent)

        return agents

    def plan_initial_paths(self):
        """Run cooperative A* to plan initial paths for all agents."""
        start = time.time()
        self.reservation_table, success = cooperative_astar(
            self.grid, self.agents, max_time=self.max_time
        )
        elapsed = time.time() - start
        self.metrics.initial_planning_time = elapsed

        # Save original paths
        for agent in self.agents:
            agent.save_original_path()

        return success

    def generate_disruptions(self, disruption_types=None):
        """Generate random disruptions for the simulation."""
        generator = DisruptionGenerator(self.grid, self.agents, seed=self.seed + 100)

        # Calculate a reasonable time range for disruptions
        max_path_len = max(len(a.path) for a in self.agents) if self.agents else 50
        time_range = (5, min(max_path_len - 5, self.max_time - 10))
        if time_range[0] >= time_range[1]:
            time_range = (3, 30)

        self.disruptions = generator.generate_random_disruptions(
            self.num_disruptions,
            time_range=time_range,
            types=disruption_types
        )

    def set_disruptions(self, disruptions):
        """Set specific disruptions (for controlled experiments)."""
        self.disruptions = sorted(disruptions, key=lambda d: d.time_step)

    def _handle_disruption(self, disruption):
        """Handle a single disruption event."""
        result = PlanRepairResult()

        if disruption.disruption_type == DisruptionType.CELL_BLOCKAGE:
            result = repair_plan_cell_blockage(
                self.grid, self.agents, self.reservation_table,
                disruption.params['position'], self.current_time, self.max_time
            )

        elif disruption.disruption_type == DisruptionType.AGENT_BREAKDOWN:
            result = repair_plan_agent_breakdown(
                self.grid, self.agents, self.reservation_table,
                disruption.params['agent_id'], self.current_time, self.max_time
            )

        elif disruption.disruption_type == DisruptionType.EMERGENCY_TASK:
            result = repair_plan_emergency_task(
                self.grid, self.agents, self.reservation_table,
                disruption.params['agent_id'], disruption.params['task'],
                self.current_time, self.max_time
            )

        disruption.handled = True

        # Update metrics
        self.metrics.disruptions_handled += 1
        num_modified = len(result.agents_modified)
        self.metrics.agents_modified_per_disruption.append(num_modified)
        self.metrics.total_agents_modified += num_modified

        self.disruption_log.append({
            'time': self.current_time,
            'type': disruption.disruption_type.value,
            'params': disruption.params,
            'agents_modified': result.agents_modified,
            'description': result.description
        })

        return result

    def _take_snapshot(self):
        """Take a snapshot of the current simulation state."""
        snapshot = {
            'time': self.current_time,
            'agents': [],
            'dynamic_obstacles': list(self.grid.dynamic_obstacles.keys()),
            'disruption_this_step': None
        }

        for agent in self.agents:
            snapshot['agents'].append({
                'id': agent.agent_id,
                'position': agent.position,
                'status': agent.status.value,
                'target': agent.current_target,
                'tasks_done': sum(1 for t in agent.tasks if t.delivered),
                'total_tasks': len(agent.tasks),
                'path_modified': agent.plan_modified,
            })

        self.history.append(snapshot)

    def run(self, verbose=False):
        """
        Run the complete simulation.

        Args:
            verbose: If True, print step-by-step information.

        Returns:
            SimulationMetrics object.
        """
        if verbose:
            print(f"Starting simulation: {len(self.agents)} agents, "
                  f"{self.grid.width}x{self.grid.height} grid")
            print(f"Disruptions scheduled: {len(self.disruptions)}")

        # Run time steps
        all_done = False
        while self.current_time < self.max_time and not all_done:
            # Check for disruptions at this time step
            for disruption in self.disruptions:
                if disruption.time_step == self.current_time and not disruption.handled:
                    if verbose:
                        print(f"\n  [!] Disruption at t={self.current_time}: {disruption}")
                    result = self._handle_disruption(disruption)
                    if verbose:
                        print(f"      {result.description if hasattr(result, 'description') else 'Handled'}")
                        if hasattr(result, 'agents_modified'):
                            print(f"      Agents modified: {result.agents_modified}")

                    # Add disruption info to snapshot
                    self.history[-1]['disruption_this_step'] = {
                        'type': disruption.disruption_type.value,
                        'params': str(disruption.params),
                    } if self.history else None

            # Advance all agents
            for agent in self.agents:
                agent.advance(self.current_time)

            # Take snapshot
            self._take_snapshot()

            # Check if all agents are done
            all_done = all(
                a.is_done() or a.status == AgentStatus.BROKEN_DOWN
                for a in self.agents
            )

            if verbose and self.current_time % 10 == 0:
                active = sum(1 for a in self.agents if a.status == AgentStatus.ACTIVE)
                done = sum(1 for a in self.agents if a.is_done())
                print(f"  t={self.current_time}: {active} active, {done} done")

            self.current_time += 1

        # Finalize metrics
        self.metrics.total_time_steps = self.current_time
        self.metrics.agents_finished = sum(1 for a in self.agents if a.is_done())

        for agent in self.agents:
            if agent.is_done():
                # Find when the agent finished (last meaningful move)
                for t in range(len(agent.path) - 1, -1, -1):
                    if t == 0 or agent.path[t] != agent.path[t - 1]:
                        self.metrics.task_completion_times[agent.agent_id] = t
                        break

        if verbose:
            print(f"\n{self.metrics}")

        return self.metrics

    def get_agent_paths(self):
        """Get all agent paths for visualization."""
        return {a.agent_id: a.path for a in self.agents}

    def get_simulation_state(self):
        """Get current simulation state for external use."""
        return {
            'grid': self.grid,
            'agents': self.agents,
            'time': self.current_time,
            'disruptions': self.disruptions,
            'metrics': self.metrics,
            'history': self.history,
        }
