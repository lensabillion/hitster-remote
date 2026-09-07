---
type: is
id: is-01m1xvveta764bgehckkd38679
title: Demote YouTube to a per-card fallback source
kind: task
status: closed
priority: 3
version: 2
labels:
  - audio
dependencies: []
created_at: 2026-09-07T12:00:26.954Z
updated_at: 2026-09-07T17:58:16.388Z
closed_at: 2026-09-07T17:58:16.387Z
close_reason: "Verified done: audio_for() tries Deezer first and falls back to the card's youtube_id; AudioClip drives the IFrame API on that path."
resolution: null
duplicate_of: null
---
Some songs are not on Deezer. Keep client/src/components/YouTubePlayer.jsx as a
fallback behind the <audio> path rather than deleting it.

deck.json gains an optional youtube_id per card. Cards fall back only when Deezer has
no track. Not a second engine — a per-card escape hatch.
