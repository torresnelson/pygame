//! Top-N high score table stored as JSON (port of `src/tetris/highscores.py`).
//!
//! The JSON format matches the Python version exactly, so a table saved by
//! either one loads in the other (desktop file and browser localStorage).

use serde::{Deserialize, Serialize};
use std::cmp::Reverse;
use std::fs;
use std::path::Path;

pub const LIMIT: usize = 10;
pub const NAME_LENGTH: usize = 10;
pub const DEFAULT_NAME: &str = "PLAYER";
/// localStorage key the browser builds use (same as the Python build).
pub const STORAGE_KEY: &str = "tetris.highscores";

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Entry {
    pub name: String,
    pub score: u32,
    #[serde(default)]
    pub lines: u32,
    #[serde(default)]
    pub level: u32,
    /// ISO date (YYYY-MM-DD) or empty.
    #[serde(default)]
    pub day: String,
}

impl Entry {
    pub fn new(name: &str, score: u32) -> Self {
        Self {
            name: name.to_owned(),
            score,
            ..Self::default()
        }
    }
}

/// Keep printable characters, trim to `NAME_LENGTH`, fall back to a default.
pub fn clean_name(name: &str) -> String {
    let printable: String = name.chars().filter(|c| !c.is_control()).collect();
    let kept: String = printable.trim().chars().take(NAME_LENGTH).collect();
    if kept.is_empty() {
        DEFAULT_NAME.to_owned()
    } else {
        kept
    }
}

/// Highest score first; ties keep the earlier entry ahead.
pub fn ranked(entries: &[Entry], limit: usize) -> Vec<Entry> {
    let mut table = entries.to_vec();
    table.sort_by_key(|entry| Reverse(entry.score)); // stable: ties keep their order
    table.truncate(limit);
    table
}

pub fn qualifies(entries: &[Entry], score: u32, limit: usize) -> bool {
    if score == 0 {
        return false;
    }
    entries.len() < limit
        || ranked(entries, limit)
            .last()
            .is_none_or(|last| score > last.score)
}

/// Add `entry`; return the new table and its 0-based rank (`None` if it missed the cut).
pub fn insert(entries: &[Entry], entry: Entry, limit: usize) -> (Vec<Entry>, Option<usize>) {
    // Tag the new entry by position so equal entries don't confuse the rank.
    let mut tagged: Vec<(usize, Entry)> = entries.iter().cloned().enumerate().collect();
    let new_index = tagged.len();
    tagged.push((new_index, entry));
    tagged.sort_by_key(|(_, entry)| Reverse(entry.score));
    tagged.truncate(limit);
    let rank = tagged.iter().position(|&(index, _)| index == new_index);
    (tagged.into_iter().map(|(_, entry)| entry).collect(), rank)
}

pub fn best(entries: &[Entry]) -> u32 {
    entries.iter().map(|entry| entry.score).max().unwrap_or(0)
}

/// Parse a stored table; missing or malformed data gives an empty table.
pub fn from_json(text: Option<&str>) -> Vec<Entry> {
    text.filter(|text| !text.is_empty())
        .and_then(|text| serde_json::from_str::<Vec<Entry>>(text).ok())
        .map(|entries| ranked(&entries, LIMIT))
        .unwrap_or_default()
}

pub fn to_json(entries: &[Entry]) -> String {
    let mut text =
        serde_json::to_string_pretty(&ranked(entries, LIMIT)).expect("entries serialise");
    text.push('\n');
    text
}

/// Read the table; import the old single-number `scores.txt` once if present.
pub fn load(path: &Path, legacy: &Path) -> Vec<Entry> {
    if let Ok(text) = fs::read_to_string(path) {
        return from_json(Some(&text));
    }
    let Ok(text) = fs::read_to_string(legacy) else {
        return Vec::new();
    };
    let trimmed = text.trim();
    let score = if trimmed.is_empty() {
        Some(0)
    } else {
        trimmed.parse::<u32>().ok()
    };
    match score {
        Some(score) if score > 0 => vec![Entry::new("LEGACY", score)],
        _ => Vec::new(),
    }
}

pub fn save(entries: &[Entry], path: &Path) -> std::io::Result<()> {
    fs::write(path, to_json(entries))
}

/// A table entry dated `day` (ISO `YYYY-MM-DD`; the caller supplies today).
pub fn new_entry(name: &str, score: u32, lines: u32, level: u32, day: &str) -> Entry {
    Entry {
        name: clean_name(name),
        score,
        lines,
        level,
        day: day.to_owned(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn table(scores: &[u32]) -> Vec<Entry> {
        scores
            .iter()
            .enumerate()
            .map(|(i, &s)| Entry::new(&format!("P{i}"), s))
            .collect()
    }

    fn temp_dir(name: &str) -> std::path::PathBuf {
        let dir = std::env::temp_dir().join(format!("tetris-core-{name}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn clean_name_trims_limits_and_defaults() {
        assert_eq!(clean_name("  ana  "), "ana");
        assert_eq!(clean_name("averyveryverylongname"), "averyveryv");
        assert_eq!(clean_name(""), DEFAULT_NAME);
        assert_eq!(clean_name("\n\t"), DEFAULT_NAME);
    }

    #[test]
    fn ranked_sorts_desc_keeps_tie_order_and_limits() {
        let mut entries = vec![
            Entry::new("a", 10),
            Entry::new("b", 30),
            Entry::new("c", 10),
        ];
        entries.extend(table(&[1, 2, 3, 4, 5, 6, 7, 8]));
        let result = ranked(&entries, LIMIT);
        assert_eq!(result.len(), LIMIT);
        assert_eq!(result[0], Entry::new("b", 30));
        let position = |name: &str| result.iter().position(|e| e.name == name).unwrap();
        assert!(position("a") < position("c"));
    }

    #[test]
    fn qualifies_needs_a_score_that_makes_the_cut() {
        assert!(!qualifies(&[], 0, LIMIT));
        assert!(qualifies(&[], 40, LIMIT));
        let full = table(&(100..100 + LIMIT as u32).collect::<Vec<_>>());
        assert!(!qualifies(&full, 100, LIMIT));
        assert!(qualifies(&full, 101, LIMIT));
    }

    #[test]
    fn insert_returns_rank() {
        let (result, rank) = insert(&table(&[500, 300, 100]), Entry::new("me", 400), LIMIT);
        assert_eq!(rank, Some(1));
        let scores: Vec<u32> = result.iter().map(|e| e.score).collect();
        assert_eq!(scores, [500, 400, 300, 100]);

        let full = table(&(100..100 + LIMIT as u32).collect::<Vec<_>>());
        let (_, rank) = insert(&full, Entry::new("low", 50), LIMIT);
        assert_eq!(rank, None);
    }

    #[test]
    fn insert_ranks_an_equal_new_entry_after_the_old_one() {
        let table = [Entry::new("same", 100)];
        let (_, rank) = insert(&table, Entry::new("same", 100), LIMIT);
        assert_eq!(rank, Some(1));
    }

    #[test]
    fn best_is_the_top_score() {
        assert_eq!(best(&[]), 0);
        assert_eq!(best(&table(&[10, 90, 30])), 90);
    }

    #[test]
    fn save_and_load_roundtrip() {
        let dir = temp_dir("roundtrip");
        let path = dir.join("highscores.json");
        let entries = vec![
            new_entry("ana", 1200, 12, 1, "2026-11-26"),
            Entry::new("bob", 40),
        ];
        save(&entries, &path).unwrap();
        let loaded = load(&path, &dir.join("none.txt"));
        assert_eq!(loaded, ranked(&entries, LIMIT));
        assert_eq!(loaded[0].day, "2026-11-26");
    }

    #[test]
    fn load_missing_or_corrupt_is_empty() {
        let dir = temp_dir("corrupt");
        let none = dir.join("nope.txt");
        assert!(load(&dir.join("nope.json"), &none).is_empty());
        fs::write(dir.join("bad.json"), "{not json").unwrap();
        assert!(load(&dir.join("bad.json"), &none).is_empty());
        fs::write(dir.join("shape.json"), r#"[{"unexpected": 1}]"#).unwrap();
        assert!(load(&dir.join("shape.json"), &none).is_empty());
    }

    #[test]
    fn load_imports_legacy_scores_txt() {
        let dir = temp_dir("legacy");
        let legacy = dir.join("scores.txt");
        fs::write(&legacy, "340\n").unwrap();
        assert_eq!(
            load(&dir.join("highscores.json"), &legacy),
            vec![Entry::new("LEGACY", 340)]
        );
        fs::write(&legacy, "0\n").unwrap();
        assert!(load(&dir.join("highscores.json"), &legacy).is_empty());
    }

    #[test]
    fn json_roundtrip_and_bad_input() {
        let entries = vec![
            Entry::new("b", 40),
            Entry {
                name: "a".into(),
                score: 1200,
                lines: 12,
                level: 1,
                day: "2026-11-26".into(),
            },
        ];
        assert_eq!(from_json(Some(&to_json(&entries))), ranked(&entries, LIMIT));
        assert!(from_json(None).is_empty());
        assert!(from_json(Some("")).is_empty());
        assert!(from_json(Some("{not json")).is_empty());
        assert!(from_json(Some(r#"[{"unexpected": 1}]"#)).is_empty());
    }

    #[test]
    fn reads_tables_written_by_the_python_version() {
        // Exactly what Python's to_json writes (json.dumps, indent=2).
        let python = "[\n  {\n    \"name\": \"ANA\",\n    \"score\": 1200,\n    \"lines\": 12,\n    \
                      \"level\": 1,\n    \"day\": \"2026-11-26\"\n  },\n  {\n    \"name\": \"LEGACY\",\n    \
                      \"score\": 340\n  }\n]\n";
        let entries = from_json(Some(python));
        assert_eq!(entries[0].name, "ANA");
        assert_eq!(entries[1], Entry::new("LEGACY", 340));
        // And writes the same layout back.
        assert!(
            to_json(&entries).starts_with("[\n  {\n    \"name\": \"ANA\",\n    \"score\": 1200,")
        );
    }
}
