---
type: is
id: is-01m1xvvd5qr2kcz3h9e3159hwk
title: Build the deck-builder CLI
kind: feature
status: open
priority: 1
version: 2
labels:
  - deck
  - tooling
dependencies:
  - type: blocks
    target: is-01m1xvvdb1n1mbj814h4zz9a9c
created_at: 2026-09-07T12:00:25.271Z
updated_at: 2026-09-07T12:00:57.047Z
---
Release years cannot be automated. MusicBrainz returned three different answers for
one of the best-documented singles in pop history:

  Billie Jean | Michael Jackson | first-release-date = 1985
  Billie Jean | Michael Jackson | first-release-date = None
  Billie Jean | Michael Jackson | first-release-date = 1982

Deezer's album.release_date fails from the other side: searching "Yesterday" returns
it off "1 (Remastered)", dating the Beatles to 2000. Reissues, remasters and
compilations poison every automated source. This is why Jumbo hand-curates 300 cards.

A run-once offline CLI:
- Search Deezer for a song, show candidate tracks, pick one
- Pull year candidates from Deezer album.release_date and MusicBrainz first-release-date
- Flag disagreement loudly; require human confirmation of the real year
- Emit deck.json: {deezer_track_id, artist, title, year, tags[]}

Track IDs only — never preview URLs.
