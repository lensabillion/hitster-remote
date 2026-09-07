---
type: is
id: is-01m1xybj81gk5tzsh4hvk65rpt
title: "Amharic sources: Deezer primary via field-scoped search, YouTube fallback"
kind: feature
status: open
priority: 0
version: 1
labels:
  - deck
  - audio
dependencies: []
created_at: 2026-09-07T12:44:11.905Z
updated_at: 2026-09-07T12:44:11.905Z
---
Correct measurement, replacing an earlier wrong one.

Deezer coverage of 24 major Amharic artists, counting only playable tracks whose
artist name actually matches:

  21/24 (87%) via field-scoped track search:  q=artist:"Teddy Afro"
   9/24 (37%) via the artist endpoint:        /search/artist + /artist/{id}/top

The artist endpoint is unreliable for these names — it answers "Teddy Afro" with
"Teddy Karo", an unrelated artist with no tracks. Field-scoped search returns 23
playable Teddy Afro tracks. The first measurement used the wrong endpoint and
wrongly concluded contemporary Amharic pop was absent.

Consequences:
- Deezer is PRIMARY (30s MP3, ~500 KB, no API key, far lighter than video —
  which matters on an Ethiopian connection)
- YouTube is the per-card fallback for the gap: Gigi, Munit Mesfin, Yehune Belay
- Never use /search/artist in this codebase
- Amharic-script search returns nothing on Deezer; search by Latin
  transliteration and carry Amharic strings separately for display

Deck rows already carry both deezer_track_id and youtube_id, so only the
priority order changes.
