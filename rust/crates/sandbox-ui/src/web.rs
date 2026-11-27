//! Browser page glue; no-ops on desktop.

/// The game canvas's size on the page in CSS pixels, the space mouse and
/// touch positions arrive in. `None` on desktop.
///
/// Bevy's window size on the web is in device pixels or logical pixels
/// depending on how the browser reports the pixel ratio, while pointer
/// positions are always CSS pixels, so pointers are mapped through this.
pub fn canvas_css_size() -> Option<(f32, f32)> {
    #[cfg(target_arch = "wasm32")]
    {
        let canvas = web_sys::window()?
            .document()?
            .query_selector(crate::CANVAS_SELECTOR)
            .ok()??;
        let (width, height) = (canvas.client_width(), canvas.client_height());
        if width > 0 && height > 0 {
            return Some((width as f32, height as f32));
        }
    }
    None
}

/// Remove the page's loading screen (`window.hide_loading()`, defined by the
/// web template) once the game draws its first frame.
pub fn hide_loading() {
    #[cfg(target_arch = "wasm32")]
    {
        use wasm_bindgen::JsCast;
        let Some(window) = web_sys::window() else {
            return;
        };
        if let Ok(hide) = js_sys::Reflect::get(&window, &"hide_loading".into())
            && let Some(hide) = hide.dyn_ref::<js_sys::Function>()
        {
            let _ = hide.call0(&window);
        }
    }
}
