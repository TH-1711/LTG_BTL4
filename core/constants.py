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