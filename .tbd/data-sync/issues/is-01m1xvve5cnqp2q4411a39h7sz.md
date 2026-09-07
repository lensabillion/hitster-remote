---
type: is
id: is-01m1xvve5cnqp2q4411a39h7sz
title: Client audio player with next-track prefetch
kind: task
status: closed
priority: 2
version: 3
spec_path: docs/project/specs/active/plan-2026-09-07-remote-group-game.md
labels:
  - client
  - audio
dependencies: []
created_at: 2026-09-07T12:00:26.284Z
updated_at: 2026-09-07T17:58:02.692Z
closed_at: 2026-09-07T17:58:02.691Z
close_reason: "Shipped: server resolves a fresh Deezer preview per round (15-min expiry), client plays it via AudioClip with Stop/Replay, re-sent on reconnect."
resolution: null
duplicate_of: null
---
Swap the hidden YouTube iframe for an <audio> element fed by resolved Deezer previews.

- Server broadcasts track id + startAt timestamp; each client plays its own copy
- Do NOT stream audio peer-to-peer. Sub-second drift is invisible in this game
- Prefetch the NEXT card's MP3 during the current placement. 500 KB, costs nothing to
  hold, and is the difference between a smooth turn and a ten-second stall
- Replay-clip button with no penalty — remote players need it
- Lobby reminder to wear headphones if players are on a parallel voice call, or the
  mics echo the music at each other
