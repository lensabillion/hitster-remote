# ዜማ (Zema) — Hitster Remote

A remote music timeline game for Amharic songs. Hear a clip, guess the release year,
place it in your timeline. First to eight correctly placed cards wins.

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

Seed format is tab-separated:
`youtube_url <TAB> year <TAB> artist_latin <TAB> title_latin [<TAB> artist_am <TAB> title_am]`

## Architecture

- `server/game.py` — pure rules. Placement validation, same-year rule, round
  resolution. No I/O, fully unit tested; this is the correctness core.
- `server/db.py` — SQLite via aiosqlite, WAL. Holds only what must survive a restart:
  deck, player identities, room seating and timelines.
- `server/sources.py` — Deezer and YouTube lookup.
- `server/tools/build_deck.py` — offline deck curation CLI.
- `client/app/` — Next.js App Router. `client/components/Timeline.tsx` is the centrepiece.

## Rules that are easy to get wrong

- **Same-year rule.** A card whose year ties with one already on the timeline may sit on
  *either* side of it. Both bounds in `is_correct_placement` are inclusive, which is
  exactly this rule — do not "fix" them to strict inequalities.
- **Everyone places every round.** The active player's placement is real; everyone
  else's is a shadow guess that earns a token when right, and steals the card when right
  while the active player was wrong.
- **Sealed until reveal.** Never send an unrevealed card's year to any client. Ties
  between correct stealers break on earliest submission, which only ever separates two
  already-correct guesses — so lower latency never wins a card.

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
