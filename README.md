# ዜማ · Zema

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
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/uvicorn main:app --reload --port 3001
```

Client:

```bash
cd client
npm install
npm run dev
```

Open the printed URL. Enter your name once, then either create a room — you get a
four-letter code to share — or type a friend's code and join.

Tests:

```bash
cd server && ./.venv/bin/python -m pytest tests/ -q
```

## Build the deck

Release years cannot be taken from an API — MusicBrainz gives three different answers for
"Billie Jean", and Deezer and iTunes both report reissue dates. So the deck is curated by
hand, once, offline, and committed.

```bash
cd server
./.venv/bin/python tools/build_deck.py add            # interactive
./.venv/bin/python tools/build_deck.py import x.tsv   # bulk
./.venv/bin/python tools/build_deck.py list
./.venv/bin/python tools/build_deck.py check          # re-probe every card's sources
```

Seed format is tab-separated:

```
year <TAB> artist_latin <TAB> title_latin [<TAB> artist_am <TAB> title_am <TAB> youtube_url]
```

Artist, title and year are enough. A YouTube URL is only needed for the minority of songs
Deezer does not carry.

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
