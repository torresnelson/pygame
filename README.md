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

Then use the `pip` commande to install the package `pygame`:

    pip install pygame

## Nixos installation

In case you're using nixos, use this:

    nix-shell

## How to play tetris clon?

Run one of the following commands to run a game (need to be in the
project's root):

    python src/tetris/tetris.py

    python src/game_of_life/game_of_life.py

    python src/sand_simulator/sand_simulator.py

