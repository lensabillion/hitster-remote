# ዜማ (Zema) — Hitster Remote

A remote music timeline game for Amharic songs. Hear a clip, guess the release year,
place it in your timeline. Highest score after the planned rounds wins.

Design contract: `docs/project/specs/active/plan-2026-09-07-remote-group-game.md`.
Verified API behaviour and source constraints: `FINDINGS.md`.

## Run

Server:

```
cd server
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/uvicorn main:app --reload --port 3001
```

Client:

```
cd client
npm install
npm run dev
```

Tests: `cd server && ./.venv/bin/python -m pytest tests/ -q`

## Deck

Release years cannot be taken from an API — MusicBrainz gives three answers for
"Billie Jean", and Deezer and iTunes both report reissue dates. Every year is
confirmed by a human, once, in the deck builder:

```
cd server
./.venv/bin/python tools/build_deck.py add            # interactive
./.venv/bin/python tools/build_deck.py import x.tsv   # bulk
./.venv/bin/python tools/build_deck.py list
```

Seed format is tab-separated. Artist, title and year are enough — a YouTube URL is only
needed for songs Deezer does not carry:

`year <TAB> artist_latin <TAB> title_latin [<TAB> artist_am <TAB> title_am <TAB> youtube_url]`

**Deployment seeds from `decks/deck.json`, never from a live import.** Deezer answers a
throttled query with an empty result set rather than an error, so re-probing at build
time silently produces a near-empty deck. Export after curating:

```
./.venv/bin/python tools/build_deck.py export   # -> decks/deck.json, commit it
./.venv/bin/python tools/build_deck.py seed     # loads it, no network
```

Songs can also be added from the running game at `/deck`, which is how the deck is meant
to grow — every comparable project curates by hand, and a page beats a text file.

## Architecture

- `server/game.py` — pure rules. Placement validation, same-year rule, round
  resolution. No I/O, fully unit tested; this is the correctness core.
- `server/db.py` — SQLite via aiosqlite, WAL. Holds only what must survive a restart:
  deck, player identities, room seating and timelines.
- `server/sources.py` — Deezer and YouTube lookup.
- `server/tools/build_deck.py` — offline deck curation CLI.
- `client/app/` — Next.js App Router. `client/components/Timeline.tsx` is the centrepiece.

## Scoring

Each round is graded out of 100 and the two halves are independent:

- **70 — the singer.** Typed into the answer card in Latin letters. Matching is
  deliberately generous (`matching.player_artist_matches`): a surname alone counts, so
  does a plausible misspelling. Amharic names have no agreed Latin spelling, so a player
  must never lose points to a transliteration they had no way to guess.
- **30 — the year.** Earned by placing the card correctly on your own timeline, not by
  typing a year. Relative order is the forgiving part of the game and it stays that way.
- **0 — the song title.** Captured and shown at the reveal, never scored.

Highest total after the planned rounds wins. Naming the singer but misplacing the card
still scores 70; the halves must not gate each other.

Answering is open from the moment the clip starts. There is no listen-then-place gate:
you may answer over the music, or stop the clip and answer after. The answer window is a
ceiling that only stops an absent player stalling the table.

## Rules that are easy to get wrong

- **Same-year rule.** A card whose year ties with one already on the timeline may sit on
  *either* side of it. Both bounds in `is_correct_placement` are inclusive, which is
  exactly this rule — do not "fix" them to strict inequalities.
- **One song, one answer.** Only the player whose turn it is answers; the server rejects
  an out-of-turn submission. Everyone else *hears the same clip* and watches — the audio
  cue goes to every socket, not just the answering one. Their song comes on their turn.
- **Turns are dealt evenly.** `rounds_planned` is rounded down to a whole number of turns
  each, so nobody sitting early in the seat order gets an extra song.
- **Two matchers, opposite temperaments.** `artist_matches` (catalogue) is strict, so a
  wrong Deezer track is never attached. `player_artist_matches` (typed input) is
  generous, so a player is never robbed by spelling. Do not collapse them into one.
- **Sealed until reveal.** Never send an unrevealed card to any client — not the year,
  not the artist, not the title. Room state is fanned out per viewer rather than
  broadcast for exactly this reason; a leak here does not fail loudly, it silently
  decides who wins.

## Music sources

Deezer is primary; YouTube is the per-card fallback. Both are keyless.

- **Search Deezer with field-scoped track search** (`q=artist:"..." track:"..."`).
  `/search/artist` is unreliable for Amharic names — it answers "Teddy Afro" with
  "Teddy Karo". This single choice moves catalogue coverage from 37% to 87%.
- **Amharic-script search returns nothing.** Query by Latin transliteration; carry the
  Amharic strings alongside for display.
- **Verify the returned artist with `artist_matches`, never a raw ratio.** A wrong
  Deezer id does not fail loudly, it silently plays a different song.
- **Deezer preview URLs expire 15 minutes after issue.** Store track ids; resolve a URL
  per round and never persist one.

## Typography

Two families, both covering Ethiopic and Latin so bilingual lines stay on one face:

- **Abyssinica SIL** — display. Calligraphic Ge'ez, single weight, used at size only.
- **Noto Sans Ethiopic** — text and UI, variable 100–900. All hierarchy comes from here.

Palette is Ethiopian Orthodox manuscript illumination — gold leaf, liturgical red and
verdigris on darkened parchment. Deliberately single-theme dark. Tokens live in
`client/app/globals.css`; use them rather than literal colours.

## Issue tracking

`tbd ready` for unblocked work, `tbd show <id>` for detail. Beads live on the
`tbd-sync` branch and never appear in a feature branch diff.
