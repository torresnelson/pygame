# Rust rewrite

Rewrite the pygame sandbox (tetris, game of life, sand simulator) in Rust
with **bevy**, reaching feature parity on desktop, browser and phones, then
adding sound effects, a finer sand grid and multi-touch. The Python version
stays and is maintained alongside; the Rust version lives in `rust/`.

## Decisions

- Engine: bevy (chosen over macroquad).
- Python and Rust are both kept long term; neither replaces the other.
- Scope: exact parity first, then three additions: sound effects, finer
  sand grid, multi-touch controls.
- Pages (default, revisit at phase 6): Python keeps `/gameoflife/`,
  `/tetris/`, `/sandsimulator/`; Rust is served under `/rust/<game>/` and
  linked from the landing page.

## Stack

- `bevy` with trimmed features (`bevy_winit`, `bevy_render`,
  `bevy_core_pipeline`, `bevy_sprite`, `bevy_audio` + `wav`, `webgl2`,
  `multi_threaded` off on wasm) to keep the wasm small.
- `serde` + `serde_json` (high scores), `fastrand` (seedable RNG in tests),
  `web-sys` `Storage` on wasm / a file on desktop for saves.
- Web: `wasm-bindgen-cli` + `wasm-opt`, driven by an `xtask` crate.
- Tooling: stable toolchain pinned in `rust/rust-toolchain.toml` with
  `wasm32-unknown-unknown`; `cargo fmt`, `cargo clippy -D warnings`,
  `cargo test`.

## Layout

```
rust/
  Cargo.toml                 workspace
  crates/
    pixelfont/   <- src/shared/pixelfont.py      glyph table, text_size, rects
    touch/       <- src/shared/touch.py          Button, rows, drag, tap/flick,
                                                 repeats, fit_box; per-pointer ids
    life/        <- life.py + patterns.py        rules, CATALOGUE, build
    tetris-core/ <- tetris_logic.py +            pieces, moves, scoring, levels,
                    highscores.py                Entry + JSON (same schema)
    sand/        <- world.py + materials.py      World, Material/Props, step,
                                                 paint, resized
    sfx/         (new)                           8-bit sound synthesis -> WAV bytes
    sandbox-ui/  <- browser.py + shared drawing  bevy plugin: pixel camera, text,
                                                 buttons, layouts, pointers,
                                                 storage, audio, loading screen
  games/
    tetris/  game-of-life/  sand-simulator/      one bevy app each
  web/
    template.html                                <- tools/web_template.tmpl
  xtask/                                         build-web, serve, stage
```

Logic crates (`pixelfont`, `touch`, `life`, `tetris-core`, `sand`, `sfx`)
do not depend on bevy, so the pytest suites port one-to-one as
`#[test]`s and run in milliseconds.

## Bevy design

- **Screens as `States`**: tetris `Menu | Playing | Paused | GameOver |
  HighScores | NameEntry`; life `Picker | Board`; sand `Title | Sandbox`.
  Each screen spawns its entities on enter and despawns them on exit.
- **Pixel look**: render each game at its virtual resolution (tetris
  400x350 / 400x760, life 649x741 / 649x1009, sand per layout) into an
  `Image` render target with nearest sampling, shown by a second camera
  scaled to fit and letterboxed; scanlines as a full-screen overlay
  sprite. Pointer positions map back through the same transform.
- **Pixel text**: build a glyph atlas texture from the `pixelfont` table at
  startup; text = sprites per glyph (exact match with Python).
- **Sand rendering**: one `Image` the size of the grid, its bytes
  rewritten each frame from `World` (as `render()` does today).
- **Layouts / orientation**: a `Layout` resource per game; a system checks
  `Window` size each frame and swaps layouts (sand calls
  `World::resized`). No CSS fitting: `fit_canvas_to_parent` +
  `prevent_default_event_handling` on the window.
- **Input**: a `Pointers` resource merging mouse and `Touches`, each
  pointer with its own id, press time and drag state, so buttons and
  gestures work per finger (multi-touch).
- **Storage**: key `tetris.highscores`, same JSON, so browser scores carry
  over from the Python build if served on the same origin path; desktop
  `highscores.json` + legacy `scores.txt` import.
- **Audio**: `sfx` synthesises square/noise blips to WAV bytes at start-up
  (no asset files); browsers start audio after the first tap.

## Phases

One PR per phase, CI green for both Python and Rust.

1. **Scaffold** - `rust/` workspace, toolchain pin, CI job (fmt, clippy,
   test, wasm build) next to the Python job. Exit: an empty bevy window
   per game opens natively and in a browser.
2. **Logic crates** - port `pixelfont`, `touch`, `life`, `tetris-core`,
   `sand` with tests from `test_pixelfont`, `test_touch`, `test_life`,
   `test_patterns`, `test_tetris_logic`, `test_highscores`, `test_world`,
   `test_browser` (`fit_box`). Exit: all pass; sand `step` benchmark.
3. **`sandbox-ui` plugin** - pixel camera + scanlines, glyph atlas text,
   NES box / buttons, layouts + orientation, `Pointers`, storage,
   `hide_loading()` call on first frame. Exit: a demo screen renders the
   same on desktop and in phone emulation.
4. **Games at parity** - life, then sand, then tetris; port the layout
   tests from `test_*_ui.py` (fit, no overlap, every key has a button).
   Exit: parity checklist ticked per game.
5. **Web build** - `cargo xtask build-web [game...]`: release wasm
   (`opt-level = "z"`, LTO, `wasm-opt -Oz`), `wasm-bindgen --target web`,
   render `web/template.html` (loading screen fed by streaming the
   `.wasm` download), stage `build/site/rust/<game>/`; extend `pages.yml`
   and the landing page. Exit: Playwright phone checks pass on the staged
   site (load, loading screen removed, tap/drag, rotation).
6. **Additions** -
   - Sound: `sfx` crate + effects for move, rotate, drop, line clear,
     game over, menu tap, cell toggle, paint; mute toggle.
   - Finer sand grid: cell size 5 -> 3 (about 2.8x the cells) if the wasm
     benchmark keeps `step` under 8 ms on a mid-range phone; else 4.
   - Multi-touch: hold `<` / `>` / `DOWN` while tapping `ROT` in tetris;
     paint while tapping the toolbar in sand.
   Exit: each addition tested and verified on the phone; revisit which
   version Pages serves at the main URLs.

## Parity checklist

- Tetris: pixel font, 2x scale, scanlines, bevelled tiles; scoring
  40/100/300/1200 x (level+1), level every 10 lines; top-10 table with
  names and legacy import; no QUIT in the browser; gestures (tap, drag,
  flick), PAUSE/END, portrait thumb buttons with hold-repeat, rotation
  mid-game; on-screen name keyboard.
- Game of life: 13 patterns with previews and descriptions; tap previews,
  START loads; run/step/speed/reset/clear/back; toggle cells while
  paused; portrait layout.
- Sand: sand/water/stone/eraser; gravity with terminal speed, density
  sinking, friction, liquid flow; brush 0..12; pause/clear/menu; portrait
  layout; sand kept on rotation.
- Web: loading screen, no zoom, fits any screen, landing page boxes.

## Risks

- **wasm size**: bevy builds are large; budget 8 MB raw / 3 MB gzip per
  game, trim features, `wasm-opt -Oz`; the loading screen shows progress.
- **WebGL2 / mobile GPUs**: test on Firefox for Android and iOS Safari
  early (phase 1), not at the end.
- **Pixel-exact text**: port the glyph table verbatim; snapshot-test rects.
- **Physics drift**: port the sand tests first, same constants
  (`GRAVITY`, `MAX_SPEED`, `SCATTER_SPEED`).
- **Two codebases**: behaviour changes now land twice; the shared JSON
  formats and the parity checklist keep them aligned.
