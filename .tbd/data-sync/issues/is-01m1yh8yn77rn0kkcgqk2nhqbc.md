---
type: is
id: is-01m1yh8yn77rn0kkcgqk2nhqbc
title: Import a deck from a YouTube playlist with proposed years
kind: feature
status: open
priority: 1
version: 1
labels:
  - deck
  - tooling
dependencies: []
created_at: 2026-09-07T18:14:49.254Z
updated_at: 2026-09-07T18:14:49.254Z
---
User asked whether a YouTube playlist can seed the deck, and whether an API could replace
the database.

VERIFIED: yt-dlp lists playlists, channels and searches with NO API key, metadata only
(--flat-playlist --dump-json, no download). Confirmed against a real channel and a real
search.

The database still has to exist. It stores 338 bytes per song — an id, names and the
year — never audio. The one thing it holds that no API will give back is the YEAR, which
every source lies about (MusicBrainz gave three answers for "Billie Jean"; Deezer and
iTunes report reissue dates). Strip the year and there is no game.

So a playlist does not replace storage; it replaces DATA ENTRY.

Build `build_deck.py import-playlist <url>`:
1. Expand the playlist via yt-dlp (keyless, metadata only)
2. Parse artist/title from each video title, stripping the usual decorations
3. Probe Deezer by Latin transliteration; attach the track id only when
   artist_matches accepts it (Deezer preview is ~500 KB against a video stream,
   which matters on an Ethiopian connection)
4. PROPOSE a year from several sources and record which agreed:
     - a 4-digit year in the YouTube title (common for Ethiopian uploads, e.g.
       "Teddy Afro TiKUR SEW (ጥቁር ሰው) 2012")
     - Deezer album.release_date
     - MusicBrainz first-release-date
   two or more agreeing -> propose; disagreement or a single source -> FLAG
5. Write a reviewable TSV with a confidence column; the human corrects and re-imports

Caveat to build in: a year scraped from a title is often the upload or album year, not
the original release. Flagging must be conservative — propose, never assume.

yt-dlp becomes a build-time dependency of the offline deck tool only. It must never be
on the play-time path.
