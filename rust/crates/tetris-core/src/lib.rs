//! Tetris rules (port of `src/tetris/tetris_logic.py`) and the high score
//! table (port of `highscores.py`). No engine code, so all of it is testable.
//!
//! The board is 10 x 20. Locked blocks map `(x, y)` to a colour; `y` grows
//! downwards and may be negative while a piece spawns.

pub mod highscores;

use std::collections::{BTreeSet, HashMap};

pub type Color = (u8, u8, u8);
pub type Pos = (i32, i32);
pub type Locked = HashMap<Pos, Color>;
/// One 5x5 rotation frame; `0` marks a block.
pub type Frame = [&'static str; 5];
pub type Shape = &'static [Frame];

pub const ROWS: i32 = 20;
pub const COLUMNS: i32 = 10;
pub type Grid = [[Color; COLUMNS as usize]; ROWS as usize];

pub const EMPTY: Color = (0, 0, 0);
/// Points for clearing 1, 2, 3 or 4 lines at once, multiplied by (level + 1).
pub const LINE_POINTS: [u32; 5] = [0, 40, 100, 300, 1200];
pub const LINES_PER_LEVEL: u32 = 10;
pub const BASE_FALL_S: f32 = 0.5;
pub const MIN_FALL_S: f32 = 0.05;
pub const FALL_STEP: f32 = 0.85;

// Limited NES-style palette for an 8-bit look.
pub const RED: Color = (228, 52, 32);
pub const GREEN: Color = (60, 188, 56);
pub const YELLOW: Color = (248, 216, 32);
pub const ORANGE: Color = (252, 140, 32);
pub const BLUE: Color = (40, 84, 228);
pub const LIGHT_BLUE: Color = (60, 196, 252);
pub const PURPLE: Color = (172, 60, 200);

#[rustfmt::skip]
pub const S: Shape = &[
    [".....", ".....", "..00.", ".00..", "....."],
    [".....", "..0..", "..00.", "...0.", "....."],
];
#[rustfmt::skip]
pub const Z: Shape = &[
    [".....", ".....", ".00..", "..00.", "....."],
    [".....", "..0..", ".00..", ".0...", "....."],
];
#[rustfmt::skip]
pub const I: Shape = &[
    ["..0..", "..0..", "..0..", "..0..", "....."],
    [".....", "0000.", ".....", ".....", "....."],
];
#[rustfmt::skip]
pub const O: Shape = &[
    [".....", ".....", ".00..", ".00..", "....."],
];
#[rustfmt::skip]
pub const J: Shape = &[
    [".....", ".0...", ".000.", ".....", "....."],
    [".....", "..00.", "..0..", "..0..", "....."],
    [".....", ".....", ".000.", "...0.", "....."],
    [".....", "..0..", "..0..", ".00..", "....."],
];
#[rustfmt::skip]
pub const L: Shape = &[
    [".....", "...0.", ".000.", ".....", "....."],
    [".....", "..0..", "..0..", "..00.", "....."],
    [".....", ".....", ".000.", ".0...", "....."],
    [".....", ".00..", "..0..", "..0..", "....."],
];
#[rustfmt::skip]
pub const T: Shape = &[
    [".....", "..0..", ".000.", ".....", "....."],
    [".....", "..0..", "..00.", "..0..", "....."],
    [".....", ".....", ".000.", "..0..", "....."],
    [".....", "..0..", ".00..", "..0..", "....."],
];

pub const SHAPES: [Shape; 7] = [S, Z, I, O, J, L, T];
pub const SHAPE_COLORS: [Color; 7] = [GREEN, RED, LIGHT_BLUE, YELLOW, ORANGE, BLUE, PURPLE];

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Piece {
    pub x: i32,
    pub y: i32,
    pub shape: Shape,
    pub color: Color,
    pub rotation: i32,
}

impl Piece {
    pub fn new(x: i32, y: i32, shape: Shape, color: Color) -> Self {
        Self {
            x,
            y,
            shape,
            color,
            rotation: 0,
        }
    }

    pub fn frame(&self) -> &'static Frame {
        &self.shape[self.rotation.rem_euclid(self.shape.len() as i32) as usize]
    }
}

pub fn new_piece(rng: &mut fastrand::Rng) -> Piece {
    let index = rng.usize(..SHAPES.len());
    Piece::new(5, 0, SHAPES[index], SHAPE_COLORS[index])
}

pub fn create_grid(locked: &Locked) -> Grid {
    let mut grid = [[EMPTY; COLUMNS as usize]; ROWS as usize];
    for (&(x, y), &color) in locked {
        if (0..COLUMNS).contains(&x) && (0..ROWS).contains(&y) {
            grid[y as usize][x as usize] = color;
        }
    }
    grid
}

/// Block coordinates of a 5x5 frame placed with its top-left at `(x, y)`.
pub fn frame_positions(frame: &Frame, x: i32, y: i32) -> Vec<Pos> {
    frame
        .iter()
        .enumerate()
        .flat_map(|(i, line)| {
            line.chars()
                .enumerate()
                .filter(|&(_, cell)| cell == '0')
                .map(move |(j, _)| (x + j as i32, y + i as i32))
        })
        .collect()
}

/// Board coordinates of `piece`; frames are anchored at offset (2, 4).
pub fn piece_positions(piece: &Piece) -> Vec<Pos> {
    frame_positions(piece.frame(), piece.x - 2, piece.y - 4)
}

pub fn valid_space(piece: &Piece, grid: &Grid) -> bool {
    piece_positions(piece).into_iter().all(|(x, y)| {
        (0..COLUMNS).contains(&x) && y < ROWS && (y < 0 || grid[y as usize][x as usize] == EMPTY)
    })
}

/// Apply the move if it lands in a valid space; return whether it did.
pub fn try_move(piece: &mut Piece, grid: &Grid, dx: i32, dy: i32, rotate: i32) -> bool {
    let frames = piece.shape.len() as i32;
    let before = (piece.x, piece.y, piece.rotation);
    piece.x += dx;
    piece.y += dy;
    piece.rotation = (piece.rotation + rotate).rem_euclid(frames);
    if valid_space(piece, grid) {
        return true;
    }
    (piece.x, piece.y, piece.rotation) = before;
    false
}

pub fn hard_drop(piece: &mut Piece, grid: &Grid) {
    while try_move(piece, grid, 0, 1, 0) {}
}

/// `locked` plus `piece`'s blocks (the input is left untouched).
pub fn lock_piece(piece: &Piece, locked: &Locked) -> Locked {
    let mut result = locked.clone();
    result.extend(
        piece_positions(piece)
            .into_iter()
            .map(|pos| (pos, piece.color)),
    );
    result
}

pub fn check_lost(locked: &Locked) -> bool {
    locked.keys().any(|&(_, y)| y < 1)
}

pub fn full_rows(locked: &Locked) -> BTreeSet<i32> {
    (0..ROWS)
        .filter(|&y| (0..COLUMNS).all(|x| locked.contains_key(&(x, y))))
        .collect()
}

/// Remove full rows and drop every block by the number of cleared rows below it.
///
/// Works for non-contiguous clears (e.g. rows 17 and 19 full, 18 not).
pub fn clear_rows(locked: &Locked) -> (Locked, u32) {
    let full = full_rows(locked);
    let remaining = locked
        .iter()
        .filter(|&(&(_, y), _)| !full.contains(&y))
        .map(|(&(x, y), &color)| {
            let below = full.iter().filter(|&&row| row > y).count() as i32;
            ((x, y + below), color)
        })
        .collect();
    (remaining, full.len() as u32)
}

/// Classic scoring: multi-line clears are worth more, scaled by level.
pub fn score_for_lines(lines: u32, level: u32) -> u32 {
    LINE_POINTS[lines.min(4) as usize] * (level + 1)
}

pub fn level_for_lines(total_lines: u32) -> u32 {
    total_lines / LINES_PER_LEVEL
}

/// Seconds between automatic drops; pieces fall faster every level.
pub fn fall_interval(level: u32) -> f32 {
    (BASE_FALL_S * FALL_STEP.powi(level as i32)).max(MIN_FALL_S)
}

#[cfg(test)]
mod tests {
    use super::*;

    const R: Color = (255, 0, 0);

    fn full_row(y: i32) -> Locked {
        (0..COLUMNS).map(|x| ((x, y), R)).collect()
    }

    fn locked(parts: &[Locked], extra: &[Pos]) -> Locked {
        let mut all: Locked = parts.iter().flat_map(|p| p.clone()).collect();
        all.extend(extra.iter().map(|&pos| (pos, R)));
        all
    }

    fn sorted(mut positions: Vec<Pos>) -> Vec<Pos> {
        positions.sort();
        positions
    }

    #[test]
    fn create_grid_places_locked_blocks() {
        let grid = create_grid(&locked(&[], &[(3, 7)]));
        assert_eq!(grid[7][3], R);
        let filled = grid.iter().flatten().filter(|&&cell| cell != EMPTY).count();
        assert_eq!(filled, 1);
    }

    #[test]
    fn piece_positions_o_shape() {
        let piece = Piece::new(5, 4, O, R);
        assert_eq!(
            sorted(piece_positions(&piece)),
            vec![(4, 2), (4, 3), (5, 2), (5, 3)]
        );
    }

    #[test]
    fn clear_single_bottom_row_shifts_above() {
        let (remaining, lines) = clear_rows(&locked(&[full_row(19)], &[(0, 18)]));
        assert_eq!(lines, 1);
        assert_eq!(remaining, locked(&[], &[(0, 19)]));
    }

    #[test]
    fn clear_non_contiguous_rows_keeps_every_block() {
        // Rows 19 and 17 are full; row 18 and row 16 each hold one block.
        let board = locked(&[full_row(19), full_row(17)], &[(0, 18), (0, 16)]);
        let (remaining, lines) = clear_rows(&board);
        assert_eq!(lines, 2);
        assert_eq!(remaining, locked(&[], &[(0, 19), (0, 18)]));
    }

    #[test]
    fn full_rows_finds_complete_rows_only() {
        let board = locked(&[full_row(19), full_row(17)], &[(0, 18)]);
        assert_eq!(full_rows(&board), [17, 19].into_iter().collect());
        assert!(full_rows(&locked(&[], &[(0, 19)])).is_empty());
    }

    #[test]
    fn clear_rows_without_full_rows_is_noop() {
        let board = locked(&[], &[(0, 19), (5, 10)]);
        assert_eq!(clear_rows(&board), (board.clone(), 0));
    }

    #[test]
    fn clear_four_rows_tetris() {
        let board = locked(
            &[full_row(16), full_row(17), full_row(18), full_row(19)],
            &[(2, 15)],
        );
        let (remaining, lines) = clear_rows(&board);
        assert_eq!(lines, 4);
        assert_eq!(remaining, locked(&[], &[(2, 19)]));
    }

    #[test]
    fn score_for_lines_matches_classic_scoring() {
        let cases = [
            (0, 0, 0),
            (1, 0, 40),
            (2, 0, 100),
            (3, 0, 300),
            (4, 0, 1200),
        ];
        for (lines, level, points) in cases.into_iter().chain([(1, 2, 120), (4, 9, 12000)]) {
            assert_eq!(
                score_for_lines(lines, level),
                points,
                "{lines} lines at {level}"
            );
        }
    }

    #[test]
    fn level_for_lines_every_ten() {
        for (total, level) in [(0, 0), (9, 0), (10, 1), (25, 2), (100, 10)] {
            assert_eq!(level_for_lines(total), level);
        }
    }

    #[test]
    fn fall_interval_speeds_up_and_is_capped() {
        let intervals: Vec<f32> = (0..40).map(fall_interval).collect();
        assert!((intervals[0] - 0.5).abs() < 1e-6);
        assert!(intervals.windows(2).all(|w| w[0] >= w[1]));
        assert!(intervals[1] < intervals[0]);
        assert!((intervals[39] - 0.05).abs() < 1e-6);
    }

    #[test]
    fn valid_space_rejects_walls_floor_and_blocks() {
        let grid = create_grid(&locked(&[], &[(5, 10)]));
        assert!(valid_space(&Piece::new(5, 5, O, R), &grid));
        assert!(!valid_space(&Piece::new(0, 5, O, R), &grid)); // x = -1
        assert!(!valid_space(&Piece::new(10, 5, O, R), &grid)); // x = 9..10
        assert!(!valid_space(&Piece::new(5, 24, O, R), &grid)); // y = 20
        assert!(!valid_space(&Piece::new(6, 12, O, R), &grid)); // overlaps (5, 10)
        assert!(valid_space(&Piece::new(6, 13, O, R), &grid)); // just below it
    }

    #[test]
    fn valid_space_allows_spawn_above_board() {
        assert!(valid_space(
            &Piece::new(5, 0, I, R),
            &create_grid(&Locked::new())
        ));
    }

    #[test]
    fn rotation_wraps_and_reverts_when_blocked() {
        let grid = create_grid(&Locked::new());
        let mut piece = Piece {
            rotation: 3,
            ..Piece::new(5, 10, T, R)
        };
        assert!(try_move(&mut piece, &grid, 0, 0, 1));
        assert_eq!(piece.rotation, 0);

        // Vertical I against the left wall cannot rotate to horizontal.
        let mut piece = Piece::new(0, 10, I, R);
        assert!(!try_move(&mut piece, &grid, 0, 0, 1));
        assert_eq!(piece.rotation, 0);
    }

    #[test]
    fn try_move_reverts_on_collision() {
        let grid = create_grid(&Locked::new());
        let mut piece = Piece::new(1, 10, O, R);
        assert!(!try_move(&mut piece, &grid, -1, 0, 0));
        assert_eq!(piece.x, 1);
    }

    #[test]
    fn hard_drop_lands_on_floor_and_on_blocks() {
        let lowest = |piece: &Piece| piece_positions(piece).iter().map(|&(_, y)| y).max();
        let mut piece = Piece::new(5, 0, O, R);
        hard_drop(&mut piece, &create_grid(&Locked::new()));
        assert_eq!(lowest(&piece), Some(ROWS - 1));

        let mut piece = Piece::new(5, 0, O, R);
        hard_drop(&mut piece, &create_grid(&full_row(19)));
        assert_eq!(lowest(&piece), Some(ROWS - 2));
    }

    #[test]
    fn lock_piece_does_not_mutate_input() {
        let empty = Locked::new();
        let result = lock_piece(&Piece::new(5, 5, O, R), &empty);
        assert!(empty.is_empty());
        assert_eq!(result.len(), 4);
    }

    #[test]
    fn check_lost_when_blocks_reach_the_top() {
        assert!(!check_lost(&locked(&[], &[(0, 19)])));
        assert!(check_lost(&locked(&[], &[(0, 0)])));
        assert!(check_lost(&locked(&[], &[(0, -1)])));
    }

    #[test]
    fn new_piece_color_matches_shape() {
        let mut rng = fastrand::Rng::with_seed(1);
        for _ in 0..20 {
            let piece = new_piece(&mut rng);
            // Compare by value: `const` shapes have no fixed address.
            let index = SHAPES.iter().position(|&s| s == piece.shape).unwrap();
            assert_eq!(piece.color, SHAPE_COLORS[index]);
        }
    }
}
