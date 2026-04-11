import math
import random
from core.constants import *
from core.models import MoveAction, AttackAction,Unit
from core.terrain import HARDCODED_MAP
from collections import deque
class GameState:
    def __init__(self, units=None, current_player=PLAYER_HUMAN, remaining_actions=2):
        self.grid              = HARDCODED_MAP        # shared, never mutated
        self.units             = units if units else []
        self.current_player    = current_player
        self.remaining_actions = remaining_actions

    # ── helpers ──────────────────────────────────────────────────────────────
    def get_unit_at(self, x, y):
        for u in self.units:
            if u.alive and u.x == x and u.y == y: return u
        return None

    def in_bounds(self, x, y):
        return 0 <= x < COLS and 0 <= y < ROWS

    def passable(self, x, y):
        if not self.in_bounds(x, y):           return False
        if self.grid[x][y] != TERRAIN_EMPTY:   return False
        return True

    def blocks_arrow(self, x, y):
        """Rocks block arrows. Rivers and empty tiles are transparent."""
        if not self.in_bounds(x, y): return True
        return self.grid[x][y] == TERRAIN_ROCK

    # ── BFS movement ─────────────────────────────────────────────────────────
    def reachable_tiles(self, unit):
        rng     = UNIT_STATS[unit.type]["move"]
        visited = {(unit.x, unit.y): 0}
        q       = deque([(unit.x, unit.y, 0)])
        result  = []
        while q:
            cx, cy, d = q.popleft()
            if d > 0: result.append((cx, cy))
            if d == rng: continue
            for ddx, ddy in ((-1,0),(1,0),(0,-1),(0,1)):
                nx, ny = cx+ddx, cy+ddy
                if (nx,ny) in visited:            continue
                if not self.passable(nx, ny):     continue
                if self.get_unit_at(nx, ny):      continue
                visited[(nx,ny)] = d+1
                q.append((nx, ny, d+1))
        return result

    # ── Warrior melee ─────────────────────────────────────────────────────────
    def warrior_attack_tiles(self, unit):
        tiles = []
        for ddx in (-1,0,1):
            for ddy in (-1,0,1):
                if ddx==0 and ddy==0: continue
                nx, ny = unit.x+ddx, unit.y+ddy
                if self.in_bounds(nx, ny): tiles.append((nx, ny))
        return tiles

    # ── Archer free-vector ray ────────────────────────────────────────────────
    def archer_ray(self, archer, x0, y0, tx, ty):
        """
        Cast a straight arrow from (x0,y0) toward (tx,ty).
        Direction is a continuous vector — not snapped to 8 dirs.
        Returns list of tiles the arrow visits, stopping:
          • EXCLUSIVE at rocks (blocked, rock tile NOT included)
          • INCLUSIVE at first unit hit (tile included, then stop)
          • Rivers are transparent (arrow passes through)
        """
        ddx = tx - x0
        ddy = ty - y0
        if ddx == 0 and ddy == 0: return []
        length = math.hypot(ddx, ddy)
        sx, sy = ddx / length, ddy / length

        tiles = []
        seen  = set()
        step  = 0.45     # sub-tile stepping avoids skipping thin columns
        t     = step
        max_t = (COLS + ROWS) * 2.5
        while t < max_t:
            cx = round(x0 + sx * t)
            cy = round(y0 + sy * t)
            t += step
            if not self.in_bounds(cx, cy): break
            if (cx, cy) in seen: continue
            seen.add((cx, cy))
            if cx == x0 and cy == y0: continue
            if self.blocks_arrow(cx, cy): break          # rock — stop exclusive
            tiles.append((cx, cy))
            hit = self.get_unit_at(cx, cy)
            if hit is not None and hit.owner != archer.owner: break                    # unit — stop inclusive
        return tiles

    # ── Legal actions ─────────────────────────────────────────────────────────
    def get_legal_actions(self):
        actions = []
        for u in self.units:
            if not u.alive or u.owner != self.current_player: continue
            for tx, ty in self.reachable_tiles(u):
                actions.append(MoveAction(u.id, tx, ty))
            if not UNIT_STATS[u.type]["can_attack"]: continue
            if u.type == TYPE_WARRIOR:
                for tx, ty in self.warrior_attack_tiles(u):
                    t = self.get_unit_at(tx, ty)
                    if t and t.owner != u.owner:
                        actions.append(AttackAction(u.id, tx, ty))
            elif u.type == TYPE_ARCHER:
                for e in self.units:
                    if not e.alive or e.owner == u.owner: continue
                    ray = self.archer_ray(u, u.x, u.y, e.x, e.y)
                    for rx, ry in ray:
                        hit = self.get_unit_at(rx, ry)
                        if hit and hit.owner != u.owner:
                            actions.append(AttackAction(u.id, rx, ry)); break
                        elif hit: break
        if not actions: actions.append(None)
        return actions

    # ── Apply → new state ─────────────────────────────────────────────────────
    def apply(self, action):
        ns = self._clone()
        if action is None:
            ns.remaining_actions = 0
        elif isinstance(action, MoveAction):
            u = ns._unit_by_id(action.unit_id)
            if u: u.x, u.y = action.tx, action.ty
            ns.remaining_actions -= 1
        elif isinstance(action, AttackAction):
            u = ns._unit_by_id(action.unit_id)
            if u:
                dmg = UNIT_STATS[u.type]["damage"]
                if u.type == TYPE_WARRIOR:
                    t = ns.get_unit_at(action.tx, action.ty)
                    if t and t.owner != u.owner:
                        t.hp = max(0, t.hp - dmg)
                elif u.type == TYPE_ARCHER:
                    ray = ns.archer_ray(u, u.x, u.y, action.tx, action.ty)
                    for rx, ry in ray:
                        hit = ns.get_unit_at(rx, ry)
                        if hit and hit.owner != u.owner:
                            hit.hp = max(0, hit.hp - dmg); break
                        elif hit: break
            ns.remaining_actions -= 1
        if ns.remaining_actions <= 0:
            ns.current_player    = 1 - ns.current_player
            ns.remaining_actions = 2
        ns.units = [u for u in ns.units if u.alive]
        return ns

    def is_terminal(self):
        h = any(u.alive and u.owner==PLAYER_HUMAN for u in self.units)
        a = any(u.alive and u.owner==PLAYER_AI    for u in self.units)
        return not h or not a

    def winner(self):
        h = any(u.alive and u.owner==PLAYER_HUMAN for u in self.units)
        a = any(u.alive and u.owner==PLAYER_AI    for u in self.units)
        if h and not a: return PLAYER_HUMAN
        if a and not h: return PLAYER_AI
        return None

    def _unit_by_id(self, uid):
        for u in self.units:
            if u.id == uid: return u
        return None

    def _clone(self):
        ns = GameState.__new__(GameState)
        ns.grid              = self.grid
        ns.units             = [u.clone() for u in self.units]
        ns.current_player    = self.current_player
        ns.remaining_actions = self.remaining_actions
        return ns


# ═══════════════════════════════════════════════════════════════
# INITIAL STATE
# ═══════════════════════════════════════════════════════════════
def make_initial_state():
    Unit._next_id = 1
    # Human spawns left side
    spawns_h = [(1,1),(1,5),(1,8),(2,3),(2,7)]
    types_h  = [TYPE_TANK, TYPE_WARRIOR, TYPE_WARRIOR, TYPE_TANK, TYPE_ARCHER]
    # AI spawns right side
    spawns_a = [(18,1),(18,5),(18,8),(17,3),(17,7)]
    types_a  = [TYPE_TANK, TYPE_WARRIOR, TYPE_WARRIOR, TYPE_TANK, TYPE_ARCHER]

    units = []
    for utype, (x, y) in zip(types_h, spawns_h):
        units.append(Unit(PLAYER_HUMAN, utype, x, y))
    for utype, (x, y) in zip(types_a, spawns_a):
        units.append(Unit(PLAYER_AI, utype, x, y))
    return GameState(units)


# ═══════════════════════════════════════════════════════════════
# AI — EVALUATION
# ═══════════════════════════════════════════════════════════════
def evaluate(state, fp):
    if state.is_terminal():
        w = state.winner()
        return 10000 if w==fp else (-10000 if w is not None else 0)
    opp    = 1 - fp
    my_hp  = sum(u.hp for u in state.units if u.owner==fp)
    op_hp  = sum(u.hp for u in state.units if u.owner==opp)
    my_n   = sum(1    for u in state.units if u.owner==fp)
    op_n   = sum(1    for u in state.units if u.owner==opp)
    score  = (my_hp - op_hp)*2 + (my_n - op_n)*10
    my_us  = [u for u in state.units if u.owner==fp]
    op_us  = [u for u in state.units if u.owner==opp]
    if my_us and op_us:
        score -= sum(min(abs(m.x-e.x)+abs(m.y-e.y) for e in op_us) for m in my_us) * 0.08
    return score
