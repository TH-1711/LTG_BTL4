"""
Grid Wars — authoritative game server.

Usage:
    python3 net_server.py [host] [port]

Defaults: host=0.0.0.0  port=55555

Flow:
  1. Wait for exactly 2 TCP connections.
  2. Assign player 0 to first connector, player 1 to second.
  3. Send each client a "waiting" message, then a "state" message when both are ready.
  4. Loop: receive action from the current-turn player, validate, apply, broadcast new state.
  5. On game-over broadcast "gameover" and close.
"""

import socket
import threading
import sys

from btl4 import make_initial_state, GameEngine, PLAYER_HUMAN, PLAYER_AI, BRIDGE_TILES
from net_protocol import send_msg, recv_msg, action_to_dict, dict_to_action, state_to_dict

HOST = "0.0.0.0"
PORT = 55556


class GameServer:
    def __init__(self, host: str, port: int):
        self.host   = host
        self.port   = port
        self.engine = GameEngine()
        self.gs     = make_initial_state()
        self.gs.bridge_tiles = BRIDGE_TILES
        self.socks  = [None, None]   # socks[player_id]
        self.lock   = threading.Lock()

    def run(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(2)
        print(f"[server] Listening on {self.host}:{self.port}")

        for player_id in (0, 1):
            conn, addr = srv.accept()
            self.socks[player_id] = conn
            print(f"[server] Player {player_id} connected from {addr}")
            send_msg(conn, {"type": "waiting", "your_player": player_id})

        print("[server] Both players connected — starting game")
        self._broadcast_state()

        # Player 0 goes first (PLAYER_HUMAN == 0 in btl4)
        # Receive actions in a simple single-threaded loop; only the active
        # player's socket is read each iteration.
        try:
            while not self.gs.is_terminal():
                active = self.gs.current_player
                try:
                    msg = recv_msg(self.socks[active])
                except (ConnectionError, OSError) as e:
                    print(f"[server] Player {active} disconnected: {e}")
                    break

                print(f"[server] Received from player {active}: type={msg.get('type')}")
                if msg.get("type") != "action":
                    continue

                action = dict_to_action(msg["action"])
                print(f"[server] Action: {msg['action']}")

                try:
                    with self.lock:
                        if self.gs.current_player != active:
                            continue
                        prev_bridges = getattr(self.gs, "bridge_tiles", BRIDGE_TILES)
                        self.gs = self.engine.apply(self.gs, action)
                        self.gs.bridge_tiles = prev_bridges
                except Exception as e:
                    import traceback; traceback.print_exc()
                    continue

                if self.gs.is_terminal():
                    winner = self.gs.winner()
                    self._broadcast({"type": "gameover", "winner": winner})
                    print(f"[server] Game over — winner: {winner}")
                    break

                self._broadcast_state()
        finally:
            for s in self.socks:
                if s:
                    try:
                        s.close()
                    except Exception:
                        pass
            srv.close()
            print("[server] Closed")

    def _broadcast_state(self):
        sd = state_to_dict(self.gs)
        for player_id, sock in enumerate(self.socks):
            if sock:
                try:
                    send_msg(sock, {"type": "state", "state": sd, "your_player": player_id})
                except Exception as e:
                    print(f"[server] Error sending to player {player_id}: {e}")

    def _broadcast(self, msg: dict):
        for sock in self.socks:
            if sock:
                try:
                    send_msg(sock, msg)
                except Exception:
                    pass


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else PORT
    GameServer(host, port).run()
