---
type: is
id: is-01m1xvveta764bgehckkd38679
title: Demote YouTube to a per-card fallback source
kind: task
status: open
priority: 3
version: 1
labels:
  - audio
dependencies: []
created_at: 2026-09-07T12:00:26.954Z
updated_at: 2026-09-07T12:00:26.954Z
---
Some songs are not on Deezer. Keep client/src/components/YouTubePlayer.jsx as a
fallback behind the <audio> path rather than deleting it.

deck.json gains an optional youtube_id per card. Cards fall back only when Deezer has
no track. Not a second engine — a per-card escape hatch.
