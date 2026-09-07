---
type: is
id: is-01m1xvvdga88wm67c0dy1h1rsc
title: Rewrite room state as the Hitster game model
kind: feature
status: open
priority: 1
version: 8
spec_path: docs/project/specs/active/plan-2026-09-07-remote-group-game.md
labels:
  - server
  - game-model
dependencies:
  - type: blocks
    target: is-01m1xvvdnjaxxs78ph51b6khp6
  - type: blocks
    target: is-01m1xvve02ewe0a3ewh6pbz51g
  - type: blocks
    target: is-01m1xvvean2qfxednhxqbb4jqq
  - type: blocks
    target: is-01m1xvvefxp254apvfj1fmax4n
  - type: blocks
    target: is-01m1xvven4afanzyph2aeqbctm
  - type: blocks
    target: is-01m1xx1mfh10ysrn5t35nsmcyh
created_at: 2026-09-07T12:00:25.609Z
updated_at: 2026-09-07T12:21:39.330Z
---
The current server plays a different game: everyone races to type an artist, scored on
reaction time. Hitster is turn-based and positional with no clock at its core.

Replace room state with:
- timeline: ordered list of cards per player
- tokens: int per player (Original starts at 2, cap 5)
- seat order + turn cursor
- phase enum: lobby | playing | placing | challenging | revealing | over
- win condition: first to 10 correctly placed cards

Depends on durable UUID player identity.
