---
type: is
id: is-01m1xvvefxp254apvfj1fmax4n
title: "Token economy: skip, buy-a-card, earn-by-naming"
kind: task
status: open
priority: 2
version: 2
spec_path: docs/project/specs/active/plan-2026-09-07-remote-group-game.md
labels:
  - server
  - game-model
dependencies: []
created_at: 2026-09-07T12:00:26.620Z
updated_at: 2026-09-07T12:21:37.680Z
---
- Earn: name artist AND title on your turn -> +1 token, even if placement is wrong
- Spend 1: skip the current song, draw a fresh one
- Spend 3: take the top card placed free, no guess (V3 then skips your next turn)
- Spend 1: challenge an opponent (see sealed challenge window)
- Cap 5 tokens; Original starts at 2, Pro at 5, Expert at 3

Ship Original first. Pro/Expert need free-text artist+title matching across two
languages and transliterated Amharic titles — genuinely hard, defer it.
