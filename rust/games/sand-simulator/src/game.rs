//! The sand simulator screens (port of `src/sand_simulator/sand_simulator.py`),
//! with no engine code: input goes in as [`Event`]s and [`Paint`]s, frames
//! come out on a [`Canvas`].

use pixelfont::Rect;
use sand::{Material, PROPS, SHADES, World, palette};
use sandbox_ui::{Canvas, Rgb};
use touch::{Button, button_at, button_row};

pub const CELL_SIZE: i32 = 5;
pub const MIN_BRUSH: i32 = 0;
pub const MAX_BRUSH: i32 = 12;

pub const BLACK: Rgb = (0, 0, 0);
pub const WHITE: Rgb = (252, 252, 252);
pub const RED: Rgb = (228, 52, 32);
pub const DIM: Rgb = (150, 150, 170);
pub const GOLD: Rgb = (248, 184, 0);
pub const MUTED: Rgb = (130, 130, 150);
pub const BACKGROUND: Rgb = (12, 12, 18);
pub const BAR_BACKGROUND: Rgb = (24, 24, 32);
pub const BUTTON: Rgb = (40, 40, 54);
pub const BUTTON_ACTIVE: Rgb = (70, 70, 100);
const SAND_COLOR: Rgb = PROPS[Material::Sand as usize].color;
const TITLE_SHADOW: Rgb = (90, 70, 30);
pub const HELP: &str =
    "1 SAND  2 WATER  3 STONE  4 ERASE  LMB PAINT  RMB ERASE  WHEEL/[] BRUSH  SPC PAUSE  C CLEAR";

/// Tools by toolbar action; the eraser paints `Empty`.
pub const TOOLS: [(&str, Material); 4] = [
    ("sand", Material::Sand),
    ("water", Material::Water),
    ("stone", Material::Stone),
    ("erase", Material::Empty),
];

/// Granular materials are poured sparsely so they look like grains.
pub fn fill(tool: Material) -> f32 {
    match tool {
        Material::Sand => 0.5,
        Material::Water => 0.6,
        Material::Stone | Material::Empty => 1.0,
    }
}

pub fn tool_for(action: &str) -> Option<Material> {
    TOOLS
        .iter()
        .find(|&&(name, _)| name == action)
        .map(|&(_, tool)| tool)
}

/// World area, canvas size and toolbar for one orientation.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Layout {
    pub name: &'static str,
    /// Pixels; the world grid is this / `CELL_SIZE`.
    pub world_size: (i32, i32),
    pub size: (i32, i32),
    pub toolbar: Vec<Button>,
    pub label_scale: i32,
    pub status_scale: i32,
}

impl Layout {
    pub fn cells(&self) -> (i32, i32) {
        (self.world_size.0 / CELL_SIZE, self.world_size.1 / CELL_SIZE)
    }

    pub fn in_world(&self, (x, y): (i32, i32)) -> bool {
        (0..self.world_size.0).contains(&x) && (0..self.world_size.1).contains(&y)
    }
}

pub fn landscape() -> Layout {
    let (width, height, bar) = (800, 600, 64);
    Layout {
        name: "landscape",
        world_size: (width, height),
        size: (width, height + bar),
        toolbar: button_row(
            &[
                ("sand", "SAND"),
                ("water", "WATER"),
                ("stone", "STONE"),
                ("erase", "ERASE"),
                ("smaller", "SIZE-"),
                ("bigger", "SIZE+"),
                ("pause", "PAUSE"),
                ("clear", "CLEAR"),
                ("menu", "MENU"),
            ],
            8,
            height + 8,
            width - 16,
            bar - 16,
            6,
        ),
        label_scale: 2,
        status_scale: 2,
    }
}

/// A tall world with the same number of cells (same speed), then two rows
/// of thumb-sized buttons.
pub fn portrait() -> Layout {
    let (width, height, row) = (600, 800, 110);
    let mut toolbar = button_row(
        &[
            ("sand", "SAND"),
            ("water", "WATER"),
            ("stone", "STONE"),
            ("erase", "ERASE"),
            ("pause", "PAUSE"),
        ],
        8,
        height + 8,
        width - 16,
        row,
        8,
    );
    toolbar.extend(button_row(
        &[
            ("smaller", "SIZE-"),
            ("bigger", "SIZE+"),
            ("clear", "CLEAR"),
            ("menu", "MENU"),
        ],
        8,
        height + 16 + row,
        width - 16,
        row,
        8,
    ));
    Layout {
        name: "portrait",
        world_size: (width, height),
        size: (width, height + 3 * 8 + 2 * row),
        toolbar,
        label_scale: 3,
        status_scale: 3,
    }
}

pub fn tool_name(tool: Material) -> &'static str {
    match tool {
        Material::Empty => "eraser",
        Material::Stone => "stone",
        Material::Sand => "sand",
        Material::Water => "water",
    }
}

pub fn status_text(tool: Material, brush: i32, fps: f32, paused: bool) -> String {
    let paused_flag = if paused { "  PAUSED" } else { "" };
    format!(
        "{}  BRUSH {brush}  {fps:.0} FPS{paused_flag}",
        tool_name(tool).to_uppercase()
    )
}

pub fn resize_brush(brush: i32, action: &str) -> i32 {
    let delta = match action {
        "smaller" => -1,
        "bigger" => 1,
        _ => 0,
    };
    (brush + delta).clamp(MIN_BRUSH, MAX_BRUSH)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Event {
    /// A key press, with the action it maps to (if any). Any key starts the
    /// game from the title screen.
    Key(Option<&'static str>),
    /// A new press of the main mouse button or a finger, in canvas pixels.
    Press((i32, i32)),
    /// Mouse wheel steps (positive: bigger brush).
    Wheel(i32),
}

/// A pointer painting this frame (it went down inside the world).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Paint {
    pub pos: (i32, i32),
    /// The right mouse button erases whatever the tool is.
    pub erase: bool,
    /// When the pointer went down (app milliseconds).
    pub start_ms: u64,
}

pub struct Sandbox {
    pub world: World,
    pub tool: Material,
    pub brush: i32,
    pub paused: bool,
    /// The tap that opened the sandbox must not paint (as in Python, where
    /// the game starts with no button held).
    started_ms: u64,
}

pub enum Screen {
    Title,
    Sandbox(Sandbox),
}

pub struct Game {
    pub screen: Screen,
    /// Touch prompt and no keyboard help in the browser.
    pub web: bool,
    seed: u64,
    /// RGB per (material, shade); empty cells use `BACKGROUND`.
    colors: [[Rgb; SHADES]; 4],
    /// App time of the current frame, set by the caller.
    pub now_ms: u64,
}

impl Game {
    pub fn new(web: bool, seed: u64) -> Self {
        let mut colors = palette();
        colors[Material::Empty as usize] = [BACKGROUND; SHADES];
        Self {
            screen: Screen::Title,
            web,
            seed,
            colors,
            now_ms: 0,
        }
    }

    pub fn handle(&mut self, event: Event, layout: &Layout) {
        match &mut self.screen {
            Screen::Title => {
                if matches!(event, Event::Key(_) | Event::Press(_)) {
                    self.seed = self.seed.wrapping_add(1);
                    let (columns, rows) = layout.cells();
                    self.screen = Screen::Sandbox(Sandbox {
                        world: World::new(columns, rows, fastrand::Rng::with_seed(self.seed)),
                        tool: Material::Sand,
                        brush: 3,
                        paused: false,
                        started_ms: self.now_ms,
                    });
                }
            }
            Screen::Sandbox(sandbox) => {
                let action = match event {
                    Event::Key(action) => action,
                    Event::Press(pos) if !layout.in_world(pos) => button_at(&layout.toolbar, pos),
                    Event::Wheel(steps) => {
                        sandbox.brush = (sandbox.brush + steps).clamp(MIN_BRUSH, MAX_BRUSH);
                        None
                    }
                    Event::Press(_) => None,
                };
                match action {
                    Some(action) if tool_for(action).is_some() => {
                        sandbox.tool = tool_for(action).expect("checked")
                    }
                    Some(action @ ("smaller" | "bigger")) => {
                        sandbox.brush = resize_brush(sandbox.brush, action)
                    }
                    Some("pause") => sandbox.paused = !sandbox.paused,
                    Some("clear") => sandbox.world.clear(),
                    Some("menu") => self.screen = Screen::Title,
                    _ => {}
                }
            }
        }
    }

    /// Paint with every active pointer, then advance the physics unless paused.
    pub fn update(&mut self, paints: &[Paint]) {
        let Screen::Sandbox(sandbox) = &mut self.screen else {
            return;
        };
        for paint in paints.iter().filter(|p| p.start_ms > sandbox.started_ms) {
            let (x, y) = (
                paint.pos.0.div_euclid(CELL_SIZE),
                paint.pos.1.div_euclid(CELL_SIZE),
            );
            let tool = if paint.erase {
                Material::Empty
            } else {
                sandbox.tool
            };
            sandbox.world.paint(x, y, sandbox.brush, tool, fill(tool));
        }
        if !sandbox.paused {
            sandbox.world.step();
        }
    }

    /// The layout changed (phone turned): carry the sand over to the new grid.
    pub fn relayout(&mut self, layout: &Layout) {
        if let Screen::Sandbox(sandbox) = &mut self.screen {
            let (columns, rows) = layout.cells();
            sandbox.world = sandbox.world.resized(columns, rows);
        }
    }

    pub fn draw(&self, canvas: &mut Canvas, layout: &Layout, now_ms: u64, fps: f32) {
        match &self.screen {
            Screen::Title => self.draw_title(canvas, layout, now_ms),
            Screen::Sandbox(sandbox) => self.draw_sandbox(canvas, layout, sandbox, fps),
        }
    }

    fn draw_title(&self, canvas: &mut Canvas, layout: &Layout, now_ms: u64) {
        let (width, height) = layout.size;
        let middle = height / 2;
        canvas.fill(BLACK);
        canvas.text(
            "SAND",
            (width / 2, middle - 150),
            SAND_COLOR,
            10,
            Some(TITLE_SHADOW),
            true,
        );
        canvas.text(
            "SIMULATOR",
            (width / 2, middle - 60),
            SAND_COLOR,
            6,
            Some(TITLE_SHADOW),
            true,
        );
        if (now_ms / 500).is_multiple_of(2) {
            let prompt = if self.web {
                "TAP TO START"
            } else {
                "PRESS ANY KEY"
            };
            canvas.text(prompt, (width / 2, middle + 50), WHITE, 3, None, true);
        }
        canvas.text(
            "TITOREBOOT INC",
            (width / 2, middle + 190),
            RED,
            2,
            None,
            true,
        );
    }

    fn draw_sandbox(&self, canvas: &mut Canvas, layout: &Layout, sandbox: &Sandbox, fps: f32) {
        let world = &sandbox.world;
        for y in 0..world.height {
            for x in 0..world.width {
                let i = (y * world.width + x) as usize;
                let color = self.colors[world.material[i] as usize][world.shade[i] as usize];
                canvas.fill_rect(
                    Rect::new(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE),
                    color,
                );
            }
        }
        let status = status_text(sandbox.tool, sandbox.brush, fps, sandbox.paused);
        canvas.text(
            &status,
            (8, 8),
            WHITE,
            layout.status_scale,
            Some(BLACK),
            false,
        );
        if !self.web {
            canvas.text(
                HELP,
                (8, 12 + 7 * layout.status_scale),
                DIM,
                1,
                Some(BLACK),
                false,
            );
        }
        let (width, height) = layout.size;
        let world_height = layout.world_size.1;
        canvas.fill_rect(
            Rect::new(0, world_height, width, height - world_height),
            BAR_BACKGROUND,
        );
        for button in &layout.toolbar {
            let active = tool_for(button.action) == Some(sandbox.tool)
                || (button.action == "pause" && sandbox.paused);
            let label = if sandbox.paused && button.action == "pause" {
                "PLAY"
            } else {
                button.label
            };
            canvas.fill_rect(button.rect, if active { BUTTON_ACTIVE } else { BUTTON });
            canvas.outline(
                button.rect,
                if active { GOLD } else { MUTED },
                if active { 2 } else { 1 },
            );
            let center = (
                button.rect.x + button.rect.w / 2,
                button.rect.y + button.rect.h / 2,
            );
            canvas.text(label, center, WHITE, layout.label_scale, None, true);
        }
    }
}

#[cfg(test)]
mod tests;
