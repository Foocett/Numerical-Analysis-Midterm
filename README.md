# Numerical Analysis Midterm: Configurable Cellular Automaton

## 1. Project overview

This project implements a finite, two-dimensional cellular automaton in Python.
The numerical engine is separated from the rule data: the update algorithm is
implemented in [`main.py`](main.py), while transition rules are stored in JSON
files. The project also includes a Matplotlib interface for observing and
editing the automaton interactively.

The default configuration is intentionally similar to Conway's Game of Life:

- The board is a finite `15 x 15` rectangular grid.
- Each cell has an integer state, normally `0` (dead) or `1` (alive).
- A cell examines its eight surrounding cells (a Moore neighborhood).
- All cells update synchronously, meaning that one generation is calculated
  entirely from the previous generation.
- Cells outside the board are assigned the configured `default_state`.
- Rules are evaluated in the order in which they appear in the JSON file.

This repository contains a reusable
state-transition engine, configuration parsing, state serialization, a
terminal-rendering method for numerical checks, and a GUI layer that exposes pause/resume, rule switching, prepared-state loading, file loading, and interactive cell editing.

## 2. Contents of this report

This document is deliberately more detailed than a conventional README as it also serves as the project report. It covers:

1. the problem being solved and the model assumptions;
2. installation and execution;
3. the JSON input formats;
4. the numerical update algorithm;
5. the object and function responsibilities;
6. the graphical user interface;
7. persistence and prepared examples;
8. computational complexity;
9. validation performed against the implementation;
10. limitations, design observations, and possible extensions.

## 3. Requirements and environment

The project metadata is defined in [`pyproject.toml`](pyproject.toml).
The declared Python requirement is **Python 3.14 or newer**. The runtime
dependencies are:

| Dependency | Purpose |
| --- | --- |
| `numpy` | Stores the grid and performs padding, unique-value discovery, and neighborhood counting. |
| `matplotlib` | Displays the grid and supplies the figure, image, buttons, and timer. |
| `tkinter` | Provides native file-selection dialogs through `tkinter.filedialog`. |

### Recommended setup with `uv`

From the repository directory:

```powershell
uv sync
```

This uses [`pyproject.toml`](pyproject.toml) and [`uv.lock`](uv.lock) to
reproduce the declared dependency environment. If `uv` is not installed, the
equivalent conceptual steps are to create a Python 3.14 virtual environment
and install NumPy and Matplotlib into it.

### Windows virtual-environment command

The checked-in environment can be invoked directly:

```powershell
.venv\Scripts\python.exe main.py
```

On macOS or Linux, use the corresponding interpreter path, for example
`.venv/bin/python main.py`.

Matplotlib must be able to select a desktop backend. The GUI is therefore
intended for a machine with a graphical display; a headless server may need a
non-interactive backend for numerical-only work.

## 4. Running the program

### Launch the GUI with the default rules

```powershell
.venv\Scripts\python.exe main.py
```

The default rules file is `rules.json`, selected by
`Path(__file__).with_name("rules.json")`. Consequently, the command works
independently of the current working directory as long as `main.py` is used
from its repository location.

### Select another rules file

```powershell
.venv\Scripts\python.exe main.py --rules 3_state_rules.json
```

The `--rules` argument is a `Path` argument. It can be a relative or absolute
path. The GUI also provides a **Rules** button that opens a JSON file chooser.

### Generation argument: important implementation note

The command-line parser accepts:

```powershell
.venv\Scripts\python.exe main.py --generations 10
```

It rejects negative values, but the value is not currently passed to the
simulation: `main()` always calls `run_gui(args.rules)`. Therefore,
`--generations` does **not** make the program run ten generations and exit.
The visible application is timer-driven and continues until the user exits it.

The function `run_terminal_demo(config_path, generations)` does implement a
finite terminal loop, but it is not selected by the current command-line
entry point. This distinction is important when reproducing results:

- **Implemented GUI path:** starts at generation 0, initially paused, and
  advances one generation every 500 milliseconds after Start is pressed.
- **Implemented terminal helper:** prints generation 0, then performs exactly
  the requested number of calls to `step()`.
- **Current CLI behavior:** parses `--generations`, validates it, and then
  launches the GUI rather than calling the terminal helper.

## 5. User interface guide

When the program opens, it displays a square grid titled **Cellular
Automaton**. The initial pattern is a centered horizontal three-cell line
created by `initial_demo_state()`. The application begins paused.

### Start/Pause button

The green button initially says **Start**. Clicking it calls
`CellularAutomaton.resume()` and changes the label to **Pause**. While running,
the Matplotlib timer calls `step()` every 500 ms. Clicking the button again
calls `pause()`, freezes the numerical state, and changes the label back to
**Start**.

### Rules button

The **Rules** button opens a file chooser starting beside `main.py`. Selecting
a JSON rules file:

1. parses the new configuration;
2. replaces the automaton's transition rules;
3. updates `default_state` and `edge_mode`;
4. clears the board to zeros;
5. resets the generation counter to zero;
6. pauses the automaton;
7. recalculates the colormap range.

Changing rules therefore does not preserve the current pattern. This reset is
intentional in the current GUI implementation.

### Prepared States button

The **Prepared States** button opens the repository's [`states`](states)
directory. It is intended for demonstrations of recognizable automaton
patterns, including:

- `block.json`;
- `glider.json`;
- `overpopulation_death.json`;
- `single_cell_death.json`;
- `survival_two_neighbors.json`;
- `toad.json`.

Loading one of these files replaces the grid and generation number, then
pauses the automaton.

### Load File button

The **Load File** button opens a general JSON chooser, so a state file can be
loaded from another directory. The selected file must follow the state format
described below and must contain a non-empty two-dimensional `state` array.

### Editing cells

When paused, clicking a grid cell cycles it through the available state values.
For a two-state rule set this is:

```text
0 -> 1 -> 0
```

For a rule set whose maximum declared state is at least `2`, the interface
uses:

```text
0 -> 1 -> 2 -> 0
```

Clicks are ignored while the automaton is running. Button clicks are also
ignored by the grid handler because it checks that the click occurred inside
the axes containing the board.

### Exit button

The red **Exit** button closes the Matplotlib figure and ends the GUI event
loop.

## 6. Mathematical model

Let the grid at generation `t` be an integer matrix:

```text
S_t[r, c]
```

For each cell `(r, c)`, the implementation examines a `3 x 3` window centered
on that cell. The center value is removed from the neighborhood count, leaving
the eight surrounding positions:

```text
N_t(r, c) = {S_t[r+i, c+j] : i,j in {-1,0,1}, (i,j) != (0,0)}
```

At the border, the grid is padded by one cell in every direction. The padding
value is `default_state`, which is `0` for both supplied rule files. This
creates a finite board with dead outside cells rather than a torus or an
infinite automatically expanding board.

A transition rule has three components:

```text
(current_state, required_neighbor_counts, next_state)
```

A rule matches when:

1. the cell's current state equals `current_state`; and
2. every listed neighbor state has a count contained in its allowed set.

Neighbor states omitted from a rule are wildcards. They are not required to
have a particular count. If no rule matches, the cell retains its current
state. This provides an implicit identity/default transition without needing
to list every possible neighborhood.

The update is synchronous. The code copies the old grid into `next_state`,
calculates every result from the old `self.state`, and only assigns
`self.state = next_state` after all cells have been processed. A cell updated
early in the nested loops cannot influence a cell updated later in the same
generation.

## 7. Rule-file format

### Top-level schema

Both supplied rule files have this shape:

```json
{
  "default_state": 0,
  "edge_mode": "dead",
  "transitions": [
    {
      "state": 0,
      "neighbors": {
        "1": [3]
      },
      "next_state": 1
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `default_state` | Value used outside the finite board. Defaults to `0` if omitted. |
| `edge_mode` | Currently must be `"dead"`. Other values are rejected by the constructor. |
| `transitions` | Required list of transition objects. |
| transition `state` | Current state of the cell to which the rule applies. |
| transition `neighbors` | Mapping from neighbor-state values to allowed counts. |
| transition `next_state` | State assigned when the rule matches. |

JSON object keys are strings, so `from_config()` converts neighbor-state keys
to integers. Counts are converted to integer sets, which removes duplicate
values and makes membership checks efficient.

### Default `rules.json`

The default file contains three transitions:

1. A dead cell with exactly three state-`1` neighbors becomes state `1`.
2. A live cell with two or three state-`1` neighbors remains state `1`.
3. A live cell with any listed count other than two or three becomes state `0`.

The third rule lists `[0, 1, 4, 5, 6, 7, 8]`, which covers all other possible
counts for an eight-cell neighborhood. Since rules are checked in order, the
survival rule is reached before the death rule for counts two and three.

### `3_state_rules.json`

The alternate file demonstrates a three-state automaton:

1. state `0` becomes `1` with exactly two state-`1` neighbors;
2. state `1` always becomes `2`;
3. state `2` always becomes `0`.

The empty `neighbors` object means “no neighbor-count restriction.” This is
different from requiring zero neighbors: it is a wildcard that matches every
neighborhood.

### Rule ordering

Rule ordering is semantically significant. `_next_cell_state()` returns the
`next_state` from the first matching rule. Overlapping rules should therefore
be ordered from most specific or highest-priority to least specific. A later
rule cannot override an earlier rule that already matched.

## 8. Saved-state format

The state files in [`states`](states) are JSON documents with two fields:

```json
{
  "generation": 0,
  "state": [
    [0, 0, 0],
    [0, 1, 0],
    [0, 0, 0]
  ]
}
```

`save_state()` writes the current generation and converts the NumPy array to
ordinary nested Python lists using `tolist()`. `load_state()` converts the
loaded list back to an integer NumPy array. If `generation` is missing, it
defaults to zero.

The state file deliberately does not store transition rules. A state is
interpreted using the rules currently active in the automaton. This means that
the same saved grid can evolve differently under different rule files.

The loader performs structural validation indirectly through the
`CellularAutomaton` constructor: the state must be non-empty and two
dimensional. It does not currently validate that every cell value is within
the range of states used by the selected rules.

## 9. Technical architecture

All application code currently resides in [`main.py`](main.py). Its
responsibilities can be divided into four layers.

### 9.1 Rule model: `TransitionRule`

`TransitionRule` is a frozen dataclass with:

- `state: int`;
- `neighbor_counts: dict[int, set[int]]`;
- `next_state: int`.

The `matches()` method first checks the current state. It then checks each
requested neighbor state using `counts.get(neighbor_state, 0)`. A state absent
from the neighborhood is therefore counted as zero, and each allowed count is
tested using set membership.

The dataclass is frozen so the rule record cannot be reassigned after
creation. The dictionaries and sets inside it are still ordinary mutable
objects, so “frozen” should be understood as protection against normal field
reassignment rather than deep immutability.

### 9.2 Numerical model: `CellularAutomaton`

The class owns:

- the current NumPy grid in `self.state`;
- the ordered rule list;
- the outside-board value;
- the edge-mode label;
- the generation number;
- the running/paused flag.

The constructor copies the input grid so later changes to the caller's array
do not automatically change the automaton. It rejects empty arrays, arrays
with dimensions other than two, and unsupported edge modes.

`from_config()` is the adapter between JSON dictionaries and typed
`TransitionRule` objects. `shape` exposes the current two-dimensional shape.
`pause()` and `resume()` only change the `running` flag.

### 9.3 Update pipeline: `step()`

The numerical update follows this sequence:

1. If paused, return a copy of the current state without changing generation.
2. Pad the grid by one cell using `default_state`.
3. Allocate `next_state` as a copy of the current grid.
4. Visit each row and column.
5. Extract the corresponding `3 x 3` neighborhood.
6. Count every value appearing in that window with NumPy.
7. Subtract one from the current cell's own count.
8. Find the first matching transition.
9. Write the result into `next_state`.
10. Replace the current grid and increment `generation`.
11. Return a copy of the new state.

Returning copies prevents a caller from accidentally modifying the automaton's
internal array through the return value.

### 9.4 Presentation and persistence helpers

`render_terminal()` turns each row into a space-separated string. It is useful
for reproducible textual inspection and for the terminal demo.

`load_config()` reads JSON and performs the minimum top-level validation:
`transitions` must be a list. Detailed field conversion is performed later by
`from_config()`, so malformed transition fields can still raise JSON, key, or
conversion errors.

`initial_demo_state()` creates the centered three-cell starting pattern.
`run_terminal_demo()` prints the initial grid and then prints each requested
generation.

`get_cmap_and_max_states()` chooses a two-color map for binary rules and a
black/gray/white map when the declared maximum state is at least two.

## 10. GUI implementation details

`run_gui()` creates the model, pauses it, and displays the NumPy array with
`ax.imshow()`. The image uses nearest-neighbor interpolation so each cell
remains visually distinct. The axes and tick labels are hidden to make the
board look like a clean cell grid.

The buttons are Matplotlib widget axes rather than a separate GUI framework.
Each button registers a callback. The GUI's nested helper functions close over
the same `automaton`, `image`, `pause_button`, and `fig` objects, which allows
callbacks to update both the model and the display.

The timer is created with a 500 millisecond interval. Its callback only calls
`step()` when `automaton.running` is true, then refreshes the image title and
data. The model remains the source of truth; the image is a view of it.

When rules change, the callback rebuilds the rules and updates the image
colormap and limits. When a state changes, `update_display()` calls
`image.set_data()` and `fig.canvas.draw_idle()` rather than constructing a
new figure. This is more efficient and preserves the existing controls.

## 11. Complexity and numerical considerations

Let the board contain `R x C` cells, let `K` be the number of rules, and let
`U` be the number of distinct values in a local neighborhood.

### Time complexity

Each call to `step()` visits every cell once and performs a constant-size
neighborhood extraction and count. The rule scan can inspect up to `K` rules
per cell. The practical upper bound is therefore:

```text
O(R * C * (K + U))
```

Because a neighborhood contains only nine positions, `U <= 9`, so for a fixed
rule set the operation is effectively linear in the number of cells:

```text
O(R * C)
```

### Space complexity

The padded array and next-state array are each proportional to the board size,
so the main additional storage is:

```text
O(R * C)
```

The implementation favors clarity and correctness over maximum vectorization:
it uses Python nested loops around small NumPy operations. This is suitable for
the 15 x 15 demonstration board. Much larger boards would benefit from
precomputed neighborhood counts, vectorized kernels, sparse representations,
or compiled numerical code.

### Boundary behavior

Padding with `default_state` means edge cells have fewer effective in-board
neighbors. The missing positions are treated as outside-board cells with the
default value. This is a fixed/dead boundary, not wraparound. The
`edge_mode` field is retained in the model and configuration for future
extension, but only `"dead"` is accepted today.

## 12. Validation and observed behavior

The implementation was inspected across the repository, including the Python
source, both rule files, all six state files, project metadata, and the lock
file. The following runtime facts were also checked with the repository's
virtual environment:

| Check | Observed result |
| --- | --- |
| Initial demo dimensions | `(15, 15)` |
| Initial generation | `0` |
| Initial running flag after direct construction | `True` |
| Initial nonzero cells | `3` |
| Default rule count | `3` |
| Generation after one running step | `1` |
| Nonzero cells after one default-rule step | `3` |
| Prepared state files | 6 JSON files |
| Alternate transition count | 3 |
| Syntax check | No syntax errors |
| Pylance diagnostics | Only unused callback-parameter warnings and one unused `_filler` warning |
| Import resolution | NumPy and Matplotlib resolve; no unresolved imports were reported |

The GUI itself requires an interactive display, so numerical checks were
performed through direct model construction rather than attempting to automate
button clicks. The source was also checked for the callback wiring and timer
behavior described above.

## 13. Current limitations and design observations

The following are implementation facts rather than hypothetical concerns:

1. **The CLI is GUI-only in practice.** The parser exposes `--generations`,
   but `main()` does not call `run_terminal_demo()`. The argument is validated
   but otherwise unused.
2. **There is no automated test suite.** The engine has a terminal renderer and
   a terminal-demo helper, but no test files are currently present.
3. **Configuration validation is intentionally minimal.** Missing transition
   fields, invalid neighbor counts, and unsupported value types may produce
   lower-level exceptions rather than a friendly configuration error.
4. **The GUI assumes a fixed visual extent.** `imshow()` uses an extent based on
   coordinates `-0.5` through `14.5`, which matches the default 15 x 15 board
   but is not recalculated for a loaded state with a different shape.
5. **The colormap supports the supplied binary and three-state examples.**
   A configuration with states above `2` is not given a distinct color for
   every state by the current helper.
6. **Saving is available as a model method but not as a GUI button.**
   `CellularAutomaton.save_state()` can be called by Python code, while the
   interface currently offers loading but not saving.
7. **The state file does not record its rules.** Reproducibility requires
   preserving both the state JSON and the rule JSON used to evolve it.
8. **Errors from file dialogs are not converted into GUI messages.** Invalid
   JSON or invalid state data will propagate as exceptions instead of being
   displayed in an application-specific error dialog.

These limitations do not prevent the supplied demonstrations from working, but
they are important when describing the project as an extensible numerical
engine rather than a finished production application.

## 14. Suggested future improvements

If the project is extended after the assignment, the highest-value changes
would be:

1. Add an explicit CLI mode, such as `--terminal`, and make
   `--generations` control `run_terminal_demo()`.
2. Add automated tests for rule matching, synchronous updates, edge cells,
   pause/resume, save/load round trips, and malformed configurations.
3. Add schema-level validation with clear messages for transition fields,
   integer states, counts from `0` through `8`, and rectangular state arrays.
4. Recalculate the image extent and board layout from `automaton.shape`.
5. Generate a color for every state used by a configuration.
6. Add a Save State button and include the active rule-file path in saved
   metadata.
7. Add a status area showing the current generation, running state, active
   rules file, and selected state.
8. Isolate GUI code from the model more formally so the numerical engine can
   be tested without importing graphical dependencies.
9. Replace the per-cell counting loop with a vectorized or compiled
   implementation if board sizes become substantially larger.
10. Provide reproducible example commands and expected terminal output for the
    prepared patterns.

## 15. Assignment conclusion

The project demonstrates the central numerical-analysis idea of iterating a
discrete state-transition system. Its strongest design decision is separating
the transition data from the update mechanism: the same engine can run the
default two-state rules, the supplied three-state rules, and additional
compatible configurations without changing the core `step()` algorithm.

The model is deterministic for a fixed initial state, rule list, boundary
value, and generation count. The GUI adds an accessible way to observe that
deterministic process, pause it, alter inputs, and load standard examples.
For a formal experiment, record all four reproducibility inputs:

1. the exact rule JSON;
2. the exact initial-state JSON or initial pattern;
3. the board dimensions and boundary mode;
4. the number of generations executed.

With those inputs preserved, the transition from one generation to the next is
fully defined by [`CellularAutomaton.step()`](main.py), and the results can be
recreated independently of the graphical interface.
