//! Wall-clock helpers that work natively and in the browser, where
//! `std::time::SystemTime` is unavailable.

/// Milliseconds since the Unix epoch.
pub fn unix_millis() -> u64 {
    #[cfg(target_arch = "wasm32")]
    {
        js_sys::Date::now() as u64
    }
    #[cfg(not(target_arch = "wasm32"))]
    {
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |elapsed| elapsed.as_millis() as u64)
    }
}

/// A seed for random numbers that differs between runs.
pub fn seed() -> u64 {
    // Spread the bits so seeds from close timestamps still differ a lot.
    unix_millis().wrapping_mul(0x9E37_79B9_7F4A_7C15)
}

/// Today's date (UTC) as `YYYY-MM-DD`, for the high score table.
pub fn today() -> String {
    iso_date(unix_millis() / 86_400_000)
}

/// `YYYY-MM-DD` for a day count since 1970-01-01 (civil-from-days algorithm).
pub fn iso_date(days_since_epoch: u64) -> String {
    let z = days_since_epoch as i64 + 719_468;
    let era = z.div_euclid(146_097);
    let day_of_era = z - era * 146_097;
    let year_of_era =
        (day_of_era - day_of_era / 1460 + day_of_era / 36_524 - day_of_era / 146_096) / 365;
    let day_of_year = day_of_era - (365 * year_of_era + year_of_era / 4 - year_of_era / 100);
    let month_index = (5 * day_of_year + 2) / 153;
    let day = day_of_year - (153 * month_index + 2) / 5 + 1;
    let month = if month_index < 10 {
        month_index + 3
    } else {
        month_index - 9
    };
    let year = year_of_era + era * 400 + i64::from(month <= 2);
    format!("{year:04}-{month:02}-{day:02}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn iso_date_converts_day_counts() {
        assert_eq!(iso_date(0), "1970-01-01");
        assert_eq!(iso_date(59), "1970-03-01");
        assert_eq!(iso_date(11_016), "2000-02-29");
        assert_eq!(iso_date(20_783), "2026-11-26");
    }

    #[test]
    fn today_looks_like_a_date() {
        let today = today();
        assert_eq!(today.len(), 10);
        assert!(today.starts_with("20"));
    }
}
