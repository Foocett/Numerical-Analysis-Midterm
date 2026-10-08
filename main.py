"""Numerical cellular automaton engine

The transition rules live in ``rules.json`` rather than in the update
algorithm.  This keeps the numerical part reusable by a future GUI.
"""
# TODO Implement GUI support for the cellular automaton

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import matplotlib.pyplot as plt
from tkinter import filedialog


@dataclass(frozen=True)
class TransitionRule:
    """A rule matching one current cell state and selected neighbor counts."""

    state: int
    neighbor_counts: dict[int, set[int]]
    next_state: int

    def matches(self, state: int, counts: dict[int, int]) -> bool:
        if state != self.state:
            return False
        return all(counts.get(neighbor_state, 0) in allowed_counts
                   for neighbor_state, allowed_counts in self.neighbor_counts.items())


class CellularAutomaton:
    """A rectangular, finite cellular automaton with Moore-neighborhood rules.

    Cells outside the board are treated as ``default_state``.  Updates are
    synchronous: every next cell is calculated from the same previous grid.
    """

    def __init__(
        self,
        state: np.ndarray,
        rules: list[TransitionRule],
        *,
        default_state: int = 0,
        edge_mode: str = "dead",
    ) -> None:
        grid = np.asarray(state, dtype=int)
        if grid.ndim != 2 or grid.size == 0:
            raise ValueError("state must be a non-empty two-dimensional array")
        if edge_mode != "dead":
            raise ValueError("only edge_mode='dead' is currently supported")
        self.state = grid.copy()
        self.rules = rules
        self.default_state = default_state
        self.edge_mode = edge_mode
        self.generation = 0
        self.running = True

    @classmethod
    def from_config(cls, state: np.ndarray, config: dict[str, Any]) -> "CellularAutomaton":
        rules = [
            TransitionRule(
                state=int(rule["state"]),
                neighbor_counts={
                    int(neighbor_state): {int(count) for count in counts}
                    for neighbor_state, counts in rule.get("neighbors", {}).items()
                },
                next_state=int(rule["next_state"]),
            )
            for rule in config["transitions"]
        ]
        return cls(
            state,
            rules,
            default_state=int(config.get("default_state", 0)),
            edge_mode=str(config.get("edge_mode", "dead")),
        )

    @property
    def shape(self) -> tuple[int, int]:
        return self.state.shape

    def pause(self) -> None:
        """Freeze the current state so a future UI can stop advancing it."""
        self.running = False

    def resume(self) -> None:
        """Allow the automaton to advance again."""
        self.running = True

    def step(self) -> np.ndarray:
        """Advance one generation and return a copy of the new state."""
        if not self.running:
            return self.state.copy()

        padded = np.pad(
            self.state,
            pad_width=1,
            mode="constant",
            constant_values=self.default_state,
        )
        next_state = self.state.copy()
        for row in range(self.shape[0]):
            for column in range(self.shape[1]):
                neighborhood = padded[row:row + 3, column:column + 3]
                counts = {
                    value: int(np.count_nonzero(neighborhood == value))
                    for value in np.unique(neighborhood)
                }
                counts[self.state[row, column]] -= 1
                next_state[row, column] = self._next_cell_state(
                    int(self.state[row, column]), counts
                )

        self.state = next_state
        self.generation += 1
        return self.state.copy()

    def _next_cell_state(self, state: int, counts: dict[int, int]) -> int:
        for rule in self.rules:
            if rule.matches(state, counts):
                return rule.next_state
        return state

    def render_terminal(self) -> str:
        """Return a compact text rendering for checking numerical behavior."""
        return "\n".join(" ".join(str(cell) for cell in row) for row in self.state)

    def save_state(self, path: str | Path) -> None:
        """Save the current grid and generation for pause/resume or demos."""
        payload = {
            "generation": self.generation,
            "state": self.state.tolist(),
        }
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load_state(
        cls,
        path: str | Path,
        rules: list[TransitionRule],
        *,
        default_state: int = 0,
        edge_mode: str = "dead",
    ) -> "CellularAutomaton":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        automaton = cls(
            np.asarray(payload["state"], dtype=int),
            rules,
            default_state=default_state,
            edge_mode=edge_mode,
        )
        automaton.generation = int(payload.get("generation", 0))
        return automaton


def load_config(path: str | Path) -> dict[str, Any]:
    """Load and minimally validate a JSON rules configuration."""
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(config.get("transitions"), list):
        raise ValueError("rules configuration must contain a transitions list")
    return config


def initial_demo_state(size: int = 15) -> np.ndarray:
    """Create a centered blinker, a simple pattern for terminal testing."""
    state = np.zeros((size, size), dtype=int)
    center = size // 2
    state[center, center - 1:center + 2] = 1
    return state


def run_terminal_demo(config_path: Path, generations: int) -> None:
    config = load_config(config_path)
    automaton = CellularAutomaton.from_config(initial_demo_state(), config)

    print(f"Generation {automaton.generation}")
    print(automaton.render_terminal())
    for _ in range(generations):
        automaton.step()
        print(f"\nGeneration {automaton.generation}")
        print(automaton.render_terminal())

    # Future GUI Implementation:
    # create one matplotlib image for automaton.state
    # on each timer tick: automaton.step(); update the existing image
    # on a pause button: automaton.pause()
    # on a resume button: automaton.resume()
    # on a load button: replace the model with CellularAutomaton.load_state(...)

def run_gui(config_path: Path) -> None:
    config = load_config(config_path)
    automaton = CellularAutomaton.from_config(initial_demo_state(), config)

    #start paused
    automaton.pause()

    fig, ax = plt.subplots(figsize=(7.5,7.5))
    fig.subplots_adjust(bottom=0.20)
    fig.suptitle("Cellular Automaton", fontsize=18, fontweight="bold")
    image = ax.imshow(automaton.state, cmap="binary", interpolation="nearest", extent=(-0.5, 14.5, 14.5, -0.5))

    
    ax.set_title(f"Generation {automaton.generation}")

    # Add grid lines
    rows, cols = automaton.state.shape

    for x in range(cols + 1):
        ax.axvline(x - 0.5, linewidth=0.5)

    for y in range(rows + 1):
        ax.axhline(y - 0.5, linewidth=0.5)

    ax.set_xticks([])
    ax.set_yticks([])

    ax.set_xticklabels([])
    ax.set_yticklabels([])


    #pause/start button at bottom window
    pause_ax = fig.add_axes([0.20, 0.04, 0.17, 0.07])
    pause_button = plt.Button(pause_ax, "Start", color="seagreen", hovercolor="green")
    pause_button.label.set_color("white")

    #load Prepared States button at bottom window
    pre_state_ax = fig.add_axes([0.415, 0.04, 0.22, 0.07])
    pre_state_button = plt.Button(pre_state_ax, "Prepared States", color="steelblue", hovercolor="royalblue")
    pre_state_button.label.set_color("white")

    #load State from File button
    file_state_ax = fig.add_axes([0.68, 0.04, 0.17, 0.07])
    file_state_button = plt.Button(file_state_ax, "Load File", color="darkorange", hovercolor="orange")
    file_state_button.label.set_color("white")

    #exit button at top
    exit_ax = fig.add_axes([0.82, 0.90, 0.10, 0.06])
    exit_button = plt.Button(exit_ax, "Exit", color="firebrick", hovercolor="red")
    exit_button.label.set_color("white")

    def update_display() -> None:
        image.set_data(automaton.state)
        ax.set_title(f"Generation {automaton.generation}")
        fig.canvas.draw_idle()

    def exit_program(event):
        plt.close(fig)

    exit_button.on_clicked(exit_program)

    def load_selected_state(file_path):
        new_automaton = CellularAutomaton.load_state(file_path, automaton.rules, default_state=automaton.default_state, edge_mode=automaton.edge_mode,)

        automaton.state = new_automaton.state
        automaton.generation = new_automaton.generation

        automaton.pause()
        pause_button.label.set_text("Start")

        update_display()

    def load_prepared_state(event):
        states_folder = Path(__file__).with_name("states")

        file_path = filedialog.askopenfilename(title="Select Prepared State", initialdir=states_folder, filetypes=[("JSON files", "*.json")])

        if not file_path:
            return

        load_selected_state(Path(file_path))

    pre_state_button.on_clicked(load_prepared_state)

    def load_state_from_file(event):
        file_path = filedialog.askopenfilename(title="Select State File", filetypes=[("JSON files", "*.json")])

        if not file_path:
            return

        load_selected_state(Path(file_path))

    file_state_button.on_clicked(load_state_from_file)


    def toggle_pause(event) -> None:
        if automaton.running:
            automaton.pause()
            pause_button.label.set_text("Start")
        else:
            automaton.resume()
            pause_button.label.set_text("Pause")

        update_display()

    pause_button.on_clicked(toggle_pause)

    def on_click(event):
        #no edit while running
        if automaton.running:
            return

        #grid don't respond to button clicks
        if event.inaxes != ax:
            return

        #check click in grid
        if event.xdata is None or event.ydata is None:
            return

        row = int(round(event.ydata))
        col = int(round(event.xdata))

        #check cell on board
        if( row < 0 or row >= automaton.state.shape[0] or col < 0 or col >= automaton.state.shape[1]):
            return

        #toggle cell
        if automaton.state[row, col] == 0:
            automaton.state[row, col] = 1
        else:
            automaton.state[row, col] = 0

        update_display()

    fig.canvas.mpl_connect("button_press_event", on_click)
    

    def update_animation() -> None:
        if automaton.running:
            automaton.step()
            update_display()

    timer = fig.canvas.new_timer(interval=500)
    timer.add_callback(update_animation)
    timer.start()

    plt.show()
    

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the cellular automaton numerically.")
    parser.add_argument(
        "--rules",
        type=Path,
        default=Path(__file__).with_name("rules.json"),
        help="JSON transition-rule file",
    )
    parser.add_argument("--generations", type=int, default=4)
    args = parser.parse_args()
    if args.generations < 0:
        parser.error("--generations must be non-negative")


    run_gui(args.rules)


if __name__ == "__main__":
    main()
