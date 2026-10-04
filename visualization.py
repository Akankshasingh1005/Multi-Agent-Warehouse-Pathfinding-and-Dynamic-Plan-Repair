"""
visualization.py - Pygame-based Warehouse Visualization

Provides real-time visual simulation of the warehouse with:
- Grid rendering with obstacles
- Animated agent movement along planned paths
- Disruption events highlighted
- Task pickup/delivery indicators
- Status panel with metrics
"""

import sys
import os

# Try importing pygame; provide fallback info if not available
try:
    import pygame
    import pygame.freetype
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

# Matplotlib fallback for static visualization
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.animation as animation
from matplotlib.colors import to_rgba
import numpy as np


# ── Color Palette ──
COLORS = {
    'background':    (30,  30,  40),
    'grid_line':     (50,  50,  65),
    'free_cell':     (45,  45,  58),
    'static_obs':    (80,  80,  95),
    'dynamic_obs':   (220, 60,  60),
    'pickup':        (0,   200, 120),
    'delivery':      (255, 180, 0),
    'text':          (220, 220, 230),
    'panel_bg':      (35,  35,  48),
    'highlight':     (100, 140, 255),
}

AGENT_COLORS = [
    (66,  133, 244),   # Blue
    (234, 67,  53),    # Red
    (52,  168, 83),    # Green
    (251, 188, 4),     # Yellow
    (171, 71,  188),   # Purple
    (0,   172, 193),   # Teal
    (255, 112, 67),    # Deep Orange
    (141, 110, 99),    # Brown
    (63,  81,  181),   # Indigo
    (0,   150, 136),   # Teal-green
]


def get_agent_color(agent_id):
    """Get a unique color for an agent."""
    return AGENT_COLORS[agent_id % len(AGENT_COLORS)]


# ════════════════════════════════════════════════════════════════════
# Pygame-Based Real-Time Visualization
# ════════════════════════════════════════════════════════════════════

class PygameVisualizer:
    """Real-time warehouse visualization using Pygame."""

    def __init__(self, simulation, cell_size=32, fps=4):
        """
        Args:
            simulation: Simulation object (already run).
            cell_size: Pixel size of each grid cell.
            fps: Frames per second for playback.
        """
        if not PYGAME_AVAILABLE:
            raise ImportError("Pygame is not installed. Install with: pip install pygame")

        self.sim = simulation
        self.grid = simulation.grid
        self.agents = simulation.agents
        self.history = simulation.history
        self.cell_size = cell_size
        self.fps = fps

        # Layout
        self.grid_pixel_w = self.grid.width * cell_size
        self.grid_pixel_h = self.grid.height * cell_size
        self.panel_width = 320
        self.window_w = self.grid_pixel_w + self.panel_width
        self.window_h = max(self.grid_pixel_h, 600)

        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((self.window_w, self.window_h))
        pygame.display.set_caption("Warehouse Multi-Agent Simulation")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 14)
        self.font_large = pygame.font.SysFont("monospace", 18, bold=True)
        self.font_small = pygame.font.SysFont("monospace", 11)

        # Playback state
        self.current_frame = 0
        self.playing = True
        self.paused = False

    def run(self):
        """Run the visualization loop."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif event.key == pygame.K_RIGHT:
                        self.current_frame = min(self.current_frame + 1, len(self.history) - 1)
                    elif event.key == pygame.K_LEFT:
                        self.current_frame = max(self.current_frame - 1, 0)
                    elif event.key == pygame.K_r:
                        self.current_frame = 0
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_UP:
                        self.fps = min(self.fps + 1, 30)
                    elif event.key == pygame.K_DOWN:
                        self.fps = max(self.fps - 1, 1)

            if not self.paused and self.current_frame < len(self.history) - 1:
                self.current_frame += 1

            self._draw_frame()
            self.clock.tick(self.fps)

        pygame.quit()

    def _draw_frame(self):
        """Draw a single frame of the simulation."""
        if self.current_frame >= len(self.history):
            return

        snapshot = self.history[self.current_frame]
        self.screen.fill(COLORS['background'])

        self._draw_grid()
        self._draw_obstacles(snapshot)
        self._draw_tasks()
        self._draw_agent_paths()
        self._draw_agents(snapshot)
        self._draw_panel(snapshot)

        pygame.display.flip()

    def _draw_grid(self):
        """Draw the grid lines."""
        for x in range(self.grid.width + 1):
            px = x * self.cell_size
            pygame.draw.line(self.screen, COLORS['grid_line'],
                           (px, 0), (px, self.grid_pixel_h))
        for y in range(self.grid.height + 1):
            py = y * self.cell_size
            pygame.draw.line(self.screen, COLORS['grid_line'],
                           (0, py), (self.grid_pixel_w, py))

    def _draw_obstacles(self, snapshot):
        """Draw static and dynamic obstacles."""
        cs = self.cell_size

        # Static obstacles
        for (ox, oy) in self.grid.static_obstacles:
            rect = pygame.Rect(ox * cs + 1, oy * cs + 1, cs - 2, cs - 2)
            pygame.draw.rect(self.screen, COLORS['static_obs'], rect)

        # Dynamic obstacles
        for (ox, oy) in snapshot.get('dynamic_obstacles', []):
            rect = pygame.Rect(ox * cs + 1, oy * cs + 1, cs - 2, cs - 2)
            pygame.draw.rect(self.screen, COLORS['dynamic_obs'], rect)
            # Draw X mark
            pygame.draw.line(self.screen, (255, 255, 255),
                           (ox * cs + 4, oy * cs + 4),
                           ((ox + 1) * cs - 4, (oy + 1) * cs - 4), 2)
            pygame.draw.line(self.screen, (255, 255, 255),
                           ((ox + 1) * cs - 4, oy * cs + 4),
                           (ox * cs + 4, (oy + 1) * cs - 4), 2)

    def _draw_tasks(self):
        """Draw pickup and delivery locations."""
        cs = self.cell_size
        for agent in self.agents:
            color = get_agent_color(agent.agent_id)
            for task in agent.tasks:
                # Pickup location (diamond)
                if not task.picked_up:
                    px, py = task.pickup
                    cx, cy = px * cs + cs // 2, py * cs + cs // 2
                    size = cs // 4
                    points = [(cx, cy - size), (cx + size, cy),
                             (cx, cy + size), (cx - size, cy)]
                    pygame.draw.polygon(self.screen, COLORS['pickup'], points)

                # Delivery location (star marker)
                if not task.delivered:
                    dx, dy = task.delivery
                    cx, cy = dx * cs + cs // 2, dy * cs + cs // 2
                    size = cs // 4
                    pygame.draw.rect(self.screen, COLORS['delivery'],
                                   (cx - size, cy - size, size * 2, size * 2))

    def _draw_agent_paths(self):
        """Draw planned paths as faint lines."""
        cs = self.cell_size

        for agent in self.agents:
            if agent.status.value == "broken_down":
                continue
            color = get_agent_color(agent.agent_id)
            faint_color = (color[0] // 3, color[1] // 3, color[2] // 3)

            # Draw future path
            start_t = max(0, self.current_frame)
            for t in range(start_t, min(len(agent.path) - 1, start_t + 30)):
                x1, y1 = agent.path[t]
                x2, y2 = agent.path[t + 1]
                p1 = (x1 * cs + cs // 2, y1 * cs + cs // 2)
                p2 = (x2 * cs + cs // 2, y2 * cs + cs // 2)
                pygame.draw.line(self.screen, faint_color, p1, p2, 2)

    def _draw_agents(self, snapshot):
        """Draw agents at their current positions."""
        cs = self.cell_size

        for agent_info in snapshot['agents']:
            aid = agent_info['id']
            pos = agent_info['position']
            status = agent_info['status']
            color = get_agent_color(aid)

            cx = pos[0] * cs + cs // 2
            cy = pos[1] * cs + cs // 2
            radius = cs // 3

            if status == "broken_down":
                # Draw with X overlay
                pygame.draw.circle(self.screen, (100, 100, 100), (cx, cy), radius)
                pygame.draw.line(self.screen, (255, 0, 0),
                               (cx - radius // 2, cy - radius // 2),
                               (cx + radius // 2, cy + radius // 2), 3)
                pygame.draw.line(self.screen, (255, 0, 0),
                               (cx + radius // 2, cy - radius // 2),
                               (cx - radius // 2, cy + radius // 2), 3)
            elif status == "finished":
                pygame.draw.circle(self.screen, color, (cx, cy), radius)
                pygame.draw.circle(self.screen, (0, 255, 100), (cx, cy), radius, 3)
            else:
                pygame.draw.circle(self.screen, color, (cx, cy), radius)
                if agent_info.get('path_modified'):
                    pygame.draw.circle(self.screen, (255, 200, 0), (cx, cy), radius + 2, 2)

            # Agent ID label
            label = self.font_small.render(str(aid), True, (255, 255, 255))
            self.screen.blit(label, (cx - label.get_width() // 2,
                                     cy - label.get_height() // 2))

    def _draw_panel(self, snapshot):
        """Draw the information panel on the right."""
        panel_x = self.grid_pixel_w
        panel_rect = pygame.Rect(panel_x, 0, self.panel_width, self.window_h)
        pygame.draw.rect(self.screen, COLORS['panel_bg'], panel_rect)

        y = 15
        # Title
        title = self.font_large.render("Warehouse Simulation", True, COLORS['highlight'])
        self.screen.blit(title, (panel_x + 15, y))
        y += 35

        # Time
        time_text = self.font.render(f"Time Step: {snapshot['time']}", True, COLORS['text'])
        self.screen.blit(time_text, (panel_x + 15, y))
        y += 22

        # FPS
        fps_text = self.font.render(f"Playback: {self.fps} FPS", True, COLORS['text'])
        self.screen.blit(fps_text, (panel_x + 15, y))
        y += 22

        # Paused indicator
        if self.paused:
            pause_text = self.font.render("|| PAUSED", True, (255, 200, 0))
            self.screen.blit(pause_text, (panel_x + 15, y))
        y += 30

        # Separator
        pygame.draw.line(self.screen, COLORS['grid_line'],
                        (panel_x + 10, y), (panel_x + self.panel_width - 10, y))
        y += 15

        # Agent status
        header = self.font_large.render("Agents", True, COLORS['text'])
        self.screen.blit(header, (panel_x + 15, y))
        y += 25

        for agent_info in snapshot['agents']:
            aid = agent_info['id']
            color = get_agent_color(aid)
            status = agent_info['status']
            tasks_done = agent_info['tasks_done']
            total = agent_info['total_tasks']

            # Agent color indicator
            pygame.draw.circle(self.screen, color, (panel_x + 25, y + 7), 6)

            status_str = f"A{aid}: {status}"
            if status == "active":
                status_str += f" ({tasks_done}/{total})"
            text = self.font_small.render(status_str, True, COLORS['text'])
            self.screen.blit(text, (panel_x + 40, y))

            if agent_info.get('path_modified'):
                mod_text = self.font_small.render("*modified*", True, (255, 200, 0))
                self.screen.blit(mod_text, (panel_x + 200, y))

            y += 18

        y += 15
        pygame.draw.line(self.screen, COLORS['grid_line'],
                        (panel_x + 10, y), (panel_x + self.panel_width - 10, y))
        y += 15

        # Metrics
        metrics = self.sim.metrics.summary()
        header = self.font_large.render("Metrics", True, COLORS['text'])
        self.screen.blit(header, (panel_x + 15, y))
        y += 25

        metric_lines = [
            f"Disruptions: {metrics['disruptions_handled']}",
            f"Plans Modified: {metrics['total_agents_modified']}",
            f"Avg Modified/Disrupt: {metrics['avg_agents_modified_per_disruption']}",
            f"Planning Time: {metrics['initial_planning_time_ms']:.1f}ms",
        ]
        for line in metric_lines:
            text = self.font_small.render(line, True, COLORS['text'])
            self.screen.blit(text, (panel_x + 15, y))
            y += 18

        y += 20
        # Legend
        pygame.draw.line(self.screen, COLORS['grid_line'],
                        (panel_x + 10, y), (panel_x + self.panel_width - 10, y))
        y += 15
        header = self.font_large.render("Legend", True, COLORS['text'])
        self.screen.blit(header, (panel_x + 15, y))
        y += 25

        legend_items = [
            (COLORS['static_obs'], "Static Obstacle"),
            (COLORS['dynamic_obs'], "Dynamic Obstacle"),
            (COLORS['pickup'], "Pickup Location"),
            (COLORS['delivery'], "Delivery Location"),
        ]
        for color, label in legend_items:
            pygame.draw.rect(self.screen, color,
                           (panel_x + 15, y, 12, 12))
            text = self.font_small.render(label, True, COLORS['text'])
            self.screen.blit(text, (panel_x + 35, y))
            y += 18

        y += 15
        # Controls
        controls = [
            "SPACE: Play/Pause",
            "←/→ : Step Back/Fwd",
            "↑/↓ : Speed Up/Down",
            "R   : Restart",
            "ESC : Quit",
        ]
        for ctrl in controls:
            text = self.font_small.render(ctrl, True, (150, 150, 160))
            self.screen.blit(text, (panel_x + 15, y))
            y += 16


# ════════════════════════════════════════════════════════════════════
# Matplotlib-Based Visualization (Fallback)
# ════════════════════════════════════════════════════════════════════

def visualize_matplotlib(simulation, save_path=None, show=True, interval=300):
    """
    Create an animated visualization using Matplotlib.

    Args:
        simulation: Simulation object (already run).
        save_path: If provided, save animation as GIF or MP4.
        show: If True, display the animation.
        interval: Milliseconds between frames.
    """
    grid = simulation.grid
    history = simulation.history
    agents = simulation.agents

    if not history:
        print("No simulation history to visualize.")
        return

    fig, (ax_grid, ax_info) = plt.subplots(1, 2, figsize=(16, 8),
                                            gridspec_kw={'width_ratios': [3, 1]})
    fig.patch.set_facecolor('#1e1e28')

    def draw_frame(frame_idx):
        ax_grid.clear()
        ax_info.clear()

        if frame_idx >= len(history):
            frame_idx = len(history) - 1

        snapshot = history[frame_idx]

        # ── Grid Background ──
        ax_grid.set_facecolor('#2d2d3a')
        ax_grid.set_xlim(-0.5, grid.width - 0.5)
        ax_grid.set_ylim(-0.5, grid.height - 0.5)
        ax_grid.set_aspect('equal')
        ax_grid.invert_yaxis()
        ax_grid.set_title(f"Warehouse Simulation — Time Step {snapshot['time']}",
                         color='white', fontsize=14, fontweight='bold', pad=15)

        # Grid lines
        for x in range(grid.width + 1):
            ax_grid.axvline(x - 0.5, color='#3a3a4a', linewidth=0.5)
        for y in range(grid.height + 1):
            ax_grid.axhline(y - 0.5, color='#3a3a4a', linewidth=0.5)

        # Static obstacles
        for (ox, oy) in grid.static_obstacles:
            rect = patches.Rectangle((ox - 0.45, oy - 0.45), 0.9, 0.9,
                                    facecolor='#505060', edgecolor='#606070',
                                    linewidth=0.5)
            ax_grid.add_patch(rect)

        # Dynamic obstacles
        for (ox, oy) in snapshot.get('dynamic_obstacles', []):
            rect = patches.Rectangle((ox - 0.45, oy - 0.45), 0.9, 0.9,
                                    facecolor='#dc3c3c', edgecolor='#ff5555',
                                    linewidth=1.5)
            ax_grid.add_patch(rect)
            ax_grid.plot(ox, oy, 'x', color='white', markersize=8, markeredgewidth=2)

        # Task locations
        for agent in agents:
            a_color = np.array(get_agent_color(agent.agent_id)) / 255.0
            for task in agent.tasks:
                if not task.picked_up:
                    px, py = task.pickup
                    ax_grid.plot(px, py, 'D', color='#00c878', markersize=8,
                               markeredgecolor='white', markeredgewidth=0.5)
                if not task.delivered:
                    dx, dy = task.delivery
                    ax_grid.plot(dx, dy, 's', color='#ffb400', markersize=8,
                               markeredgecolor='white', markeredgewidth=0.5)

        # Agent paths (faded)
        for agent in agents:
            if agent.status.value == "broken_down":
                continue
            a_color = np.array(get_agent_color(agent.agent_id)) / 255.0
            start_t = max(0, frame_idx)
            end_t = min(len(agent.path), start_t + 20)
            if end_t > start_t + 1:
                path_x = [agent.path[t][0] for t in range(start_t, end_t)]
                path_y = [agent.path[t][1] for t in range(start_t, end_t)]
                ax_grid.plot(path_x, path_y, '-', color=(*a_color[:3], 0.3),
                           linewidth=2)

        # Agents
        for agent_info in snapshot['agents']:
            aid = agent_info['id']
            pos = agent_info['position']
            status = agent_info['status']
            a_color = np.array(get_agent_color(aid)) / 255.0

            if status == "broken_down":
                ax_grid.plot(pos[0], pos[1], 'o', color='gray', markersize=14,
                           markeredgecolor='red', markeredgewidth=2)
                ax_grid.plot(pos[0], pos[1], 'x', color='red', markersize=10,
                           markeredgewidth=2)
            elif status == "finished":
                ax_grid.plot(pos[0], pos[1], 'o', color=a_color, markersize=14,
                           markeredgecolor='#00ff64', markeredgewidth=2.5)
            else:
                ax_grid.plot(pos[0], pos[1], 'o', color=a_color, markersize=14,
                           markeredgecolor='white', markeredgewidth=1)
                if agent_info.get('path_modified'):
                    ax_grid.plot(pos[0], pos[1], 'o', color='none', markersize=18,
                               markeredgecolor='#ffc800', markeredgewidth=2)

            ax_grid.text(pos[0], pos[1], str(aid), ha='center', va='center',
                        color='white', fontsize=8, fontweight='bold')

        ax_grid.tick_params(colors='#888888', labelsize=8)

        # ── Info Panel ──
        ax_info.set_facecolor('#23232f')
        ax_info.set_xlim(0, 1)
        ax_info.set_ylim(0, 1)
        ax_info.axis('off')

        y = 0.95
        ax_info.text(0.05, y, "Agent Status", color='white', fontsize=13,
                    fontweight='bold', transform=ax_info.transAxes)
        y -= 0.05

        for agent_info in snapshot['agents']:
            aid = agent_info['id']
            a_color = np.array(get_agent_color(aid)) / 255.0
            status = agent_info['status']
            tasks_done = agent_info['tasks_done']
            total = agent_info['total_tasks']

            label = f"A{aid}: {status} ({tasks_done}/{total})"
            if agent_info.get('path_modified'):
                label += " *"
            ax_info.text(0.08, y, "●", color=a_color, fontsize=12,
                        transform=ax_info.transAxes)
            ax_info.text(0.15, y, label, color='#ddd', fontsize=9,
                        transform=ax_info.transAxes)
            y -= 0.04

        y -= 0.03
        metrics = simulation.metrics.summary()
        ax_info.text(0.05, y, "Metrics", color='white', fontsize=13,
                    fontweight='bold', transform=ax_info.transAxes)
        y -= 0.05

        metric_lines = [
            f"Total Steps: {metrics['total_time_steps']}",
            f"Agents Done: {metrics['agents_finished']}/{metrics['total_agents']}",
            f"Disruptions: {metrics['disruptions_handled']}",
            f"Plans Modified: {metrics['total_agents_modified']}",
            f"Avg Mod/Disruption: {metrics['avg_agents_modified_per_disruption']}",
        ]
        for line in metric_lines:
            ax_info.text(0.08, y, line, color='#bbb', fontsize=9,
                        transform=ax_info.transAxes)
            y -= 0.04

        y -= 0.03
        ax_info.text(0.05, y, "Legend", color='white', fontsize=13,
                    fontweight='bold', transform=ax_info.transAxes)
        y -= 0.05
        legend_items = [
            ('#505060', '■ Static Obstacle'),
            ('#dc3c3c', '■ Dynamic Obstacle'),
            ('#00c878', '◆ Pickup Location'),
            ('#ffb400', '■ Delivery Location'),
        ]
        for color, label in legend_items:
            ax_info.text(0.08, y, label, color=color, fontsize=9,
                        transform=ax_info.transAxes)
            y -= 0.04

    # Create animation
    num_frames = len(history)
    anim = animation.FuncAnimation(fig, draw_frame, frames=num_frames,
                                    interval=interval, repeat=True)

    if save_path:
        print(f"Saving animation to {save_path}...")
        if save_path.endswith('.gif'):
            anim.save(save_path, writer='pillow', fps=max(1, 1000 // interval))
        else:
            anim.save(save_path, writer='ffmpeg', fps=max(1, 1000 // interval))
        print(f"Animation saved to {save_path}")

    if show:
        plt.tight_layout()
        plt.show()

    return anim


def plot_static_snapshot(simulation, time_step=0, save_path=None):
    """
    Create a static snapshot of the simulation at a given time step.

    Args:
        simulation: Simulation object (already run).
        time_step: Time step to visualize.
        save_path: If provided, save the plot to this path.
    """
    grid = simulation.grid
    agents = simulation.agents

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    fig.patch.set_facecolor('#1e1e28')
    ax.set_facecolor('#2d2d3a')

    ax.set_xlim(-0.5, grid.width - 0.5)
    ax.set_ylim(-0.5, grid.height - 0.5)
    ax.set_aspect('equal')
    ax.invert_yaxis()
    ax.set_title(f"Warehouse State at Time Step {time_step}",
                color='white', fontsize=14, fontweight='bold')

    # Grid lines
    for x in range(grid.width + 1):
        ax.axvline(x - 0.5, color='#3a3a4a', linewidth=0.5)
    for y in range(grid.height + 1):
        ax.axhline(y - 0.5, color='#3a3a4a', linewidth=0.5)

    # Static obstacles
    for (ox, oy) in grid.static_obstacles:
        rect = patches.Rectangle((ox - 0.45, oy - 0.45), 0.9, 0.9,
                                facecolor='#505060', edgecolor='#606070')
        ax.add_patch(rect)

    # Dynamic obstacles
    for (ox, oy) in grid.dynamic_obstacles:
        rect = patches.Rectangle((ox - 0.45, oy - 0.45), 0.9, 0.9,
                                facecolor='#dc3c3c', edgecolor='#ff5555')
        ax.add_patch(rect)

    # Agent paths
    for agent in agents:
        a_color = np.array(get_agent_color(agent.agent_id)) / 255.0
        if len(agent.path) > 1:
            path_x = [p[0] for p in agent.path]
            path_y = [p[1] for p in agent.path]
            ax.plot(path_x, path_y, '-', color=(*a_color[:3], 0.4), linewidth=2,
                   label=f"Agent {agent.agent_id}")

        # Tasks
        for task in agent.tasks:
            ax.plot(task.pickup[0], task.pickup[1], 'D', color='#00c878',
                   markersize=8, markeredgecolor='white', markeredgewidth=0.5)
            ax.plot(task.delivery[0], task.delivery[1], 's', color='#ffb400',
                   markersize=8, markeredgecolor='white', markeredgewidth=0.5)

    # Agents at time_step
    for agent in agents:
        pos = agent.get_position_at(time_step)
        a_color = np.array(get_agent_color(agent.agent_id)) / 255.0
        ax.plot(pos[0], pos[1], 'o', color=a_color, markersize=16,
               markeredgecolor='white', markeredgewidth=1.5)
        ax.text(pos[0], pos[1], str(agent.agent_id), ha='center', va='center',
               color='white', fontsize=9, fontweight='bold')

    ax.legend(facecolor='#2d2d3a', edgecolor='#444', labelcolor='white',
             fontsize=9, loc='upper right')
    ax.tick_params(colors='#888888')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, facecolor=fig.get_facecolor())
        print(f"Snapshot saved to {save_path}")

    plt.show()
