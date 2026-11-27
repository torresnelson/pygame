//! Catalogue of well-known patterns, written as plaintext grids:
//! `O` is a live cell, `.` is dead (port of `patterns.py`).

use crate::{Cell, Cells};

#[derive(Debug, PartialEq, Eq)]
pub struct Pattern {
    pub name: &'static str,
    pub kind: &'static str,
    pub description: &'static str,
    pub rows: &'static [&'static str],
}

impl Pattern {
    pub fn cells(&self) -> Cells {
        parse(self.rows)
    }

    /// (height, width) of the pattern's bounding box.
    pub fn size(&self) -> (i32, i32) {
        let width = self.rows.iter().map(|row| row.len()).max().unwrap_or(0);
        (self.rows.len() as i32, width as i32)
    }
}

pub fn parse(rows: &[&str]) -> Cells {
    rows.iter()
        .enumerate()
        .flat_map(|(r, row)| {
            row.chars()
                .enumerate()
                .filter(|&(_, char)| char == 'O')
                .map(move |(c, _)| (r as i32, c as i32))
        })
        .collect()
}

/// Centre `pattern` on a `rows` x `columns` board, clipping what falls outside.
pub fn place(pattern: &Cells, rows: i32, columns: i32) -> Cells {
    let (Some(height), Some(width)) = (
        pattern.iter().map(|&(r, _)| r + 1).max(),
        pattern.iter().map(|&(_, c)| c + 1).max(),
    ) else {
        return Cells::new();
    };
    let (top, left) = (
        (rows - height).div_euclid(2),
        (columns - width).div_euclid(2),
    );
    pattern
        .iter()
        .map(|&(r, c)| (r + top, c + left))
        .filter(|&(r, c)| (0..rows).contains(&r) && (0..columns).contains(&c))
        .collect()
}

/// Every cell alive with probability `density`.
pub fn random_soup(rows: i32, columns: i32, density: f64, rng: &mut fastrand::Rng) -> Cells {
    let mut cells = Cells::new();
    for r in 0..rows {
        for c in 0..columns {
            if rng.f64() < density {
                cells.insert((r, c) as Cell);
            }
        }
    }
    cells
}

pub const GLIDER: Pattern = Pattern {
    name: "Glider",
    kind: "spaceship",
    description: "The smallest spaceship, moves diagonally",
    rows: &[".O.", "..O", "OOO"],
};

pub const LWSS: Pattern = Pattern {
    name: "Lightweight spaceship",
    kind: "spaceship",
    description: "Moves left 2 cells every 4 generations",
    rows: &[".O..O", "O....", "O...O", "OOOO."],
};

pub const BLINKER: Pattern = Pattern {
    name: "Blinker",
    kind: "oscillator",
    description: "Period 2, the smallest oscillator",
    rows: &["OOO"],
};

pub const TOAD: Pattern = Pattern {
    name: "Toad",
    kind: "oscillator",
    description: "Period 2",
    rows: &[".OOO", "OOO."],
};

pub const BEACON: Pattern = Pattern {
    name: "Beacon",
    kind: "oscillator",
    description: "Period 2, two blocks blinking at the corner",
    rows: &["OO..", "OO..", "..OO", "..OO"],
};

pub const PULSAR: Pattern = Pattern {
    name: "Pulsar",
    kind: "oscillator",
    description: "Period 3, the most common big oscillator",
    rows: &[
        "..OOO...OOO..",
        ".............",
        "O....O.O....O",
        "O....O.O....O",
        "O....O.O....O",
        "..OOO...OOO..",
        ".............",
        "..OOO...OOO..",
        "O....O.O....O",
        "O....O.O....O",
        "O....O.O....O",
        ".............",
        "..OOO...OOO..",
    ],
};

pub const PENTADECATHLON: Pattern = Pattern {
    name: "Pentadecathlon",
    kind: "oscillator",
    description: "Period 15",
    rows: &["..O....O..", "OO.OOOO.OO", "..O....O.."],
};

pub const GOSPER_GUN: Pattern = Pattern {
    name: "Gosper glider gun",
    kind: "gun",
    description: "Fires a new glider every 30 generations",
    rows: &[
        "........................O...........",
        "......................O.O...........",
        "............OO......OO............OO",
        "...........O...O....OO............OO",
        "OO........O.....O...OO..............",
        "OO........O...O.OO....O.O...........",
        "..........O.....O.......O...........",
        "...........O...O....................",
        "............OO......................",
    ],
};

pub const R_PENTOMINO: Pattern = Pattern {
    name: "R-pentomino",
    kind: "methuselah",
    description: "Stays chaotic for 1103 generations",
    rows: &[".OO", "OO.", ".O."],
};

pub const DIEHARD: Pattern = Pattern {
    name: "Diehard",
    kind: "methuselah",
    description: "Vanishes completely after 130 generations",
    rows: &["......O.", "OO......", ".O...OOO"],
};

pub const ACORN: Pattern = Pattern {
    name: "Acorn",
    kind: "methuselah",
    description: "7 cells that grow for 5206 generations",
    rows: &[".O.....", "...O...", "OO..OOO"],
};

pub const RANDOM: Pattern = Pattern {
    name: "Random soup",
    kind: "random",
    description: "Fill 30% of the board at random",
    rows: &[],
};

pub const EMPTY: Pattern = Pattern {
    name: "Empty board",
    kind: "draw",
    description: "Draw your own cells with the mouse",
    rows: &[],
};

pub const CATALOGUE: [&Pattern; 13] = [
    &GLIDER,
    &LWSS,
    &BLINKER,
    &TOAD,
    &BEACON,
    &PULSAR,
    &PENTADECATHLON,
    &GOSPER_GUN,
    &R_PENTOMINO,
    &DIEHARD,
    &ACORN,
    &RANDOM,
    &EMPTY,
];

/// Initial live cells for `pattern` on a `rows` x `columns` board.
pub fn build(pattern: &Pattern, rows: i32, columns: i32, rng: &mut fastrand::Rng) -> Cells {
    if pattern.kind == RANDOM.kind {
        return random_soup(rows, columns, 0.3, rng);
    }
    place(&pattern.cells(), rows, columns)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::next_generation;
    use std::collections::HashSet;

    const BIG: i32 = 120;

    fn run(mut cells: Cells, generations: usize) -> Cells {
        for _ in 0..generations {
            cells = next_generation(&cells, BIG, BIG);
        }
        cells
    }

    fn normalised(cells: &Cells) -> Cells {
        let top = cells.iter().map(|&(r, _)| r).min().unwrap_or(0);
        let left = cells.iter().map(|&(_, c)| c).min().unwrap_or(0);
        cells.iter().map(|&(r, c)| (r - top, c - left)).collect()
    }

    fn centred(pattern: &Pattern) -> Cells {
        build(pattern, BIG, BIG, &mut fastrand::Rng::with_seed(0))
    }

    fn shifted(cells: &Cells, dr: i32, dc: i32) -> Cells {
        cells.iter().map(|&(r, c)| (r + dr, c + dc)).collect()
    }

    #[test]
    fn parse_reads_live_cells() {
        let expected: Cells = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
            .into_iter()
            .collect();
        assert_eq!(parse(&[".O.", "..O", "OOO"]), expected);
    }

    #[test]
    fn known_populations() {
        let cases: [(&Pattern, usize); 11] = [
            (&GLIDER, 5),
            (&LWSS, 9),
            (&BLINKER, 3),
            (&TOAD, 6),
            (&BEACON, 8),
            (&PULSAR, 48),
            (&PENTADECATHLON, 12),
            (&GOSPER_GUN, 36),
            (&R_PENTOMINO, 5),
            (&DIEHARD, 7),
            (&ACORN, 7),
        ];
        for (pattern, population) in cases {
            assert_eq!(pattern.cells().len(), population, "{}", pattern.name);
        }
    }

    #[test]
    fn catalogue_names_are_unique_and_described() {
        let names: HashSet<&str> = CATALOGUE.iter().map(|p| p.name).collect();
        assert_eq!(names.len(), CATALOGUE.len());
        assert!(CATALOGUE.iter().all(|p| !p.description.is_empty()));
    }

    #[test]
    fn size_is_height_by_width() {
        assert_eq!(GOSPER_GUN.size(), (9, 36));
        assert_eq!(RANDOM.size(), (0, 0));
    }

    #[test]
    fn place_centres_and_clips() {
        let one: Cells = [(0, 0)].into_iter().collect();
        assert_eq!(place(&one, 11, 11), [(5, 5)].into_iter().collect());
        assert_eq!(place(&GLIDER.cells(), 3, 3), GLIDER.cells());
        assert!(place(&GOSPER_GUN.cells(), 5, 5).len() < GOSPER_GUN.cells().len());
        assert!(place(&Cells::new(), 10, 10).is_empty());
    }

    #[test]
    fn oscillators_have_their_period() {
        for (pattern, period) in [
            (&BLINKER, 2),
            (&TOAD, 2),
            (&BEACON, 2),
            (&PULSAR, 3),
            (&PENTADECATHLON, 15),
        ] {
            let start = centred(pattern);
            assert_eq!(run(start.clone(), period), start, "{}", pattern.name);
            for n in 1..period {
                assert_ne!(run(start.clone(), n), start, "{} at {n}", pattern.name);
            }
        }
    }

    #[test]
    fn glider_moves_one_cell_diagonally_every_4_generations() {
        let start = centred(&GLIDER);
        assert_eq!(run(start.clone(), 4), shifted(&start, 1, 1));
    }

    #[test]
    fn lwss_moves_two_cells_left_every_4_generations() {
        let start = centred(&LWSS);
        assert_eq!(run(start.clone(), 4), shifted(&start, 0, -2));
    }

    #[test]
    fn gosper_gun_fires_one_glider_every_30_generations() {
        let start = centred(&GOSPER_GUN);
        let populations: Vec<usize> = (0..4).map(|k| run(start.clone(), 30 * k).len()).collect();
        let gains: Vec<usize> = populations.windows(2).map(|w| w[1] - w[0]).collect();
        assert_eq!(gains, vec![5, 5, 5]);
    }

    #[test]
    fn diehard_vanishes_after_130_generations() {
        let cells = run(centred(&DIEHARD), 129);
        assert!(!cells.is_empty());
        assert!(next_generation(&cells, BIG, BIG).is_empty());
    }

    #[test]
    fn r_pentomino_is_not_static() {
        let start = centred(&R_PENTOMINO);
        assert_ne!(normalised(&run(start.clone(), 50)), normalised(&start));
    }

    #[test]
    fn random_soup_and_empty() {
        let soup = build(&RANDOM, 20, 20, &mut fastrand::Rng::with_seed(1));
        assert!((60..180).contains(&soup.len()), "{}", soup.len());
        assert!(
            soup.iter()
                .all(|&(r, c)| (0..20).contains(&r) && (0..20).contains(&c))
        );
        assert!(build(&EMPTY, 20, 20, &mut fastrand::Rng::with_seed(1)).is_empty());
    }
}
