//! Conway's Game of Life on a bounded (non-wrapping) board, plus the pattern
//! catalogue (port of `src/game_of_life/life.py` and `patterns.py`).
//!
//! Cells are `(row, column)` pairs; the board state is the set of live cells.

mod patterns;

pub use patterns::{
    ACORN, BEACON, BLINKER, CATALOGUE, DIEHARD, EMPTY, GLIDER, GOSPER_GUN, LWSS, PENTADECATHLON,
    PULSAR, Pattern, R_PENTOMINO, RANDOM, TOAD, build, parse, place, random_soup,
};

use std::collections::{HashMap, HashSet};

pub type Cell = (i32, i32);
pub type Cells = HashSet<Cell>;

const NEIGHBOUR_OFFSETS: [Cell; 8] = [
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
];

/// Live neighbours of every cell next to a live cell, inside the board.
pub fn neighbour_counts(cells: &Cells, rows: i32, columns: i32) -> HashMap<Cell, u8> {
    let mut counts = HashMap::new();
    for &(r, c) in cells {
        for (dr, dc) in NEIGHBOUR_OFFSETS {
            let (nr, nc) = (r + dr, c + dc);
            if (0..rows).contains(&nr) && (0..columns).contains(&nc) {
                *counts.entry((nr, nc)).or_insert(0) += 1;
            }
        }
    }
    counts
}

/// Birth on 3 neighbours, survival on 2 or 3, death otherwise.
pub fn next_generation(cells: &Cells, rows: i32, columns: i32) -> Cells {
    neighbour_counts(cells, rows, columns)
        .into_iter()
        .filter(|&(cell, count)| count == 3 || (count == 2 && cells.contains(&cell)))
        .map(|(cell, _)| cell)
        .collect()
}

/// `cells` with `cell` flipped between alive and dead.
pub fn toggle(cells: &Cells, cell: Cell) -> Cells {
    let mut toggled = cells.clone();
    if !toggled.remove(&cell) {
        toggled.insert(cell);
    }
    toggled
}

/// The cell under pixel (`x`, `y`), or `None` for gaps and outside the board.
pub fn cell_at(x: i32, y: i32, size: i32, gap: i32, amount: i32) -> Option<Cell> {
    let pitch = size + gap;
    let (row, row_offset) = (y.div_euclid(pitch), y.rem_euclid(pitch));
    let (column, column_offset) = (x.div_euclid(pitch), x.rem_euclid(pitch));
    if !(0..amount).contains(&row) || !(0..amount).contains(&column) {
        return None;
    }
    if row_offset >= size || column_offset >= size {
        return None;
    }
    Some((row, column))
}

#[cfg(test)]
mod tests {
    use super::*;

    const N: i32 = 10;

    fn set(cells: &[Cell]) -> Cells {
        cells.iter().copied().collect()
    }

    #[test]
    fn empty_board_stays_empty() {
        assert!(next_generation(&Cells::new(), N, N).is_empty());
    }

    #[test]
    fn lonely_cell_dies() {
        assert!(next_generation(&set(&[(5, 5)]), N, N).is_empty());
    }

    #[test]
    fn block_is_still_life() {
        let block = set(&[(1, 1), (1, 2), (2, 1), (2, 2)]);
        assert_eq!(next_generation(&block, N, N), block);
    }

    #[test]
    fn blinker_oscillates() {
        let horizontal = set(&[(5, 4), (5, 5), (5, 6)]);
        let vertical = set(&[(4, 5), (5, 5), (6, 5)]);
        assert_eq!(next_generation(&horizontal, N, N), vertical);
        assert_eq!(next_generation(&vertical, N, N), horizontal);
    }

    #[test]
    fn glider_moves_diagonally() {
        let glider = set(&[(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]);
        let mut cells = glider.clone();
        for _ in 0..4 {
            cells = next_generation(&cells, N, N);
        }
        let moved: Cells = glider.iter().map(|&(r, c)| (r + 1, c + 1)).collect();
        assert_eq!(cells, moved);
    }

    #[test]
    fn board_edges_do_not_wrap() {
        // A blinker on the top edge loses its out-of-board cells.
        let top_edge = set(&[(0, 4), (0, 5), (0, 6)]);
        assert_eq!(next_generation(&top_edge, N, N), set(&[(0, 5), (1, 5)]));
        // Corner block survives without wrapping neighbours.
        let corner = set(&[(0, 0), (0, 1), (1, 0), (1, 1)]);
        assert_eq!(next_generation(&corner, N, N), corner);
    }

    #[test]
    fn toggle_adds_and_removes() {
        let cells = toggle(&Cells::new(), (1, 1));
        assert_eq!(cells, set(&[(1, 1)]));
        assert!(toggle(&cells, (1, 1)).is_empty());
    }

    #[test]
    fn cell_at_maps_pixels_and_skips_gaps() {
        let at = |x, y| cell_at(x, y, 20, 1, 20);
        assert_eq!(at(0, 0), Some((0, 0)));
        assert_eq!(at(19, 19), Some((0, 0)));
        assert_eq!(at(20, 0), None); // gap column
        assert_eq!(at(21, 0), Some((0, 1)));
        assert_eq!(at(21 * 19 + 5, 21 * 3 + 5), Some((3, 19)));
        assert_eq!(at(21 * 20, 0), None); // past the right edge
        assert_eq!(at(-1, 0), None);
    }
}
