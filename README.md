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

- tetris: 8-bit style (built-in pixel font, 2x pixel scaling with
  scanlines, bevelled blocks, NES-like palette). The main menu has
  play, high scores and quit. In game,
  arrows move/rotate, space hard drops, `p` pauses, `esc` ends the
  game. Clearing 1/2/3/4 lines at once scores 40/100/300/1200
  times (level + 1); every 10 lines is a new level and pieces fall
  faster. A top-10 table with names lives in
  `src/tetris/highscores.json` (ignored by git); an old
  `scores.txt` best score is imported once as `LEGACY`.
- game of life: the start screen lets you pick a pattern (glider,
  lightweight spaceship, blinker, toad, beacon, pulsar,
  pentadecathlon, Gosper glider gun, R-pentomino, diehard, acorn,
  random soup or an empty board) with up/down + enter or a click.
  On the board: `space` runs/pauses, `n` steps once, click toggles
  cells while paused, `+` `-` change speed, `r` reloads the
  pattern, `c` clears, `esc` goes back to the picker.
- sand simulator: left mouse paints, right mouse erases, `1` sand,
  `2` water, `3` stone, mouse wheel or `[` `]` brush size, `space`
  pause, `c` clear, `esc` back to the menu. Sand accelerates under
  gravity, piles into slopes and sinks through water; water flows
  and levels out; stone stays put.

Game rules live in pygame-free modules (`tetris_logic.py`,
`life.py` + `patterns.py`, and the sand engine `world.py` + `materials.py`)
covered by the tests in `tests/`.

## Game of life in the browser

The game of life also runs in the browser through
[pygbag](https://pypi.org/project/pygbag/) (pygame compiled to
WebAssembly), using the same code as the desktop version.

    pip install -e '.[web]'
    python tools/build_life_web.py           # static site in build/site (game in build/site/gameoflife)
    python tools/build_life_web.py --serve   # local test server on http://localhost:8000

Every push to `master` builds it and publishes it to GitHub Pages
(`.github/workflows/life-web.yml`) at
https://torresnelson.github.io/pygame/gameoflife/ (the site root
redirects there). The first visit downloads the Python runtime, so it
takes a few seconds to start.

## Development

    ruff check .
    pytest
