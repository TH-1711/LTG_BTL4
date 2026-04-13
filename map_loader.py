"""
Map Loader for Grid Wars
Supports loading maps from text files, CSV, or TMX (Tiled)
"""

import os

# Terrain constants (must match btl4.py)
TERRAIN_EMPTY = 0
TERRAIN_ROCK = 1
TERRAIN_RIVER = 2

def load_map_from_text(filepath):
    """
    Load map from simple text file format

    Format:
        . = ground
        # = rock
        ~ = water/river
        = = bridge (walkable)

    Returns:
        (grid, bridge_tiles)
        - grid: 20x10 2D array [col][row]
        - bridge_tiles: set of (col, row) tuples
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Map file not found: {filepath}")

    with open(filepath, 'r') as f:
        lines = [line.rstrip('\n') for line in f if line.strip() and not line.startswith('#')]

    # Expected dimensions
    cols, rows = 15, 8

    # Initialize grid
    grid = [[TERRAIN_EMPTY for _ in range(rows)] for _ in range(cols)]
    bridge_tiles = set()

    # Parse line by line (each line = one row)
    for row_idx, line in enumerate(lines[:rows]):  # Take first 10 lines
        for col_idx, char in enumerate(line[:cols]):  # Take first 20 chars
            if char == '#':
                grid[col_idx][row_idx] = TERRAIN_ROCK
            elif char == '~':
                grid[col_idx][row_idx] = TERRAIN_RIVER
            elif char == '=':
                grid[col_idx][row_idx] = TERRAIN_EMPTY  # Bridge is walkable
                bridge_tiles.add((col_idx, row_idx))
            else:  # '.' or anything else
                grid[col_idx][row_idx] = TERRAIN_EMPTY

    return grid, bridge_tiles


def load_map_from_csv(filepath):
    """
    Load map from CSV file (e.g., exported from Tiled)

    CSV format: comma-separated tile IDs
        0 = ground
        1 = rock
        2 = water
        -1 = empty/no tile

    Returns:
        (grid, bridge_tiles)
    """
    import csv

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    cols, rows = 20, 10
    grid = [[TERRAIN_EMPTY for _ in range(rows)] for _ in range(cols)]
    bridge_tiles = set()

    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        for row_idx, row in enumerate(reader):
            if row_idx >= rows:
                break
            for col_idx, cell in enumerate(row):
                if col_idx >= cols:
                    break
                try:
                    tile_id = int(cell.strip())
                    if tile_id == 1:
                        grid[col_idx][row_idx] = TERRAIN_ROCK
                    elif tile_id == 2:
                        grid[col_idx][row_idx] = TERRAIN_RIVER
                    elif tile_id == 3:
                        grid[col_idx][row_idx] = TERRAIN_EMPTY
                        bridge_tiles.add((col_idx, row_idx))
                    else:
                        grid[col_idx][row_idx] = TERRAIN_EMPTY
                except (ValueError, IndexError):
                    grid[col_idx][row_idx] = TERRAIN_EMPTY

    return grid, bridge_tiles


def load_map_from_tmx(filepath):
    """
    Load map from Tiled TMX file
    Requires: pip install pytmx

    Returns:
        (grid, bridge_tiles)
    """
    try:
        import pytmx
    except ImportError:
        raise ImportError("pytmx not installed. Run: pip install pytmx")

    tmx_data = pytmx.TiledMap(filepath)

    cols, rows = tmx_data.width, tmx_data.height
    grid = [[TERRAIN_EMPTY for _ in range(rows)] for _ in range(cols)]
    bridge_tiles = set()

    # Assuming first layer is terrain
    layer = tmx_data.layers[0]

    for col in range(cols):
        for row in range(rows):
            tile = layer.data[row][col]
            if tile:
                # Map tile GID to terrain type (customize based on your tileset)
                gid = tile.gid
                if gid == 2:  # Rock tile
                    grid[col][row] = TERRAIN_ROCK
                elif gid == 3:  # Water tile
                    grid[col][row] = TERRAIN_RIVER
                elif gid == 4:  # Bridge tile
                    grid[col][row] = TERRAIN_EMPTY
                    bridge_tiles.add((col, row))
                else:
                    grid[col][row] = TERRAIN_EMPTY

    return grid, bridge_tiles


# Helper function to create empty map template
def create_empty_map_template(filepath):
    """Create an empty 20x10 map template"""
    template = """# Grid Wars Map Template
# Size: 20x10
# Legend: . = ground, # = rock, ~ = water, = = bridge

....................
....................
....................
....................
....................
....................
....................
....................
....................
....................
"""
    with open(filepath, 'w') as f:
        f.write(template)
    print(f"Created empty map template: {filepath}")


if __name__ == "__main__":
    # Test loading the example map
    print("Testing map loader...")

    try:
        grid, bridges = load_map_from_text("maps/battlefield_01.txt")
        print(f"✓ Loaded map successfully")
        print(f"  Grid size: {len(grid)}x{len(grid[0])}")
        print(f"  Bridge tiles: {len(bridges)}")
        print(f"  Sample bridges: {sorted(list(bridges))[:5]}")

        # Count terrain types
        empty = sum(1 for col in grid for cell in col if cell == TERRAIN_EMPTY)
        rocks = sum(1 for col in grid for cell in col if cell == TERRAIN_ROCK)
        water = sum(1 for col in grid for cell in col if cell == TERRAIN_RIVER)
        print(f"  Terrain: {empty} ground, {rocks} rocks, {water} water tiles")

    except Exception as e:
        print(f"✗ Error: {e}")
