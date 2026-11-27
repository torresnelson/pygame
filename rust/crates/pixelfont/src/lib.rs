//! Built-in 5x7 bitmap font for an 8-bit look (port of `src/shared/pixelfont.py`).
//!
//! Each glyph is 7 rows of 5 cells (`#` on, `.` off). Text is upper-cased;
//! unknown characters render as `?`. The crate only computes geometry; the
//! game draws the returned rectangles.

pub const GLYPH_WIDTH: i32 = 5;
pub const GLYPH_HEIGHT: i32 = 7;
pub const SPACING: i32 = 1;

/// Glyph table, copied verbatim from the Python font.
const RAW: &[(char, &str)] = &[
    ('A', ".###. #...# #...# ##### #...# #...# #...#"),
    ('B', "####. #...# #...# ####. #...# #...# ####."),
    ('C', ".###. #...# #.... #.... #.... #...# .###."),
    ('D', "####. #...# #...# #...# #...# #...# ####."),
    ('E', "##### #.... #.... ####. #.... #.... #####"),
    ('F', "##### #.... #.... ####. #.... #.... #...."),
    ('G', ".###. #...# #.... #.### #...# #...# .####"),
    ('H', "#...# #...# #...# ##### #...# #...# #...#"),
    ('I', ".###. ..#.. ..#.. ..#.. ..#.. ..#.. .###."),
    ('J', "..### ...#. ...#. ...#. ...#. #..#. .##.."),
    ('K', "#...# #..#. #.#.. ##... #.#.. #..#. #...#"),
    ('L', "#.... #.... #.... #.... #.... #.... #####"),
    ('M', "#...# ##.## #.#.# #.#.# #...# #...# #...#"),
    ('N', "#...# #...# ##..# #.#.# #..## #...# #...#"),
    ('O', ".###. #...# #...# #...# #...# #...# .###."),
    ('P', "####. #...# #...# ####. #.... #.... #...."),
    ('Q', ".###. #...# #...# #...# #.#.# #..#. .##.#"),
    ('R', "####. #...# #...# ####. #.#.. #..#. #...#"),
    ('S', ".#### #.... #.... .###. ....# ....# ####."),
    ('T', "##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#.."),
    ('U', "#...# #...# #...# #...# #...# #...# .###."),
    ('V', "#...# #...# #...# #...# #...# .#.#. ..#.."),
    ('W', "#...# #...# #...# #.#.# #.#.# #.#.# .#.#."),
    ('X', "#...# #...# .#.#. ..#.. .#.#. #...# #...#"),
    ('Y', "#...# #...# .#.#. ..#.. ..#.. ..#.. ..#.."),
    ('Z', "##### ....# ...#. ..#.. .#... #.... #####"),
    ('0', ".###. #...# #..## #.#.# ##..# #...# .###."),
    ('1', "..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###."),
    ('2', ".###. #...# ....# ...#. ..#.. .#... #####"),
    ('3', "####. ....# ....# .###. ....# ....# ####."),
    ('4', "...#. ..##. .#.#. #..#. ##### ...#. ...#."),
    ('5', "##### #.... ####. ....# ....# #...# .###."),
    ('6', ".###. #.... #.... ####. #...# #...# .###."),
    ('7', "##### ....# ...#. ..#.. .#... .#... .#..."),
    ('8', ".###. #...# #...# .###. #...# #...# .###."),
    ('9', ".###. #...# #...# .#### ....# ....# .###."),
    (' ', "..... ..... ..... ..... ..... ..... ....."),
    ('.', "..... ..... ..... ..... ..... .##.. .##.."),
    (',', "..... ..... ..... ..... .##.. ..#.. .#..."),
    (':', "..... .##.. .##.. ..... .##.. .##.. ....."),
    ('!', "..#.. ..#.. ..#.. ..#.. ..#.. ..... ..#.."),
    ('?', ".###. #...# ....# ...#. ..#.. ..... ..#.."),
    ('-', "..... ..... ..... ##### ..... ..... ....."),
    ('+', "..... ..#.. ..#.. ##### ..#.. ..#.. ....."),
    ('/', "....# ....# ...#. ..#.. .#... #.... #...."),
    ('>', ".#... ..#.. ...#. ....# ...#. ..#.. .#..."),
    ('<', "...#. ..#.. .#... #.... .#... ..#.. ...#."),
    ('(', "...#. ..#.. .#... .#... .#... ..#.. ...#."),
    (')', ".#... ..#.. ...#. ...#. ...#. ..#.. .#..."),
    ('_', "..... ..... ..... ..... ..... ..... #####"),
    ('[', ".###. .#... .#... .#... .#... .#... .###."),
    (']', ".###. ...#. ...#. ...#. ...#. ...#. .###."),
    ('\'', "..#.. ..#.. .#... ..... ..... ..... ....."),
];

/// A rectangle in pixels: top-left corner, width and height.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Rect {
    pub x: i32,
    pub y: i32,
    pub w: i32,
    pub h: i32,
}

impl Rect {
    pub const fn new(x: i32, y: i32, w: i32, h: i32) -> Self {
        Self { x, y, w, h }
    }
}

/// Every character the font can draw.
pub fn charset() -> impl Iterator<Item = char> {
    RAW.iter().map(|&(char, _)| char)
}

fn glyph(char: char) -> Option<&'static str> {
    RAW.iter().find(|&&(c, _)| c == char).map(|&(_, rows)| rows)
}

/// The 7 rows of `char`'s glyph, or `None` if the font lacks it.
pub fn glyph_rows(char: char) -> Option<Vec<&'static str>> {
    glyph(char).map(|rows| rows.split(' ').collect())
}

/// Upper-case `text` and replace characters the font lacks with `?`.
pub fn normalise(text: &str) -> String {
    text.to_uppercase()
        .chars()
        .map(|char| if glyph(char).is_some() { char } else { '?' })
        .collect()
}

/// (width, height) of `text` at `scale`.
pub fn text_size(text: &str, scale: i32) -> (i32, i32) {
    let count = normalise(text).chars().count() as i32;
    if count == 0 {
        return (0, GLYPH_HEIGHT * scale);
    }
    let advance = (GLYPH_WIDTH + SPACING) * scale;
    (count * advance - SPACING * scale, GLYPH_HEIGHT * scale)
}

/// (x, y) cells that are on for `char` (unknown characters use `?`).
pub fn glyph_pixels(char: char) -> Vec<(i32, i32)> {
    let normalised = normalise(&char.to_string()).chars().next().unwrap_or('?');
    let rows = glyph(normalised).unwrap_or_else(|| glyph('?').expect("'?' glyph"));
    rows.split(' ')
        .enumerate()
        .flat_map(|(y, row)| {
            row.chars()
                .enumerate()
                .filter(|&(_, cell)| cell == '#')
                .map(move |(x, _)| (x as i32, y as i32))
        })
        .collect()
}

/// Rectangles (relative to the text's top-left) that make up `text`.
pub fn pixel_rects(text: &str, scale: i32) -> Vec<Rect> {
    let advance = (GLYPH_WIDTH + SPACING) * scale;
    normalise(text)
        .chars()
        .enumerate()
        .flat_map(|(i, char)| {
            glyph_pixels(char).into_iter().map(move |(x, y)| {
                Rect::new(i as i32 * advance + x * scale, y * scale, scale, scale)
            })
        })
        .collect()
}

/// Where `text` lands when drawn at `pos` (top-left, or centre when `center`).
///
/// Matches the rectangle the Python `draw` returns: a drop shadow (offset by
/// one font pixel) makes the box one font pixel larger.
pub fn text_rect(text: &str, pos: (i32, i32), scale: i32, shadow: bool, center: bool) -> Rect {
    let (width, height) = text_size(text, scale);
    let (mut x, mut y) = pos;
    if center {
        x -= width.div_euclid(2);
        y -= height.div_euclid(2);
    }
    let offset = if shadow { scale } else { 0 };
    Rect::new(x, y, width + offset, height + offset)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    #[test]
    fn every_glyph_is_5x7_of_on_and_off_cells() {
        for char in charset() {
            let rows = glyph_rows(char).unwrap();
            assert_eq!(rows.len(), GLYPH_HEIGHT as usize, "{char}");
            for row in rows {
                assert_eq!(row.len(), GLYPH_WIDTH as usize, "{char}");
                assert!(row.chars().all(|cell| cell == '#' || cell == '.'), "{char}");
            }
        }
    }

    #[test]
    fn letters_digits_and_ui_punctuation_are_covered() {
        let set: HashSet<char> = charset().collect();
        let wanted = ('A'..='Z').chain('0'..='9').chain(" .:!?-/>[]".chars());
        for char in wanted {
            assert!(set.contains(&char), "{char}");
        }
    }

    #[test]
    fn glyphs_are_distinct_and_only_space_is_blank() {
        let shapes: HashSet<&str> = RAW.iter().map(|&(_, rows)| rows).collect();
        assert_eq!(shapes.len(), RAW.len());
        let blank: Vec<char> = charset().filter(|&c| glyph_pixels(c).is_empty()).collect();
        assert_eq!(blank, vec![' ']);
    }

    #[test]
    fn normalise_uppercases_and_replaces_unknown() {
        assert_eq!(normalise("Nelson 1st!"), "NELSON 1ST!");
        assert_eq!(normalise("a~b"), "A?B");
    }

    #[test]
    fn text_size_matches_python() {
        assert_eq!(text_size("", 1), (0, 7));
        assert_eq!(text_size("A", 1), (5, 7));
        assert_eq!(text_size("AB", 1), (11, 7));
        assert_eq!(text_size("TETRIS", 3), (105, 21));
    }

    #[test]
    fn pixel_rects_put_each_glyph_pixel_at_scale() {
        let rects = pixel_rects("I", 2);
        let expected: Vec<Rect> = glyph_pixels('I')
            .into_iter()
            .map(|(x, y)| Rect::new(x * 2, y * 2, 2, 2))
            .collect();
        assert_eq!(rects, expected);
        // The second glyph starts one advance (6 font pixels) to the right.
        let pair = pixel_rects("II", 1);
        assert!(pair.contains(&Rect::new(6 + 1, 0, 1, 1)));
    }

    #[test]
    fn pixel_rects_count_matches_glyphs() {
        assert_eq!(
            pixel_rects("HI", 3).len(),
            glyph_pixels('H').len() + glyph_pixels('I').len()
        );
        assert!(pixel_rects("", 1).is_empty());
    }

    #[test]
    fn text_rect_matches_python_draw() {
        assert_eq!(
            text_rect("I", (3, 4), 2, false, false),
            Rect::new(3, 4, 10, 14)
        );
        assert_eq!(
            text_rect("HI", (20, 15), 1, true, true),
            Rect::new(15, 12, 12, 8)
        );
    }

    #[test]
    fn unknown_characters_draw_as_question_marks() {
        assert_eq!(glyph_pixels('~'), glyph_pixels('?'));
        assert_eq!(glyph_pixels('a'), glyph_pixels('A'));
    }
}
