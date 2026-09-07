---
type: is
id: is-01m1xwvnndeqpep59s32ca7fdx
title: Write and review the game design doc
kind: task
status: in_progress
priority: 0
version: 4
spec_path: docs/project/specs/active/plan-2026-09-07-remote-group-game.md
labels:
  - design
  - docs
dependencies: []
created_at: 2026-09-07T12:18:02.541Z
updated_at: 2026-09-07T12:21:39.171Z
---
Before implementation: a DESIGN.md covering what makes this fun as a REMOTE group
game, not merely a faithful Hitster port.

The core risk: Hitster is turn-based. One player places, everyone else waits. Around a
table that idle time is social — people talk, heckle, watch the card. On a video call
idle time is dead air, and dead air is how remote games die.

Must cover:
- What every non-active player is doing during every turn
- Group scaling (this must work for 3-6 friends, not just 2)
- Latency fairness
- Session shape: length, drop-in/drop-out, what happens when someone's connection dies
- Which prior art to borrow from (Jackbox, Gartic Phone, skribbl.io)

User reviews the doc before any implementation starts.
