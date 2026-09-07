---
type: is
id: is-01m1ygpyxh1wwgw486z8s477sz
title: "Decide how a timeline starts: seed card, empty, or fixed anchor"
kind: task
status: open
priority: 1
version: 1
labels:
  - design
dependencies: []
created_at: 2026-09-07T18:04:59.697Z
updated_at: 2026-09-07T18:04:59.697Z
---
User asked why every player begins with one random song already on their timeline.

Current behaviour: start_game deals each player ONE random card from the deck, face up,
as their anchor. Each player gets a DIFFERENT card.

Why an anchor exists at all: is_correct_placement([], card, 0) is True — on an empty
timeline every placement is trivially correct, so round 1 would hand out a free 30 points
with no decision made.

Problems with the current version:
- Different anchors mean different information per player, decided by shuffle luck
- It consumes one deck card per player, which matters while the deck is small

Options discussed:
(a) keep one random card each — simplest, faithful to physical Hitster
(b) empty timeline, first placement scores 0 for the year — honest, no free points
(c) the SAME anchor card for everyone — removes the luck, one-line change
(d) a fixed non-song year marker (e.g. 1980) on every timeline — identical for all,
    costs no deck card, matches the user's "offer some fixed date as a starting point"

Leaning (d), possibly with faint decade gridlines behind the rail as pure visual
scaffolding (no rule change). Needs the user's call before building.
