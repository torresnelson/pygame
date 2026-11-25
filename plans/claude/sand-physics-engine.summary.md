Add a particle physics engine to the sand simulator

- Replace set-based `sand.py` with `world.py` (`World` grid engine) and
  `materials.py` (`Material`, `State`, `Props`)
- Add gravity with acceleration and `MAX_SPEED` terminal velocity
- Let heavier particles sink through lighter liquids, capped by drag
- Slide powders diagonally without squeezing through diagonal gaps;
  add static friction and impact scatter for natural piles
- Make water fall, flow sideways (`dispersion`) and level out
- Add stone walls, disc brush with sparse fill, eraser and `clear`
- Render the 160x120 grid as one RGB buffer scaled to the window
- Add material keys, brush size, pause and an on-screen status line
- Add `tests/test_world.py` (21 tests) and drop `tests/test_sand.py`

## Stats

- 1 commit on `feat/sand-physics`, stacked on `feat/sand-simulator`
- `ruff check .` clean, 57 tests passing
- ~5-7 ms per engine step with ~3.5k particles; demo holds 60 FPS

(this patch was generated in some part by
[`claude-code`][claude-code-gh])
[claude-code-gh]: https://github.com/anthropics/claude-code
