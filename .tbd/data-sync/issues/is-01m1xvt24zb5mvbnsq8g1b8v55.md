---
type: is
id: is-01m1xvt24zb5mvbnsq8g1b8v55
title: Verify Deezer CDN reaches Ethiopia before building on it
kind: task
status: open
priority: 0
version: 2
labels:
  - research
  - blocker
dependencies:
  - type: blocks
    target: is-01m1xvt2h1xv7n957w1t7bppv1
created_at: 2026-09-07T11:59:41.214Z
updated_at: 2026-09-07T12:00:56.887Z
---
The entire audio architecture assumes Deezer's preview CDN (cdnt-preview.dzcdn.net)
is reachable with usable throughput from Addis Ababa. Verified from the US only.

Every other finding has a fallback. This one does not — if it fails we fall back to
YouTube (heavier, geo-variable) or self-hosted MP3s (legally murkier).

Test: have the player in Ethiopia open a live preview URL in a browser and report
whether it plays and how fast it starts. Resolve a fresh URL first — they expire in
15 minutes (see the preview-expiry issue).

Blocks: committing to Deezer as the primary source.
