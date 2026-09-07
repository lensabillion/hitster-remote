---
type: is
id: is-01m1xvvezk6njpmmbdks8xm2nj
title: Deploy the server reachable from both continents
kind: task
status: open
priority: 3
version: 1
labels:
  - infra
dependencies: []
created_at: 2026-09-07T12:00:27.122Z
updated_at: 2026-09-07T12:00:27.122Z
---
Fly.io or Railway on a small instance is plenty. The server only ever moves JSON —
audio comes from Deezer's CDN directly to each client.

- Pick a region sensibly between the two players, or accept US-based
- WebSocket support required (socket.io)
- Test on a deliberately throttled connection before calling it done
