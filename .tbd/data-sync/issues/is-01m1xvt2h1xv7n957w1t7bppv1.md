---
type: is
id: is-01m1xvt2h1xv7n957w1t7bppv1
title: Resolve Deezer preview URLs server-side at round start
kind: feature
status: open
priority: 0
version: 2
labels:
  - audio
dependencies:
  - type: blocks
    target: is-01m1xvve5cnqp2q4411a39h7sz
created_at: 2026-09-07T11:59:41.600Z
updated_at: 2026-09-07T12:00:58.198Z
---
Deezer preview URLs are HMAC-signed and expire in exactly 15 minutes. Measured:

  exp=1788782138  ->  2026-09-07 11:55:38 UTC
  fetched at      ->  2026-09-07 11:40:55 UTC
  fresh fetch     ->  expires in 15.0 minutes

Storing playable URLs in deck.json produces a game that works in testing and dies
about twenty minutes into the first real session.

- deck.json stores Deezer track IDs, never URLs
- Server endpoint resolves id -> fresh preview URL on demand
- Resolve at round start; include the URL in the round:start payload
- Handle resolution failure by skipping to the next card, not hanging the turn
