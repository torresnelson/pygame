//! The game of life screens (port of `src/game_of_life/game_of_life.py`),
//! with no engine code: input goes in as [`Event`]s, frames come out on a
//! [`Canvas`].

use life::{CATALOGUE, Cells, Pattern, build, cell_at, next_generation, toggle};
use pixelfont::Rect;
use sandbox_ui::{Canvas, Rgb};
use touch::{Button, button_at, button_row};

pub const BACKGROUND: Rgb = (10, 10, 14);
pub const DEAD_CELL: Rgb = (24, 24, 30);
pub const ALIVE_CELL: Rgb = (195, 195, 195);
pub const HIGHLIGHT: Rgb = (40, 40, 70);
pub const ACCENT: Rgb = (120, 200, 255);
pub const GOLD: Rgb = (248, 184, 0);
pub const TEXT: Rgb = (230, 230, 230);
pub const MUTED: Rgb = (130, 130, 150);
pub const SHADOW: Rgb = (20, 40, 70);

pub const AMOUNT: i32 = 50;
pub const SIZE: i32 = 12;
pub const GAP: i32 = 1;
pub const SPEEDS: [u64; 7] = [1, 2, 5, 10, 20, 30, 60];
/// Index into `SPEEDS`: 10 generations per second.
pub const DEFAULT_SPEED: usize = 3;

pub const BOARD_SIZE: i32 = AMOUNT * SIZE + (AMOUNT - 1) * GAP;
pub const STATUS_HEIGHT: i32 = 36;
pub const BAR_TOP: i32 = BOARD_SIZE + STATUS_HEIGHT;
pub const BAR_HEIGHT: i32 = 56;
pub const PORTRAIT_ROW: i32 = 150;

pub const MENU_TOP: i32 = 96;
pub const MENU_ROW: i32 = 34;
pub const PREVIEW: Rect = Rect::new(BOARD_SIZE - 232, MENU_TOP - 4, 214, 214);
/// Fits `PREVIEW`'s width at font scale 2.
pub const DESCRIPTION_CHARS: usize = 17;
pub const DESCRIPTION_ROW: i32 = 22;

/// Canvas size and touch targets for one orientation.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Layout {
    pub name: &'static str,
    pub size: (i32, i32),
    /// Board controls.
    pub buttons: Vec<Button>,
    /// Loads the selected pattern from the picker.
    pub start: Button,
    pub label_scale: i32,
}

const BOARD_ACTIONS: [(&str, &str); 7] = [
    ("run", "RUN"),
    ("step", "STEP"),
    ("slower", "-"),
    ("faster", "+"),
    ("reset", "RESET"),
    ("clear", "CLEAR"),
    ("back", "BACK"),
];

pub fn landscape() -> Layout {
    Layout {
        name: "landscape",
        size: (BOARD_SIZE, BAR_TOP + BAR_HEIGHT),
        buttons: button_row(
            &BOARD_ACTIONS,
            8,
            BAR_TOP,
            BOARD_SIZE - 16,
            BAR_HEIGHT - 8,
            8,
        ),
        start: Button::new("start", "START", Rect::new(PREVIEW.x, 452, PREVIEW.w, 48)),
        label_scale: 2,
    }
}

/// Same board, then two rows of thumb-sized buttons under it.
pub fn portrait() -> Layout {
    let mut buttons = button_row(
        &BOARD_ACTIONS[..4],
        8,
        BAR_TOP + 8,
        BOARD_SIZE - 16,
        PORTRAIT_ROW,
        8,
    );
    buttons.extend(button_row(
        &BOARD_ACTIONS[4..],
        8,
        BAR_TOP + 16 + PORTRAIT_ROW,
        BOARD_SIZE - 16,
        PORTRAIT_ROW,
        8,
    ));
    Layout {
        name: "portrait",
        size: (BOARD_SIZE, BAR_TOP + 2 * PORTRAIT_ROW + 3 * 8),
        buttons,
        start: Button::new(
            "start",
            "START",
            Rect::new(
                8,
                BAR_TOP + 16 + PORTRAIT_ROW,
                BOARD_SIZE - 16,
                PORTRAIT_ROW,
            ),
        ),
        label_scale: 3,
    }
}

/// Keyboard input the game understands.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Key {
    Up,
    Down,
    Enter,
    Space,
    Escape,
    Step,
    Faster,
    Slower,
    Reset,
    Clear,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Event {
    Key(Key),
    /// A press of the main mouse button or a finger, in canvas pixels.
    Press {
        pos: (i32, i32),
        touch: bool,
    },
    /// The mouse cursor moved (touches never hover).
    Hover((i32, i32)),
}

/// What the app should do after an event.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Outcome {
    Continue,
    /// Close the game (desktop only).
    Quit,
}

#[derive(Debug)]
pub struct Board {
    pub pattern: usize,
    pub cells: Cells,
    pub generation: u32,
    pub running: bool,
    pub speed: usize,
    last_step_ms: u64,
    step_once: bool,
}

#[derive(Debug)]
pub enum Screen {
    Picker { selected: usize },
    Board(Board),
}

pub struct Game {
    pub screen: Screen,
    /// The browser has nothing to quit to and shows touch hints.
    pub web: bool,
    rng: fastrand::Rng,
}

/// Greedy word wrap to lines of at most `width` characters.
pub fn wrap(value: &str, width: usize) -> Vec<String> {
    let mut lines = Vec::new();
    let mut line = String::new();
    for word in value.split_whitespace() {
        let candidate = if line.is_empty() {
            word.to_owned()
        } else {
            format!("{line} {word}")
        };
        if candidate.chars().count() > width && !line.is_empty() {
            lines.push(std::mem::replace(&mut line, word.to_owned()));
        } else {
            line = candidate;
        }
    }
    if !line.is_empty() {
        lines.push(line);
    }
    lines
}

pub fn status_text(generation: u32, population: usize, speed: u64, running: bool) -> String {
    let state = if running { "RUN" } else { "PAUSE" };
    format!("GEN {generation}  POP {population}  {speed}/S  {state}")
}

/// Handle a press on menu row `index`: (selected, start it?).
///
/// A mouse hovers before it clicks, so a click starts right away. A finger
/// cannot hover, so a tap only selects (to show the preview) and START loads
/// it; a second tap would be a double tap, which some phones turn into a zoom.
pub fn pick_tap(index: usize, touch: bool) -> (usize, bool) {
    (index, !touch)
}

pub fn menu_index_at((x, y): (i32, i32)) -> Option<usize> {
    let index = (y - MENU_TOP + 8).div_euclid(MENU_ROW);
    let in_list = x < PREVIEW.x - 8 && y >= MENU_TOP - 8;
    (in_list && (0..CATALOGUE.len() as i32).contains(&index)).then_some(index as usize)
}

fn center(rect: Rect) -> (i32, i32) {
    (rect.x + rect.w / 2, rect.y + rect.h / 2)
}

fn draw_button(canvas: &mut Canvas, button: &Button, label: &str, scale: i32, color: Rgb) {
    canvas.fill_rect(button.rect, HIGHLIGHT);
    canvas.outline(button.rect, MUTED, 1);
    canvas.text(label, center(button.rect), color, scale, None, true);
}

fn draw_preview(canvas: &mut Canvas, pattern: &Pattern) {
    canvas.fill_rect(PREVIEW, DEAD_CELL);
    canvas.outline(PREVIEW, MUTED, 1);
    let cells = pattern.cells();
    if cells.is_empty() {
        let label = if pattern.kind == "random" {
            "RANDOM"
        } else {
            "EMPTY"
        };
        canvas.text(label, center(PREVIEW), MUTED, 2, None, true);
        return;
    }
    let (height, width) = pattern.size();
    let cell = ((PREVIEW.w - 20).div_euclid(height.max(width))).clamp(2, 20);
    let (cx, cy) = center(PREVIEW);
    let (left, top) = (
        cx - (width * cell).div_euclid(2),
        cy - (height * cell).div_euclid(2),
    );
    for (r, c) in cells {
        canvas.fill_rect(
            Rect::new(left + c * cell, top + r * cell, cell - 1, cell - 1),
            ALIVE_CELL,
        );
    }
}

impl Game {
    pub fn new(web: bool, seed: u64) -> Self {
        Self {
            screen: Screen::Picker { selected: 0 },
            web,
            rng: fastrand::Rng::with_seed(seed),
        }
    }

    fn start(&mut self, pattern: usize) {
        let cells = build(CATALOGUE[pattern], AMOUNT, AMOUNT, &mut self.rng);
        self.screen = Screen::Board(Board {
            pattern,
            cells,
            generation: 0,
            running: false,
            speed: DEFAULT_SPEED,
            last_step_ms: 0,
            step_once: false,
        });
    }

    pub fn handle(&mut self, event: Event, layout: &Layout) -> Outcome {
        match &mut self.screen {
            Screen::Picker { selected } => {
                let count = CATALOGUE.len();
                let mut start = None;
                match event {
                    Event::Key(Key::Up) => *selected = (*selected + count - 1) % count,
                    Event::Key(Key::Down) => *selected = (*selected + 1) % count,
                    Event::Key(Key::Enter | Key::Space) => start = Some(*selected),
                    Event::Key(Key::Escape) if !self.web => return Outcome::Quit,
                    Event::Hover(pos) => {
                        if let Some(index) = menu_index_at(pos) {
                            *selected = index;
                        }
                    }
                    Event::Press { pos, touch } => {
                        if layout.start.contains(pos) {
                            start = Some(*selected);
                        } else if let Some(index) = menu_index_at(pos) {
                            let (index, go) = pick_tap(index, touch);
                            *selected = index;
                            if go {
                                start = Some(index);
                            }
                        }
                    }
                    Event::Key(_) => {}
                }
                if let Some(pattern) = start {
                    self.start(pattern);
                }
            }
            Screen::Board(board) => {
                let action = match event {
                    Event::Key(Key::Space) => Some("run"),
                    Event::Key(Key::Step) => Some("step"),
                    Event::Key(Key::Faster) => Some("faster"),
                    Event::Key(Key::Slower) => Some("slower"),
                    Event::Key(Key::Reset) => Some("reset"),
                    Event::Key(Key::Clear) => Some("clear"),
                    Event::Key(Key::Escape) => Some("back"),
                    Event::Press { pos, .. } => {
                        let action = button_at(&layout.buttons, pos);
                        if action.is_none()
                            && !board.running
                            && let Some(cell) = cell_at(pos.0, pos.1, SIZE, GAP, AMOUNT)
                        {
                            board.cells = toggle(&board.cells, cell);
                        }
                        action
                    }
                    _ => None,
                };
                match action {
                    Some("run") => board.running = !board.running && !board.cells.is_empty(),
                    Some("step") if !board.running => board.step_once = true,
                    Some("faster") => board.speed = (board.speed + 1).min(SPEEDS.len() - 1),
                    Some("slower") => board.speed = board.speed.saturating_sub(1),
                    Some("reset") => {
                        let pattern = board.pattern;
                        self.start(pattern);
                    }
                    Some("clear") => {
                        board.cells.clear();
                        board.generation = 0;
                        board.running = false;
                    }
                    Some("back") => {
                        self.screen = Screen::Picker {
                            selected: board.pattern,
                        }
                    }
                    _ => {}
                }
            }
        }
        Outcome::Continue
    }

    /// Advance the board when a generation is due (`now_ms`: app time).
    pub fn update(&mut self, now_ms: u64) {
        let Screen::Board(board) = &mut self.screen else {
            return;
        };
        let due = board.running
            && now_ms.saturating_sub(board.last_step_ms) >= 1000 / SPEEDS[board.speed];
        if due || board.step_once {
            board.cells = next_generation(&board.cells, AMOUNT, AMOUNT);
            board.generation += 1;
            board.last_step_ms = now_ms;
            board.step_once = false;
            // Everything died: go back to editing instead of running empty.
            board.running = board.running && !board.cells.is_empty();
        }
    }

    pub fn draw(&self, canvas: &mut Canvas, layout: &Layout) {
        match &self.screen {
            Screen::Picker { selected } => self.draw_menu(canvas, layout, *selected),
            Screen::Board(board) => self.draw_board(canvas, layout, board),
        }
    }

    fn draw_menu(&self, canvas: &mut Canvas, layout: &Layout, selected: usize) {
        canvas.fill(BACKGROUND);
        canvas.text("GAME OF LIFE", (20, 18), ACCENT, 4, Some(SHADOW), false);
        let hint = if self.web {
            "TAP A PATTERN, THEN START"
        } else {
            "UP/DOWN + ENTER, OR CLICK"
        };
        canvas.text(hint, (20, 60), MUTED, 2, None, false);
        for (i, pattern) in CATALOGUE.iter().enumerate() {
            let y = MENU_TOP + i as i32 * MENU_ROW;
            if i == selected {
                canvas.fill_rect(
                    Rect::new(12, y - 9, PREVIEW.x - 20, MENU_ROW - 2),
                    HIGHLIGHT,
                );
                canvas.text(">", (16, y), GOLD, 2, None, false);
            }
            let color = if i == selected { TEXT } else { MUTED };
            canvas.text(pattern.name, (32, y), color, 2, None, false);
            canvas.text(pattern.kind, (300, y + 4), MUTED, 1, None, false);
        }
        let pattern = CATALOGUE[selected];
        draw_preview(canvas, pattern);
        for (i, line) in wrap(pattern.description, DESCRIPTION_CHARS)
            .iter()
            .enumerate()
        {
            let y = PREVIEW.y + PREVIEW.h + 16 + i as i32 * DESCRIPTION_ROW;
            canvas.text(line, (PREVIEW.x, y), TEXT, 2, None, false);
        }
        draw_button(
            canvas,
            &layout.start,
            layout.start.label,
            layout.label_scale,
            GOLD,
        );
    }

    fn draw_board(&self, canvas: &mut Canvas, layout: &Layout, board: &Board) {
        canvas.fill(BACKGROUND);
        for row in 0..AMOUNT {
            for column in 0..AMOUNT {
                let color = if board.cells.contains(&(row, column)) {
                    ALIVE_CELL
                } else {
                    DEAD_CELL
                };
                canvas.fill_rect(
                    Rect::new(column * (SIZE + GAP), row * (SIZE + GAP), SIZE, SIZE),
                    color,
                );
            }
        }
        let status = status_text(
            board.generation,
            board.cells.len(),
            SPEEDS[board.speed],
            board.running,
        );
        canvas.text(&status, (8, BOARD_SIZE + 11), TEXT, 2, None, false);
        let hint = if self.web { "" } else { "SPC N +/- R C ESC" };
        let name = CATALOGUE[board.pattern].name;
        let width = pixelfont::text_size(hint, 1)
            .0
            .max(pixelfont::text_size(name, 1).0);
        canvas.text(
            name,
            (BOARD_SIZE - 8 - width, BOARD_SIZE + 8),
            ACCENT,
            1,
            None,
            false,
        );
        canvas.text(
            hint,
            (BOARD_SIZE - 8 - width, BOARD_SIZE + 21),
            MUTED,
            1,
            None,
            false,
        );
        for button in &layout.buttons {
            let label = if board.running && button.action == "run" {
                "PAUSE"
            } else {
                button.label
            };
            draw_button(canvas, button, label, layout.label_scale, TEXT);
        }
    }
}

#[cfg(test)]
mod tests;
