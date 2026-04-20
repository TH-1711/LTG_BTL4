"""
Grid Wars — authoritative game server.

Usage:
    python3 net_server.py [host] [port]

Defaults: host=0.0.0.0  port=55556

The server runs forever, accepting a new pair of players after each game ends.
"""

import socket
import threading
import sys
import traceback

from btl4 import make_initial_state, GameEngine, BRIDGE_TILES
from net_protocol import send_msg, recv_msg, dict_to_action, state_to_dict

HOST = "0.0.0.0"
PORT = 55556


class GameSession:
    """Handles one complete game between two connected clients."""

    def __init__(self, socks):
        self.socks  = socks   # [sock_p0, sock_p1]
        self.engine = GameEngine()
        self.gs     = make_initial_state()
        self.gs.bridge_tiles = BRIDGE_TILES
        self.lock   = threading.Lock()

    def run(self):
        print("[session] Starting game")
        self._broadcast_state()

        try:
            while not self.gs.is_terminal():
                active = self.gs.current_player
                try:
                    msg = recv_msg(self.socks[active])
                except (ConnectionError, OSError) as e:
                    print(f"[session] Player {active} disconnected: {e}")
                    return

                if msg.get("type") != "action":
                    continue

                action = dict_to_action(msg["action"])

                try:
                    with self.lock:
                        if self.gs.current_player != active:
                            continue
                        prev_bridges = getattr(self.gs, "bridge_tiles", BRIDGE_TILES)
                        self.gs = self.engine.apply(self.gs, action)
                        self.gs.bridge_tiles = prev_bridges
                except Exception:
                    traceback.print_exc()
                    continue

                if self.gs.is_terminal():
                    winner = self.gs.winner()
                    self._broadcast({"type": "gameover", "winner": winner})
                    print(f"[session] Game over — winner: {winner}")
                    return

                self._broadcast_state()
        finally:
            for s in self.socks:
                try:
                    s.close()
                except Exception:
                    pass
            print("[session] Closed")

    def _broadcast_state(self):
        sd = state_to_dict(self.gs)
        for player_id, sock in enumerate(self.socks):
            try:
                send_msg(sock, {"type": "state", "state": sd, "your_player": player_id})
            except Exception as e:
                print(f"[session] Error sending to player {player_id}: {e}")

    def _broadcast(self, msg: dict):
        for sock in self.socks:
            try:
                send_msg(sock, msg)
            except Exception:
                pass


def run_server(host: str, port: int):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(4)
    print(f"[server] Listening on {host}:{port}")

    while True:
        print("[server] Waiting for 2 players...")
        socks = []
        for player_id in range(2):
            conn, addr = srv.accept()
            socks.append(conn)
            print(f"[server] Player {player_id} connected from {addr}")
            send_msg(conn, {"type": "waiting", "your_player": player_id})

        print("[server] Both players connected — starting session")
        # Run each game in its own thread so the server loop is free immediately
        t = threading.Thread(target=GameSession(socks).run, daemon=True)
        t.start()


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else PORT
    run_server(host, port)
