# Sand physics engine

Turn the sand simulator into a real falling-sand sandbox by replacing the
set-based `sand.py` with a particle engine. Stacked on `feat/sand-simulator`.

## Engine (`src/sand_simulator/`)

- `materials.py`: `Material` (empty, stone, sand, water), `State`
  (gas/solid/powder/liquid) and per-material `Props` (density, colour,
  friction, dispersion, drag speed).
- `world.py`: `World` grid stored as flat lists (material, velocity, shade,
  flow direction, tick stamp).
  - Bottom-up scan, alternating horizontal direction per row/tick.
  - Gravity with acceleration and terminal velocity (multi-cell moves).
  - Density displacement: heavier particles sink through lighter liquids,
    speed capped by the liquid's drag.
  - Powders slide diagonally without squeezing through diagonal gaps;
    static friction on resting grains; fast impacts scatter downhill.
  - Liquids fall, then flow sideways up to `dispersion` cells keeping a
    flow direction.
  - `paint` disc brush (sparse fill for granular look), eraser, `clear`.

## Front end

- Render the grid as one RGB buffer scaled to the window (5px cells,
  160x120 grid).
- Material selection, paint/erase, brush size, pause, clear, HUD.

## Verification

- `tests/test_world.py`: acceleration, terminal velocity, floor/stone
  collisions, diagonal-gap rule, pile slope, water levelling, sinking,
  drag, conservation, painting.
- Headless scripted demo with screenshot; step time benchmark.
