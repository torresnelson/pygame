//! A CPU pixel buffer the games draw on, like the pygame surfaces they came
//! from: plain rectangle fills, so drawing is exact and testable without a GPU.
//! The display module uploads it to the screen once per frame.

use pixelfont::Rect;

pub type Rgb = (u8, u8, u8);

pub const BLACK: Rgb = (0, 0, 0);

/// An opaque RGBA8 image, `width` x `height` pixels, origin at the top-left.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Canvas {
    width: i32,
    height: i32,
    pixels: Vec<u8>,
}

impl Canvas {
    /// A black canvas.
    pub fn new(width: i32, height: i32) -> Self {
        let mut canvas = Self {
            width,
            height,
            pixels: Vec::new(),
        };
        canvas.resize(width, height);
        canvas
    }

    pub fn width(&self) -> i32 {
        self.width
    }

    pub fn height(&self) -> i32 {
        self.height
    }

    pub fn size(&self) -> (i32, i32) {
        (self.width, self.height)
    }

    /// RGBA bytes, row by row (what the GPU texture receives).
    pub fn pixels(&self) -> &[u8] {
        &self.pixels
    }

    /// Change the size; the content becomes black.
    pub fn resize(&mut self, width: i32, height: i32) {
        self.width = width.max(1);
        self.height = height.max(1);
        let count = (self.width * self.height) as usize;
        self.pixels = [0, 0, 0, 255].repeat(count);
    }

    pub fn get(&self, x: i32, y: i32) -> Option<Rgb> {
        if !(0..self.width).contains(&x) || !(0..self.height).contains(&y) {
            return None;
        }
        let i = ((y * self.width + x) * 4) as usize;
        Some((self.pixels[i], self.pixels[i + 1], self.pixels[i + 2]))
    }

    pub fn set(&mut self, x: i32, y: i32, color: Rgb) {
        self.fill_rect(Rect::new(x, y, 1, 1), color);
    }

    pub fn fill(&mut self, color: Rgb) {
        self.fill_rect(Rect::new(0, 0, self.width, self.height), color);
    }

    /// Fill `rect`, clipped to the canvas.
    pub fn fill_rect(&mut self, rect: Rect, color: Rgb) {
        let (x0, y0) = (rect.x.max(0), rect.y.max(0));
        let (x1, y1) = (
            (rect.x + rect.w).min(self.width),
            (rect.y + rect.h).min(self.height),
        );
        if x0 >= x1 || y0 >= y1 {
            return;
        }
        let pixel = [color.0, color.1, color.2, 255];
        for y in y0..y1 {
            let start = ((y * self.width + x0) * 4) as usize;
            let end = ((y * self.width + x1) * 4) as usize;
            let (row, _) = self.pixels[start..end].as_chunks_mut::<4>();
            row.fill(pixel);
        }
    }

    /// A `width`-pixel border drawn inside `rect` (like `pygame.draw.rect(..., width)`).
    pub fn outline(&mut self, rect: Rect, color: Rgb, width: i32) {
        let w = width.min(rect.w).min(rect.h).max(1);
        self.fill_rect(Rect::new(rect.x, rect.y, rect.w, w), color);
        self.fill_rect(Rect::new(rect.x, rect.y + rect.h - w, rect.w, w), color);
        self.fill_rect(Rect::new(rect.x, rect.y, w, rect.h), color);
        self.fill_rect(Rect::new(rect.x + rect.w - w, rect.y, w, rect.h), color);
    }

    /// Draw `text` in the pixel font at `pos` (top-left, or centre when `center`).
    ///
    /// Same result as the Python `pixelfont.draw`: `shadow` adds a drop shadow
    /// offset by one font pixel; returns the box the text covers.
    pub fn text(
        &mut self,
        text: &str,
        pos: (i32, i32),
        color: Rgb,
        scale: i32,
        shadow: Option<Rgb>,
        center: bool,
    ) -> Rect {
        let area = pixelfont::text_rect(text, pos, scale, shadow.is_some(), center);
        let rects = pixelfont::pixel_rects(text, scale);
        if let Some(shadow) = shadow {
            for r in &rects {
                self.fill_rect(
                    Rect::new(area.x + r.x + scale, area.y + r.y + scale, r.w, r.h),
                    shadow,
                );
            }
        }
        for r in &rects {
            self.fill_rect(Rect::new(area.x + r.x, area.y + r.y, r.w, r.h), color);
        }
        area
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const WHITE: Rgb = (255, 255, 255);

    #[test]
    fn new_canvas_is_black_and_opaque() {
        let canvas = Canvas::new(3, 2);
        assert_eq!(canvas.pixels().len(), 3 * 2 * 4);
        assert!(canvas.pixels().chunks(4).all(|p| p == [0, 0, 0, 255]));
        assert_eq!(canvas.get(2, 1), Some(BLACK));
        assert_eq!(canvas.get(3, 0), None);
    }

    #[test]
    fn fill_rect_is_clipped_to_the_canvas() {
        let mut canvas = Canvas::new(4, 4);
        canvas.fill_rect(Rect::new(-2, 2, 4, 10), WHITE);
        let lit: Vec<(i32, i32)> = (0..4)
            .flat_map(|y| (0..4).map(move |x| (x, y)))
            .filter(|&(x, y)| canvas.get(x, y) == Some(WHITE))
            .collect();
        assert_eq!(lit, [(0, 2), (1, 2), (0, 3), (1, 3)]);
        canvas.fill_rect(Rect::new(10, 10, 3, 3), WHITE); // fully outside: no panic
    }

    #[test]
    fn outline_draws_a_border_inside_the_rect() {
        let mut canvas = Canvas::new(5, 5);
        canvas.outline(Rect::new(0, 0, 5, 5), WHITE, 1);
        assert_eq!(canvas.get(0, 0), Some(WHITE));
        assert_eq!(canvas.get(4, 4), Some(WHITE));
        assert_eq!(canvas.get(4, 2), Some(WHITE));
        assert_eq!(canvas.get(2, 2), Some(BLACK));
    }

    #[test]
    fn text_fills_glyph_pixels_like_python() {
        let mut canvas = Canvas::new(40, 30);
        let area = canvas.text("I", (3, 4), WHITE, 2, None, false);
        assert_eq!(area, Rect::new(3, 4, 10, 14));
        let on = pixelfont::glyph_pixels('I');
        for y in 0..pixelfont::GLYPH_HEIGHT {
            for x in 0..pixelfont::GLYPH_WIDTH {
                let lit = canvas.get(3 + x * 2 + 1, 4 + y * 2 + 1) != Some(BLACK);
                assert_eq!(lit, on.contains(&(x, y)), "({x}, {y})");
            }
        }
    }

    #[test]
    fn text_center_and_shadow_like_python() {
        let mut canvas = Canvas::new(40, 30);
        let area = canvas.text("HI", (20, 15), WHITE, 1, Some((100, 0, 0)), true);
        assert_eq!(area, Rect::new(15, 12, 12, 8));
        // 'H' top-left pixel is lit; the shadow sits one pixel down-right of the last row.
        assert_eq!(canvas.get(15, 12), Some(WHITE));
        assert_eq!(canvas.get(16, 19), Some((100, 0, 0)));
    }

    #[test]
    fn resize_clears_to_black() {
        let mut canvas = Canvas::new(2, 2);
        canvas.fill(WHITE);
        canvas.resize(3, 1);
        assert_eq!(canvas.size(), (3, 1));
        assert_eq!(canvas.get(2, 0), Some(BLACK));
    }
}
