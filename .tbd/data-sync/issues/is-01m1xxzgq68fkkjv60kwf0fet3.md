---
type: is
id: is-01m1xxzgq68fkkjv60kwf0fet3
title: Deck builder takes YouTube URLs, no API key required
kind: feature
status: closed
priority: 1
version: 2
labels:
  - deck
  - tooling
dependencies: []
created_at: 2026-09-07T12:37:37.126Z
updated_at: 2026-09-07T12:49:02.447Z
closed_at: 2026-09-07T12:49:02.447Z
close_reason: Deck builder shipped at server/tools/build_deck.py; YouTube oEmbed needs no API key, verified end-to-end on real Amharic songs.
resolution: null
duplicate_of: null
---
Since the deck is hand-curated anyway (years cannot be automated), the operator pastes a
YouTube URL per song. Titles come from YouTube oEmbed, which needs no API key — the
existing server already has this fallback path.

Sidesteps the YouTube Data API key entirely.

Per card, capture:
  youtube_id, title_am (Amharic), title_latin, artist_am, artist_latin,
  year (human-confirmed), deezer_track_id (optional), added_by

Opportunistically probe Deezer by Latin transliteration; attach the track id only when
the artist name actually matches.
