Fix game bugs and add tested logic modules

- Add `pyproject.toml`, `.gitignore` and a pip-free `default.nix`
  that provides `pygame`, `pytest` and `ruff` from nixpkgs
- Drop the unrelated PyPI `square` package from the nix shell
- Resolve tetris `scores.txt` next to the script via `scores.py`,
  fixing the `FileNotFoundError` when run from the repo root
- Extract tetris rules into `tetris_logic.py`; fix `clear_rows`
  losing blocks on non-contiguous clears, rotation precedence,
  mutable defaults and per-frame font creation
- Replace game of life `square.py`/`deepcopy` with pure
  `next_generation` over a set of live cells; pause instead of
  quitting when everything dies
- Replace the sand simulator tetris clone with a falling-sand
  automaton in `sand.py`, removing the edge `IndexError`
- Guard every game entry point with `if __name__ == '__main__':`
- Add 46 pytest tests and enforce `ruff` (single quotes) everywhere

## Stats

- 4 stacked branches / PRs, 4 commits
- `ruff check .` clean, 46 tests passing on the top branch
- Each game smoke-tested headlessly with `SDL_VIDEODRIVER=dummy`
- No CI added (no workflow existed); checks run locally

(this patch was generated in some part by
[`claude-code`][claude-code-gh])
[claude-code-gh]: https://github.com/anthropics/claude-code
