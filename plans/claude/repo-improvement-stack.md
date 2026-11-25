# Repo improvement stack

Resolve the issues found in the initial repo review using four stacked
branches, each tested and opened as a PR against the branch below it.

## Stack

1. `fix/project-setup` (base: `master`)
   - Add `pyproject.toml` (pygame dep, pytest/ruff dev tooling, ruff
     single-quote rule, pytest `pythonpath`).
   - Add `.gitignore`; untrack `src/tetris/scores.txt`.
   - `default.nix`: drop the unrelated PyPI `square` package and the
     duplicate pip install; provide pygame, pytest and ruff from nixpkgs.
   - Tetris: resolve `scores.txt` next to the script and treat a missing
     or empty file as a score of 0.
   - Tests for score persistence; README updates.
2. `refactor/tetris-logic` (base: `fix/project-setup`)
   - Extract pure, typed game logic into `src/tetris/tetris_logic.py`.
   - Fix `clear_rows` for non-contiguous cleared rows.
   - Fix rotation precedence, mutable default args, bare `except`,
     leftover debug `print`, per-frame font creation.
   - Guard entry point with `if __name__ == '__main__':`.
   - Tests in `tests/test_tetris_logic.py`.
3. `refactor/game-of-life` (base: `refactor/tetris-logic`)
   - Replace `square.py` classes and `deepcopy` neighbour checks with a
     pure `next_generation(cells)` over a set of live coordinates.
   - Fix exit-on-start when no cells are placed.
   - Tests in `tests/test_life.py`.
4. `feat/sand-simulator` (base: `refactor/game-of-life`)
   - Replace the Tetris-clone loop with a falling-sand cellular
     automaton (`src/sand_simulator/sand.py`), mouse to pour sand.
   - Removes the edge `IndexError` / wraparound drawing bug.
   - Tests in `tests/test_sand.py`.

## Verification

- `ruff check .` and `pytest` pass on every branch.
- Each game boots headlessly (`SDL_VIDEODRIVER=dummy`) without errors.
