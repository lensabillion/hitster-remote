---
type: is
id: is-01m1xvvdtrv1e0m1jd9msawd1w
title: Never send unrevealed card years to clients
kind: task
status: open
priority: 1
version: 2
spec_path: docs/project/specs/active/plan-2026-09-07-remote-group-game.md
labels:
  - server
  - security
dependencies: []
created_at: 2026-09-07T12:00:25.944Z
updated_at: 2026-09-07T12:21:38.675Z
---
Face-down placement is a physical secret in the boxed game. Remotely the server must
hold the pending card and reveal to everyone simultaneously.

Any client receiving the year before the reveal can read it in devtools. The
round:start payload carries the audio URL and card id only — never the year, and
never artist/title while Pro or Expert mode is in play.
