---
type: is
id: is-01m1xyzcttw4gf6whwf174dekv
title: "Never require typed answers: Amharic input rules out free text"
kind: task
status: closed
priority: 1
version: 2
labels:
  - design
  - ui
dependencies: []
created_at: 2026-09-07T12:55:01.722Z
updated_at: 2026-09-07T17:28:10.113Z
closed_at: 2026-09-07T17:28:10.113Z
close_reason: "Reversed by the user: they want typed answers after all, in Latin script, which resolves the Ge'ez-keyboard objection. Implemented as a 70/30 answer card with generous transliteration matching (matching.player_artist_matches)."
resolution: null
duplicate_of: null
---
Raised by the user while reviewing the first build: "how am I gonna type my answer?"

In Original mode nobody types — tapping the gap IS the answer. That stays true and is
the reason the game works one-handed on a call.

Typing only appears in Pro/Expert, where you also name artist and title. For an Amharic
deck that is not viable:
- Typing Ge'ez requires a keyboard most players do not have installed
- Latin transliteration has no agreed spelling: Tezeta / Tizita / Tezeta, Yekermo /
  Yikermo. Fuzzy matching cannot fairly adjudicate that
- It penalises the player with the worse keyboard, not the worse music knowledge

So if naming ships at all, it is MULTIPLE CHOICE — four artist names, tap one. Same
information, no keyboard, latency-fair, and it works identically in both scripts.

Blocks any Pro/Expert work.
