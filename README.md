# ሸክላ · Shekla

A remote music game for Amharic songs, played across continents. Take turns: a clip
plays, you name the singer and place the song on your timeline. Everyone hears every
song. Highest score wins.

Inspired by [Hitster](https://hitstergame.com), but rebuilt for people who are not in
the same room — and for a catalogue the retail box does not carry.

> **Status: playable.** Rooms, turns, scoring, reveal and reconnect all work end to end.
> The visual design is a first pass and is due a rework. The starter deck's years are
> unverified.

## How a turn works

A 30-second clip plays and the player whose turn it is fills in an answer card:

| | worth | how |
|---|---|---|
| **The singer** | **70** | typed, in Latin letters |
| **The year** | **30** | tap where the song belongs on your timeline |
| The song title | 0 | optional; shown at the reveal, not scored |

The two halves are graded independently, so naming the singer and misplacing the year
still scores 70. Place it correctly and the card joins your timeline.

You can answer while the music is still playing, or stop it first. Everyone else hears
the same clip and answers on their own turn.

Spelling is forgiving on purpose. Amharic names have no agreed Latin form, so
`Telahun Gesesse`, `Gessesse` and `Tilahun Gessesse` all score for the same artist.

## Run it

Server:

```bash
cd server
python3 -m venv .venv && ./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/uvicorn main:app --reload --port 3001
```

`requirements.txt` is the runtime set the Docker image installs; `requirements-dev.txt`
adds the test, lint and deck-tooling extras.

Client:

```bash
cd client
npm install
npm run dev
```

Open the printed URL. Enter your name once, then either create a room — you get a
four-letter code to share — or type a friend's code and join.

Tests and checks — the same commands CI runs:

```bash
cd server && ./.venv/bin/python -m pytest tests/ -q && ./.venv/bin/ruff check .
```

```bash
cd client && npm run typecheck && npm run lint
```

## Build the deck

The deck ships with 320 Amharic songs across 85 artists, from Tilahun Gessesse and
Mulatu Astatke to Rophnan and Kassmasse. Every year on it is a **proposal** until a
person confirms it: no database reports original release dates reliably — Deezer dates
a 1975 Mahmoud Ahmed recording to its 2004 reissue — so the game plays each card as
proposed and `/deck` shows which years still need a look.

Open **`/deck`** in the running game to curate from a browser. Unconfirmed years come
with the year prefilled: tap **Confirm** if it is right, type the right one and tap
**Fix year** if not. Adding a song is the same page — search Deezer or paste a YouTube
link, type the year, done. It works from a phone, so anyone in the group can contribute
the songs they actually know.

On a deployed server those edits live only in that server's database, which is thrown
away on the next deploy. The page says exactly which songs are not yet in the committed
deck and offers **Download deck.json**; save it as `server/decks/deck.json` and commit it.
Set `DECK_TOKEN` on the server if the editor's URL ever leaves the group, and share
`/deck?token=…` instead.

The CLI does the bulk work:

```bash
cd server
./.venv/bin/python tools/build_deck.py harvest decks/artists-amharic.txt   # Deezer -> worksheet
./.venv/bin/python tools/build_deck.py import decks/harvest.tsv --by harvest  # as unconfirmed
./.venv/bin/python tools/build_deck.py export                                  # -> decks/deck.json
```

`harvest` walks each artist's Deezer catalogue, keeps their most-played songs and
proposes a year for each from the release it sits on, with a note on how far to trust
it — a compilation or a bulk-upload date is flagged `low`, because it is the date of a
reissue, not of the song. Add artists to `decks/artists-amharic.txt` to widen the net.
`decks/amharic-2026-10.tsv` is the curated first harvest, with its reasoning beside each
year.


## Why not just use the Hitster app?

It needs the physical deck, everyone in one room, and a Spotify account each. Rebuilding
it remotely turned out to need three things the retail game does not:

- **A music source that costs players nothing.** Spotify withdrew 30-second preview URLs
  for new apps in November 2024, and its Web Playback SDK demands Premium per listener.
  Deezer's public API needs no key at all and returns a real 30-second MP3.
- **A hand-curated deck**, because automated release-year lookup is unusable.
- **Latin-script typed answers with forgiving matching**, because a Ge'ez keyboard is not
  something most players have installed.

All three are documented with evidence in [FINDINGS.md](FINDINGS.md).

## Deploy

Two hosts, and the split is forced: the Next.js client goes to Vercel, but the Socket.IO
server **cannot** — it holds a WebSocket open for the whole game and Vercel's functions are
serverless. It needs Fly.io, Railway or Render.

If you imported this repo to Vercel and got a **404**, set the project's **Root Directory**
to `client`. The app is not at the repo root.

Full steps: [docs/DEPLOY.md](docs/DEPLOY.md).

## Documentation

| Document | What it covers |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | How the system works — round lifecycle, socket protocol, state, scoring, matching |
| [FINDINGS.md](FINDINGS.md) | What the music APIs actually do, verified against live services |
| [Design spec](docs/project/specs/active/plan-2026-09-07-remote-group-game.md) | Why the game is shaped this way, including decisions that were later reversed |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Getting it online, and why the server cannot live on Vercel |
| [docs/REVIEW-2026-10-18.md](docs/REVIEW-2026-10-18.md) | Whole-codebase review: what was found, what was removed, what is still open |
| [docs/REVIEW-2026-09-08.md](docs/REVIEW-2026-09-08.md) | Page-by-page review: nine failure modes found and fixed |
| [CLAUDE.md](CLAUDE.md) | Working notes — the things that are easy to get wrong |

## Issue tracking

This repo uses [tbd](https://github.com/jlevy/tbd), which keeps issues in git:

```bash
tbd ready      # what is unblocked right now
tbd list       # everything
tbd show <id>  # one issue in detail
```

Issues live on the `tbd-sync` branch and do not appear in feature-branch diffs.

## Credits

Hitster is a game by [Jumbo Games](https://hitstergame.com). This is an unaffiliated
personal project. Audio previews come from Deezer's public API, whose developer terms
permit non-commercial personal use.
