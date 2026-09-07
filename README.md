# Hitster Remote

A remote, browser-based take on [Hitster](https://hitstergame.com) — the music timeline
party game. Hear a song, guess when it came out, slot it into your timeline. First to
ten correctly placed cards wins.

The boxed game assumes everyone is around one table with one phone playing out loud.
This project is about making it work when the players are on different continents.

> **Status: rebuild in progress.** What is in `server/` and `client/` today is an
> earlier prototype of a *different* game — a speed quiz where everyone races to type
> the artist for points. The Hitster timeline game is being built on top of that
> plumbing. See [FINDINGS.md](FINDINGS.md) for the research and the plan.

## Why not just use the app?

Hitster's own app scans a QR code on a physical card and hands playback to Spotify. That
requires the physical deck, everyone in the same room, and a Spotify account per player.
It has no remote mode, and the official FAQ does not mention online play.

Rebuilding it remotely turns out to need three things the retail game does not:

- **A music source that works without a subscription.** Spotify removed 30-second
  preview URLs for new apps in Nov 2024, and its Web Playback SDK demands Premium per
  listener. Deezer's public API needs no key at all and returns a real 30-second MP3.
- **A hand-curated deck.** Automated release-year lookup is unreliable enough to be
  unusable — reissues and remasters poison every source.
- **A latency-fair replacement for shouting "HITSTER!"** A click race across a few
  hundred milliseconds of asymmetric latency hands every steal to whoever has better
  transit.

All three are documented with evidence in [FINDINGS.md](FINDINGS.md).

## Run it

Server:

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 3001
```

Client:

```bash
cd client
npm install
npm run dev
```

Open the printed Vite URL. One player creates a room, the others join with the
four-letter code.

## Architecture

| Path | Role |
|---|---|
| `server/main.py` | FastAPI + python-socketio (`AsyncServer` via `ASGIApp`). All socket events. |
| `server/rooms.py` | In-memory room registry and player lifecycle. |
| `server/game.py` | Song metadata parsing, fuzzy matching, scoring. |
| `client/src/lib/socket.js` | Single socket.io-client instance. |
| `client/src/screens/` | Home, Lobby, Game, RoundResult, Final. |
| `client/src/components/` | Audio playback and countdown UI. |

Rooms live in memory — no database. Empty rooms are garbage collected.

## Issue tracking

This repo uses [tbd](https://github.com/jlevy/tbd) for git-native issue tracking:

```bash
tbd ready      # what is unblocked right now
tbd list       # everything
tbd show <id>  # detail for one issue
```

## Credits

Hitster is a game by [Jumbo Games](https://hitstergame.com). This is an unaffiliated
personal project for playing something like it with friends who live too far away.
Audio previews are served by Deezer's public API, whose developer terms permit
non-commercial personal use.
