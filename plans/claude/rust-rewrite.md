# Rust rewrite

Rewrite the pygame sandbox (tetris, game of life, sand simulator) in Rust
with feature parity on desktop, browser and phones, keeping the GitHub Pages
URLs (`/gameoflife/`, `/tetris/`, `/sandsimulator/`) and saved tetris scores.

## Stack

- Engine: **macroquad** (one codebase for native and `wasm32`, touch and
  mouse built in, async `next_frame().await` loop matching today's async
  loops, plain `index.html` + `.wasm` output, no wasm-bindgen).
  Rejected: bevy (heavy for 2D toys, large wasm), ggez (weak wasm),
  pixels+winit (more glue for the same result).
- Crates: `macroquad`, `quad-storage` (localStorage / file), `serde` +
  `serde_json` (high scores), `fastrand` (seedable RNG for tests).
- Tooling: stable toolchain pinned in `rust-toolchain.toml` with the
  `wasm32-unknown-unknown` target; `cargo fmt`, `cargo clippy -D warnings`,
  `cargo test`; an `xtask` crate replaces `tools/build_web.py`.

## Layout

Cargo workspace; logic crates have no engine dependency, so today's pytest
suites port one-to-one as `#[test]`s.

```
Cargo.toml                 workspace
crates/
  pixelfont/   <- src/shared/pixelfont.py    5x7 glyphs, text_size, rects
  touch/       <- src/shared/touch.py        Button, button_row, Drag, gestures,
                                             repeats, fit_box
  life/        <- life.py + patterns.py      next_generation, cell_at, toggle,
                                             CATALOGUE, build
  tetris-core/ <- tetris_logic.py +          pieces, SRS-less rotation as today,
                  highscores.py              scoring, levels, Entry, JSON format
  sand/        <- world.py + materials.py    World, Material/Props, step, paint,
                                             resized
  ui/          <- browser.py + shared draw   virtual canvas, pixel text, buttons,
                                             layouts, orientation, storage
games/
  tetris/  game-of-life/  sand-simulator/    one binary each (native + wasm)
web/
  template.html                              <- tools/web_template.tmpl
  landing.html                               <- landing_page()
xtask/                                       build-web, serve, stage site
```

## Cross-cutting design

- **Virtual canvas**: each game draws to a fixed-size render target per
  layout (e.g. tetris 400x350 / 400x760) with nearest filtering, scaled and
  letterboxed to the window; pointer input is mapped back through the same
  transform. Replaces `SCALE`, `fit_canvas`, `keep_fitted`.
- **Layouts**: a `Layout` struct per game and orientation (as today); pick
  by `screen_height() > screen_width()` every frame, so rotation needs no
  `set_mode` and no CSS fitting tricks.
- **Input**: one `Pointer` stream built from mouse and `touches()`; keeps the
  tap / drag / flick / hold-repeat rules from `touch.py`. Bonus: real
  multi-touch (hold `<` while tapping `ROT`).
- **Storage**: `quad-storage` key `tetris.highscores` with the same JSON
  schema, so browser scores survive the switch; desktop reads/writes
  `highscores.json` next to the binary and still imports `scores.txt`.
- **Web page**: macroquad's `index.html` replaced by `web/template.html`
  carrying the current loading screen (title, falling blocks, progress bar
  fed by a `fetch` stream of the `.wasm`, 45 s hint), the single viewport
  tag, `touch-action: none`, no-zoom guard; the game calls a JS
  `hide_loading()` on its first frame.

## Phases

Each phase lands as one PR with green CI; Python stays the shipped version
until phase 6.

1. **Scaffold** - workspace, toolchain pin, CI job (fmt, clippy, test,
   `cargo build --target wasm32-unknown-unknown`) next to the Python one.
   Exit: empty `games/*` open a window natively and in a browser.
2. **Pure crates** - port `pixelfont` (same glyph table), `touch`, `life`,
   `tetris-core`, `sand` with their tests (`test_pixelfont`, `test_touch`,
   `test_life`, `test_patterns`, `test_tetris_logic`, `test_highscores`,
   `test_world`). Exit: all ported tests pass; sand `step` benchmarked
   (expect well over 10x the Python speed).
3. **UI crate** - virtual canvas + scanlines, pixel text, NES box / button
   drawing, pointer stream, orientation, storage, `hide_loading` call.
   Exit: a demo scene renders identically on desktop and phone emulation.
4. **Games** - in order of risk:
   - Game of life: picker with preview + START, board, button bar, both
     layouts, speed steps.
   - Sand: toolbar, brush, pause/clear, both layouts, resize on rotation;
     consider a finer grid now that it is fast.
   - Tetris: menu with falling blocks, play (gestures, buttons, repeat,
     pause/end, line flash), game over, high score table, name keyboard,
     both layouts.
   Exit: parity checklist below ticked per game; layout tests (fit, no
   overlap, every key has a button) ported from `test_*_ui.py`.
5. **Web build** - `cargo xtask build-web [game...]`: release wasm per
   game (`opt-level = "z"`, `lto`, `wasm-opt`), copy `mq_js_bundle.js`,
   render `web/template.html`, stage `build/site/<path>/` + landing page;
   `cargo xtask serve`. Swap `pages.yml` to it.
   Exit: Playwright phone checks (load, loading screen removed, tap/drag,
   rotation) pass against the staged site.
6. **Cutover** - delete `src/`, `tests/`, `tools/`, `pyproject.toml`; update
   `default.nix` (rustup/cargo, wasm target) and README.
   Exit: Pages serves the Rust build at the same URLs; old scores load.

## Parity checklist

- Tetris: 8-bit look (pixel font, 2x scale, scanlines, bevelled tiles),
  scoring 40/100/300/1200 x (level+1), level every 10 lines, top-10 table
  with names and legacy import, menu without QUIT in the browser, touch
  gestures, portrait thumb buttons, rotation mid-game.
- Game of life: 13 patterns with previews and descriptions, run/step/
  speed/reset/clear/back, toggle cells while paused, portrait layout.
- Sand: sand/water/stone/eraser, gravity with terminal speed, density
  sinking, friction, liquid flow, brush 0..12, portrait layout, sand kept
  on rotation.
- Web: landing page boxes, loading screen, no zoom, fits any screen.

## Risks

- wasm size / first load: budget < 2 MB per game; keep the loading screen.
- Pixel-exact text: port the glyph table verbatim and snapshot-test rects.
- Mobile browsers (Firefox for Android zoom, iOS callouts): carry over the
  page fixes from `browser.py` into `web/template.html`.
- Behaviour drift in physics: port the sand tests first and keep the same
  constants (`GRAVITY`, `MAX_SPEED`, `SCATTER_SPEED`).

## Open questions

- macroquad (recommended) vs bevy?
- Rewrite in place (phase 6 cutover) or keep Python alongside long term?
- Any desktop-only extras to drop or add (e.g. sound, which none have now)?
