---
type: is
id: is-01m1xvven4afanzyph2aeqbctm
title: Remove speed-quiz scoring
kind: chore
status: closed
priority: 3
version: 2
labels:
  - cleanup
dependencies: []
created_at: 2026-09-07T12:00:26.788Z
updated_at: 2026-09-07T17:58:16.228Z
closed_at: 2026-09-07T17:58:16.228Z
close_reason: "Verified done: score_guess, parse_artist_song and fuse.js are all gone; nothing in the tree references speed-quiz scoring."
resolution: null
duplicate_of: null
---
Dead once the timeline game lands. Wrong game.

- server/game.py: score_guess(), the speed-bonus logic
- server/game.py: parse_artist_song() — Deezer returns clean structured fields
- client: fuse.js dependency and the guess-matching path
- server/main.py: round auto-advance timers, replaced by turn order + challenge window

Keep fuzzy_match() — it becomes relevant again for Pro/Expert naming.
