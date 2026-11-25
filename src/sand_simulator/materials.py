'''Material definitions for the falling-sand engine.'''

from dataclasses import dataclass
from enum import IntEnum

Color = tuple[int, int, int]


class Material(IntEnum):
    EMPTY = 0
    STONE = 1
    SAND = 2
    WATER = 3


class State(IntEnum):
    GAS = 0  # empty space
    SOLID = 1  # never moves
    POWDER = 2  # falls, piles up, slides diagonally
    LIQUID = 3  # falls, then flows sideways to level out


@dataclass(frozen=True)
class Props:
    state: State
    density: float
    color: Color
    # Chance per tick that a resting grain refuses to slide (powders).
    friction: float = 0.0
    # Max cells a liquid flows sideways per tick.
    dispersion: int = 0
    # Max fall speed (cells per tick) when sinking through a liquid.
    drag_speed: float = 1.0


PROPS: dict[Material, Props] = {
    Material.EMPTY: Props(State.GAS, 0.0, (0, 0, 0)),
    Material.STONE: Props(State.SOLID, 100.0, (110, 110, 120)),
    Material.SAND: Props(State.POWDER, 1.6, (220, 190, 110), friction=0.6),
    Material.WATER: Props(State.LIQUID, 1.0, (40, 110, 220), dispersion=8),
}

SHADES = 8


def shade(color: Color, level: int) -> Color:
    '''Darken/lighten `color` by `level` in [0, SHADES) to give grains texture.'''
    factor = 0.85 + 0.3 * level / (SHADES - 1)
    r, g, b = (min(255, int(channel * factor)) for channel in color)
    return r, g, b


def palette() -> dict[Material, list[Color]]:
    return {m: [shade(p.color, s) for s in range(SHADES)] for m, p in PROPS.items()}


def is_mobile(material: Material) -> bool:
    return PROPS[material].state in (State.POWDER, State.LIQUID)


def can_displace(mover: Material, target: Material) -> bool:
    '''A particle can move into empty space or sink through a lighter liquid.'''
    target_props = PROPS[target]
    if target_props.state == State.GAS:
        return True
    return target_props.state == State.LIQUID and PROPS[mover].density > target_props.density
