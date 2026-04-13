"""
Simple Visual Map Editor for Grid Wars
Click tiles to change terrain type
Save/load maps easily
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import os

# Map dimensions
COLS, ROWS = 15, 8
TILE_SIZE = 40  # Smaller for editor view

# Terrain types
TERRAIN_EMPTY = 0
TERRAIN_ROCK = 1
TERRAIN_RIVER = 2
TERRAIN_BRIDGE = 3

# Colors
COLORS = {
    TERRAIN_EMPTY: "#C9A876",   # Tan ground
    TERRAIN_ROCK: "#5A5A5A",    # Gray rock
    TERRAIN_RIVER: "#2B4A6D",   # Blue water
    TERRAIN_BRIDGE: "#8B7355",  # Brown bridge
}

TERRAIN_CHARS = {
    TERRAIN_EMPTY: '.',
    TERRAIN_ROCK: '#',
    TERRAIN_RIVER: '~',
    TERRAIN_BRIDGE: '=',
}

class MapEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Grid Wars - Map Editor")

        # Current terrain brush
        self.current_terrain = TERRAIN_EMPTY

        # Map data
        self.grid = [[TERRAIN_EMPTY for _ in range(ROWS)] for _ in range(COLS)]

        # Create UI
        self._create_ui()

    def _create_ui(self):
        # Top toolbar
        toolbar = tk.Frame(self.root, bg="#2a2a2a", height=60)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        tk.Label(toolbar, text="Brush:", bg="#2a2a2a", fg="#ffffff",
                 font=("Arial", 12)).pack(side=tk.LEFT, padx=10)

        # Terrain buttons
        terrains = [
            ("Ground", TERRAIN_EMPTY),
            ("Rock", TERRAIN_ROCK),
            ("River", TERRAIN_RIVER),
            ("Bridge", TERRAIN_BRIDGE),
        ]

        for name, terrain_type in terrains:
            btn = tk.Button(
                toolbar,
                text=name,
                bg=COLORS[terrain_type],
                width=8,
                height=2,
                command=lambda t=terrain_type: self.set_brush(t)
            )
            btn.pack(side=tk.LEFT, padx=5, pady=10)

        # File operations
        tk.Button(toolbar, text="New", command=self.new_map,
                  width=6).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Load", command=self.load_map,
                  width=6).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Save", command=self.save_map,
                  width=6).pack(side=tk.LEFT, padx=5)

        # Canvas for map
        self.canvas = tk.Canvas(
            self.root,
            width=COLS * TILE_SIZE,
            height=ROWS * TILE_SIZE,
            bg="#1a1410",
            highlightthickness=0
        )
        self.canvas.pack(side=tk.TOP, padx=10, pady=10)

        # Bind mouse events
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)

        # Info label
        self.info_label = tk.Label(
            self.root,
            text="Click tiles to paint. Left-click = paint, Right-click = erase",
            bg="#2a2a2a",
            fg="#aaaaaa",
            pady=10
        )
        self.info_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Draw initial grid
        self.draw_grid()

    def set_brush(self, terrain_type):
        """Set current terrain brush"""
        self.current_terrain = terrain_type
        self.info_label.config(
            text=f"Brush: {list(TERRAIN_CHARS.values())[terrain_type]} "
                 f"({['Ground', 'Rock', 'River', 'Bridge'][terrain_type]})"
        )

    def draw_grid(self):
        """Redraw the entire grid"""
        self.canvas.delete("all")

        for col in range(COLS):
            for row in range(ROWS):
                x1 = col * TILE_SIZE
                y1 = row * TILE_SIZE
                x2 = x1 + TILE_SIZE
                y2 = y1 + TILE_SIZE

                terrain = self.grid[col][row]
                color = COLORS[terrain]

                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=color,
                    outline="#333333",
                    width=1
                )

                # Draw character label
                char = TERRAIN_CHARS[terrain]
                self.canvas.create_text(
                    x1 + TILE_SIZE // 2,
                    y1 + TILE_SIZE // 2,
                    text=char,
                    fill="#000000" if terrain == TERRAIN_EMPTY else "#ffffff",
                    font=("Courier", 10, "bold")
                )

    def _on_click(self, event):
        """Handle mouse click"""
        col = event.x // TILE_SIZE
        row = event.y // TILE_SIZE

        if 0 <= col < COLS and 0 <= row < ROWS:
            self.grid[col][row] = self.current_terrain
            self.draw_grid()

    def _on_drag(self, event):
        """Handle mouse drag (paint multiple tiles)"""
        self._on_click(event)

    def new_map(self):
        """Create new empty map"""
        if messagebox.askyesno("New Map", "Clear current map?"):
            self.grid = [[TERRAIN_EMPTY for _ in range(ROWS)] for _ in range(COLS)]
            self.draw_grid()
            self.info_label.config(text="New map created")

    def load_map(self):
        """Load map from text file"""
        filepath = filedialog.askopenfilename(
            title="Load Map",
            initialdir="maps",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not filepath:
            return

        try:
            from map_loader import load_map_from_text
            grid, bridges = load_map_from_text(filepath)

            # Convert bridge tiles back to TERRAIN_BRIDGE for editor
            for col, row in bridges:
                grid[col][row] = TERRAIN_BRIDGE

            self.grid = grid
            self.draw_grid()
            self.info_label.config(text=f"Loaded: {os.path.basename(filepath)}")

        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load map:\n{e}")

    def save_map(self):
        """Save map to text file"""
        filepath = filedialog.asksaveasfilename(
            title="Save Map",
            initialdir="maps",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not filepath:
            return

        try:
            with open(filepath, 'w') as f:
                f.write("# Grid Wars Map\n")
                f.write(f"# Size: {COLS}x{ROWS}\n")
                f.write("# Legend: . = ground, # = rock, ~ = water, = = bridge\n\n")

                for row in range(ROWS):
                    line = ""
                    for col in range(COLS):
                        terrain = self.grid[col][row]
                        line += TERRAIN_CHARS[terrain]
                    f.write(line + "\n")

            self.info_label.config(text=f"Saved: {os.path.basename(filepath)}")
            messagebox.showinfo("Saved", f"Map saved to:\n{filepath}")

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save map:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = MapEditor(root)
    root.mainloop()
