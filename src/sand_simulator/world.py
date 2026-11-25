'''Falling-sand physics engine (no pygame).

The world is a fixed grid of particles stored in flat, row-major lists for
speed. Each tick rows are scanned bottom-up, alternating the horizontal scan
direction per row and per tick so no side is favoured. A per-cell tick stamp
guarantees a particle moves at most once per tick.

Physics:
- Gravity: mobile particles accelerate by `GRAVITY` cells/tick^2 up to
  `MAX_SPEED`, moving several cells per tick when fast.
- Density: a particle may move into empty space or sink through a lighter
  liquid (swapping places); sinking is capped at the liquid's drag speed.
- Powders (sand) slide diagonally when blocked, never squeezing between two
  diagonal neighbours. Resting grains resist sliding with `friction`, and
  fast impacts scatter grains further down the slope.
- Liquids (water) fall like powders, then flow sideways up to `dispersion`
  cells per tick, keeping a flow direction until they hit something.
- Solids (stone) never move. Outside the grid counts as solid.
'''

import random
from collections.abc import Iterator

from materials import PROPS, SHADES, Material, State

GRAVITY = 0.5
MAX_SPEED = 6.0
SCATTER_SPEED = 3.0

_EMPTY = int(Material.EMPTY)
_STATE = [PROPS[m].state for m in Material]
_FRICTION = [PROPS[m].friction for m in Material]
_DISPERSION = [PROPS[m].dispersion for m in Material]
_DRAG = [PROPS[m].drag_speed for m in Material]
# _DISPLACE[mover][target]: mover may swap into target's cell.
_DISPLACE = [
    [
        PROPS[t].state == State.GAS
        or (PROPS[t].state == State.LIQUID and PROPS[m].density > PROPS[t].density)
        for t in Material
    ]
    for m in Material
]


class World:
    def __init__(self, width: int, height: int, rng: random.Random | None = None) -> None:
        self.width = width
        self.height = height
        self.rng = rng or random.Random()
        self.tick = 0
        size = width * height
        self.material: list[int] = [_EMPTY] * size
        self.velocity: list[float] = [0.0] * size
        self.shade: list[int] = [0] * size
        self.flow: list[int] = [1] * size
        self.stamp: list[int] = [0] * size

    # -- queries -----------------------------------------------------------

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x: int, y: int) -> Material:
        if not self.in_bounds(x, y):
            return Material.STONE
        return Material(self.material[y * self.width + x])

    def count(self, material: Material) -> int:
        return self.material.count(int(material))

    def particles(self) -> Iterator[tuple[int, int, Material]]:
        for i, m in enumerate(self.material):
            if m != _EMPTY:
                yield i % self.width, i // self.width, Material(m)

    def column_height(self, x: int, material: Material) -> int:
        '''Number of `material` cells in column `x`.'''
        m = int(material)
        return sum(1 for y in range(self.height) if self.material[y * self.width + x] == m)

    # -- editing -----------------------------------------------------------

    def set(self, x: int, y: int, material: Material) -> None:
        if not self.in_bounds(x, y):
            return
        i = y * self.width + x
        self.material[i] = int(material)
        self.velocity[i] = 0.0
        self.shade[i] = self.rng.randrange(SHADES)
        self.flow[i] = self.rng.choice((-1, 1))

    def paint(
        self, cx: int, cy: int, radius: int, material: Material, fill: float = 1.0
    ) -> int:
        '''Paint a disc of `material`; returns how many cells changed.

        `Material.EMPTY` erases anything. Other materials only fill empty
        cells, each with probability `fill` so poured sand looks granular.
        '''
        changed = 0
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 > radius * radius or not self.in_bounds(x, y):
                    continue
                current = self.material[y * self.width + x]
                if material == Material.EMPTY:
                    if current != _EMPTY:
                        self.set(x, y, material)
                        changed += 1
                elif current == _EMPTY and self.rng.random() < fill:
                    self.set(x, y, material)
                    changed += 1
        return changed

    def clear(self) -> None:
        size = self.width * self.height
        self.material[:] = [_EMPTY] * size
        self.velocity[:] = [0.0] * size

    # -- simulation --------------------------------------------------------

    def step(self) -> int:
        '''Advance one tick; return how many particles moved.'''
        self.tick += 1
        tick, width, material, stamp = self.tick, self.width, self.material, self.stamp
        moved = 0
        for y in range(self.height - 1, -1, -1):
            row = y * width
            xs = range(width) if (tick + y) % 2 else range(width - 1, -1, -1)
            for x in xs:
                i = row + x
                m = material[i]
                if m == _EMPTY or stamp[i] == tick:
                    continue
                state = _STATE[m]
                if state == State.POWDER:
                    moved += self._update_powder(x, y, i, m)
                elif state == State.LIQUID:
                    moved += self._update_liquid(x, y, i, m)
        return moved

    def _target(self, x: int, y: int, mover: int) -> int:
        '''Index of (x, y) if `mover` can move there, else -1.'''
        if 0 <= x < self.width and 0 <= y < self.height:
            j = y * self.width + x
            if _DISPLACE[mover][self.material[j]]:
                return j
        return -1

    def _swap(self, i: int, j: int) -> None:
        mat, vel, sh, fl = self.material, self.velocity, self.shade, self.flow
        mat[i], mat[j] = mat[j], mat[i]
        vel[i], vel[j] = vel[j], vel[i]
        sh[i], sh[j] = sh[j], sh[i]
        fl[i], fl[j] = fl[j], fl[i]
        self.stamp[i] = self.stamp[j] = self.tick

    def _fall(self, x: int, y: int, i: int, m: int) -> tuple[int, int, float]:
        '''Accelerate and fall; return (new y, new index, impact speed or 0 if airborne).'''
        speed = min(self.velocity[i] + GRAVITY, MAX_SPEED)
        budget = max(1, int(speed))
        fallen = 0
        while fallen < budget:
            j = self._target(x, y + 1, m)
            if j < 0:
                break
            if self.material[j] != _EMPTY:
                # Sinking through a liquid: drag caps the speed.
                drag = _DRAG[self.material[j]]
                speed = min(speed, drag)
                budget = min(budget, max(1, int(drag)))
            self._swap(i, j)
            i, y = j, y + 1
            fallen += 1
        if fallen == budget:
            self.velocity[i] = speed
            return y, i, 0.0
        self.velocity[i] = 0.0
        return y, i, max(speed, 1.0) if fallen else 0.0

    def _slide(self, x: int, y: int, i: int, m: int, dx: int) -> int:
        '''Move one cell diagonally down towards `dx` if not squeezing; new index or -1.'''
        j = self._target(x + dx, y + 1, m)
        if j < 0 or self._target(x + dx, y, m) < 0:
            return -1
        self._swap(i, j)
        return j

    def _update_powder(self, x: int, y: int, i: int, m: int) -> int:
        was_resting = self.velocity[i] == 0.0
        new_y, i, impact = self._fall(x, y, i, m)
        if new_y != y and impact == 0.0:
            return 1  # still in free fall
        if new_y == y and was_resting and self.rng.random() < _FRICTION[m]:
            return 0  # static friction holds the grain this tick

        fell = new_y != y
        y = new_y
        dirs = [-1, 1]
        self.rng.shuffle(dirs)
        for dx in dirs:
            j = self._slide(x, y, i, m, dx)
            if j < 0:
                continue
            # Fast impacts keep tumbling down the slope.
            extra = int(impact / 2) if impact >= SCATTER_SPEED else 0
            x, y, i = x + dx, y + 1, j
            for _ in range(extra):
                j = self._slide(x, y, i, m, dx)
                if j < 0:
                    break
                x, y, i = x + dx, y + 1, j
            return 1
        return int(fell)

    def _update_liquid(self, x: int, y: int, i: int, m: int) -> int:
        new_y, i, impact = self._fall(x, y, i, m)
        if new_y != y and impact == 0.0:
            return 1
        moved = new_y != y
        y = new_y

        dirs = [-1, 1]
        self.rng.shuffle(dirs)
        for dx in dirs:
            j = self._slide(x, y, i, m, dx)
            if j >= 0:
                return 1

        direction = self.flow[i]
        for step in range(_DISPERSION[m]):
            j = self._target(x + direction, y, m)
            if j < 0:
                if step == 0:
                    self.flow[i] = -direction
                break
            self._swap(i, j)
            i, x = j, x + direction
            moved = True
            if self._target(x, y + 1, m) >= 0:
                break  # found a drop: fall next tick
        return int(moved)
