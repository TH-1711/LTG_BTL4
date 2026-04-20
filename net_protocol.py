"""
Shared network protocol for Grid Wars multiplayer.

Wire format: 4-byte big-endian length header + UTF-8 JSON body.

Message types (field "type"):
  client -> server:  {"type": "action", "action": {...}}
  server -> client:  {"type": "state",  "state": {...}, "your_player": 0|1}
                     {"type": "waiting"}          -- waiting for second player
                     {"type": "gameover", "winner": 0|1|null}
"""

import json
import struct
import socket


# ── Wire helpers ─────────────────────────────────────────────────────────────

def send_msg(sock: socket.socket, obj: dict) -> None:
    data = json.dumps(obj).encode()
    sock.sendall(struct.pack(">I", len(data)) + data)


def recv_msg(sock: socket.socket) -> dict:
    raw_len = _recv_exactly(sock, 4)
    (length,) = struct.unpack(">I", raw_len)
    return json.loads(_recv_exactly(sock, length).decode())


def _recv_exactly(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed")
        buf += chunk
    return buf


# ── Serialization ─────────────────────────────────────────────────────────────

def action_to_dict(action) -> dict:
    from btl4 import MoveAction, AttackAction
    if action is None:
        return {"kind": "pass"}
    if isinstance(action, MoveAction):
        return {"kind": "move", "unit_id": action.unit_id, "tx": action.tx, "ty": action.ty}
    if isinstance(action, AttackAction):
        return {"kind": "attack", "unit_id": action.unit_id, "tx": action.tx, "ty": action.ty}
    return {"kind": "pass"}


def dict_to_action(d: dict):
    from btl4 import MoveAction, AttackAction
    kind = d.get("kind")
    if kind == "move":
        return MoveAction(d["unit_id"], d["tx"], d["ty"])
    if kind == "attack":
        return AttackAction(d["unit_id"], d["tx"], d["ty"])
    return None


def state_to_dict(gs) -> dict:
    return {
        "units": [
            {
                "id":     u.id,
                "owner":  u.owner,
                "type":   u.type,
                "x":      u.x,
                "y":      u.y,
                "hp":     u.hp,
                "max_hp": u.max_hp,
            }
            for u in gs.units if u.alive
        ],
        "current_player":    gs.current_player,
        "remaining_actions": gs.remaining_actions,
        "grid":    [col[:] for col in gs.grid],
        "bridges": list(gs.bridge_tiles) if hasattr(gs, "bridge_tiles") else [],
    }


def dict_to_state(d: dict):
    from btl4 import GameState, Unit
    units = []
    for ud in d["units"]:
        u = Unit.__new__(Unit)
        u.id     = ud["id"]
        u.owner  = ud["owner"]
        u.type   = ud["type"]
        u.x      = ud["x"]
        u.y      = ud["y"]
        u.hp     = ud["hp"]
        u.max_hp = ud["max_hp"]
        units.append(u)
    gs = GameState(units, d["current_player"], d["remaining_actions"])
    if "grid" in d:
        gs.grid = [list(col) for col in d["grid"]]
    if "bridges" in d:
        gs.bridge_tiles = set(tuple(b) for b in d["bridges"])
    return gs
