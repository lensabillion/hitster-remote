---
type: is
id: is-01m1ygpyqvsb3t2pkjzzk0txdk
title: Song title as a tiebreak bonus, not a score
kind: feature
status: open
priority: 1
version: 1
labels:
  - design
  - scoring
dependencies: []
created_at: 2026-09-07T18:04:59.514Z
updated_at: 2026-09-07T18:04:59.514Z
---
User's idea. Keep the title unscored in the main total, but count it as the tiebreaker.

Rationale: the user does not want the title inflating scores or feeling compulsory, but
someone who knows the title as well as the singer has demonstrated more, and that should
decide a draw.

Proposed:
- Track title_hits per player alongside score (the title is ALREADY matched and stored —
  player_title_matches runs every round and the result is thrown away, so this is close
  to free)
- Ranking: score desc, then title_hits desc, then fewer cards used
- Show it on the scoreboard as a small marker, not a number competing with the score

Open: whether a title hit should also be worth a token later, if tokens ever ship.
