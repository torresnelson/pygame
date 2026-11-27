//! Small text saves (the tetris high score table): localStorage in the
//! browser, a file in the user's data folder on desktop.

/// The saved text for `key`, if any.
pub fn load_text(key: &str) -> Option<String> {
    platform::load_text(key)
}

/// Save `value` under `key`; failures are reported, not fatal.
pub fn save_text(key: &str, value: &str) -> Result<(), String> {
    platform::save_text(key, value)
}

#[cfg(not(target_arch = "wasm32"))]
mod platform {
    use std::path::{Path, PathBuf};

    /// `$XDG_DATA_HOME`, `~/.local/share` or `%APPDATA%`, plus `pygame-sandbox`.
    pub fn data_dir() -> PathBuf {
        let base = std::env::var_os("XDG_DATA_HOME")
            .map(PathBuf::from)
            .or_else(|| {
                std::env::var_os("HOME").map(|home| PathBuf::from(home).join(".local/share"))
            })
            .or_else(|| std::env::var_os("APPDATA").map(PathBuf::from))
            .unwrap_or_else(|| PathBuf::from("."));
        base.join("pygame-sandbox")
    }

    pub fn load_text_in(dir: &Path, key: &str) -> Option<String> {
        std::fs::read_to_string(dir.join(key)).ok()
    }

    pub fn save_text_in(dir: &Path, key: &str, value: &str) -> Result<(), String> {
        std::fs::create_dir_all(dir).map_err(|error| error.to_string())?;
        std::fs::write(dir.join(key), value).map_err(|error| error.to_string())
    }

    pub fn load_text(key: &str) -> Option<String> {
        load_text_in(&data_dir(), key)
    }

    pub fn save_text(key: &str, value: &str) -> Result<(), String> {
        save_text_in(&data_dir(), key, value)
    }

    #[cfg(test)]
    mod tests {
        use super::*;

        #[test]
        fn save_then_load_roundtrip_creates_the_folder() {
            let dir = std::env::temp_dir()
                .join(format!("sandbox-ui-storage-{}", std::process::id()))
                .join("nested");
            let _ = std::fs::remove_dir_all(&dir);
            assert_eq!(load_text_in(&dir, "tetris.highscores"), None);
            save_text_in(&dir, "tetris.highscores", "[]\n").unwrap();
            assert_eq!(
                load_text_in(&dir, "tetris.highscores").as_deref(),
                Some("[]\n")
            );
        }

        #[test]
        fn data_dir_is_named_after_the_project() {
            assert!(data_dir().ends_with("pygame-sandbox"));
        }
    }
}

#[cfg(target_arch = "wasm32")]
mod platform {
    fn storage() -> Option<web_sys::Storage> {
        web_sys::window()?.local_storage().ok().flatten()
    }

    pub fn load_text(key: &str) -> Option<String> {
        storage()?.get_item(key).ok().flatten()
    }

    pub fn save_text(key: &str, value: &str) -> Result<(), String> {
        let storage = storage().ok_or("localStorage is unavailable")?;
        storage
            .set_item(key, value)
            .map_err(|error| format!("{error:?}"))
    }
}
