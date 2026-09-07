# Deploying ዜማ

Two pieces, two hosts. That split is not a preference — it is forced by how the game
works.

```
  Vercel                        Fly.io / Render                 Deezer + YouTube
  ──────                        ───────────────                 ────────────────
  Next.js client   ──socket──▶  FastAPI + Socket.IO
  (static + SSR)                (long-lived process)
        │                                                              ▲
        └──────────── audio streams straight from the CDN ─────────────┘
```

**The server cannot run on Vercel.** Socket.IO holds a WebSocket open for the whole game;
Vercel's functions are serverless and are torn down between requests. There is no
configuration that fixes this — it needs a host that runs an ordinary long-lived process.

The good news: the server only ever moves JSON. Audio goes from Deezer's CDN or YouTube
straight to each browser and never touches it, so the smallest instance on any host is
plenty.

---

## 1. Fixing the 404 on Vercel

If you imported this repo and got a 404, this is why: **the Next.js app is in `client/`,
not at the repo root.** Vercel built the root, found no application, and served nothing.

In your Vercel project → **Settings → Build and Deployment → Root Directory**, set:

```
client
```

Then redeploy. That alone fixes the 404.

There is no way to set this from a file — `vercel.json` cannot relocate the project root,
so it has to be the dashboard setting (or `vercel --cwd client` from the CLI).

---

## 2. Deploy the server first

You need its URL before the client is useful, so start here.

### Fly.io — recommended

Keeps a machine warm, so there is no cold start mid-game.

```bash
cd server
fly launch --no-deploy        # accept the existing fly.toml
fly deploy
```

Note the URL it prints, e.g. `https://zema-server.fly.dev`. Check it:

```bash
curl https://zema-server.fly.dev/health
# {"ok":true,"rooms":0,"cards":16}
```

`fly.toml` sets `primary_region = "cdg"` (Paris) as a rough midpoint between Addis Ababa
and San Francisco. Change it if your players sit elsewhere.

### Render — the one-click alternative

`render.yaml` at the repo root already describes the service. Free instances sleep after
inactivity and cold-start slowly, which is survivable for testing and irritating on a game
night.

---

## 3. Point the client at the server

In Vercel → **Settings → Environment Variables**:

```
NEXT_PUBLIC_SERVER_URL = https://zema-server.fly.dev
```

This is baked in at build time, not read at runtime, so **redeploy after setting it** or
the client will keep talking to `localhost:3001`.

## 4. Let the server accept the client

Back on the server, allow your Vercel origin:

```bash
fly secrets set CORS_ORIGINS=https://your-app.vercel.app
```

Exact origin, no trailing slash. Several are comma-separated. Left unset it defaults to
`*`, which is fine while testing and worth tightening once the URL settles.

Verify:

```bash
curl -sD - -o /dev/null -H "Origin: https://your-app.vercel.app" \
  https://zema-server.fly.dev/health | grep -i access-control-allow-origin
```

---

## The deck

The Docker image runs the deck import at **build** time, so the 16 starter cards are baked
in and there is no volume to manage and no Deezer lookup on a cold start. A card with no
playable source fails the build rather than turning up broken mid-game.

To change the deck, edit `server/decks/starter-amharic.tsv` and redeploy.

**The starter deck's years are unverified guesses.** They are marked as such at the top of
the file. Fix them before the deck is fair to play with.

---

## What survives a restart, and what does not

| | Survives | Why |
|---|---|---|
| The deck | yes | baked into the image |
| Player identity | yes | a UUID in the browser's `localStorage` |
| Score, timeline, seating | **no** | written to SQLite on the container's own disk |
| A game in progress | **no** | live round state is in memory |

A restart mid-game ends that game. For a handful of friends playing for half an hour this
is an acceptable trade, and it is why `min_machines_running = 1` is set on Fly. If it ever
matters, attach a Fly volume at the SQLite path and set `DB_PATH` to it.

---

## Checklist

- [ ] Vercel **Root Directory** set to `client` — this is the 404 fix
- [ ] Server deployed; `/health` returns `cards: 16`
- [ ] `NEXT_PUBLIC_SERVER_URL` set on Vercel, **and redeployed after setting it**
- [ ] `CORS_ORIGINS` on the server set to the Vercel origin
- [ ] Open the site in two browsers, create a room, join with the code
- [ ] Everyone wears headphones, or the music echoes through the call
