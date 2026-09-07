---
type: is
id: is-01m1yekh687jfx0xjx26x9bcf3
title: "Answer card: 70/30 scoring with typed artist in Latin"
kind: feature
status: closed
priority: 1
version: 2
labels:
  - design
dependencies: []
created_at: 2026-09-07T17:28:10.183Z
updated_at: 2026-09-07T17:58:02.506Z
closed_at: 2026-09-07T17:58:02.506Z
close_reason: "Shipped in PR #4 and documented in docs/ARCHITECTURE.md: typed Latin answer card with 70/30 independent scoring, classic turn order, watchers still receive audio."
resolution: null
duplicate_of: null
---
Shipped. Replaces the pure timeline game with a graded answer card.

- 70 points: the singer, typed in Latin letters. Generous matching — surname alone or a
  plausible misspelling both count, because Amharic names have no agreed Latin spelling.
- 30 points: the year, earned by placing on the timeline (not by typing a year).
  Relative order stays the forgiving part of the game.
- 0 points: the song title. Captured and shown at the reveal; the user explicitly does
  not want it scored.
- Highest total after the planned rounds wins.

The halves are independent: naming the singer but misplacing the card still scores 70.

Also removes the listen-then-place gate. Answering is open from the moment the clip
starts, with a Stop control, because waiting for the clip to end made the round rigid
and punished anyone who recognised the song immediately.
