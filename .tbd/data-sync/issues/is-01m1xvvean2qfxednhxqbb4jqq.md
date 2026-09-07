---
type: is
id: is-01m1xvvean2qfxednhxqbb4jqq
title: Sealed challenge window for latency-fair steals
kind: feature
status: open
priority: 2
version: 1
labels:
  - server
  - game-model
dependencies: []
created_at: 2026-09-07T12:00:26.453Z
updated_at: 2026-09-07T12:00:26.453Z
---
The steal rule is what makes Hitster a game rather than a quiz — every player must form
an opinion on every card, because staying silent while an opponent fumbles is how you
lose. It is also the hardest rule to move online.

"First to shout HITSTER" is unfair across a few hundred ms of asymmetric latency
between Addis Ababa and San Francisco. Whoever has better transit wins every steal,
permanently. This needs a different mechanism, not a faster one.

Sealed challenge window:
- Active player commits a face-down placement
- 10s window opens; every other player privately marks the gap they think is right
- Everything reveals at once — placement and challenges together
- No latency advantage: nothing is first-come-first-served
- Two correct challengers: award by earliest server receipt, refund both tokens

Arguably a better rule than the original.
