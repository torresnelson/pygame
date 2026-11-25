# pygame sandbox

This repo is for pygame experiments and testing, i already made
a tetris, game of life and a sand simulator that you can try B)

## Installation

I recomend the use of a virtual environment, for this run the
following command:

    python -m venv .venv

Once created the virtual environment, we need to activate it, run
this:

    source .venv/bin/activate

Then install the project with its dev tools (`pygame`, `pytest`,
`ruff`):

    pip install -e '.[dev]'

## Nixos installation

In case you're using nixos, use this (it provides `pygame`,
`pytest` and `ruff`, no pip needed):

    nix-shell

## How to play?

Run one of the following commands to run a game (from the
project's root or anywhere else):

    python src/tetris/tetris.py

    python src/game_of_life/game_of_life.py

    python src/sand_simulator/sand_simulator.py

Controls:

- tetris: arrows move/rotate, space hard drops. The best score is
  stored in `src/tetris/scores.txt` (ignored by git, created on
  first game over).
- game of life: click cells to toggle them, space runs/pauses.
- sand simulator: left mouse paints, right mouse erases, `1` sand,
  `2` water, `3` stone, mouse wheel or `[` `]` brush size, `space`
  pause, `c` clear, `esc` back to the menu. Sand accelerates under
  gravity, piles into slopes and sinks through water; water flows
  and levels out; stone stays put.

Game rules live in pygame-free modules (`tetris_logic.py`,
`life.py`, and the sand engine `world.py` + `materials.py`)
covered by the tests in `tests/`.

## Development

    ruff check .
    pytest
