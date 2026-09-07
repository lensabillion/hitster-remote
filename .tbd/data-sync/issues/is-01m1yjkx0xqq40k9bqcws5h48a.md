---
type: is
id: is-01m1yjkx0xqq40k9bqcws5h48a
title: Use Discogs as the primary year source, filtered to Ethiopian pressings
kind: feature
status: open
priority: 0
version: 1
labels:
  - deck
  - research
dependencies: []
created_at: 2026-09-07T18:38:16.605Z
updated_at: 2026-09-07T18:38:16.605Z
---
MEASURED FINDING. Discogs is the only source that carries ORIGINAL Ethiopian pressings,
and filtering by country cleanly separates originals from reissues.

  Mahmoud Ahmed — Tezeta
    Ethiopian pressings : [1974, 1975]      <- Amha Records, the original
    other countries     : [1997, 1997, 1997, 1999, 1999, 2003]   <- Ethiopiques reissues
    -> pick 1974, CORRECT

  Alemayehu Eshete — Tashamanaletch (actual ~1969)
    Ethiopian pressings : none
    other countries     : [2007, 2013, 2021]
    -> no Ethiopian pressing, so FLAG rather than guess

The rule: an Ethiopian pressing is trustworthy; its absence means flag for human review.
Never fall back to a foreign pressing silently — that is precisely how streaming metadata
dates 1970s music to 1997.

Coverage measured: Discogs produced a year for 6/10 Amharic tracks, and every
Ethiopian-pressing hit was right.

Discogs search works with NO token (~25 req/min; a free token raises it to 60).

Build into the deck builder:
- query /database/search?artist=&track=&type=release
- partition results by country == "Ethiopia"
- Ethiopian present -> propose min(year), confidence HIGH
- otherwise -> propose nothing, show the foreign years as context, confidence NONE
