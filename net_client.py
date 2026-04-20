"""
Grid Wars — networked client.

Usage:
    python3 net_client.py [host] [port]

Defaults: host=127.0.0.1  port=55555

Each client is assigned player 0 or 1 by the server.
Player 0 sees their units on the left (same as the original single-player game).
Player 1 sees the same map; their units start on the right.

Controls are identical to btl4.py — click your unit, then click to move/attack.
Actions are sent to the server; the server broadcasts authoritative state back.
"""

import tkinter as tk
import socket
import threading
import queue
import sys

# Re-use all game logic and rendering from btl4
from btl4 import (
    App, PLAYER_HUMAN, PLAYER_AI, PLAYER_AI,
    MoveAction, AttackAction, TYPE_ARCHER,
    UNIT_STATS, C_P1, C_P2,
    make_initial_state,
)
from net_protocol import send_msg, recv_msg, dict_to_state, action_to_dict

HOST = "127.0.0.1"
PORT = 55556


class NetClient(App):
    """Networked variant of App. Replaces local AI with server communication."""

    def __init__(self, host: str, port: int):
        self._net_host = host
        self._net_port = port
        self._sock: socket.socket | None = None
        self._my_player: int | None = None    # assigned by server (0 or 1)
        self._msg_queue: queue.Queue = queue.Queue()
        self._connected = False

        super().__init__()
        self.title("GRID WARS — Multiplayer")

        # Override: remove AI, start connecting immediately
        self.ai = None
        self._connect()

    # ── Connection ────────────────────────────────────────────────────────────

    def _connect(self):
        self.screen = "connecting"
        self._draw_connecting("Connecting to server...")
        t = threading.Thread(target=self._connect_thread, daemon=True)
        t.start()

    def _connect_thread(self):
        try:
            sock = socket.create_connection((self._net_host, self._net_port), timeout=10)
            sock.settimeout(None)  # switch to blocking after connect
            self._sock = sock
            self._connected = True
            threading.Thread(target=self._recv_thread, daemon=True).start()
        except OSError as e:
            self._msg_queue.put({"type": "_connect_error", "msg": str(e)})

    def _recv_thread(self):
        """Background thread: read server messages into queue."""
        try:
            while True:
                msg = recv_msg(self._sock)
                self._msg_queue.put(msg)
        except Exception as e:
            import traceback; traceback.print_exc()
            self._msg_queue.put({"type": "_disconnected", "msg": str(e)})

    # ── Tick (override) ───────────────────────────────────────────────────────

    def _tick(self):
        self._drain_queue()

        if self.screen == "game":
            self.anim_tick += 1
            if self.anim_tick >= 5:
                self.anim_tick = 0
                self.anim_frame = (self.anim_frame + 1) % 4
            self._render_game()

        elif self.screen in ("connecting", "waiting"):
            pass   # static screens, redrawn on state change

        self.after(40, self._tick)

    def _drain_queue(self):
        try:
            while True:
                msg = self._msg_queue.get_nowait()
                self._handle_server_msg(msg)
        except queue.Empty:
            pass

    def _handle_server_msg(self, msg: dict):
        t = msg.get("type")

        if t == "_connect_error":
            self._draw_connecting(f"Connection failed: {msg['msg']}\n\nClose and retry.")
            return

        if t == "_disconnected":
            reason = msg.get("msg", "")
            self._draw_connecting(f"Disconnected from server.\n{reason}")
            return

        if t == "waiting":
            self._my_player = msg["your_player"]
            self._draw_connecting(
                f"Connected! You are Player {self._my_player + 1}.\nWaiting for opponent..."
            )
            return

        if t == "state":
            self._my_player = msg["your_player"]
            new_gs = dict_to_state(msg["state"])
            if self.screen not in ("game", "gameover"):
                # First state — start the game
                self.gs = new_gs
                self._start_net()
            else:
                self.gs = new_gs
                # Clear pending animation / selection if it's now our turn or not
                if self.gs.current_player != self._my_player:
                    self._cancel()
            return

        if t == "gameover":
            if self.gs:
                # Patch winner for display — gs.winner() reads live units
                # Force gameover screen
                self.after(300, self._draw_gameover_net(msg.get("winner")))
            return

    # ── Screen helpers ────────────────────────────────────────────────────────

    def _draw_connecting(self, text: str):
        from btl4 import WIN_W, WIN_H, C_BG, C_ACC, C_DIM
        self.screen = "connecting"
        c = self.canvas
        c.delete("all")
        c.create_rectangle(0, 0, WIN_W, WIN_H, fill=C_BG)
        c.create_text(WIN_W // 2, WIN_H // 2 - 30,
                      text="GRID WARS", font=("Courier", 36, "bold"), fill=C_ACC)
        c.create_text(WIN_W // 2, WIN_H // 2 + 30,
                      text=text, font=("Courier", 13), fill=C_DIM, justify="center")

    def _start_net(self):
        """Called when first state arrives from server."""
        self.sel_unit  = None
        self.mode      = None
        self.hl_move   = []
        self.hl_attack = []
        self.arrow_ray = []
        self.ai_queue  = []
        self.ai_anim   = None
        self.arrow_anim = None
        self.ai_busy   = False
        self.log = ["Game started. " + (
            "Your turn!" if self.gs.current_player == self._my_player
            else "Waiting for opponent..."
        )]
        self.screen = "game"

    def _draw_gameover_net(self, winner):
        """Return a callable (for after()) that shows game-over with correct label."""
        def _show():
            from btl4 import WIN_W, WIN_H, C_P1, C_P2
            self.screen = "gameover"
            c = self.canvas
            c.delete("all")
            if winner == self._my_player:
                label, col = "YOU WIN!", C_P1
            elif winner is None:
                label, col = "DRAW", "#aaaaaa"
            else:
                label, col = "YOU LOSE", C_P2
            c.create_rectangle(0, 0, WIN_W, WIN_H, fill="#040810")
            c.create_text(WIN_W // 2, 128, text=label,
                          font=("Courier", 54, "bold"), fill=col)
            self._mbtn("↺  RECONNECT", WIN_W // 2, 275,  "btn_again")
            self._mbtn("✕  EXIT",      WIN_W // 2, 345,  "btn_exit2")
            c.tag_bind("btn_again", "<Button-1>", lambda e: self._reconnect())
            c.tag_bind("btn_exit2", "<Button-1>", lambda e: self.quit())
        return _show

    def _reconnect(self):
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
        self._sock = None
        self._connected = False
        self._my_player = None
        self.gs = None
        self._connect()

    # ── Terrain rendering (use server's bridge tiles) ────────────────────────

    def _draw_tile(self, c, cx, cy, gs):
        from btl4 import TILE, TERRAIN_ROCK, TERRAIN_RIVER
        x1, y1 = cx * TILE, cy * TILE
        t = gs.grid[cx][cy]
        bridges = getattr(gs, "bridge_tiles", None) or set()
        is_bridge = (cx, cy) in bridges

        if is_bridge:
            sprite_key = "tile_bridge"
        elif t == TERRAIN_ROCK:
            sprite_key = "tile_rock"
        elif t == TERRAIN_RIVER:
            sprite_key = "tile_river"
        else:
            sprite_key = "tile_empty"

        sprite = None
        if sprite_key in self.imgs:
            img_data = self.imgs[sprite_key]
            if isinstance(img_data, list) and img_data:
                variation_data = self.tile_variations.get((cx, cy), {})
                variation_key  = sprite_key.replace("tile_", "")
                variation_index = variation_data.get(variation_key, 0)
                sprite = img_data[variation_index % len(img_data)]
            else:
                sprite = img_data
        if sprite:
            c.create_image(x1, y1, anchor="nw", image=sprite)

    # ── Input (override) ─────────────────────────────────────────────────────

    def _on_click(self, e):
        if self.screen != "game": return
        gs = self.gs
        if gs is None: return

        # Only allow input on our turn
        if gs.current_player != self._my_player: return
        if self.arrow_anim: return

        from btl4 import COLS, ROWS, TILE
        tx, ty = e.x // TILE, e.y // TILE
        if not (0 <= tx < COLS and 0 <= ty < ROWS): return

        clicked_unit = gs.get_unit_at(tx, ty)

        if clicked_unit and clicked_unit.owner == self._my_player:
            self.sel_unit  = clicked_unit
            self.mode      = "both"
            self.hl_move   = gs.reachable_tiles(clicked_unit)
            self.hl_attack = (gs.warrior_attack_tiles(clicked_unit)
                              if clicked_unit.type == "WARRIOR" else [])
            self.arrow_ray = []
            self._log(f"Selected {UNIT_STATS[clicked_unit.type]['label']}")
            return

        if self.sel_unit:
            u = gs._unit_by_id(self.sel_unit.id)
            if not u:
                self._cancel(); return

            if (tx, ty) in self.hl_move:
                self._send_action(MoveAction(u.id, tx, ty))
                return

            if (tx, ty) in self.hl_attack and u.type == "WARRIOR":
                target = gs.get_unit_at(tx, ty)
                if target and target.owner != self._my_player:
                    self._send_action(AttackAction(u.id, tx, ty))
                return

            if u.type == TYPE_ARCHER:
                ray = gs.archer_ray(u.x, u.y, tx, ty)
                if ray:
                    action = AttackAction(u.id, tx, ty)
                    self._cancel()
                    self._play_arrow(ray, C_P1,
                                     lambda a=action: self._send_action(a))
                return

    def _send_action(self, action):
        self._cancel()
        if self._sock:
            try:
                send_msg(self._sock, {"type": "action",
                                      "action": action_to_dict(action)})
            except Exception as e:
                self._log(f"Send error: {e}")
        # Optimistically log; server will send back authoritative state
        self._log(f"Action sent")

    # ── Panel override: show "opponent's turn" instead of "AI thinking" ───────

    def _draw_action_bar(self, c, gs):
        from btl4 import ROWS, TILE, WIN_H, COLS, C_DIM, C_P1, C_P2, C_ACC
        bar_y  = ROWS * TILE
        grid_w = COLS * TILE
        c.create_rectangle(0, bar_y, grid_w, WIN_H, fill="#07090f", outline="")

        if self.arrow_anim:
            c.create_text(12, bar_y + 20, text="ARROW IN FLIGHT...",
                          anchor="w", font=("Courier", 14, "bold"), fill="#ffcc00")
            return

        if gs.current_player != self._my_player:
            c.create_text(12, bar_y + 20, text="OPPONENT'S TURN...",
                          anchor="w", font=("Courier", 14, "bold"), fill=C_P2)
            c.create_text(12, bar_y + 44,
                          text=f"Actions remaining: {gs.remaining_actions}",
                          anchor="w", font=("Courier", 11), fill=C_DIM)
            return

        if self.sel_unit:
            u = self.sel_unit
            bx = 10
            self._abtn(c, bx, bar_y + 8, "CANCEL", "abtn_ca")
            c.tag_bind("abtn_ca", "<Button-1>", lambda e: self._cancel())
            utype = u.type
            if utype == TYPE_ARCHER:
                hint = f"{UNIT_STATS[utype]['label']} — Green: move | Aim & click: shoot"
            elif utype == "WARRIOR":
                hint = f"{UNIT_STATS[utype]['label']} — Green: move | Red: attack"
            else:
                hint = f"{UNIT_STATS[utype]['label']} — Click green tile to move"
            c.create_text(bx + 120, bar_y + 30, text=hint,
                          anchor="w", font=("Courier", 11), fill=C_DIM)
        else:
            c.create_text(12, bar_y + 20, text="YOUR TURN",
                          anchor="w", font=("Courier", 14, "bold"), fill=C_P1)
            c.create_text(12, bar_y + 44,
                          text=f"Actions remaining: {gs.remaining_actions}  — click one of your units",
                          anchor="w", font=("Courier", 11), fill=C_DIM)

    def _draw_panel(self, c, gs):
        """Same as original but labels opponent as 'Opponent' not 'AI'."""
        from btl4 import (COLS, TILE, PANEL_W, WIN_W, WIN_H,
                          C_PANEL, C_GRID, C_ACC, C_DIM, C_P1, C_P2,
                          C_SEL, C_HP_BG, C_HP_OK, C_HP_MID, C_HP_LOW,
                          C_LOG_NEW, C_LOG_AI, UNIT_STATS)
        px = COLS * TILE; pw = PANEL_W
        c.create_rectangle(px, 0, WIN_W, WIN_H, fill=C_PANEL, outline=C_GRID)
        c.create_text(px + pw // 2, 15, text="GRID WARS",
                      font=("Courier", 12, "bold"), fill=C_ACC)

        opp = 1 - self._my_player if self._my_player is not None else 1
        whose = ("You" if gs.current_player == self._my_player else "Opponent")
        col   = C_P1 if gs.current_player == self._my_player else C_P2
        c.create_text(px + 10, 36,
                      text=f"Turn: {whose}  [{gs.remaining_actions} action{'s' if gs.remaining_actions != 1 else ''}]",
                      anchor="w", font=("Courier", 10), fill=col)

        iy = 60
        for owner, label, ucol in [
            (self._my_player,  "YOUR UNITS",      C_P1),
            (opp,              "OPPONENT UNITS",   C_P2),
        ]:
            if owner is None: continue
            c.create_text(px + 10, iy, text=f"-- {label} --",
                          anchor="w", font=("Courier", 9), fill=ucol)
            iy += 16
            for u in gs.units:
                if u.owner != owner or not u.alive: continue
                sym = UNIT_STATS[u.type]["sym"]
                lbl = UNIT_STATS[u.type]["label"][:3]
                c.create_text(px + 10, iy,
                              text=f" {sym} {lbl}  {u.hp}/{u.max_hp} HP",
                              anchor="w", font=("Courier", 9), fill=ucol)
                iy += 14
            iy += 8

        if self.sel_unit:
            fresh = gs._unit_by_id(self.sel_unit.id)
            if fresh:
                iy = max(iy + 4, WIN_H - 210)
                c.create_text(px + 10, iy, text="-- SELECTED --",
                              anchor="w", font=("Courier", 9), fill=C_SEL)
                iy += 15
                c.create_text(px + 10, iy, text=UNIT_STATS[fresh.type]["label"],
                              anchor="w", font=("Courier", 11, "bold"), fill=C_SEL)
                iy += 14
                for k, v in [("HP",   f"{fresh.hp}/{fresh.max_hp}"),
                              ("Move", str(UNIT_STATS[fresh.type]["move"])),
                              ("Atk",  ("No" if not UNIT_STATS[fresh.type]["can_attack"]
                                        else f"Dmg {UNIT_STATS[fresh.type]['damage']}"))]:
                    c.create_text(px + 10, iy, text=f"{k:<5}{v}",
                                  anchor="w", font=("Courier", 9), fill=C_DIM)
                    iy += 13

        log_top = WIN_H - 100
        c.create_rectangle(px, log_top - 2, WIN_W, WIN_H, fill="#07090e", outline=C_GRID)
        c.create_text(px + 10, log_top + 3, text="LOG",
                      anchor="w", font=("Courier", 8), fill=C_DIM)
        recent = self.log[-5:]
        for i, entry in enumerate(recent):
            fc = C_LOG_AI if entry.startswith("Opponent") else (
                C_LOG_NEW if i == len(recent) - 1 else C_DIM)
            c.create_text(px + 10, log_top + 17 + i * 15, text=entry[:27],
                          anchor="w", font=("Courier", 8), fill=fc)

        c.create_text(px + pw // 2, WIN_H - 3, text="ESC = pause",
                      font=("Courier", 8), fill="#1a2830", anchor="s")

    # ── Disable single-player AI paths ───────────────────────────────────────

    def _ai_compute(self): pass
    def _ai_next(self):    pass
    def _ai_apply(self, _): pass

    def _start(self):
        """Disable local restart — must reconnect to server."""
        self._reconnect()

    def _continue(self): pass


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else PORT
    app = NetClient(host, port)
    app.mainloop()
