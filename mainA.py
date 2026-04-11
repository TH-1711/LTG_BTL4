"""
GRID WARS — Turn-based grid strategy game
Python + tkinter (stdlib only, no extra dependencies)

Controls:
  • Left-click a unit  → select it (shows Move / Attack buttons)
  • Move mode         → highlighted tiles are clickable destinations
  • Attack mode       → click to attack (Warrior: adjacent; Archer: ray toward click)
  • ESC               → pause / in-game menu
"""

import tkinter as tk
from tkinter import font as tkfont
import copy, random, math, time

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
COLS, ROWS = 20, 15
TILE = 52          # pixels per tile
PANEL_W = 220      # right-side info panel
WIN_W = COLS * TILE + PANEL_W
WIN_H = ROWS * TILE + 60  # +60 for bottom action bar

TERRAIN_EMPTY = 0
TERRAIN_ROCK  = 1
TERRAIN_RIVER = 2

PLAYER_HUMAN = 0
PLAYER_AI    = 1

TYPE_TANK    = "TANK"
TYPE_WARRIOR = "WARRIOR"
TYPE_ARCHER  = "ARCHER"

# Colours
C_BG        = "#0b0f14"
C_TILE      = "#111820"
C_GRID      = "#1a2530"
C_ROCK      = "#2a3040"
C_RIVER     = "#0d3050"
C_MOVE_HL   = "#1a4a2a"
C_ATTACK_HL = "#4a1a1a"
C_RAY_HL    = "#3a2a0a"
C_SELECT    = "#ffd700"
C_P1        = "#00e5ff"
C_P2        = "#ff4d6d"
C_HP_BG     = "#222"
C_HP_GOOD   = "#39ff14"
C_HP_MED    = "#ffd700"
C_HP_LOW    = "#ff4d6d"
C_PANEL     = "#0f1318"
C_ACCENT    = "#00e5ff"
C_TEXT      = "#c8d8e8"
C_DIM       = "#4a6070"

UNIT_COLORS = {PLAYER_HUMAN: C_P1, PLAYER_AI: C_P2}

UNIT_STATS = {
    TYPE_TANK:    {"hp": 10, "move": 3, "can_attack": False, "damage": 0,  "symbol": "⬡"},
    TYPE_WARRIOR: {"hp": 5,  "move": 5, "can_attack": True,  "damage": 2,  "symbol": "⚔"},
    TYPE_ARCHER:  {"hp": 3,  "move": 2, "can_attack": True,  "damage": 1,  "symbol": "◈"},
}

# ─────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────
class Unit:
    _id = 0
    def __init__(self, owner, utype, x, y):
        Unit._id += 1
        self.id    = Unit._id
        self.owner = owner
        self.type  = utype
        self.x     = x
        self.y     = y
        self.hp    = UNIT_STATS[utype]["hp"]
        self.max_hp = self.hp

    @property
    def alive(self): return self.hp > 0

    def clone(self):
        u = Unit.__new__(Unit)
        u.__dict__.update(self.__dict__)
        return u

    def __repr__(self):
        return f"Unit({self.type},{self.owner},({self.x},{self.y}),hp={self.hp})"


class MoveAction:
    def __init__(self, unit_id, tx, ty):
        self.unit_id = unit_id
        self.tx, self.ty = tx, ty

class AttackAction:
    def __init__(self, unit_id, tx, ty):
        self.unit_id = unit_id
        self.tx, self.ty = tx, ty   # target tile (warrior) or direction tile (archer)


# ─────────────────────────────────────────────
# TERRAIN GENERATOR
# ─────────────────────────────────────────────
def make_terrain():
    grid = [[TERRAIN_EMPTY]*ROWS for _ in range(COLS)]
    # Fixed rivers (vertical stripes)
    for y in range(ROWS):
        if y in range(3, 6):
            grid[6][y] = TERRAIN_RIVER
            grid[13][y] = TERRAIN_RIVER
        if y in range(10,12):
            grid[6][y] = TERRAIN_RIVER
            grid[13][y] = TERRAIN_RIVER
        
    # Scatter rocks (deterministic seed for reproducibility)
    rng = random.Random(42)
    attempts = 0
    rocks = 0
    while rocks < 18 and attempts < 500:
        attempts += 1
        x = rng.randint(1, COLS-2)
        y = rng.randint(0, ROWS-1)
        if grid[x][y] == TERRAIN_EMPTY and x not in (0,1,COLS-1,COLS-2):
            grid[x][y] = TERRAIN_ROCK
            rocks += 1
    return grid


# ─────────────────────────────────────────────
# GAME STATE
# ─────────────────────────────────────────────
class GameState:
    def __init__(self, grid=None, units=None, current_player=PLAYER_HUMAN, remaining_actions=2):
        self.grid              = grid if grid is not None else make_terrain()
        self.units             = units if units is not None else []
        self.current_player    = current_player
        self.remaining_actions = remaining_actions

    # ── helpers ──────────────────────────────
    def get_unit_at(self, x, y):
        for u in self.units:
            if u.alive and u.x == x and u.y == y:
                return u
        return None

    def occupied(self, x, y):
        return self.get_unit_at(x, y) is not None

    def in_bounds(self, x, y):
        return 0 <= x < COLS and 0 <= y < ROWS

    def passable(self, x, y):
        """Passable for movement (not rock, not river)."""
        if not self.in_bounds(x, y): return False
        t = self.grid[x][y]
        return t == TERRAIN_EMPTY

    def blocks_projectile(self, x, y):
        """Only rocks block arrows."""
        if not self.in_bounds(x, y): return True   # out-of-bounds
        return self.grid[x][y] == TERRAIN_ROCK

    # ── movement BFS ─────────────────────────
    def reachable_tiles(self, unit):
        from collections import deque
        visited = {(unit.x, unit.y): 0}
        q = deque([(unit.x, unit.y, 0)])
        result = []
        while q:
            cx, cy, dist = q.popleft()
            if dist > 0:
                result.append((cx, cy))
            if dist == unit_move(unit): continue
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = cx+dx, cy+dy
                if (nx,ny) in visited: continue
                if not self.passable(nx, ny): continue
                if self.occupied(nx, ny): continue
                visited[(nx,ny)] = dist+1
                q.append((nx, ny, dist+1))
        return result

    # ── attack tiles ─────────────────────────
    def warrior_attack_tiles(self, unit):
        tiles = []
        for dx in [-1,0,1]:
            for dy in [-1,0,1]:
                if dx==0 and dy==0: continue
                nx, ny = unit.x+dx, unit.y+dy
                if self.in_bounds(nx, ny):
                    tiles.append((nx, ny))
        return tiles

    def archer_ray(self, unit, tx, ty):
        """Return list of tiles along ray from unit toward (tx,ty).
           Stops at rock (exclusive) or first unit (inclusive)."""
        if tx == unit.x and ty == unit.y:
            return []
        dx = tx - unit.x
        dy = ty - unit.y
        tiles = []
        # Bresenham-style step
        steps = max(abs(dx), abs(dy), 1)
        ox, oy = unit.x, unit.y
        for i in range(1, COLS + ROWS):
            t = i / steps
            nx = round(ox + dx * t / max(1, abs(dx) if abs(dx)>=abs(dy) else 0.001))
            ny = round(oy + dy * t / max(1, abs(dy) if abs(dy)>=abs(dx) else 0.001))
            # safer: just step
            break
        # Use proper Bresenham
        return self._bresenham_ray(unit.x, unit.y, tx, ty)

    def _bresenham_ray(self, x0, y0, tx, ty):
        """Walk ray from (x0,y0) toward (tx,ty) tile by tile."""
        dx = tx - x0
        dy = ty - y0
        if dx == 0 and dy == 0:
            return []
        # Normalise step: step along both axes proportionally
        # We extend well beyond the target to cross the whole board
        length = math.hypot(dx, dy)
        sdx = dx / length
        sdy = dy / length

        tiles = []
        seen = set()
        prev_x, prev_y = x0, y0
        for step in range(1, COLS + ROWS):
            rx = x0 + sdx * step
            ry = y0 + sdy * step
            cx, cy = round(rx), round(ry)
            if not self.in_bounds(cx, cy): break
            if (cx, cy) in seen: continue
            seen.add((cx, cy))
            if cx == x0 and cy == y0: continue
            if self.blocks_projectile(cx, cy):
                break   # rock stops ray (don't include rock tile)
            tiles.append((cx, cy))
            hit = self.get_unit_at(cx, cy)
            if hit is not None:
                break   # stop at first unit
        return tiles

    # ── legal actions ─────────────────────────
    def get_legal_actions(self):
        actions = []
        for u in self.units:
            if not u.alive or u.owner != self.current_player:
                continue
            # move actions
            for tx, ty in self.reachable_tiles(u):
                actions.append(MoveAction(u.id, tx, ty))
            # attack actions
            stats = UNIT_STATS[u.type]
            if stats["can_attack"]:
                if u.type == TYPE_WARRIOR:
                    for tx, ty in self.warrior_attack_tiles(u):
                        target = self.get_unit_at(tx, ty)
                        if target and target.owner != u.owner:
                            actions.append(AttackAction(u.id, tx, ty))
                elif u.type == TYPE_ARCHER:
                    # Shoot toward each enemy
                    enemies = [e for e in self.units if e.alive and e.owner != u.owner]
                    for e in enemies:
                        ray = self._bresenham_ray(u.x, u.y, e.x, e.y)
                        for tx, ty in ray:
                            hit = self.get_unit_at(tx, ty)
                            if hit and hit.owner != u.owner:
                                actions.append(AttackAction(u.id, tx, ty))
                                break
                            elif hit:
                                break
        if not actions:
            # pass action — just end action
            actions.append(None)
        return actions

    # ── apply action ─────────────────────────
    def apply(self, action):
        """Return new GameState after applying action."""
        ns = self.clone()
        if action is None:
            ns.remaining_actions = 0
        elif isinstance(action, MoveAction):
            u = ns._unit_by_id(action.unit_id)
            if u:
                u.x, u.y = action.tx, action.ty
            ns.remaining_actions -= 1
        elif isinstance(action, AttackAction):
            u = ns._unit_by_id(action.unit_id)
            if u:
                stats = UNIT_STATS[u.type]
                if u.type == TYPE_WARRIOR:
                    target = ns.get_unit_at(action.tx, action.ty)
                    if target and target.owner != u.owner:
                        target.hp = max(0, target.hp - stats["damage"])
                elif u.type == TYPE_ARCHER:
                    ray = ns._bresenham_ray(u.x, u.y, action.tx, action.ty)
                    for tx, ty in ray:
                        hit = ns.get_unit_at(tx, ty)
                        if hit and hit.owner != u.owner:
                            hit.hp = max(0, hit.hp - stats["damage"])
                            break
                        elif hit:
                            break
            ns.remaining_actions -= 1

        if ns.remaining_actions <= 0:
            ns.current_player = 1 - ns.current_player
            ns.remaining_actions = 2
        # Remove dead units
        ns.units = [u for u in ns.units if u.alive]
        return ns

    def is_terminal(self):
        p0_alive = any(u.alive and u.owner == PLAYER_HUMAN for u in self.units)
        p1_alive = any(u.alive and u.owner == PLAYER_AI   for u in self.units)
        return not p0_alive or not p1_alive

    def winner(self):
        p0 = any(u.alive and u.owner == PLAYER_HUMAN for u in self.units)
        p1 = any(u.alive and u.owner == PLAYER_AI   for u in self.units)
        if p0 and not p1: return PLAYER_HUMAN
        if p1 and not p0: return PLAYER_AI
        return None

    # ── utilities ────────────────────────────
    def _unit_by_id(self, uid):
        for u in self.units:
            if u.id == uid: return u
        return None

    def clone(self):
        ns = GameState.__new__(GameState)
        ns.grid              = self.grid   # immutable, shared
        ns.units             = [u.clone() for u in self.units]
        ns.current_player    = self.current_player
        ns.remaining_actions = self.remaining_actions
        return ns


def unit_move(u):
    return UNIT_STATS[u.type]["move"]


# ─────────────────────────────────────────────
# INITIAL SETUP
# ─────────────────────────────────────────────
def make_initial_state():
    grid = make_terrain()
    # Clear starting columns of any rocks
    for y in range(ROWS):
        for x in [0,1,2,3]:
            grid[x][y] = TERRAIN_EMPTY
        for x in [COLS-4,COLS-3,COLS-2,COLS-1]:
            grid[x][y] = TERRAIN_EMPTY



    units = []

    # ===== Define spawn areas =====
    # Left: columns 0-1, rows 0-14 (4x15)
    left_area = [(x, y) for x in range(0, 4) for y in range(0, 15)]

    # Right: columns 18-19, rows 0-14 (4x15)
    right_area = [(x, y) for x in range(16, 20) for y in range(0, 15)]

    # Shuffle positions
    random.shuffle(left_area)
    random.shuffle(right_area)

    # ===== Unit types =====
    types_h = [TYPE_TANK, TYPE_WARRIOR, TYPE_WARRIOR, TYPE_TANK, TYPE_ARCHER]
    types_a = [TYPE_TANK, TYPE_WARRIOR, TYPE_WARRIOR, TYPE_TANK, TYPE_ARCHER]

    # ===== Spawn Human =====
    for i in range(5):
        x, y = left_area[i]
        u = Unit(PLAYER_HUMAN, types_h[i], x, y)
        u.id = i + 1
        units.append(u)

    # ===== Spawn AI =====
    for i in range(5):
        x, y = right_area[i]
        u = Unit(PLAYER_AI, types_a[i], x, y)
        u.id = i + 6
        units.append(u)

    Unit._id = 20  # avoid collision
    return GameState(grid, units)


# ─────────────────────────────────────────────
# AI — EVALUATION
# ─────────────────────────────────────────────
def evaluate(state, for_player):
    if state.is_terminal():
        w = state.winner()
        if w == for_player: return 10000
        if w is not None:   return -10000
        return 0

    opp = 1 - for_player
    my_hp  = sum(u.hp for u in state.units if u.alive and u.owner == for_player)
    opp_hp = sum(u.hp for u in state.units if u.alive and u.owner == opp)
    my_n   = sum(1    for u in state.units if u.alive and u.owner == for_player)
    opp_n  = sum(1    for u in state.units if u.alive and u.owner == opp)

    score = (my_hp - opp_hp) * 2 + (my_n - opp_n) * 10

    # proximity bonus: closer to enemies is slightly better
    my_units  = [u for u in state.units if u.alive and u.owner == for_player]
    opp_units = [u for u in state.units if u.alive and u.owner == opp]
    if my_units and opp_units:
        total_dist = 0
        for mu in my_units:
            min_d = min(abs(mu.x-e.x)+abs(mu.y-e.y) for e in opp_units)
            total_dist += min_d
        score -= total_dist * 0.1

    return score


# ─────────────────────────────────────────────
# AI — MINIMAX (depth=2, alpha-beta)
# ─────────────────────────────────────────────
def minimax(state, depth, alpha, beta, for_player):
    if depth == 0 or state.is_terminal():
        return evaluate(state, for_player), None

    actions = state.get_legal_actions()
    random.shuffle(actions)   # randomise ties
    best_action = actions[0] if actions else None

    if state.current_player == for_player:
        best = -math.inf
        for a in actions[:12]:   # cap branching
            ns = state.apply(a)
            val, _ = minimax(ns, depth-1, alpha, beta, for_player)
            if val > best:
                best = val
                best_action = a
            alpha = max(alpha, best)
            if beta <= alpha: break
        return best, best_action
    else:
        best = math.inf
        for a in actions[:12]:
            ns = state.apply(a)
            val, _ = minimax(ns, depth-1, alpha, beta, for_player)
            if val < best:
                best = val
                best_action = a
            beta = min(beta, best)
            if beta <= alpha: break
        return best, best_action


class MinimaxAI:
    def choose(self, state):
        _, action = minimax(state, 2, -math.inf, math.inf, state.current_player)
        return action


# ─────────────────────────────────────────────
# AI — MCTS
# ─────────────────────────────────────────────
class MCTSNode:
    __slots__ = ("state","action","parent","children","wins","visits","untried")
    def __init__(self, state, action=None, parent=None):
        self.state    = state
        self.action   = action
        self.parent   = parent
        self.children = []
        self.wins     = 0.0
        self.visits   = 0
        actions = state.get_legal_actions()
        self.untried  = [a for a in actions if a is not None] or [None]

    def uct_select(self):
        log_n = math.log(self.visits + 1)
        return max(self.children,
                   key=lambda c: c.wins/max(c.visits,1) + 1.41*math.sqrt(log_n/max(c.visits,1)))

    def expand(self):
        a = self.untried.pop()
        ns = self.state.apply(a)
        child = MCTSNode(ns, a, self)
        self.children.append(child)
        return child

    def rollout(self, for_player, max_steps=20):
        s = self.state.clone()
        for _ in range(max_steps):
            if s.is_terminal(): break
            acts = s.get_legal_actions()
            s = s.apply(random.choice(acts))
        return evaluate(s, for_player)

    def backpropagate(self, value):
        self.visits += 1
        self.wins   += value
        if self.parent:
            self.parent.backpropagate(value)


class MCTSAI:
    def __init__(self, iterations=600):
        self.iterations = iterations

    def choose(self, state):
        root = MCTSNode(state)
        for_player = state.current_player
        for _ in range(self.iterations):
            node = root
            # selection
            while node.untried == [] and node.children:
                node = node.uct_select()
            # expansion
            if node.untried:
                node = node.expand()
            # simulation
            val = node.rollout(for_player)
            # backprop
            node.backpropagate(val)

        if not root.children:
            return None
        best = max(root.children, key=lambda c: c.visits)
        return best.action


# ─────────────────────────────────────────────
# GAME ENGINE
# ─────────────────────────────────────────────
class GameEngine:
    def apply(self, state, action):
        return state.apply(action)


# ─────────────────────────────────────────────
# UI / RENDERER  (tkinter Canvas)
# ─────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GRID WARS")
        self.resizable(False, False)
        self.configure(bg=C_BG)

        self.canvas = tk.Canvas(self, width=WIN_W, height=WIN_H,
                                bg=C_BG, highlightthickness=0)
        self.canvas.pack()

        # State machine
        self.screen        = "menu"   # menu | game | pause | gameover
        self.game_state    = None
        self.saved_state   = None     # for pause/continue
        self.engine        = GameEngine()
        self.ai            = MCTSAI(600)   # swap to MinimaxAI() if desired

        # Interaction state
        self.selected_unit = None
        self.mode          = None       # "move" | "attack"
        self.highlight     = []
        self.ray_tiles     = []
        self.log           = []
        self.ai_thinking   = False
        self.mouse_tile    = None

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>",   self.on_mouse_move)
        self.bind("<Escape>", self.on_escape)
        self.bind("<Configure>", lambda e: None)

        self._draw_menu()
        self._schedule_loop()

    # ─────────────────────────────────────────
    # MAIN LOOP
    # ─────────────────────────────────────────
    def _schedule_loop(self):
        self._loop()
        # loop driven by after() — no busy waiting

    def _loop(self):
        if self.screen == "game":
            self._render_game()
            if (self.game_state and
                    self.game_state.current_player == PLAYER_AI and
                    not self.ai_thinking and
                    not self.game_state.is_terminal()):
                self.ai_thinking = True
                self.after(80, self._ai_move)
        elif self.screen == "menu":
            pass   # static, only redrawn on event
        elif self.screen == "pause":
            pass
        elif self.screen == "gameover":
            pass
        self.after(50, self._loop)

    # ─────────────────────────────────────────
    # SCREENS
    # ─────────────────────────────────────────
    def _clear(self):
        self.canvas.delete("all")

    def _draw_menu(self):
        self._clear()
        self.screen = "menu"
        c = self.canvas
        W, H = WIN_W, WIN_H

        # Background grid effect
        for x in range(0, W, 40):
            c.create_line(x, 0, x, H, fill="#0d1520", width=1)
        for y in range(0, H, 40):
            c.create_line(0, y, W, y, fill="#0d1520", width=1)

        # Title
        c.create_text(W//2, 110, text="GRID WARS",
                      font=("Courier", 56, "bold"), fill=C_ACCENT,
                      anchor="center")
        c.create_text(W//2, 160, text="TURN-BASED STRATEGY",
                      font=("Courier", 14), fill=C_DIM, anchor="center")

        # Buttons
        by = 250
        self._menu_btn("▶  START GAME",    W//2, by,      tag="btn_start")
        if self.saved_state:
            self._menu_btn("⟳  CONTINUE GAME", W//2, by+70, tag="btn_continue")
        self._menu_btn("✕  EXIT",           W//2, by+140, tag="btn_exit")

        c.tag_bind("btn_start",    "<Button-1>", lambda e: self._start_new())
        c.tag_bind("btn_continue", "<Button-1>", lambda e: self._continue_game())
        c.tag_bind("btn_exit",     "<Button-1>", lambda e: self.quit())

        # Legend
        ly = H - 80
        c.create_text(W//2, ly,    text="⬡ TANK  ⚔ WARRIOR  ◈ ARCHER",
                      font=("Courier", 12), fill=C_DIM)
        c.create_text(W//2, ly+22, text="▓ ROCK  ≈ RIVER  |  AI: MCTS",
                      font=("Courier", 12), fill=C_DIM)
        c.create_text(W//2, ly+44, text="ESC = pause  •  LClick unit = select",
                      font=("Courier", 11), fill="#2a3a4a")

    def _menu_btn(self, text, cx, cy, tag=None):
        x1, y1, x2, y2 = cx-130, cy-22, cx+130, cy+22
        self.canvas.create_rectangle(x1, y1, x2, y2,
                                     fill="#0f1a28", outline=C_ACCENT,
                                     width=2, tags=tag)
        self.canvas.create_text(cx, cy, text=text,
                                font=("Courier", 15, "bold"),
                                fill=C_ACCENT, tags=tag)

    def _draw_pause(self):
        self._clear()
        self.screen = "pause"
        c = self.canvas
        W, H = WIN_W, WIN_H

        c.create_rectangle(0, 0, W, H, fill="#050a10")
        c.create_text(W//2, 130, text="— PAUSED —",
                      font=("Courier", 42, "bold"), fill=C_ACCENT)

        by = 240
        self._menu_btn("▶  CONTINUE",       W//2, by,      tag="btn_resume")
        self._menu_btn("↺  RESTART",         W//2, by+70,   tag="btn_restart")
        self._menu_btn("⌂  MAIN MENU",       W//2, by+140,  tag="btn_mainmenu")

        c.tag_bind("btn_resume",   "<Button-1>", lambda e: self._resume_game())
        c.tag_bind("btn_restart",  "<Button-1>", lambda e: self._start_new())
        c.tag_bind("btn_mainmenu", "<Button-1>", lambda e: self._draw_menu())

    def _draw_gameover(self):
        self._clear()
        self.screen = "gameover"
        c = self.canvas
        W, H = WIN_W, WIN_H
        w = self.game_state.winner()
        label = "HUMAN WINS!" if w == PLAYER_HUMAN else ("AI WINS!" if w == PLAYER_AI else "DRAW!")
        color = C_P1 if w == PLAYER_HUMAN else C_P2

        c.create_rectangle(0, 0, W, H, fill="#050a10")
        c.create_text(W//2, 140, text=label, font=("Courier", 52, "bold"),
                      fill=color)
        by = 280
        self._menu_btn("↺  PLAY AGAIN", W//2, by,     tag="btn_again")
        self._menu_btn("⌂  MAIN MENU",  W//2, by+70,  tag="btn_mainmenu2")
        c.tag_bind("btn_again",    "<Button-1>", lambda e: self._start_new())
        c.tag_bind("btn_mainmenu2","<Button-1>", lambda e: self._draw_menu())

    # ─────────────────────────────────────────
    # GAME CONTROL
    # ─────────────────────────────────────────
    def _start_new(self):
        self.game_state    = make_initial_state()
        self.saved_state   = None
        self.selected_unit = None
        self.mode          = None
        self.highlight     = []
        self.ray_tiles     = []
        self.log           = ["Game started. Your turn."]
        self.ai_thinking   = False
        self.screen        = "game"

    def _resume_game(self):
        if self.saved_state:
            self.game_state = self.saved_state
        self.screen = "game"

    def _continue_game(self):
        if self.saved_state:
            self.game_state = self.saved_state
            self.screen = "game"

    def on_escape(self, event):
        if self.screen == "game":
            self.saved_state = self.game_state.clone()
            self._draw_pause()
        elif self.screen == "pause":
            self._resume_game()

    # ─────────────────────────────────────────
    # RENDER
    # ─────────────────────────────────────────
    def _render_game(self):
        if self.screen != "game": return
        c = self.canvas
        c.delete("all")
        gs = self.game_state

        # ── Grid & terrain ────────────────────
        for cx in range(COLS):
            for cy in range(ROWS):
                x1, y1 = cx*TILE, cy*TILE
                x2, y2 = x1+TILE, y1+TILE
                t = gs.grid[cx][cy]
                if t == TERRAIN_ROCK:
                    fill = C_ROCK
                elif t == TERRAIN_RIVER:
                    fill = C_RIVER
                else:
                    fill = C_TILE
                c.create_rectangle(x1, y1, x2, y2, fill=fill, outline=C_GRID, width=1)

                # terrain symbols
                if t == TERRAIN_ROCK:
                    c.create_text(x1+TILE//2, y1+TILE//2, text="▲",
                                  font=("Courier", 14), fill="#3a4a5a")
                elif t == TERRAIN_RIVER:
                    c.create_text(x1+TILE//2, y1+TILE//2, text="≈",
                                  font=("Courier", 14), fill="#1a5080")

        # ── Highlights ────────────────────────
        for (hx, hy) in self.highlight:
            x1, y1 = hx*TILE+2, hy*TILE+2
            x2, y2 = x1+TILE-4, y1+TILE-4
            color = C_MOVE_HL if self.mode == "move" else C_ATTACK_HL
            c.create_rectangle(x1, y1, x2, y2, fill=color, outline="", width=0)

        for (rx, ry) in self.ray_tiles:
            x1, y1 = rx*TILE+2, ry*TILE+2
            x2, y2 = x1+TILE-4, y1+TILE-4
            c.create_rectangle(x1, y1, x2, y2, fill=C_RAY_HL, outline="", width=0)

        # ── Units ─────────────────────────────
        for u in gs.units:
            if not u.alive: continue
            ux, uy = u.x*TILE, u.y*TILE
            cx2, cy2 = ux+TILE//2, uy+TILE//2

            col = UNIT_COLORS[u.owner]
            is_sel = (self.selected_unit and self.selected_unit.id == u.id)

            # Unit circle
            pad = 6
            outline_w = 3 if is_sel else 1
            outline_c = C_SELECT if is_sel else col
            c.create_oval(ux+pad, uy+pad, ux+TILE-pad, uy+TILE-pad,
                          fill="#0a1520", outline=outline_c, width=outline_w)

            # Symbol
            sym = UNIT_STATS[u.type]["symbol"]
            c.create_text(cx2, cy2-3, text=sym, font=("Courier", 16, "bold"),
                          fill=col)

            # HP bar
            max_hp = u.max_hp
            bar_w  = TILE - 8
            bar_h  = 5
            bx, by2 = ux+4, uy+TILE-10
            ratio  = u.hp / max_hp
            hpc = C_HP_GOOD if ratio > 0.6 else (C_HP_MED if ratio > 0.3 else C_HP_LOW)
            c.create_rectangle(bx, by2, bx+bar_w, by2+bar_h, fill=C_HP_BG, outline="")
            c.create_rectangle(bx, by2, bx+int(bar_w*ratio), by2+bar_h, fill=hpc, outline="")

            # HP number
            c.create_text(cx2, uy+TILE-15, text=str(u.hp),
                          font=("Courier", 8), fill=C_DIM)

        # ── Action bar (bottom) ────────────────
        bar_y = ROWS * TILE
        c.create_rectangle(0, bar_y, COLS*TILE, WIN_H, fill="#080c12", outline="")
        if self.selected_unit and gs.current_player == PLAYER_HUMAN:
            u = self.selected_unit
            # Move button
            self._action_btn(c, 10, bar_y+8, "MOVE", "btn_move")
            c.tag_bind("btn_move", "<Button-1>", lambda e: self._set_mode_move())
            # Attack button (if unit can attack)
            if UNIT_STATS[u.type]["can_attack"]:
                self._action_btn(c, 120, bar_y+8, "ATTACK", "btn_attack")
                c.tag_bind("btn_attack", "<Button-1>", lambda e: self._set_mode_attack())
            # Cancel
            self._action_btn(c, 240, bar_y+8, "CANCEL", "btn_cancel")
            c.tag_bind("btn_cancel", "<Button-1>", lambda e: self._cancel_selection())
        else:
            turn_txt = "YOUR TURN" if gs.current_player == PLAYER_HUMAN else "AI THINKING..."
            turn_col = C_P1 if gs.current_player == PLAYER_HUMAN else C_P2
            c.create_text(10, bar_y+20, text=turn_txt, anchor="w",
                          font=("Courier", 14, "bold"), fill=turn_col)
            acts_txt = f"Actions left: {gs.remaining_actions}"
            c.create_text(10, bar_y+40, text=acts_txt, anchor="w",
                          font=("Courier", 11), fill=C_DIM)

        # Mode label
        if self.mode:
            c.create_text(COLS*TILE//2, bar_y+20, text=f"MODE: {self.mode.upper()}",
                          font=("Courier", 12, "bold"), fill=C_YELLOW if self.mode=="move" else C_ACCENT2)

        # ── Info panel (right) ─────────────────
        px = COLS * TILE
        c.create_rectangle(px, 0, WIN_W, WIN_H, fill=C_PANEL, outline=C_GRID)
        c.create_text(px+PANEL_W//2, 16, text="GRID WARS",
                      font=("Courier", 13, "bold"), fill=C_ACCENT)

        # Turn info
        c.create_text(px+10, 45, text=f"Turn: {'Human' if gs.current_player==0 else 'AI'}",
                      anchor="w", font=("Courier", 11), fill=C_TEXT)
        c.create_text(px+10, 63, text=f"Actions: {gs.remaining_actions}",
                      anchor="w", font=("Courier", 11), fill=C_DIM)

        # Unit list
        c.create_text(px+10, 90, text="─── YOUR UNITS ───",
                      anchor="w", font=("Courier", 10), fill=C_P1)
        iy = 108
        for u in gs.units:
            if u.owner == PLAYER_HUMAN and u.alive:
                sym = UNIT_STATS[u.type]["symbol"]
                c.create_text(px+10, iy, text=f"{sym} {u.type[:3]} HP:{u.hp}/{u.max_hp}",
                               anchor="w", font=("Courier", 10), fill=C_P1)
                iy += 16

        c.create_text(px+10, iy+6, text="─── AI UNITS ───",
                      anchor="w", font=("Courier", 10), fill=C_P2)
        iy += 24
        for u in gs.units:
            if u.owner == PLAYER_AI and u.alive:
                sym = UNIT_STATS[u.type]["symbol"]
                c.create_text(px+10, iy, text=f"{sym} {u.type[:3]} HP:{u.hp}/{u.max_hp}",
                               anchor="w", font=("Courier", 10), fill=C_P2)
                iy += 16

        # Selected unit info
        if self.selected_unit:
            u = self.selected_unit
            # find fresh reference
            fresh = gs._unit_by_id(u.id)
            if fresh:
                iy = max(iy+16, WIN_H - 200)
                c.create_text(px+10, iy, text="─── SELECTED ───",
                               anchor="w", font=("Courier", 10), fill=C_SELECT)
                iy += 18
                c.create_text(px+10, iy, text=f"{fresh.type}",
                               anchor="w", font=("Courier", 11, "bold"), fill=C_SELECT)
                iy += 16
                c.create_text(px+10, iy, text=f"HP: {fresh.hp}/{fresh.max_hp}",
                               anchor="w", font=("Courier", 10), fill=C_TEXT)
                iy += 14
                c.create_text(px+10, iy, text=f"Move: {UNIT_STATS[fresh.type]['move']}",
                               anchor="w", font=("Courier", 10), fill=C_DIM)

        # Log
        log_y = WIN_H - 80
        c.create_rectangle(px, log_y-4, WIN_W, WIN_H, fill="#08080f", outline=C_GRID)
        for i, msg in enumerate(self.log[-4:]):
            c.create_text(px+8, log_y + i*17, text=msg[:22], anchor="w",
                          font=("Courier", 9), fill=C_DIM)

        # ESC hint
        c.create_text(px+PANEL_W//2, WIN_H-6, text="ESC = pause",
                      font=("Courier", 9), fill="#1e2a38", anchor="s")

    def _action_btn(self, c, x, y, text, tag):
        c.create_rectangle(x, y, x+100, y+44, fill="#0f1a28",
                            outline=C_ACCENT, width=2, tags=tag)
        c.create_text(x+50, y+22, text=text, font=("Courier", 12, "bold"),
                      fill=C_ACCENT, tags=tag)

    # ─────────────────────────────────────────
    # INPUT HANDLERS
    # ─────────────────────────────────────────
    def _tile_from_event(self, event):
        tx = event.x // TILE
        ty = event.y // TILE
        if 0 <= tx < COLS and 0 <= ty < ROWS:
            return tx, ty
        return None, None

    def on_mouse_move(self, event):
        if self.screen != "game": return
        tx, ty = self._tile_from_event(event)
        self.mouse_tile = (tx, ty)

        # Update archer ray preview
        if (self.mode == "attack" and self.selected_unit and
                self.selected_unit.type == TYPE_ARCHER and tx is not None):
            self.ray_tiles = self.game_state._bresenham_ray(
                self.selected_unit.x, self.selected_unit.y, tx, ty)

    def on_click(self, event):
        if self.screen != "game": return
        gs = self.game_state
        if gs.current_player != PLAYER_HUMAN: return

        tx, ty = self._tile_from_event(event)
        if tx is None: return

        # In move mode
        if self.mode == "move":
            if (tx, ty) in self.highlight:
                action = MoveAction(self.selected_unit.id, tx, ty)
                self._apply_human_action(action)
            return

        # In attack mode
        if self.mode == "attack":
            u = self.selected_unit
            if u.type == TYPE_WARRIOR:
                if (tx, ty) in self.highlight:
                    target = gs.get_unit_at(tx, ty)
                    if target and target.owner == PLAYER_AI:
                        action = AttackAction(u.id, tx, ty)
                        self._apply_human_action(action)
                    else:
                        self._log("No enemy there.")
            elif u.type == TYPE_ARCHER:
                # Shoot toward clicked tile
                action = AttackAction(u.id, tx, ty)
                self._apply_human_action(action)
            return

        # No mode — try selecting a unit
        clicked = gs.get_unit_at(tx, ty)
        if clicked and clicked.owner == PLAYER_HUMAN:
            self.selected_unit = clicked
            self.mode          = None
            self.highlight     = []
            self.ray_tiles     = []
            self._log(f"Selected {clicked.type}")

    def _set_mode_move(self):
        if not self.selected_unit: return
        gs = self.game_state
        fresh = gs._unit_by_id(self.selected_unit.id)
        if not fresh: return
        self.mode      = "move"
        self.highlight = gs.reachable_tiles(fresh)
        self.ray_tiles = []

    def _set_mode_attack(self):
        if not self.selected_unit: return
        gs = self.game_state
        fresh = gs._unit_by_id(self.selected_unit.id)
        if not fresh: return
        self.mode = "attack"
        if fresh.type == TYPE_WARRIOR:
            self.highlight = gs.warrior_attack_tiles(fresh)
        else:
            self.highlight = []
        self.ray_tiles = []

    def _cancel_selection(self):
        self.selected_unit = None
        self.mode          = None
        self.highlight     = []
        self.ray_tiles     = []

    def _apply_human_action(self, action):
        gs = self.game_state
        self.game_state = self.engine.apply(gs, action)
        self._log(self._action_desc(action, gs))
        self._cancel_selection()
        if self.game_state.is_terminal():
            self._draw_gameover()

    def _action_desc(self, action, gs):
        if isinstance(action, MoveAction):
            u = gs._unit_by_id(action.unit_id)
            return f"{u.type if u else '?'} moved"
        elif isinstance(action, AttackAction):
            u = gs._unit_by_id(action.unit_id)
            return f"{u.type if u else '?'} attacked"
        return "Action"

    def _log(self, msg):
        self.log.append(msg)
        if len(self.log) > 20:
            self.log = self.log[-20:]

    # ─────────────────────────────────────────
    # AI MOVE
    # ─────────────────────────────────────────
    def _ai_move(self):
        if self.screen != "game":
            self.ai_thinking = False
            return
        gs = self.game_state
        if gs.current_player != PLAYER_AI or gs.is_terminal():
            self.ai_thinking = False
            return

        action = self.ai.choose(gs)
        if action is not None:
            self.game_state = self.engine.apply(gs, action)
            self._log("AI: " + self._action_desc(action, gs))
        else:
            # pass
            self.game_state = gs.apply(None)

        if self.game_state.is_terminal():
            self._draw_gameover()
            return

        # If AI still has actions, schedule next
        if self.game_state.current_player == PLAYER_AI:
            self.after(120, self._ai_move)
        else:
            self.ai_thinking = False
            self._log("Your turn.")


# needed for colour refs in renderer
C_YELLOW  = "#ffd700"
C_ACCENT2 = "#ff4d6d"

# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()