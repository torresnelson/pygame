//! Portrait or landscape, from the window shape; games pick their layout by it.

use bevy::prelude::*;
use bevy::window::PrimaryWindow;

#[derive(Resource, Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Orientation {
    #[default]
    Landscape,
    Portrait,
}

/// Portrait when the window is taller than wide.
pub fn orientation_for(width: f32, height: f32) -> Orientation {
    if height > width {
        Orientation::Portrait
    } else {
        Orientation::Landscape
    }
}

pub(crate) fn plugin(app: &mut App) {
    app.init_resource::<Orientation>()
        .add_systems(PreUpdate, update_orientation);
}

fn update_orientation(
    mut orientation: ResMut<Orientation>,
    window: Single<&Window, With<PrimaryWindow>>,
) {
    orientation.set_if_neq(orientation_for(window.width(), window.height()));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn taller_than_wide_is_portrait() {
        assert_eq!(orientation_for(390.0, 844.0), Orientation::Portrait);
        assert_eq!(orientation_for(844.0, 390.0), Orientation::Landscape);
        assert_eq!(orientation_for(500.0, 500.0), Orientation::Landscape);
    }
}
