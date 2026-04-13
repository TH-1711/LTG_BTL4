# Grid Wars - Turn-Based Tactical Game

A turn-based tactical strategy game built with Python and Tkinter, featuring AI opponents, custom maps, and multiple unit types.

## Features

- **Turn-based tactical combat**: Strategic unit movement and combat on a grid-based battlefield
- **3 Unit types**: Tank (high HP, low mobility), Warrior (balanced), Archer (ranged attacks)
- **AI opponent**: Monte Carlo Tree Search (MCTS) AI for challenging gameplay
- **Custom maps**: Load and create your own battlefield layouts
- **Visual map editor**: Easy-to-use GUI for designing custom maps
- **Animated sprites**: Character idle animations and smooth combat visuals
- **Segmented health bars**: Clear HP visualization for each unit

## Prerequisites

- Python 3.7 or higher
- tkinter (usually included with Python)
- Pillow (PIL) library

## Installation

1. Clone this repository:
```bash
git clone https://github.com/TH-1711/LTG_BTL4.git
cd LTG_BTL4
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install Pillow
```

## Running the Game

Start the main game:
```bash
python3 btl4.py
```

## Game Controls

- **Left-click on a unit**: Select unit and show movement/attack range
- **Left-click on highlighted tile**: Move unit to that position
- **Left-click on enemy unit**: Attack the enemy (if in range)
- **Right-click**: Deselect current unit
- **"End Turn" button**: End your turn and let AI move

## How to Play

1. **Objective**: Defeat all enemy units
2. **Units**:
   - **Tank**: 4 HP, moves 2 tiles, melee attack (2 damage)
   - **Warrior**: 3 HP, moves 3 tiles, melee attack (1 damage)
   - **Archer**: 2 HP, moves 3 tiles, ranged attack (1 damage, 4 tile range)
3. **Strategy**: Use terrain (rocks block movement, rivers are impassable except bridges) to your advantage
4. **Turns**: Move all your units, then click "End Turn" to let the AI play

## Map Editor

Create custom battlefield layouts with the visual map editor:

```bash
python3 map_editor_gui.py
```

### Editor Features

- **Brush tools**: Ground, Rock, River, Bridge
- **Click and drag**: Paint multiple tiles at once
- **Save/Load**: Export maps as `.txt` files
- **New**: Clear the map and start fresh

### Map Format

Maps are stored as text files in the `maps/` directory:

```
# Legend:
# . = ground (walkable)
# # = rock (blocks movement)
# ~ = river (impassable)
# = = bridge (walkable over water)

..#...~....~.#....
.#....~....~....#.
#.....~....~.....#
```

To use a custom map, save it in the `maps/` folder and update the map path in `btl4.py`:

```python
from map_loader import load_map_from_text
grid, bridges = load_map_from_text("maps/your_map.txt")
```

## Project Structure

```
.
├── btl4.py                 # Main game file
├── map_loader.py           # Map loading utilities
├── map_editor_gui.py       # Visual map editor
├── maps/                   # Map files
│   └── battlefield_01.txt  # Default map
├── assets/                 # Game assets
│   └── game_seamless/      # Sprite images
│       ├── tile_*.png      # Terrain tiles
│       ├── tank_*.png      # Tank sprites
│       ├── warrior_*.png   # Warrior sprites
│       ├── archer_*.png    # Archer sprites
│       └── arrow.png       # Projectile sprite
└── README.md              # This file
```

## Development

### AI Algorithm

The AI uses **Monte Carlo Tree Search (MCTS)** with:
- Random playouts for position evaluation
- UCB1 selection for balancing exploration/exploitation
- Configurable simulation depth and iterations

### Movement System

- **BFS (Breadth-First Search)** for calculating valid movement tiles
- Terrain-aware pathfinding (rocks block, rivers require bridges)
- Attack range calculation with line-of-sight checks

## Credits

- **Assets**: Kenney.nl game assets (modified)
- **Game design**: HCMUT BTL4 project
- **Developer**: TH-1711

## License

Educational project for HCMUT coursework.
