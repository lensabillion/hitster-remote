---
type: is
id: is-01m1xvvdnjaxxs78ph51b6khp6
title: Placement validator including the same-year rule
kind: task
status: closed
priority: 1
version: 4
spec_path: docs/project/specs/active/plan-2026-09-07-remote-group-game.md
labels:
  - server
  - game-model
dependencies: []
created_at: 2026-09-07T12:00:25.777Z
updated_at: 2026-09-07T12:49:02.774Z
closed_at: 2026-09-07T12:49:02.774Z
close_reason: Placement validator implemented in game.py with 20 tests covering same-year ties at both edges, runs of identical years, and all resolve_round branches.
resolution: null
duplicate_of: null
---
A card is correctly placed if its year falls within the gap it was inserted into.

The rule that is easy to get wrong: if the card's year equals the year of an adjacent
card already on the timeline, EITHER side of that card counts as correct. Official
wording: "If the year matches an existing card, you can place it just before or just
after that card, and it will still count as correct."

Needs unit tests: empty timeline, single card, duplicate years, ties at both ends.
