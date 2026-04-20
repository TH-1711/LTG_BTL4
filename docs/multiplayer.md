# Grid Wars — Multiplayer Architecture

## Overview

Grid Wars multiplayer uses a **client-server model over raw TCP sockets** using Python's stdlib only (`socket`, `threading`, `queue`, `json`). The server is the single source of truth for all game state. Clients never modify state locally — they only send inputs and render what the server tells them.

```
Player 0 (client)          Server                Player 1 (client)
      |                      |                         |
      |----TCP connect------->|                         |
      |<---waiting (p=0)------|                         |
      |                      |<------TCP connect--------|
      |                      |-------waiting (p=1)----->|
      |                      |                         |
      |<---state broadcast----|---state broadcast------->|  ← game starts
      |                      |                         |
      |----action (move)----->|                         |
      |                      |  apply action            |
      |<---state broadcast----|---state broadcast------->|
      |                      |                         |
      |                      |<------action (attack)----|
      |                      |  apply action            |
      |<---state broadcast----|---state broadcast------->|
      |                      |                         |
```

---

## Wire Protocol (`net_protocol.py`)

All messages are framed with a **4-byte big-endian length prefix** followed by a UTF-8 JSON body.

```
[ 4 bytes: length ][ N bytes: JSON ]
```

This lets `recv_msg` know exactly how many bytes to read, since TCP is a stream (not a message protocol) and can deliver partial or batched data.

```python
def send_msg(sock, obj):
    data = json.dumps(obj).encode()
    sock.sendall(struct.pack(">I", len(data)) + data)

def recv_msg(sock):
    raw_len = _recv_exactly(sock, 4)
    (length,) = struct.unpack(">I", raw_len)
    return json.loads(_recv_exactly(sock, length).decode())
```

### Message Types

| Direction | Type | Purpose |
|---|---|---|
| server → client | `waiting` | Assigned player ID, waiting for opponent |
| server → client | `state` | Full game state after every action |
| server → client | `gameover` | Match result (winner: 0, 1, or null) |
| client → server | `action` | A move or attack from the active player |

---

## Server (`net_server.py`)

### Startup

1. Binds a TCP socket on `0.0.0.0:55556`
2. Calls `accept()` twice — blocks until exactly 2 clients connect
3. Sends each client a `waiting` message with their assigned player ID (0 or 1)
4. Broadcasts the initial full game state to both clients

### Main Loop

The server runs a **single-threaded loop** — no concurrency needed because only one player acts at a time:

```python
while not self.gs.is_terminal():
    active = self.gs.current_player   # 0 or 1
    msg = recv_msg(self.socks[active])  # blocks until active player sends
    action = dict_to_action(msg["action"])
    self.gs = self.engine.apply(self.gs, action)
    self._broadcast_state()           # send new state to both clients
```

`recv_msg` blocks on the active player's socket. The inactive player's socket is simply not read — their client queues any premature sends (which shouldn't happen since the UI blocks input on the opponent's turn).

### Authority

The server validates that the received action comes from the current-turn player before applying it. `GameEngine.apply()` (from `btl4.py`) handles all game rule enforcement — movement range, attack validity, damage, death, and turn switching.

### Map Ownership

The server loads the map (including any custom map file) and includes the full `grid` array and `bridge_tiles` set in every state broadcast. Clients never load a map file — they receive and use the server's map.

---

## Client (`net_client.py`)

### Threading Model

The client runs two threads:

- **Main thread** — tkinter event loop and rendering (required by tkinter)
- **Recv thread** — blocks on `recv_msg(sock)`, pushes messages into a `queue.Queue`

```python
def _recv_thread(self):
    while True:
        msg = recv_msg(self._sock)
        self._msg_queue.put(msg)   # thread-safe
```

The main thread's `_tick()` (called every 40ms via `tk.after`) drains the queue:

```python
def _tick(self):
    self._drain_queue()   # process any server messages
    if self.screen == "game":
        self._render_game()
    self.after(40, self._tick)
```

This pattern avoids threading issues with tkinter, which must only be touched from the main thread.

### Input Handling

When the local player clicks to move or attack, the client sends an `action` message to the server and waits. It does **not** apply the action locally.

```python
def _send_action(self, action):
    send_msg(self._sock, {"type": "action", "action": action_to_dict(action)})
```

The server applies the action and broadcasts the new state back. The client then updates its display from that authoritative state. This means there is a small round-trip delay between clicking and seeing the result, but the game state is always consistent.

### Turn Enforcement

The client only allows clicks when `gs.current_player == self._my_player`. The opponent's turn is blocked at the UI level. The server also enforces this independently.

---

## State Serialization (`net_protocol.py`)

Every `state` message contains the complete game state — not a diff. This keeps the protocol simple and makes reconnection trivial (just re-send the last state).

```json
{
  "type": "state",
  "your_player": 0,
  "state": {
    "units": [
      {"id": 1, "owner": 0, "type": "TANK", "x": 1, "y": 1, "hp": 10, "max_hp": 10},
      ...
    ],
    "current_player": 0,
    "remaining_actions": 2,
    "grid": [[0, 0, ...], ...],
    "bridges": [[6, 4], [6, 5], [13, 4], [13, 5]]
  }
}
```

`grid` is a 2D array of terrain values (0=empty, 1=rock, 2=river). `bridges` is a list of `[col, row]` pairs. Both are sent every message so the client can render terrain correctly without any local map files.

---

## Running Over the Internet (ngrok)

Since the server only needs one inbound TCP port, ngrok TCP tunneling works cleanly:

```
Friend's machine → ngrok cloud → your machine (port 55556) → net_server.py
```

```bash
# Your machine
venv/bin/python net_server.py
ngrok tcp 55556
# ngrok gives: tcp://0.tcp.ap.ngrok.io:XXXXX

# You (local)
venv/bin/python net_client.py 127.0.0.1 55556

# Friend (remote)
venv/bin/python net_client.py 0.tcp.ap.ngrok.io XXXXX
```

Note: connecting to your own ngrok tunnel from the same machine does not work (ngrok blocks loopback). You must connect locally via `127.0.0.1`.
