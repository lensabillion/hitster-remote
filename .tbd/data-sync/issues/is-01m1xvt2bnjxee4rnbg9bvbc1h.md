---
type: is
id: is-01m1xvt2bnjxee4rnbg9bvbc1h
title: Replace socket-id player keys with durable UUID identity
kind: feature
status: open
priority: 0
version: 3
labels:
  - server
  - resilience
dependencies:
  - type: blocks
    target: is-01m1xvvdga88wm67c0dy1h1rsc
  - type: blocks
    target: is-01m1xvvf4v7q1794xhy10hhber
created_at: 2026-09-07T11:59:41.429Z
updated_at: 2026-09-07T12:00:58.355Z
---
server/rooms.py keys players by socket.io sid. A refresh, a sleep, or a dropped
connection destroys the player and their timeline.

In the current speed-quiz that costs a few points. In Hitster it ends a 40-minute
game, and the player most likely to drop is the one on Ethiopian connectivity.

- Issue each player a UUID, persist in localStorage, key the room off it
- Treat the socket id as a mutable attachment that can be re-bound on reconnect
- Full state resync on rejoin: timeline, tokens, turn cursor, current phase
- Host migration keyed off UUID, not sid

Small change now, a rewrite once the game model lands. Do this first.
