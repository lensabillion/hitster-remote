---
type: is
id: is-01m1xvvf4v7q1794xhy10hhber
title: "Resilience pass: reconnect, resync, generous timers"
kind: task
status: open
priority: 3
version: 1
labels:
  - server
  - resilience
dependencies: []
created_at: 2026-09-07T12:00:27.291Z
updated_at: 2026-09-07T12:00:27.291Z
---
- Full state resync on reconnect (depends on UUID identity)
- Host migration keyed off UUID
- Generous, host-controlled pacing rather than hard countdown timers
- Graceful handling of a player who never comes back mid-turn
- Test with a deliberately throttled/interrupted connection
