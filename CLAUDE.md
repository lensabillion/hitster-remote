# Hitster Remote

Real-time multiplayer music guessing game. Host plays a 10-second YouTube clip; players race to type the artist within 15 seconds.

## Run

Server:
```
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 3001
```

Client:
```
cd client
npm install
npm run dev
```

Open the printed Vite URL. Host creates a room, players join with the 4-letter code.

## Architecture

- `server/main.py` — FastAPI + python-socketio (AsyncServer mounted via ASGIApp). All socket events live here.
- `server/rooms.py` — in-memory rooms dict and player lifecycle.
- `server/game.py` — YouTube ID parsing, "Artist - Song" splitting, fuzzy matching, scoring.
- `client/src/lib/socket.js` — single socket.io-client instance.
- `client/src/screens/` — Home, Lobby, Game, RoundResult, Final.
- `client/src/components/YouTubePlayer.jsx` — hidden iframe, plays 0–10s.

## Scoring

`1 point` for a correct guess + speed bonus (5 → 0, dropping by 1 every 3s of the 15s guessing window). Frontend does the primary fuzzy match with fuse.js (threshold 0.4); server re-checks with `difflib`.

## State

Rooms live in memory (no DB). On host disconnect, the first remaining player is promoted to host. Empty rooms are GC'd.
