import random
from core.constants import *

def _build_map():
    E, R, W = TERRAIN_EMPTY, TERRAIN_ROCK, TERRAIN_RIVER
    grid = [[E]*ROWS for _ in range(COLS)]

    # Rivers at columns 6 and 13, rows 0-3 and 6-9 (gap at rows 4,5)
    for col in (6, 13):
        for row in list(range(0, 4)) + list(range(6, 10)):
            grid[col][row] = W
    # Rows 4-5 at those columns remain EMPTY (ford/crossing)

    # Hand-placed rocks — avoid cols 0-2, 17-19 (spawn zones) and river cols 6,13
    for cx, cy in [
        # upper section
        (2,0),(4,1),(7,2),(9,0),(11,1),(16,0),
        (3,3),(7,1),(10,3),(17,3),
        # lower section
        (8,8),(10,6),(12,7),(7,8),(9,9),(16,9),
        (2,9),(16,8),(3,7),(11,8),
        # NOTE: rows 4-5 are kept clear (crossing corridor) — no rocks placed there
    ]:
        # safety guard — never overwrite spawn zones or river cols
        if cx in (0,1,2,3,6,13,17,18,19): continue
        if 0 <= cx < COLS and 0 <= cy < ROWS:
            grid[cx][cy] = R
    return grid

HARDCODED_MAP = _build_map()   # built once at import time, never mutated

# river crossing tiles (visual marker only)
BRIDGE_TILES = {(6,4),(6,5),(13,4),(13,5)}
