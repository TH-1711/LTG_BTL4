import tkinter as tk

from core.constants import *
from core.state import GameState
from core.models import MoveAction, AttackAction

from core.state import make_initial_state

from core.terrain import BRIDGE_TILES

from ai.mcts import MCTSAI
from engine.game_engine import GameEngine
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

        import os
        self.imgs = {}
        for name in ["tile_empty","tile_rock","tile_river","tile_bridge",
                    "tank_p1","tank_p2","warrior_p1","warrior_p2",
                    "archer_p1","archer_p2","arrow"]:
            path = f"assets/{name}.png"
            if os.path.exists(path):
                self.imgs[name] = tk.PhotoImage(file=path)

        self._draw_menu()
        self._tick()

    # ─────────────────────────────────────────────────────────────────────────
    # MAIN LOOP
    # ─────────────────────────────────────────────────────────────────────────
    def _tick(self):
        if self.screen == "game":
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
        if (self.mode == "attack" and self.sel_unit and
                self.sel_unit.type == TYPE_ARCHER and self.arrow_ray):
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
        x2, y2 = x1+TILE, y1+TILE
        t = gs.grid[cx][cy]

        is_bridge = (cx, cy) in BRIDGE_TILES

        if is_bridge:
            # ASSET: replace with bridge/ford image
            c.create_rectangle(x1,y1,x2,y2, fill=C_BRIDGE,  outline=C_GRID, width=1)
            c.create_text(x1+TILE//2, y1+TILE//2, text="╫",
                          font=("Courier",16), fill=C_BRIDGE_S)
        
        elif t == TERRAIN_ROCK:
            # ASSET: tile_rock.png
            c.create_rectangle(x1,y1,x2,y2, fill=C_ROCK,  outline=C_GRID, width=1)
            c.create_text(x1+TILE//2, y1+TILE//2, text="▲",
                          font=("Courier",15), fill=C_ROCK_S)
        elif t == TERRAIN_RIVER:
            # ASSET: tile_river.png
            c.create_rectangle(x1,y1,x2,y2, fill=C_RIVER, outline=C_GRID, width=1)
            c.create_text(x1+TILE//2, y1+TILE//2, text="≈",
                          font=("Courier",14), fill=C_RIVER_S)
        else:
            # ASSET: tile_empty.png
            c.create_rectangle(x1,y1,x2,y2, fill=C_TILE,  outline=C_GRID, width=1)

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

        pad = 6
        ow  = 3 if is_sel else 1
        oc  = C_SEL if is_sel else col
        # ASSET: c.create_image(cx,cy, image=self.imgs[f"{u.type.lower()}_p{u.owner+1}"])
        c.create_oval(ux+pad,uy+pad,ux+TILE-pad,uy+TILE-pad,
                      fill="#080e18", outline=oc, width=ow)
        c.create_text(cx, cy-2, text=UNIT_STATS[u.type]["sym"],
                      font=("Courier",15,"bold"), fill=col)

        # HP bar
        bw = TILE-10
        bx, by2 = ux+5, uy+TILE-9
        ratio = u.hp/u.max_hp
        hc = C_HP_OK if ratio>0.6 else (C_HP_MID if ratio>0.3 else C_HP_LOW)
        c.create_rectangle(bx,by2,bx+bw,by2+5, fill=C_HP_BG, outline="")
        c.create_rectangle(bx,by2,bx+int(bw*ratio),by2+5, fill=hc, outline="")
        c.create_text(cx, uy+TILE-16, text=str(u.hp),
                      font=("Courier",8), fill=C_DIM)

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
            r = 6
            # ASSET: c.create_image(px2,py2, image=self.imgs["arrow"])
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
            self._abtn(c, bx,      bar_y+8, "MOVE",   "abtn_mv")
            c.tag_bind("abtn_mv","<Button-1>",lambda e: self._mode_move())
            if UNIT_STATS[u.type]["can_attack"]:
                self._abtn(c, bx+114, bar_y+8, "ATTACK", "abtn_at")
                c.tag_bind("abtn_at","<Button-1>",lambda e: self._mode_attack())
            self._abtn(c, bx+228, bar_y+8, "CANCEL", "abtn_ca")
            c.tag_bind("abtn_ca","<Button-1>",lambda e: self._cancel())

            if self.mode == "move":
                hint = "Click a green tile to move"
            elif self.mode == "attack" and u.type == TYPE_ARCHER:
                hint = "Aim with mouse — click to fire arrow"
            elif self.mode == "attack":
                hint = "Click an adjacent enemy tile"
            else:
                hint = f"Selected: {UNIT_STATS[u.type]['label']}  ({u.hp}/{u.max_hp} HP)   — choose action"
            c.create_text(bx+350, bar_y+30, text=hint, anchor="w",
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
        if (self.mode == "attack" and self.sel_unit and
                self.sel_unit.type == TYPE_ARCHER):
            tx, ty = e.x//TILE, e.y//TILE
            u = self.gs._unit_by_id(self.sel_unit.id)
            if u and self.gs.in_bounds(tx, ty):
                self.arrow_ray = self.gs.archer_ray(u,u.x, u.y, tx, ty)

    def _on_click(self, e):
        if self.screen != "game": return
        gs = self.gs
        if gs.current_player != PLAYER_HUMAN: return
        if self.ai_anim or self.arrow_anim: return

        tx, ty = self._tile_at(e)
        if tx is None: return

        if self.mode == "move":
            if (tx,ty) in self.hl_move:
                self._apply_human(MoveAction(self.sel_unit.id, tx, ty))
            return

        if self.mode == "attack":
            u = gs._unit_by_id(self.sel_unit.id)
            if not u: self._cancel(); return
            if u.type == TYPE_WARRIOR:
                if (tx,ty) in self.hl_attack:
                    t = gs.get_unit_at(tx, ty)
                    if t and t.owner==PLAYER_AI:
                        self._apply_human(AttackAction(u.id, tx, ty))
                    else:
                        self._log("No enemy there.")
            elif u.type == TYPE_ARCHER:
                ray = gs.archer_ray(u, u.x, u.y, tx, ty)
                if ray:
                    action = AttackAction(u.id, tx, ty)
                    self._cancel()
                    self._play_arrow(ray, C_P1, lambda: self._apply_human(action))
                else:
                    self._log("Arrow blocked immediately.")
            return

        # Select unit
        clicked = gs.get_unit_at(tx, ty)
        if clicked and clicked.owner==PLAYER_HUMAN:
            self.sel_unit  = clicked
            self.mode      = None
            self.hl_move   = []; self.hl_attack = []; self.arrow_ray = []
            self._log(f"Selected {UNIT_STATS[clicked.type]['label']}")

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

    def _mode_move(self):
        if not self.sel_unit: return
        u = self.gs._unit_by_id(self.sel_unit.id)
        if not u: return
        self.mode = "move"
        self.hl_move = self.gs.reachable_tiles(u)
        self.hl_attack = []; self.arrow_ray = []

    def _mode_attack(self):
        if not self.sel_unit: return
        u = self.gs._unit_by_id(self.sel_unit.id)
        if not u: return
        self.mode = "attack"
        self.hl_move = []; self.arrow_ray = []
        self.hl_attack = self.gs.warrior_attack_tiles(u) if u.type==TYPE_WARRIOR else []

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
