# Numerical cellular automaton

Run the terminal demo with the project virtual environment:

```text
.venv\Scripts\python.exe main.py --generations 4
```

The transition rules are configured in [rules.json](rules.json). A rule can
match counts for any cell state; omitted neighbor states are treated as
wildcards. The current implementation uses a finite rectangular board and
treats cells outside the board as the configured `default_state`.

`CellularAutomaton.pause()`, `resume()`, `save_state()`, and `load_state()`
provide the numerical controls needed by the future interactive display.