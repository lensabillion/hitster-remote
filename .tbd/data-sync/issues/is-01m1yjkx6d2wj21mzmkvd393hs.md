---
type: is
id: is-01m1yjkx6d2wj21mzmkvd393hs
title: Year-proposal chain with confidence, not a single source
kind: feature
status: open
priority: 1
version: 1
labels:
  - deck
dependencies: []
created_at: 2026-09-07T18:38:16.781Z
updated_at: 2026-09-07T18:38:16.781Z
---
No single source is good enough. Measured accuracy, on songs whose real year is known:

  Wikidata P577                    English 6/8 found, most accurate; Amharic 0/8
  Discogs (Ethiopian pressing)     Amharic: every hit correct
  Discogs (foreign pressing)       reissue dates — actively misleading
  MusicBrainz release-group        3/6 correct on famous English songs
  MusicBrainz recording f-r-d      finds data but it is usually a REMASTER date
  Deezer album.release_date        reissue dates
  YouTube title scrape             0/65 titles in the user's playlist carried a year

Chain them and score agreement rather than trusting one:
  1. Discogs filtered to country == Ethiopia   -> HIGH
  2. Wikidata P577                             -> HIGH for non-Ethiopian music
  3. MusicBrainz release-group first-release   -> MEDIUM
  4. Discogs foreign pressing / Deezer album   -> CONTEXT ONLY, never auto-accepted
  two or more agreeing within a year           -> propose
  disagreement, or only context-tier sources   -> FLAG for the human

The worksheet gains a confidence column so the human reviews the flagged rows first
instead of checking all 65 equally.
