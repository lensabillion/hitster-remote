---
type: is
id: is-01m1ygpz2v299mtby70vwb308s
title: Grow the deck and handle exhaustion as player count rises
kind: task
status: open
priority: 1
version: 1
labels:
  - deck
dependencies: []
created_at: 2026-09-07T18:04:59.867Z
updated_at: 2026-09-07T18:04:59.867Z
---
The deck is a FIXED curated pool in SQLite, shuffled per game. Not fetched from an API at
play time — the same songs recur every session in a different order.

Current size is 16. Constraint: seed cards + rounds must fit inside the deck.
  cards_needed = players + rounds_planned
  6 players x 12 rounds needs 18 cards; 16 is already too few for that table.

With 16 cards and 12 rounds, a single game shows ~75% of the deck, so repeats are obvious
by the second session.

Work:
- Curate toward 80-120 cards (see hitster-g1dh)
- Make the round planner degrade honestly when the deck is thin, rather than silently
  shortening the game
- Consider a per-game filter (decade, artist) once the pool is big enough to support it
