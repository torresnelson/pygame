//! Material definitions (port of `src/sand_simulator/materials.py`).

pub type Color = (u8, u8, u8);

#[repr(u8)]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Material {
    Empty = 0,
    Stone = 1,
    Sand = 2,
    Water = 3,
}

impl Material {
    pub const ALL: [Material; 4] = [
        Material::Empty,
        Material::Stone,
        Material::Sand,
        Material::Water,
    ];

    pub fn from_index(index: u8) -> Self {
        Self::ALL[index as usize]
    }

    pub fn props(self) -> &'static Props {
        &PROPS[self as usize]
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum State {
    /// Empty space.
    Gas,
    /// Never moves.
    Solid,
    /// Falls, piles up, slides diagonally.
    Powder,
    /// Falls, then flows sideways to level out.
    Liquid,
}

#[derive(Debug, PartialEq)]
pub struct Props {
    pub state: State,
    pub density: f32,
    pub color: Color,
    /// Chance per tick that a resting grain refuses to slide (powders).
    pub friction: f32,
    /// Max cells a liquid flows sideways per tick.
    pub dispersion: i32,
    /// Max fall speed (cells per tick) when sinking through a liquid.
    pub drag_speed: f32,
}

const fn props(state: State, density: f32, color: Color) -> Props {
    Props {
        state,
        density,
        color,
        friction: 0.0,
        dispersion: 0,
        drag_speed: 1.0,
    }
}

/// Indexed by `Material as usize`.
pub const PROPS: [Props; 4] = [
    props(State::Gas, 0.0, (0, 0, 0)),
    props(State::Solid, 100.0, (110, 110, 120)),
    Props {
        friction: 0.6,
        ..props(State::Powder, 1.6, (220, 190, 110))
    },
    Props {
        dispersion: 8,
        ..props(State::Liquid, 1.0, (40, 110, 220))
    },
];

pub const SHADES: usize = 8;

/// Darken/lighten `color` by `level` in [0, SHADES) to give grains texture.
pub fn shade(color: Color, level: usize) -> Color {
    let factor = 0.85 + 0.3 * level as f32 / (SHADES - 1) as f32;
    let channel = |c: u8| (c as f32 * factor).min(255.0) as u8;
    (channel(color.0), channel(color.1), channel(color.2))
}

/// Every shade of every material, indexed by `Material as usize`.
pub fn palette() -> [[Color; SHADES]; 4] {
    PROPS
        .each_ref()
        .map(|p| std::array::from_fn(|level| shade(p.color, level)))
}

pub fn is_mobile(material: Material) -> bool {
    matches!(material.props().state, State::Powder | State::Liquid)
}

/// A particle can move into empty space or sink through a lighter liquid.
pub fn can_displace(mover: Material, target: Material) -> bool {
    let target = target.props();
    match target.state {
        State::Gas => true,
        State::Liquid => mover.props().density > target.density,
        _ => false,
    }
}
