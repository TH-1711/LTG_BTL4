"""
GRID WARS — Turn-based grid strategy game
Python + tkinter (stdlib only — no extra dependencies)

HOW TO RUN:
    python3 grid_wars.py          (needs python3-tk)
    sudo apt install python3-tk   (Ubuntu/Debian)

CONTROLS:
  • Click your unit   → select (Move / Attack buttons appear below)
  • MOVE mode         → green tiles shown; click to move
  • ATTACK mode:
      Warrior  → click any adjacent red tile that has an enemy
      Archer   → move mouse to aim (free-vector arrow preview), click to fire
                 Arrow travels tile-by-tile; blocked by rocks & units
  • ESC             → pause menu

═══════════════════════════════════════════════════════
ASSET GUIDE — where to drop real graphics
═══════════════════════════════════════════════════════
Search "# ASSET:" in the code to find every placeholder.

Tile PNGs (52×52, place in assets/ folder):
  assets/tile_empty.png   — grass / ground
  assets/tile_rock.png    — mountain / boulder
  assets/tile_river.png   — water tile
  assets/tile_bridge.png  — crossing tile (col 6&13, rows 4-5)

Unit sprites (40×40 with alpha, named by type & owner):
  assets/tank_p1.png      assets/tank_p2.png
  assets/warrior_p1.png   assets/warrior_p2.png
  assets/archer_p1.png    assets/archer_p2.png

Projectile (small, will be drawn at arrow-head position):
  assets/arrow.png        — 16×6 or 8×8 arrow sprite

To wire them in, inside App.__init__ add:
    import os
    self.imgs = {}
    for name in ["tile_empty","tile_rock","tile_river","tile_bridge",
                 "tank_p1","tank_p2","warrior_p1","warrior_p2",
                 "archer_p1","archer_p2","arrow"]:
        path = f"assets/{name}.png"
        if os.path.exists(path):
            self.imgs[name] = tk.PhotoImage(file=path)

Then in _draw_terrain_tile() replace create_rectangle with:
    key = {0:"tile_empty",1:"tile_rock",2:"tile_river"}[t]
    c.create_image(x1, y1, anchor="nw", image=self.imgs.get(key))

And in _draw_unit() replace create_oval+create_text with:
    key = f"{u.type.lower()}_p{u.owner+1}"
    c.create_image(cx, cy, image=self.imgs.get(key))
"""

import tkinter as tk
import math, random
from collections import deque
import os
from PIL import Image, ImageTk

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════
COLS, ROWS = 20, 10
TILE       = 52           # px per cell
PANEL_W    = 234          # right info panel width
WIN_W      = COLS * TILE + PANEL_W
WIN_H      = ROWS * TILE + 72   # +72 for bottom action bar

TERRAIN_EMPTY = 0
TERRAIN_ROCK  = 1
TERRAIN_RIVER = 2

PLAYER_HUMAN = 0
PLAYER_AI    = 1

TYPE_TANK    = "TANK"
TYPE_WARRIOR = "WARRIOR"
TYPE_ARCHER  = "ARCHER"

UNIT_STATS = {
    TYPE_TANK:    dict(hp=10, move=3, can_attack=False, damage=0, sym="⬡", label="Tank"),
    TYPE_WARRIOR: dict(hp=5,  move=5, can_attack=True,  damage=2, sym="⚔", label="Warrior"),
    TYPE_ARCHER:  dict(hp=3,  move=2, can_attack=True,  damage=1, sym="◈", label="Archer"),
}

# Colours
C_BG      = "#0b0f14"
C_TILE    = "#111820"
C_GRID    = "#1c2838"
C_ROCK    = "#22303d"
C_ROCK_S  = "#3a5060"
C_RIVER   = "#0c2a40"
C_RIVER_S = "#1a5070"
C_BRIDGE  = "#3d2e12"
C_BRIDGE_S= "#8a6930"
C_MOVE_F  = "#0e2a10"
C_MOVE_B  = "#2aaa44"
C_ATK_F   = "#2a0808"
C_ATK_B   = "#dd2244"
C_ARW_F   = "#2a2000"
C_ARW_B   = "#ffcc00"
C_SEL     = "#ffd700"
C_P1      = "#00e5ff"
C_P2      = "#ff5060"
C_HP_BG   = "#111"
C_HP_OK   = "#33ff44"
C_HP_MID  = "#ffdd00"
C_HP_LOW  = "#ff3344"
C_PANEL   = "#0c1018"
C_ACC     = "#00e5ff"
C_TEXT    = "#bdd0e0"
C_DIM     = "#3a5565"
C_LOG_NEW = "#c8e8c8"
C_LOG_AI  = "#ffaaaa"

AI_SHOW_MS  = 650   # ms AI action overlay is shown
ARROW_STEPS = 8     # animation steps for arrow flight

# ═══════════════════════════════════════════════════════════════
# HARD-CODED MAP  (permanent, never randomised)
# ═══════════════════════════════════════════════════════════════
#
# Two SHORT rivers at columns 6 and 13.
# Each river occupies rows 0-3 and 6-9, leaving rows 4-5 EMPTY
# (marked as "bridge/ford" visually) so both players can cross
# and meet in the middle.
#
# Rocks are hand-placed to create tactical cover without
# blocking the crossing corridors.
#
# Map overview  (. empty  # rock  ~ river  = bridge/ford)
#  col:  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19
# row 0: .  .  #  .  .  .  ~  .  .  #  .  .  .  ~  .  .  #  .  .  .
# row 1: .  .  .  .  #  .  ~  .  .  .  .  #  .  ~  .  .  .  .  .  .
# row 2: .  .  .  .  .  .  ~  #  .  .  .  .  .  ~  .  .  .  .  .  .
# row 3: .  .  .  #  .  .  ~  .  .  .  #  .  .  ~  .  .  .  #  .  .
# row 4: .  .  .  .  .  .  =  .  .  .  .  .  .  =  .  .  .  .  .  .  ← crossing
# row 5: .  .  .  .  .  .  =  .  .  .  .  .  .  =  .  .  .  .  .  .  ← crossing
# row 6: .  .  .  .  .  .  ~  .  .  .  #  .  .  ~  .  .  .  .  .  .
# row 7: .  .  .  #  .  .  ~  .  .  .  .  .  #  ~  .  .  .  #  .  .
# row 8: .  .  .  .  .  .  ~  .  #  .  .  .  .  ~  .  .  .  .  .  .
# row 9: .  .  #  .  .  .  ~  .  .  #  .  .  .  ~  .  .  #  .  .  .

def _build_map():
    """
    Load map from file if available, otherwise use default

    To use custom maps:
    1. Create a text file in maps/ folder
    2. Set MAP_FILE below to your map filename
    3. Use map_loader.py format (see MAP_EDITOR_GUIDE.md)
    """
    # SET THIS to load custom maps (or None for default)
    MAP_FILE = "maps/battlefield_01.txt"  # or None to use default

    if MAP_FILE and os.path.exists(MAP_FILE):
        try:
            from map_loader import load_map_from_text
            grid, bridges = load_map_from_text(MAP_FILE)
            print(f"✓ Loaded custom map: {MAP_FILE}")
            return grid, bridges
        except Exception as e:
            print(f"✗ Failed to load map '{MAP_FILE}': {e}")
            print("  Using default map instead...")

    # Default fallback map
    E, R, W = TERRAIN_EMPTY, TERRAIN_ROCK, TERRAIN_RIVER
    grid = [[E]*ROWS for _ in range(COLS)]

    # Horizontal river across middle (rows 4-5) with two bridge crossings
    for col in range(COLS):
        if col not in (6, 13):  # Leave gaps for bridges
            grid[col][4] = W
            grid[col][5] = W

    # MINIMAL rock placement
    rock_positions = [(5, 2), (9, 1), (14, 2), (5, 7), (9, 8), (14, 7)]

    for cx, cy in rock_positions:
        if cx <= 2 or cx >= 17:
            continue
        if 0 <= cx < COLS and 0 <= cy < ROWS:
            grid[cx][cy] = R

    bridges = {(6,4),(6,5),(13,4),(13,5)}
    return grid, bridges

HARDCODED_MAP, BRIDGE_TILES = _build_map()   # Load map once at import


# ═══════════════════════════════════════════════════════════════
# DATA — Unit, Actions
# ═══════════════════════════════════════════════════════════════
class Unit:
    _next_id = 1

    def __init__(self, owner, utype, x, y, uid=None):
        self.id      = uid if uid is not None else Unit._alloc()
        self.owner   = owner
        self.type    = utype
        self.x       = x
        self.y       = y
        self.hp      = UNIT_STATS[utype]["hp"]
        self.max_hp  = self.hp

    @staticmethod
    def _alloc():
        uid = Unit._next_id; Unit._next_id += 1; return uid

    @property
    def alive(self): return self.hp > 0

    def clone(self):
        u = Unit.__new__(Unit); u.__dict__.update(self.__dict__); return u

    def center_px(self):
        return self.x * TILE + TILE // 2, self.y * TILE + TILE // 2

    def __repr__(self):
        return f"<{UNIT_STATS[self.type]['label']} P{self.owner} ({self.x},{self.y}) hp={self.hp}>"


class MoveAction:
    def __init__(self, unit_id, tx, ty):
        self.unit_id = unit_id
        self.tx, self.ty = tx, ty

class AttackAction:
    def __init__(self, unit_id, tx, ty):
        self.unit_id = unit_id
        self.tx, self.ty = tx, ty


# ═══════════════════════════════════════════════════════════════
# GAME STATE
# ═══════════════════════════════════════════════════════════════
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
    def archer_ray(self, x0, y0, tx, ty):
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
            if hit is not None: break                    # unit — stop inclusive
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
                    ray = self.archer_ray(u.x, u.y, e.x, e.y)
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
                    ray = ns.archer_ray(u.x, u.y, action.tx, action.ty)
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


# ═══════════════════════════════════════════════════════════════
# AI — MINIMAX (depth 2, alpha-beta)
# ═══════════════════════════════════════════════════════════════
def minimax(state, depth, alpha, beta, fp):
    if depth==0 or state.is_terminal():
        return evaluate(state, fp), None
    actions = state.get_legal_actions()
    random.shuffle(actions)
    best_a = actions[0]
    if state.current_player == fp:
        best = -math.inf
        for a in actions[:14]:
            val, _ = minimax(state.apply(a), depth-1, alpha, beta, fp)
            if val > best: best, best_a = val, a
            alpha = max(alpha, best)
            if beta <= alpha: break
        return best, best_a
    else:
        best = math.inf
        for a in actions[:14]:
            val, _ = minimax(state.apply(a), depth-1, alpha, beta, fp)
            if val < best: best, best_a = val, a
            beta = min(beta, best)
            if beta <= alpha: break
        return best, best_a

class MinimaxAI:
    def choose(self, state):
        _, a = minimax(state, 2, -math.inf, math.inf, state.current_player)
        return a


# ═══════════════════════════════════════════════════════════════
# AI — MCTS
# ═══════════════════════════════════════════════════════════════
class _MCTSNode:
    __slots__ = ("state","action","parent","children","wins","visits","untried")
    def __init__(self, state, action=None, parent=None):
        self.state    = state
        self.action   = action
        self.parent   = parent
        self.children = []
        self.wins     = 0.0
        self.visits   = 0
        acts          = state.get_legal_actions()
        self.untried  = [a for a in acts if a is not None] or [None]

    def uct(self):
        logn = math.log(self.visits+1)
        return max(self.children,
                   key=lambda c: c.wins/max(c.visits,1)+1.41*math.sqrt(logn/max(c.visits,1)))

    def expand(self):
        a = self.untried.pop()
        child = _MCTSNode(self.state.apply(a), a, self)
        self.children.append(child); return child

    def rollout(self, fp, steps=18):
        s = self.state._clone()
        for _ in range(steps):
            if s.is_terminal(): break
            s = s.apply(random.choice(s.get_legal_actions()))
        return evaluate(s, fp)

    def backprop(self, v):
        self.visits += 1; self.wins += v
        if self.parent: self.parent.backprop(v)

class MCTSAI:
    def __init__(self, iters=600): self.iters = iters
    def choose(self, state):
        root = _MCTSNode(state); fp = state.current_player
        for _ in range(self.iters):
            node = root
            while not node.untried and node.children: node = node.uct()
            if node.untried: node = node.expand()
            node.backprop(node.rollout(fp))
        if not root.children: return None
        return max(root.children, key=lambda c: c.visits).action


# ═══════════════════════════════════════════════════════════════
# GAME ENGINE
# ═══════════════════════════════════════════════════════════════
class GameEngine:
    def apply(self, state, action): return state.apply(action)


# ═══════════════════════════════════════════════════════════════
# APPLICATION
# ═══════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GRID WARS")
        self.resizable(False, False)
        self.configure(bg=C_BG)
        self.canvas = tk.Canvas(self, width=WIN_W, height=WIN_H,
                                bg=C_BG, highlightthickness=0)
        self.canvas.pack()

        self.engine  = GameEngine()
        self.ai      = MCTSAI(600)   # swap to MinimaxAI() if desired

        # Load sprites
        self.imgs = self._load_sprites()

        # Generate tile variation map (deterministic based on position)
        self.tile_variations = self._generate_tile_variations()

        # Idle animation state
        self.anim_frame = 0
        self.anim_tick = 0

        # Screen
        self.screen   = "menu"
        self.gs       = None
        self.saved_gs = None

        # Human interaction
        self.sel_unit  = None
        self.mode      = None         # "move" | "attack" | None
        self.hl_move   = []
        self.hl_attack = []
        self.arrow_ray = []           # archer preview tiles
        self.mouse_px  = (0, 0)

        # AI animation
        self.ai_queue  = []           # list of pending action dicts
        self.ai_anim   = None         # current displayed action dict
        self.ai_busy   = False

        # Projectile animation
        # {"ray":[(x,y)...], "step":int, "color":str, "on_done":callable|None}
        self.arrow_anim = None

        self.log = []

        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>",   self._on_mouse)
        self.bind("<Escape>", self._on_escape)

        self._draw_menu()
        self._tick()

    def _load_sprites(self):
        """Load all game sprites including tile variations and animations"""
        imgs = {}
        assets_dir = "assets/game_seamless"

        # Load unit sprites (single files) + animation frames
        unit_names = ["tank_p1", "tank_p2", "warrior_p1", "warrior_p2",
                      "archer_p1", "archer_p2"]

        for name in unit_names:
            # Load default sprite
            path = os.path.join(assets_dir, f"{name}.png")
            if os.path.exists(path):
                pil_img = Image.open(path)
                imgs[name] = ImageTk.PhotoImage(pil_img)

            # Load animation frames
            frames = []
            for f in range(10):
                fpath = os.path.join(assets_dir, f"{name}_f{f}.png")
                if os.path.exists(fpath):
                    frames.append(ImageTk.PhotoImage(Image.open(fpath)))
            if frames:
                imgs[f"{name}_anim"] = frames

        # Load arrow
        arrow_path = os.path.join(assets_dir, "arrow.png")
        if os.path.exists(arrow_path):
            imgs["arrow"] = ImageTk.PhotoImage(Image.open(arrow_path))

        # Load tile variations
        tile_types = [
            "tile_empty", "tile_rock", "tile_river", "tile_bridge",
        ]

        for terrain_type in tile_types:
            variations = []
            for i in range(10):
                path = os.path.join(assets_dir, f"{terrain_type}_{i}.png")
                if os.path.exists(path):
                    variations.append(ImageTk.PhotoImage(Image.open(path)))

            if variations:
                imgs[terrain_type] = variations

        return imgs

    def _generate_tile_variations(self):
        """Generate tile variations with ZONES (not random per-tile)"""
        import random
        variation_map = {}

        # Create larger zones instead of per-tile randomness
        # Divide map into 4x2 zones (5x5 tiles each)
        zone_width = 5
        zone_height = 5

        for cx in range(COLS):
            for cy in range(ROWS):
                # Determine which zone this tile belongs to
                zone_x = cx // zone_width
                zone_y = cy // zone_height

                # Use zone-based seed (tiles in same zone get same variation)
                zone_seed = zone_x * 100 + zone_y
                rng = random.Random(zone_seed)

                # Pick variation for this ZONE (not per tile)
                variation_map[(cx, cy)] = {
                    "empty": rng.randint(0, 3),    # 0-3 for 4 variations
                    "rock": rng.randint(0, 5),     # 0-5 for 6 variations
                    "river": rng.randint(0, 3),    # 0-3 for 4 variations
                    "bridge": rng.randint(0, 3),   # 0-3 for 4 variations
                }

        return variation_map

    # ─────────────────────────────────────────────────────────────────────────
    # MAIN LOOP
    # ─────────────────────────────────────────────────────────────────────────
    def _tick(self):
        if self.screen == "game":
            # Advance idle animation (~5 FPS for animation, game runs at 25 FPS)
            self.anim_tick += 1
            if self.anim_tick >= 5:  # Every 5 ticks = ~200ms per frame
                self.anim_tick = 0
                self.anim_frame = (self.anim_frame + 1) % 4

            self._render_game()
            if (self.gs and
                    self.gs.current_player == PLAYER_AI and
                    not self.ai_busy and
                    not self.gs.is_terminal() and
                    not self.ai_anim and
                    not self.ai_queue and
                    not self.arrow_anim):
                self.ai_busy = True
                self.after(80, self._ai_compute)
        self.after(40, self._tick)

    # ─────────────────────────────────────────────────────────────────────────
    # SCREENS
    # ─────────────────────────────────────────────────────────────────────────
    def _clear(self): self.canvas.delete("all")

    def _draw_menu(self):
        self._clear(); self.screen = "menu"
        c, W, H = self.canvas, WIN_W, WIN_H
        for x in range(0, W, 44):
            c.create_line(x,0,x,H, fill="#0e1520", width=1)
        for y in range(0, H, 44):
            c.create_line(0,y,W,y, fill="#0e1520", width=1)
        c.create_text(W//2, 96,  text="GRID WARS",
                      font=("Courier",58,"bold"), fill=C_ACC, anchor="center")
        c.create_text(W//2, 150, text="TURN-BASED STRATEGY",
                      font=("Courier",13), fill=C_DIM, anchor="center")
        by = 235
        self._mbtn("▶  START GAME",   W//2, by,     "btn_start")
        if self.saved_gs:
            self._mbtn("⟳  CONTINUE", W//2, by+70,  "btn_cont")
        self._mbtn("✕  EXIT",         W//2, by+140, "btn_exit")
        c.tag_bind("btn_start","<Button-1>",lambda e: self._start())
        c.tag_bind("btn_cont", "<Button-1>",lambda e: self._continue())
        c.tag_bind("btn_exit", "<Button-1>",lambda e: self.quit())

        ly = H - 100
        c.create_text(W//2, ly,    text="⬡ Tank  ⚔ Warrior  ◈ Archer",
                      font=("Courier",12), fill=C_DIM)
        c.create_text(W//2, ly+22, text="≈ River (cross at ╫ ford)   ▲ Rock (blocks all)",
                      font=("Courier",11), fill=C_DIM)
        c.create_text(W//2, ly+44, text="Archer: move mouse to aim free-vector arrow, click to fire",
                      font=("Courier",10), fill="#283848")
        c.create_text(W//2, ly+66, text="AI actions are animated — watch what the enemy does",
                      font=("Courier",10), fill="#283848")
        c.create_text(W//2, ly+88, text="ESC = pause",
                      font=("Courier",9), fill="#1e2830")

    def _mbtn(self, text, cx, cy, tag):
        c = self.canvas
        c.create_rectangle(cx-138,cy-22,cx+138,cy+22,
                            fill="#0d1a26", outline=C_ACC, width=2, tags=tag)
        c.create_text(cx, cy, text=text, font=("Courier",15,"bold"),
                      fill=C_ACC, tags=tag)

    def _draw_pause(self):
        self._clear(); self.screen = "pause"
        c, W, H = self.canvas, WIN_W, WIN_H
        c.create_rectangle(0,0,W,H, fill="#040810")
        c.create_text(W//2, 118, text="⏸  PAUSED",
                      font=("Courier",44,"bold"), fill=C_ACC)
        by = 240
        self._mbtn("▶  RESUME",    W//2, by,     "btn_res")
        self._mbtn("↺  RESTART",   W//2, by+70,  "btn_rst")
        self._mbtn("⌂  MAIN MENU", W//2, by+140, "btn_mm")
        c.tag_bind("btn_res","<Button-1>",lambda e: self._resume())
        c.tag_bind("btn_rst","<Button-1>",lambda e: self._start())
        c.tag_bind("btn_mm", "<Button-1>",lambda e: self._draw_menu())

    def _draw_gameover(self):
        self._clear(); self.screen = "gameover"
        c, W, H = self.canvas, WIN_W, WIN_H
        w     = self.gs.winner()
        label = "YOU WIN!" if w==PLAYER_HUMAN else ("AI WINS!" if w==PLAYER_AI else "DRAW")
        col   = C_P1 if w==PLAYER_HUMAN else C_P2
        c.create_rectangle(0,0,W,H, fill="#040810")
        c.create_text(W//2, 128, text=label, font=("Courier",54,"bold"), fill=col)
        by = 275
        self._mbtn("↺  PLAY AGAIN", W//2, by,    "btn_again")
        self._mbtn("⌂  MAIN MENU",  W//2, by+70, "btn_mm2")
        c.tag_bind("btn_again","<Button-1>",lambda e: self._start())
        c.tag_bind("btn_mm2",  "<Button-1>",lambda e: self._draw_menu())

    # ─────────────────────────────────────────────────────────────────────────
    # GAME CONTROL
    # ─────────────────────────────────────────────────────────────────────────
    def _start(self):
        self.gs = make_initial_state()
        self.saved_gs = None
        self.sel_unit = self.mode = None
        self.hl_move = self.hl_attack = self.arrow_ray = []
        self.ai_queue = []; self.ai_anim = None
        self.arrow_anim = None; self.ai_busy = False
        self.log = ["Your turn — click a unit to begin."]
        self.screen = "game"

    def _resume(self):
        if self.saved_gs: self.gs = self.saved_gs
        self.screen = "game"

    def _continue(self):
        if self.saved_gs: self.gs = self.saved_gs; self.screen = "game"

    def _on_escape(self, _):
        if self.screen == "game":
            self.saved_gs = self.gs._clone(); self._draw_pause()
        elif self.screen == "pause":
            self._resume()

    # ─────────────────────────────────────────────────────────────────────────
    # RENDER
    # ─────────────────────────────────────────────────────────────────────────
    def _render_game(self):
        c = self.canvas; c.delete("all"); gs = self.gs

        # 0. Draw map border (frame around playable area)
        grid_w = COLS * TILE
        grid_h = ROWS * TILE
        border_color = "#4A3020"  # Dark brown border
        border_width = 4

        # Outer border (thick frame)
        c.create_rectangle(
            -border_width, -border_width,
            grid_w + border_width, grid_h + border_width,
            outline=border_color, width=border_width * 2
        )

        # Inner shadow for depth
        c.create_rectangle(
            0, 0, grid_w, grid_h,
            outline="#2A2010", width=2
        )

        # 1. Terrain
        for cx in range(COLS):
            for cy in range(ROWS):
                self._draw_tile(c, cx, cy, gs)

        # 2. Move highlights
        for hx, hy in self.hl_move:
            self._hl(c, hx, hy, C_MOVE_F, C_MOVE_B)

        # 3. Warrior attack highlights
        for hx, hy in self.hl_attack:
            self._hl(c, hx, hy, C_ATK_F, C_ATK_B)

        # 4. Archer ray preview + arrow line
        if (self.sel_unit and self.sel_unit.type == TYPE_ARCHER and self.arrow_ray):
            for rx, ry in self.arrow_ray:
                self._hl(c, rx, ry, C_ARW_F, C_ARW_B)
            u = self.gs._unit_by_id(self.sel_unit.id)
            if u:
                ax, ay = u.center_px()
                lx, ly = self.arrow_ray[-1]
                ex, ey = lx*TILE+TILE//2, ly*TILE+TILE//2
                c.create_line(ax, ay, ex, ey,
                              fill="#ffcc00", width=2, dash=(6,3),
                              arrow=tk.LAST, arrowshape=(12,14,5))

        # 5. AI anim overlay (drawn BEFORE units so rings appear under)
        if self.ai_anim:
            self._render_ai_overlay(c)

        # 6. Projectile arrow anim
        if self.arrow_anim:
            self._render_arrow_dot(c)

        # 7. Units
        for u in gs.units:
            if u.alive: self._draw_unit(c, u, gs)

        # 8. Action bar
        self._draw_action_bar(c, gs)

        # 9. Panel
        self._draw_panel(c, gs)

    # ── Terrain ───────────────────────────────────────────────────────────────
    def _draw_tile(self, c, cx, cy, gs):
        x1, y1 = cx*TILE, cy*TILE
        t = gs.grid[cx][cy]

        is_bridge = (cx, cy) in BRIDGE_TILES

        if is_bridge:
            sprite_key = "tile_bridge"
        elif t == TERRAIN_ROCK:
            sprite_key = "tile_rock"
        elif t == TERRAIN_RIVER:
            sprite_key = "tile_river"
        else:
            sprite_key = "tile_empty"

        # Get sprite (with variation if available)
        sprite = None
        if sprite_key in self.imgs:
            img_data = self.imgs[sprite_key]

            if isinstance(img_data, list) and len(img_data) > 0:
                variation_data = self.tile_variations.get((cx, cy), {})
                variation_key = sprite_key.replace("tile_", "")
                variation_index = variation_data.get(variation_key, 0)
                actual_index = variation_index % len(img_data)
                sprite = img_data[actual_index]
            else:
                sprite = img_data

        if sprite:
            c.create_image(x1, y1, anchor="nw", image=sprite)

    def _hl(self, c, hx, hy, fill, border):
        x1, y1 = hx*TILE+2, hy*TILE+2
        c.create_rectangle(x1,y1,x1+TILE-4,y1+TILE-4,
                           fill=fill, outline=border, width=2)

    # ── Unit ──────────────────────────────────────────────────────────────────
    def _draw_unit(self, c, u, gs):
        ux, uy = u.x*TILE, u.y*TILE
        cx, cy = ux+TILE//2, uy+TILE//2
        col    = C_P1 if u.owner==PLAYER_HUMAN else C_P2
        is_sel = self.sel_unit and self.sel_unit.id==u.id

        # Draw unit sprite with idle animation
        sprite_key = f"{u.type.lower()}_p{u.owner+1}"
        anim_key = f"{sprite_key}_anim"

        # Use animated frame if available
        sprite = None
        if anim_key in self.imgs:
            frames = self.imgs[anim_key]
            frame_idx = self.anim_frame % len(frames)
            sprite = frames[frame_idx]
        elif sprite_key in self.imgs:
            sprite = self.imgs[sprite_key]

        if sprite:
            c.create_image(cx, cy, image=sprite)
        else:
            # Fallback to original circle+text rendering
            pad = 6
            ow  = 3 if is_sel else 1
            oc  = C_SEL if is_sel else col
            c.create_oval(ux+pad,uy+pad,ux+TILE-pad,uy+TILE-pad,
                          fill="#080e18", outline=oc, width=ow)
            c.create_text(cx, cy-2, text=UNIT_STATS[u.type]["sym"],
                          font=("Courier",15,"bold"), fill=col)

        # Draw selection ring if selected
        if is_sel:
            pad = 6
            oc = C_SEL
            c.create_oval(ux+pad,uy+pad,ux+TILE-pad,uy+TILE-pad,
                          fill="", outline=oc, width=3)

        # HP bar (segmented - one segment per HP point)
        bw = TILE - 10
        bx, by2 = ux + 5, uy + TILE - 9
        bar_h = 5
        max_hp = u.max_hp
        seg_gap = 1  # Gap between segments
        seg_w = (bw - seg_gap * (max_hp - 1)) / max_hp  # Width of each segment

        # Background (full bar, dark)
        c.create_rectangle(bx, by2, bx + bw, by2 + bar_h, fill=C_HP_BG, outline="")

        # Draw each HP segment
        for i in range(max_hp):
            sx = bx + i * (seg_w + seg_gap)

            if i < u.hp:
                # Filled segment - color based on health ratio
                ratio = u.hp / max_hp
                hc = C_HP_OK if ratio > 0.6 else (C_HP_MID if ratio > 0.3 else C_HP_LOW)
                c.create_rectangle(sx, by2, sx + seg_w, by2 + bar_h, fill=hc, outline="")
            else:
                # Empty segment - dark
                c.create_rectangle(sx, by2, sx + seg_w, by2 + bar_h, fill="#1a1a1a", outline="")

    # ── AI action overlay ─────────────────────────────────────────────────────
    def _render_ai_overlay(self, c):
        anim   = self.ai_anim
        action = anim["action"]
        sb     = anim["state_before"]
        if action is None: return
        u = sb._unit_by_id(action.unit_id)
        if not u: return

        # Bright ring on the acting unit
        ux, uy = u.x*TILE, u.y*TILE
        c.create_oval(ux+2,uy+2,ux+TILE-2,uy+TILE-2,
                      fill="", outline="#ffffff", width=3)
        c.create_oval(ux+5,uy+5,ux+TILE-5,uy+TILE-5,
                      fill="", outline=C_P2, width=2)

        # Label badge above the unit
        label = anim["label"]
        bx = ux+TILE//2
        by2 = uy - 14
        # Background pill
        tw = max(len(label)*7, 60)
        c.create_rectangle(bx-tw//2-4, by2-10, bx+tw//2+4, by2+10,
                           fill="#200808", outline=C_P2, width=1)
        c.create_text(bx, by2, text=label, font=("Courier",9,"bold"),
                      fill="#ffffff", anchor="center")

        # Move: dashed ghost arrow to destination
        if isinstance(action, MoveAction):
            dx, dy = action.tx*TILE, action.ty*TILE
            c.create_oval(dx+8,dy+8,dx+TILE-8,dy+TILE-8,
                          fill="", outline=C_P2, width=2, dash=(4,3))
            c.create_line(ux+TILE//2, uy+TILE//2,
                          dx+TILE//2, dy+TILE//2,
                          fill=C_P2, width=2, dash=(5,4),
                          arrow=tk.LAST, arrowshape=(10,12,4))

        # Attack: red highlight on target tile
        if isinstance(action, AttackAction):
            tx2, ty2 = action.tx*TILE, action.ty*TILE
            c.create_rectangle(tx2+2,ty2+2,tx2+TILE-2,ty2+TILE-2,
                               fill="", outline="#ff2020", width=3)
            # Line from attacker to target
            c.create_line(ux+TILE//2, uy+TILE//2,
                          tx2+TILE//2, ty2+TILE//2,
                          fill="#ff4040", width=2, dash=(4,3),
                          arrow=tk.LAST, arrowshape=(8,10,3))

    # ── Arrow projectile dot ──────────────────────────────────────────────────
    def _render_arrow_dot(self, c):
        aa   = self.arrow_anim
        step = aa["step"]
        ray  = aa["ray"]
        col  = aa.get("color", "#ffcc00")
        if 0 <= step < len(ray):
            tx, ty = ray[step]
            px2, py2 = tx*TILE+TILE//2, ty*TILE+TILE//2

            # Draw arrow sprite if available
            if "arrow" in self.imgs:
                c.create_image(px2, py2, image=self.imgs["arrow"])
            else:
                # Fallback to circle
                r = 6
                c.create_oval(px2-r,py2-r,px2+r,py2+r, fill=col, outline="#fff", width=1)

    # ── Action bar ────────────────────────────────────────────────────────────
    def _draw_action_bar(self, c, gs):
        bar_y  = ROWS*TILE
        grid_w = COLS*TILE
        c.create_rectangle(0,bar_y,grid_w,WIN_H, fill="#07090f", outline="")

        # During AI turn or AI animation
        if gs.current_player==PLAYER_AI or self.ai_anim or self.arrow_anim:
            lbl = "AI IS ACTING..." if (self.ai_anim or self.arrow_anim) else "AI THINKING..."
            col = "#ff8844" if (self.ai_anim or self.arrow_anim) else C_P2
            c.create_text(12, bar_y+20, text=lbl, anchor="w",
                          font=("Courier",14,"bold"), fill=col)
            if self.ai_anim:
                lbl2 = self.ai_anim.get("label","")
                c.create_text(12, bar_y+44, text=lbl2, anchor="w",
                              font=("Courier",11), fill="#ffccaa")
            else:
                c.create_text(12, bar_y+44,
                              text=f"Actions remaining: {gs.remaining_actions}",
                              anchor="w", font=("Courier",11), fill=C_DIM)
            return

        if self.sel_unit and gs.current_player==PLAYER_HUMAN:
            u = self.sel_unit
            bx = 10

            # Just show Cancel button
            self._abtn(c, bx, bar_y+8, "CANCEL", "abtn_ca")
            c.tag_bind("abtn_ca","<Button-1>",lambda e: self._cancel())

            # Show helpful hint based on unit type
            unit_name = UNIT_STATS[u.type]['label']
            if u.type == TYPE_ARCHER:
                hint = f"{unit_name} ({u.hp}/{u.max_hp} HP) — Green: move | Aim & click: shoot arrow"
            elif u.type == TYPE_WARRIOR:
                hint = f"{unit_name} ({u.hp}/{u.max_hp} HP) — Green: move | Red: attack enemy"
            else:  # Tank
                hint = f"{unit_name} ({u.hp}/{u.max_hp} HP) — Click green tile to move"

            c.create_text(bx+120, bar_y+30, text=hint, anchor="w",
                          font=("Courier",11), fill=C_DIM)
        else:
            c.create_text(12, bar_y+20, text="YOUR TURN", anchor="w",
                          font=("Courier",14,"bold"), fill=C_P1)
            c.create_text(12, bar_y+44,
                          text=f"Actions remaining: {gs.remaining_actions}  — click one of your units",
                          anchor="w", font=("Courier",11), fill=C_DIM)

    def _abtn(self, c, x, y, text, tag):
        c.create_rectangle(x,y,x+108,y+48, fill="#0c1620",
                            outline=C_ACC, width=2, tags=tag)
        c.create_text(x+54,y+24, text=text, font=("Courier",12,"bold"),
                      fill=C_ACC, tags=tag)

    # ── Right panel ───────────────────────────────────────────────────────────
    def _draw_panel(self, c, gs):
        px = COLS*TILE; pw = PANEL_W
        c.create_rectangle(px,0,WIN_W,WIN_H, fill=C_PANEL, outline=C_GRID)
        c.create_text(px+pw//2, 15, text="GRID WARS",
                      font=("Courier",12,"bold"), fill=C_ACC)
        who = "Human" if gs.current_player==PLAYER_HUMAN else "AI"
        col = C_P1    if gs.current_player==PLAYER_HUMAN else C_P2
        c.create_text(px+10, 36,
                      text=f"Turn: {who}   [{gs.remaining_actions} action{'s' if gs.remaining_actions!=1 else ''}]",
                      anchor="w", font=("Courier",10), fill=col)

        iy = 60
        for owner, label, ucol in [(PLAYER_HUMAN,"YOUR UNITS",C_P1),(PLAYER_AI,"AI UNITS",C_P2)]:
            c.create_text(px+10, iy, text=f"── {label} ──",
                          anchor="w", font=("Courier",9), fill=ucol)
            iy += 16
            for u in gs.units:
                if u.owner!=owner or not u.alive: continue
                sym = UNIT_STATS[u.type]["sym"]
                lbl = UNIT_STATS[u.type]["label"][:3]
                c.create_text(px+10, iy,
                              text=f" {sym} {lbl}  {u.hp}/{u.max_hp} HP",
                              anchor="w", font=("Courier",9), fill=ucol)
                iy += 14
            iy += 8

        # Selected info
        if self.sel_unit:
            fresh = gs._unit_by_id(self.sel_unit.id)
            if fresh:
                iy = max(iy+4, WIN_H - 210)
                c.create_text(px+10, iy, text="── SELECTED ──",
                              anchor="w", font=("Courier",9), fill=C_SEL)
                iy += 15
                c.create_text(px+10, iy, text=UNIT_STATS[fresh.type]["label"],
                              anchor="w", font=("Courier",11,"bold"), fill=C_SEL)
                iy += 14
                for k, v in [("HP",  f"{fresh.hp}/{fresh.max_hp}"),
                             ("Move",str(UNIT_STATS[fresh.type]["move"])),
                             ("Atk", ("No" if not UNIT_STATS[fresh.type]["can_attack"]
                                      else f"Dmg {UNIT_STATS[fresh.type]['damage']}"))]:
                    c.create_text(px+10, iy, text=f"{k:<5}{v}",
                                  anchor="w", font=("Courier",9), fill=C_DIM)
                    iy += 13

        # Log
        log_top = WIN_H - 100
        c.create_rectangle(px,log_top-2,WIN_W,WIN_H, fill="#07090e", outline=C_GRID)
        c.create_text(px+10, log_top+3, text="LOG", anchor="w",
                      font=("Courier",8), fill=C_DIM)
        recent = self.log[-5:]
        for i, entry in enumerate(recent):
            is_ai = entry.startswith("AI:")
            fc = C_LOG_AI if is_ai else (C_LOG_NEW if i==len(recent)-1 else C_DIM)
            c.create_text(px+10, log_top+17+i*15, text=entry[:27],
                          anchor="w", font=("Courier",8), fill=fc)

        c.create_text(px+pw//2, WIN_H-3, text="ESC = pause",
                      font=("Courier",8), fill="#1a2830", anchor="s")

    # ─────────────────────────────────────────────────────────────────────────
    # INPUT
    # ─────────────────────────────────────────────────────────────────────────
    def _tile_at(self, e):
        tx, ty = e.x//TILE, e.y//TILE
        if 0<=tx<COLS and 0<=ty<ROWS: return tx, ty
        return None, None

    def _on_mouse(self, e):
        self.mouse_px = (e.x, e.y)
        if self.screen != "game": return
        # Show archer aim preview when mouse moves (if archer selected)
        if self.sel_unit and self.sel_unit.type == TYPE_ARCHER:
            tx, ty = e.x//TILE, e.y//TILE
            u = self.gs._unit_by_id(self.sel_unit.id)
            if u and self.gs.in_bounds(tx, ty):
                self.arrow_ray = self.gs.archer_ray(u.x, u.y, tx, ty)

    def _on_click(self, e):
        if self.screen != "game": return
        gs = self.gs
        if gs.current_player != PLAYER_HUMAN: return
        if self.ai_anim or self.arrow_anim: return

        tx, ty = self._tile_at(e)
        if tx is None: return

        # No mode active - check if selecting a unit or clicking on valid action tile
        clicked_unit = gs.get_unit_at(tx, ty)

        # If clicking on your own unit, select it and show all ranges
        if clicked_unit and clicked_unit.owner==PLAYER_HUMAN:
            self.sel_unit = clicked_unit
            self.mode = "both"  # Show both move and attack ranges
            # Calculate and show move range (green)
            self.hl_move = gs.reachable_tiles(clicked_unit)
            # Calculate and show attack range (red)
            if clicked_unit.type == TYPE_WARRIOR:
                self.hl_attack = gs.warrior_attack_tiles(clicked_unit)
            elif clicked_unit.type == TYPE_ARCHER:
                # For archers, we'll show attack when they aim
                self.hl_attack = []
            else:
                self.hl_attack = []
            self.arrow_ray = []
            self._log(f"Selected {UNIT_STATS[clicked_unit.type]['label']} — Click to move/attack")
            return

        # If we have a unit selected and clicking on an empty/enemy tile
        if self.sel_unit:
            u = gs._unit_by_id(self.sel_unit.id)
            if not u:
                self._cancel()
                return

            # Check if clicking on move range
            if (tx, ty) in self.hl_move:
                self._apply_human(MoveAction(u.id, tx, ty))
                return

            # Check if clicking on attack range (for warriors)
            if (tx, ty) in self.hl_attack and u.type == TYPE_WARRIOR:
                target = gs.get_unit_at(tx, ty)
                if target and target.owner == PLAYER_AI:
                    self._apply_human(AttackAction(u.id, tx, ty))
                else:
                    self._log("No enemy there.")
                return

            # For archers, any click fires arrow if path is valid
            if u.type == TYPE_ARCHER:
                ray = gs.archer_ray(u.x, u.y, tx, ty)
                if ray:
                    action = AttackAction(u.id, tx, ty)
                    self._cancel()
                    self._play_arrow(ray, C_P1, lambda: self._apply_human(action))
                else:
                    self._log("Can't fire arrow there.")
                return

    # ─────────────────────────────────────────────────────────────────────────
    # ARROW ANIMATION  (shared for human and AI)
    # ─────────────────────────────────────────────────────────────────────────
    def _play_arrow(self, ray, color, on_done):
        """Start arrow animation, call on_done() when finished."""
        self.arrow_anim = {"ray": ray, "step": 0, "color": color, "on_done": on_done}
        delay = max(35, 280 // max(len(ray), 1))
        self._step_arrow(delay)

    def _step_arrow(self, delay):
        aa = self.arrow_anim
        if not aa: return
        aa["step"] += 1
        if aa["step"] >= len(aa["ray"]):
            cb = aa.get("on_done")
            self.arrow_anim = None
            if cb: cb()
        else:
            self.after(delay, lambda: self._step_arrow(delay))

    # ─────────────────────────────────────────────────────────────────────────
    # HUMAN ACTION
    # ─────────────────────────────────────────────────────────────────────────
    def _apply_human(self, action):
        gs_before    = self.gs
        self.gs      = self.engine.apply(gs_before, action)
        self._log(self._describe(action, gs_before))
        self._cancel()
        if self.gs.is_terminal():
            self.after(300, self._draw_gameover)

    def _describe(self, action, gs):
        u = gs._unit_by_id(action.unit_id)
        n = UNIT_STATS[u.type]["label"] if u else "?"
        owner = "You" if (u and u.owner==PLAYER_HUMAN) else "AI"
        if isinstance(action, MoveAction):
            return f"{owner}: {n} → ({action.tx},{action.ty})"
        return f"{owner}: {n} attacks!"

    def _cancel(self):
        self.sel_unit = self.mode = None
        self.hl_move = self.hl_attack = self.arrow_ray = []

    def _log(self, msg):
        self.log.append(msg)
        if len(self.log) > 40: self.log = self.log[-40:]

    # ─────────────────────────────────────────────────────────────────────────
    # AI COMPUTE + ANIMATED PLAYBACK
    # ─────────────────────────────────────────────────────────────────────────
    def _ai_compute(self):
        """Choose up to 2 AI actions, queue them."""
        gs   = self.gs
        sim  = gs
        queue = []
        for _ in range(2):
            if sim.current_player != PLAYER_AI or sim.is_terminal(): break
            action = self.ai.choose(sim)
            queue.append({"action": action, "state_before": sim,
                          "label": self._ai_label(action, sim)})
            sim = sim.apply(action)
            if sim.current_player != PLAYER_AI: break

        self.ai_queue = queue
        self.ai_busy  = False
        self._ai_next()

    def _ai_label(self, action, gs):
        if action is None: return "AI: passes"
        u = gs._unit_by_id(action.unit_id)
        n = UNIT_STATS[u.type]["label"] if u else "?"
        if isinstance(action, MoveAction):
            return f"AI: {n} moves to ({action.tx},{action.ty})"
        return f"AI: {n} attacks!"

    def _ai_next(self):
        """Show + apply next queued AI action."""
        if not self.ai_queue:
            self.ai_anim = None
            if self.gs.is_terminal():
                self.after(400, self._draw_gameover)
            else:
                self._log("Your turn.")
            return

        entry  = self.ai_queue.pop(0)
        action = entry["action"]
        gs_sb  = entry["state_before"]
        label  = entry["label"]
        self.ai_anim = entry
        self._log(label)

        if isinstance(action, AttackAction):
            u = gs_sb._unit_by_id(action.unit_id)
            if u and u.type == TYPE_ARCHER:
                ray = gs_sb.archer_ray(u.x, u.y, action.tx, action.ty)
                if ray:
                    # Show anim, then apply after arrow lands
                    self._play_arrow(ray, C_P2, lambda a=action: self._ai_apply(a))
                    return

        # Non-archer attack or move: show overlay for AI_SHOW_MS then apply
        self.after(AI_SHOW_MS, lambda a=action: self._ai_apply(a))

    def _ai_apply(self, action):
        self.gs      = self.engine.apply(self.gs, action)
        self.ai_anim = None
        self.after(260, self._ai_next)


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()