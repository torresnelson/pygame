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
  On a touch screen: tap rotates, drag sideways moves, drag down
  soft drops, flick down hard drops, and the PAUSE / END buttons
  replace `p` / `esc`. Names are typed or tapped on an on-screen
  keyboard. On a phone held upright tetris switches to a portrait
  layout: a bigger board with `<` `ROT` `>` `DOWN` `DROP` thumb
  buttons under it (left, right and down repeat while held); it
  follows the phone when it is turned, even mid-game. Run
  `python src/tetris/tetris.py --portrait` to see that layout on
  desktop.
- game of life: the start screen lets you pick a pattern (glider,
  lightweight spaceship, blinker, toad, beacon, pulsar,
  pentadecathlon, Gosper glider gun, R-pentomino, diehard, acorn,
  random soup or an empty board) with up/down + enter or a click.
  On the board: `space` runs/pauses, `n` steps once, click toggles
  cells while paused, `+` `-` change speed, `r` reloads the
  pattern, `c` clears, `esc` goes back to the picker. The button
  bar under the board does the same with a click or a tap; on a
  touch screen a tap in the picker previews a pattern and START
  loads it. On a phone held upright the game uses a portrait
  layout with two rows of big buttons under the board, and follows
  the phone when it is turned (`--portrait` shows it on desktop).
- sand simulator: left mouse (or a finger) paints, right mouse
  erases, `1` sand, `2` water, `3` stone, `4` eraser, mouse wheel
  or `[` `]` brush size, `space` pause, `c` clear, `esc` back to
  the menu; the toolbar under the world does the same with a tap.
  On a phone held upright it uses a portrait layout (a tall world
  and two rows of big toolbar buttons); turning the phone switches
  layouts and keeps the sand (`--portrait` shows it on desktop).
  Sand accelerates under
  gravity, piles into slopes and sinks through water; water flows
  and levels out; stone stays put.

Game rules live in pygame-free modules (`tetris_logic.py`,
`life.py` + `patterns.py`, and the sand engine `world.py` + `materials.py`)
covered by the tests in `tests/`.

## Play in the browser

All three games also run in the browser through
[pygbag](https://pypi.org/project/pygbag/) (pygame compiled to
WebAssembly), using the same code as the desktop versions, with
touch controls for phones; every game fits a phone either way up
and follows it when it is turned:

- https://torresnelson.github.io/pygame/ (landing page)
- https://torresnelson.github.io/pygame/gameoflife/
- https://torresnelson.github.io/pygame/tetris/ (high scores are kept
  in the browser's local storage)
- https://torresnelson.github.io/pygame/sandsimulator/

Build locally:

    pip install -e '.[web]'
    python tools/build_web.py                    # every game, site staged in build/site
    python tools/build_web.py tetris             # only some games
    python tools/build_web.py --serve tetris     # local test server on http://localhost:8000

Every push to `master` builds the site and publishes it to GitHub
Pages (`.github/workflows/pages.yml`). The first visit downloads the
Python runtime, so a game takes a few seconds to start; meanwhile
each game shows a loading screen with its title and a progress bar.
That screen lives in `tools/web_template.tmpl`, pygbag's default
page template with the loading screen added (and a single
phone-friendly viewport tag); the build passes it to pygbag with
`--template`, and each game removes the screen on its first frame.

To test a full build locally, use `--serve`, or open the static site
via `127.0.0.1` rather than `localhost`: on `localhost` pygbag fetches
pygame from its own dev server.

## Rust port

A Rust/bevy port of these games lives in its own repository,
[torresnelson/rustgame](https://github.com/torresnelson/rustgame), and
is published at https://torresnelson.github.io/rustgame/.

## Development

    ruff check .
    pytest
