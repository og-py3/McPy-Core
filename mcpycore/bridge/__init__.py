"""
mcpycore.bridge — WebSocket bridge server.

Exposes a running MinecraftClient session over a WebSocket connection so that
any programming language can drive a Minecraft bot without reimplementing the
full protocol.

Start the bridge::

    python -m mcpycore.bridge                   # default port 25580
    python -m mcpycore.bridge --port 25580

Then connect from any language SDK (see sdks/ in the repo root), or directly
with any WebSocket client using the JSON message protocol below.

Message format (client → bridge)
---------------------------------
All messages are JSON objects with an ``"action"`` field.

  connect
    { "action": "connect", "host": "...", "port": 25565, "username": "...",
      "protocol": 775, "access_token": null,
      "humanize": true }              # humanize = true/false or config dict

  disconnect
    { "action": "disconnect" }

  chat
    { "action": "chat", "message": "Hello!" }

  move
    { "action": "move", "x": 0, "y": 64, "z": 0, "yaw": 0, "pitch": 0 }

  look
    { "action": "look", "yaw": 45.0, "pitch": -10.0 }

  swing_arm
    { "action": "swing_arm", "hand": 0 }

  set_held_slot
    { "action": "set_held_slot", "slot": 0 }

  respawn
    { "action": "respawn" }

Message format (bridge → client)
----------------------------------
Events pushed to the WebSocket as they occur.

  { "event": "connected",    "version": "1.21.11",  "protocol": 775 }
  { "event": "disconnected", "reason": "..." }
  { "event": "error",        "message": "..." }
  { "event": "chat",         "message": "...", "sender": "..." }
  { "event": "system_chat",  "content": "...", "overlay": false }
  { "event": "health",       "health": 20.0, "food": 20, "saturation": 5.0 }
  { "event": "position",     "x": 0.0, "y": 64.0, "z": 0.0,
                              "yaw": 0.0, "pitch": 0.0 }
  { "event": "spawn",        "x": 0.0, "y": 64.0, "z": 0.0 }
  { "event": "login",        "entity_id": 1, "game_mode": 0 }
  { "event": "keepalive",    "latency_ms": 50.0 }
  { "event": "death" }
  { "event": "respawn",      "data": "<base64>" }
  { "event": "block_update", "x": 0, "y": 0, "z": 0, "state_id": 0 }
  { "event": "chunk_load",   "cx": 0, "cz": 0 }
  { "event": "chunk_unload", "cx": 0, "cz": 0 }
  { "event": "title",        "text": "..." }
  { "event": "action_bar",   "text": "..." }
  { "event": "game_mode",    "game_mode": 0 }
  { "event": "time_update",  "world_age": 0, "time_of_day": 0 }
  { "event": "remove_entities", "ids": [1, 2, 3] }
  { "event": "transfer",     "host": "...", "port": 25565 }
"""
from mcpycore.bridge.server import BridgeServer

__all__ = ["BridgeServer"]
