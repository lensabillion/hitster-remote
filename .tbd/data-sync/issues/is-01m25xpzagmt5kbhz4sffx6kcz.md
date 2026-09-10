---
type: is
id: is-01m25xpzagmt5kbhz4sffx6kcz
title: Prior art confirms manual curation; steal their tagging trick
kind: task
status: open
priority: 1
version: 1
labels:
  - deck
  - research
dependencies: []
created_at: 2026-09-10T15:06:52.623Z
updated_at: 2026-09-10T15:06:52.623Z
---
User asked whether the GitHub prior-art projects populate songs manually. Checked all
four. They do — without exception.

Timtam/hitster
  etc/hits.yml — 7,239 hand-curated entries, 2.2 MB, committed to the repo:
      - artist: (G)-IDLE
        title: Oh my god
        year: 2020
        yt_id: phDQEkp2FTw
        playback_offset: 0
  Plus a create-hit page in the client and a report-hit-issue modal, so the data is
  added and corrected by people through the UI over time.

Born2Root/HitStar
  Local file tags exported via mp3Tag to CSV, then refined by hand in a spreadsheet.
  Explicitly warns that sampler albums carry wrong dates, and recommends a
  MusicBrainz Picard script:
      $set(date,$if2(%_recording_firstreleasedate%,%originaldate%,%date%))
  i.e. prefer MusicBrainz recording first-release-date, then originaldate, then date.

ruuda/hitsgame
  Reads FLAC tags and requires ORIGINALDATE, falling back to DATE. The distinction is
  the whole point: DATE is this pressing, ORIGINALDATE is the first release.

david-auk/Mixster
  Schema only, no seed data — scans the user's own playlists.

Takeaways for us:
1. Manual curation is not a shortcoming of our approach, it is what everyone does. The
   only question is how pleasant the tooling makes it.
2. Audio TAGS have a dedicated original-release field — ORIGINALDATE (Vorbis) / TDOR
   (ID3v2.4) / TORY (ID3v2.3) — distinct from the ordinary date. Most files lack it
   unless tagged with Picard, which is why HitStar ships a Picard script rather than
   trusting plain tags.
3. Worth stealing: playback_offset per card, so a clip can start at the hook rather
   than the intro.
4. Worth stealing: an in-app add-song page and a report-a-bad-card control, so the deck
   improves during play instead of only in a text file.
