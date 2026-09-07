---
type: is
id: is-01m1xvvdtrv1e0m1jd9msawd1w
title: Never send unrevealed card years to clients
kind: task
status: closed
priority: 1
version: 3
spec_path: docs/project/specs/active/plan-2026-09-07-remote-group-game.md
labels:
  - server
  - security
dependencies: []
created_at: 2026-09-07T12:00:25.944Z
updated_at: 2026-09-07T16:58:34.938Z
closed_at: 2026-09-07T16:58:34.938Z
close_reason: "Shipped in PR #4: Hitster game model in rooms.py, and per-viewer serialization asserted by tests to withhold unrevealed years."
resolution: null
duplicate_of: null
---
Face-down placement is a physical secret in the boxed game. Remotely the server must
hold the pending card and reveal to everyone simultaneously.

Any client receiving the year before the reveal can read it in devtools. The
round:start payload carries the audio URL and card id only — never the year, and
never artist/title while Pro or Expert mode is in play.
