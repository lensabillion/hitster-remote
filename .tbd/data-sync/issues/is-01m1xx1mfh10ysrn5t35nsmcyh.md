---
type: is
id: is-01m1xx1mfh10ysrn5t35nsmcyh
title: "Simultaneous shadow placement: every player places every round"
kind: feature
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-09-07-remote-group-game.md
labels:
  - design
  - game-model
dependencies:
  - type: blocks
    target: is-01m1xx1mt60d37s8vh2bdgnx0n
created_at: 2026-09-07T12:21:17.937Z
updated_at: 2026-09-07T16:58:34.772Z
closed_at: 2026-09-07T16:58:34.772Z
close_reason: "Shipped in PR #4: durable UUID identity with reconnect (verified by full page reload mid-game), and simultaneous shadow placement resolving in resolve_round."
resolution: null
duplicate_of: null
---
THE core design change. Converts N-1 idle players into N engaged players.

Every round every player privately places the card:
- Active player's placement is real: correct = keeps the card, wrong = loses it
- Everyone else's is a shadow guess on their own timeline:
    correct                        -> +1 token
    correct AND active was wrong   -> steal the card

All placements sealed until reveal, so nothing is first-come-first-served and no
latency advantage exists. At most one card enters a timeline per round, so the card
economy does not accelerate with group size.

From the player's seat the instruction is always the same — "where does this go?" —
only the stakes change. No new rule to learn.
