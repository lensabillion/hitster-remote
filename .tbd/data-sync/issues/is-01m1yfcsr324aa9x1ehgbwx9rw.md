---
type: is
id: is-01m1yfcsr324aa9x1ehgbwx9rw
title: "Turn-based play: one song, one answerer, everyone listens"
kind: feature
status: open
priority: 1
version: 1
labels:
  - design
dependencies: []
created_at: 2026-09-07T17:41:58.147Z
updated_at: 2026-09-07T17:41:58.147Z
---
Shipped, replacing simultaneous shadow placement.

- A song plays and ONLY the player whose turn it is answers it. The server rejects
  out-of-turn submissions with a clear message.
- Everyone else hears the same clip — the audio cue is sent to every socket, and the
  watcher's screen says whose turn it is and that their song is coming.
- The turn passes to the next seated player each round.
- rounds_planned is rounded to a whole number of turns each, so nobody early in the seat
  order gets an extra song.

Why the reversal: the design doc argued from board-game downtime theory that turn-based
play would mean N-1 idle players. Real play showed the opposite problem — everyone
answering every round did not feel like a turn-taking game at all. The user's call, and
the right one.

Open question for later: whether watchers should get anything to do beyond listening.
Do NOT add it unprompted; the user rejected exactly that once.
