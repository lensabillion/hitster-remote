# እስቲ (Isti) — Hitster Remote

A remote music timeline game for Amharic songs. Hear a clip, guess the release year,
place it in your timeline. Highest score after the planned rounds wins. The name is
እስቲ, *isti*, "go on, then" — the word that opens a dare, as in እስቲ ማን ዘፈነው? — and
the logo is a quaver whose flag curls into a question mark: who? when? It has engraving
proportions — heavy head, thin stem, a flag that swells and tapers to a point — and is a
generated outline (`client/design/mark.py`); rerun the script rather than nudging points,
and paste its output into `client/components/Logo.tsx` and, in the heavier cut,
`client/app/icon.svg`.

Design contract: `docs/project/specs/active/plan-2026-09-07-remote-group-game.md`.
Verified API behaviour and source constraints: `FINDINGS.md`.

## Run

Server:

```
cd server
python3 -m venv .venv && ./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/uvicorn main:app --reload --port 3001
```

Client:

```
cd client
npm install
npm run dev
```

Tests: `cd server && ./.venv/bin/python -m pytest tests/ -q`
Lint: `./.venv/bin/ruff check .` (server) · `npm run typecheck && npm run lint` (client)

## Deck

Release years cannot be taken from an API — MusicBrainz gives three answers for
"Billie Jean", and Deezer and iTunes both report reissue dates. So a year is only ever
*proposed* by a machine and *confirmed* by a human, once. Every card carries
`year_confirmed`; the game deals only confirmed cards, and `/deck` lists the unconfirmed
ones first so a person can confirm or fix each one with one tap and bring it into play.

Growing the deck, from broad to narrow:

```
cd server
./.venv/bin/python tools/build_deck.py harvest decks/artists-amharic.txt   # Deezer -> worksheet
./.venv/bin/python tools/build_deck.py import decks/harvest.tsv --by harvest  # unconfirmed
./.venv/bin/python tools/build_deck.py add            # interactive, confirmed
./.venv/bin/python tools/build_deck.py list
```

`harvest` walks each artist's Deezer catalogue, keeps the most-played songs, and proposes
a year from the release each sits on, labelled by how far to trust it: a year in the
release title is `high`, an ordinary release `medium`, a compilation or a bulk-upload
date `low` (it is a reissue date, not the song's). `decks/amharic-2026-10.tsv` is the
curated result of the first harvest — 300 songs across 85 artists with the golden-era
years corrected from the Ethiopiques spans — and `decks/harvest-2026-10-25.tsv` is the
raw worksheet it was cut from.

`decks/amharic-1980s-1990s.tsv` is the second cut: 85 songs that lift the two thin decades
to 50 and 72 cards. Deezer's dates are reissue dates for all of them, so every row carries
a note saying where its year came from — the original cassette or CD on Discogs, the
African Cassettes archive at Mainz University, a Wikipedia discography, the artist's own
dated releases. A note that starts with `confirmed` imports that row as confirmed, so one
worksheet carries documented years and open proposals side by side; a year converted from
an Ethiopian-calendar cassette date is never marked confirmed. Its artist list is
`decks/artists-1980s-1990s.txt` and its raw worksheet `decks/harvest-1980s-1990s-2026-10-25.tsv`.

Seed format is tab-separated. Artist, title and year are enough — a YouTube URL is only
needed for songs Deezer does not carry, and a Deezer track id (column 7) skips the lookup:

`year <TAB> artist_latin <TAB> title_latin [<TAB> artist_am <TAB> title_am <TAB> youtube_url <TAB> deezer_track_id]`

**Deployment seeds from `decks/deck.json`, never from a live import.** Deezer answers a
throttled query with an empty result set rather than an error, so re-probing at build
time silently produces a near-empty deck. Export after curating:

```
./.venv/bin/python tools/build_deck.py export   # -> decks/deck.json, commit it
./.venv/bin/python tools/build_deck.py seed     # loads it, no network
```

Songs can also be added and years confirmed from the running game at `/deck`, which is
how the deck is meant to be curated — every comparable project curates by hand, and a
page beats a text file. On a deployed server those edits are lost on the next deploy; the
page lists what is not in `deck.json` yet and offers it as a download that is
byte-identical to the CLI export.

Every year in the deck, on the timeline and in the worksheets is Gregorian; the landing
page says so, because Ethiopian covers and listeners count in ዓ.ም, seven or eight years
behind. Where a year came from is written down beside it. The three curated worksheets,
`decks/starter-amharic.tsv`, `decks/amharic-2026-10.tsv` and
`decks/amharic-1980s-1990s.tsv`, carry a `#` note on every row naming the source of its
year: the Éthiopiques booklets as transcribed on Discogs and the original Amha, Kaifa and
Philips records for the 1960s and 70s; cassette covers in the African Cassettes archive at
Mainz University and on Discogs for the 1980s and 90s, where an Ethiopian-calendar year is
converted but never confirmed; and for anything after 2000 Deezer's own date set beside a
second, independent source, usually the official video's upload date or a dated
discography. A note that starts with `confirmed` imports its row as confirmed, so the
worksheets and `deck.json` agree; a year that could not be sourced says so in its note
and stays unconfirmed for `/deck`.

## Architecture

- `server/game.py` — pure rules. Placement validation, same-year rule, round
  resolution. No I/O, fully unit tested; this is the correctness core.
- `server/rooms.py` — live room state, in memory only. Seating, turn order, the sealed
  answer, and the per-viewer `serialize()`.
- `server/deck.py` — the deck as data: stable card ids, the `deck.json` export, the
  unsaved diff, and the year bounds.
- `server/db.py` — SQLite via aiosqlite, WAL. Holds only the deck; a restart ends any
  game in progress, by design.
- `server/sources.py` — Deezer and YouTube lookup. The only module that talks to Deezer.
- `server/tools/build_deck.py` — offline deck curation CLI, including the harvest and its
  judgement about which Deezer dates to believe.
- `client/app/` — Next.js App Router. `client/components/Timeline.tsx` is the centrepiece.

## Scoring

Each round is graded out of 100 and the two halves are independent:

- **70 — the singer.** Typed into the answer card in Latin letters. Matching is
  deliberately generous (`matching.player_artist_matches`): a surname alone counts, so
  does a plausible misspelling, and the vowels are set aside before comparing, so Makiya
  Bahilu is Mikaya Behailu. Amharic names have no agreed Latin spelling, so a player must
  never lose points to a transliteration they had no way to guess.
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
- **Rounds rotate through the eras.** `deal_across_eras` orders the shuffled deck so
  consecutive cards cycle through the classics before 1980 and then each decade. A deck
  thick in the 2010s still deals a 1980s song as often as a 2010s one. Do not replace it
  with a plain shuffle.
- **Two matchers, opposite temperaments.** `artist_matches` and `title_matches`
  (catalogue) are strict, so a wrong Deezer track is never attached.
  `player_artist_matches` (typed input) is generous, so a player is never robbed by
  spelling. Do not collapse them into one.
- **Sealed until reveal.** Never send an unrevealed card to any client — not the year,
  not the artist, not the title. Room state is fanned out per viewer rather than
  broadcast for exactly this reason; a leak here does not fail loudly, it silently
  decides who wins.
- **The answer timer reveals from inside itself.** When the window expires, the timer
  task calls `do_reveal`, which calls `cancel_timer`. It must never cancel the current
  task: the cancellation lands on the next `await`, inside `push_state`, and the reveal
  is applied to the room but reaches no client. That stall is covered by
  `test_an_absent_player_cannot_stall_the_table`.

## Music sources

Deezer is primary; YouTube is the per-card fallback. Both are keyless.

- **Search Deezer with a plain query** (`q=Aster Aweke Gela Gela`) and verify every
  result. The documented field syntax (`artist:"..." track:"..."`) worked in September
  2026 and returns nothing at all since October 2026: Deezer ignores the prefixes, so
  `track:"Gela Gela"` matches "Moving Gelatine Plates". `/search/artist` is unreliable
  for Amharic names — it answers "Teddy Afro" with "Teddy Karo".
- **Amharic-script search returns nothing.** Query by Latin transliteration; carry the
  Amharic strings alongside for display.
- **Verify the returned artist with `artist_matches` and the title with
  `title_matches`, never a raw ratio.** A plain query ranks by popularity across every
  artist, and a wrong Deezer id does not fail loudly, it silently plays a different song.
- **Deezer preview URLs expire 15 minutes after issue.** Store track ids; resolve a URL
  once per round, share it with every socket, and never persist one.
- **A round is never silent.** A card whose sources all fail to resolve is skipped for
  the next one rather than played as "no audio".

## Typography and palette

Two families, both covering Ethiopic and Latin so bilingual lines stay on one face:

- **Abyssinica SIL** — display. Calligraphic Ge'ez, single weight, used at size only,
  and only where it earns its place: the እስቲ wordmark and the year at the reveal.
- **Noto Sans Ethiopic** — text and UI, variable 100–900. All hierarchy comes from
  here, headings included (`.h`).

Never introduce a Latin-only family anywhere an Amharic string can appear. `.am`
carries extra line-height because Ge'ez has more vertical detail per glyph.

Palette is plain white and green, deliberately single-theme light: a white ground,
grey ink and hairline rules, and one green family as the only accent — primary
actions, focus rings, the active turn, a selected slot, a correct answer. Red is kept
for the few things that need a danger colour (a wrong half at the reveal, an
unreachable server, changes about to be lost) and stays quiet. No textures, washes,
gradients or glows. Every text/background pair in the token block meets WCAG AA, and
every control is at least 44px tall. Tokens live in `client/app/globals.css`; use them
rather than literal colours.

Motion is spent in one place: the arrival (`client/components/Arrival.tsx`), which heads
the home page and the name form a shared room link opens. A crowd of grey ears turns toward the mark as it appears, clears for the name, and
"Listen." gives way to "Who? When?". It is pure CSS, and every element's resting style is
its final frame, so reduced motion shows the plain header and nothing on the page waits.

## Issue tracking

`tbd ready` for unblocked work, `tbd show <id>` for detail. Beads live on the
`tbd-sync` branch and never appear in a feature branch diff.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
