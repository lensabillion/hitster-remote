# How ዜማ works

Written 2026-09-07, against the code at that date. Every constant and behaviour below is
taken from the source rather than from memory; where a number appears, the file that owns
it is named.

For *why* the game is shaped this way, see the
[design spec](project/specs/active/plan-2026-09-07-remote-group-game.md). For what the
music APIs actually do, see [FINDINGS.md](../FINDINGS.md).

---

## 1. The game in one paragraph

Players take turns. On your turn a 30-second clip plays, and you fill in an answer card:
who sang it, and where it belongs on your timeline. Naming the singer is worth 70 points,
placing it correctly is worth 30, and they are graded independently — so you can name the
singer, misplace the year, and still take 70. Place it correctly and the card joins your
timeline, which is both the play surface and the record of what you have won. Everyone
else hears the same clip while you answer, and gets their own song when their turn comes.
Highest score at the end wins.

---

## 2. Shape of the system

```
  browser (Next.js)                          server (FastAPI + python-socketio)
  ─────────────────                          ──────────────────────────────────
  app/page.tsx          name, create, join
  app/room/[code]       ──── socket.io ────▶  main.py     events, fan-out, timers
  components/                                 rooms.py    live room state (memory)
    AnswerCard          ◀─── room:state ────  game.py     pure rules, scoring
    AudioClip           ◀─── round:audio ───  matching.py name matching
    Timeline                                  sources.py  Deezer / YouTube lookup
  lib/                                        db.py       SQLite (deck, identities)
    identity.ts   durable player UUID
    room.ts       socket + typed state              │
                                                    ▼
  audio streams straight from Deezer's CDN    tools/build_deck.py  (offline curation)
  to each browser — never through the server
```

Two things worth noticing in that diagram.

**Audio never touches the server.** The server resolves a URL and sends it; each browser
fetches the ~500 KB clip from Deezer's CDN itself. The server only ever moves JSON, which
is why it can be a small instance anywhere.

**The deck is built offline and committed.** Nothing curates itself at runtime.

---

## 3. State, split by lifetime

The split is deliberate: things that must survive a process restart go to SQLite, and
things that change several times a second and are worthless afterwards stay in memory.

| Lives in | What | Why |
|---|---|---|
| **SQLite** (`db.py`) | deck cards, player identities, room records, seating, timelines | Must outlive a dropped socket or a restart |
| **Memory** (`rooms.py`) | current card, sealed answer, phase, timers, clip start | Changes constantly, meaningless once the round resolves |

SQLite runs in WAL with `synchronous=NORMAL` on one shared connection. Postgres would be
operational cost for load this will never see; SQLite reads are in-process and
sub-millisecond, and the whole database is one file.

### Player identity

Players are keyed by a UUID the browser keeps in `localStorage` (`lib/identity.ts`),
**never by socket id**. The socket is a mutable attachment to a seat.

This is the single decision that makes the game survive a bad connection. On reconnect
the server re-binds the new socket to the same seat, and the player gets back their
score, their timeline, their place in the turn order — and the current round's audio,
so they can keep playing rather than merely watching. Keying by socket id would mean a
dropped connection in Addis Ababa ends someone's game.

`localStorage` can throw (private windows, blocked site data), so the helper falls back
to a per-tab id rather than failing to start.

---

## 4. A round, step by step

Phases are `lobby → answering → revealing → over` (`game.py:Phase`).

There is deliberately **no separate listening phase**. The answer card is open from the
moment the clip starts, so a player who recognises the song in two seconds can answer
immediately, and there is a Stop control for anyone who would rather kill the music and
think. Gating answers behind the end of the clip made the round feel rigid.

```
1. host emits game:start
     └─ deck loaded from SQLite, shuffled
     └─ every player seeded with one card, face up, as their starting year
     └─ rounds_planned rounded DOWN to a whole number of turns each

2. start_round()
     └─ draw a card, phase = answering, record clip_started_ms
     └─ resolve a FRESH Deezer preview URL (they expire in 15 minutes)
     └─ round:audio  →  EVERY connected socket, not just the answering player
     └─ room:state   →  each socket, individually filtered
     └─ arm a 90s timer (rooms.ANSWER_SECONDS) as a ceiling, not a pace

3. the player whose turn it is emits round:answer {gap, artist, title}
     └─ server refuses it from anyone else
     └─ answer sealed; no second attempt

4. reveal — as soon as that one answer lands, or when the timer expires
     └─ grade out of 100, add to the running score
     └─ if the placement was right, insert the card into their timeline
     └─ phase = revealing; the card is disclosed to everyone now and not before
     └─ persist score and timeline to SQLite

5. host emits round:next
     └─ advance_seat() skips disconnected players
     └─ back to 2, or finish_game() on the last round
```

### Constants

| Name | Value | File |
|---|---|---|
| `CLIP_SECONDS` | 30 | `rooms.py` |
| `ANSWER_SECONDS` | 90 | `rooms.py` |
| `DEFAULT_ROUNDS` | 12 | `rooms.py` |
| `MIN_DECK` | 6 | `main.py` |
| `ARTIST_POINTS` | 70 | `game.py` |
| `YEAR_POINTS` | 30 | `game.py` |

`rounds_planned` is rounded down to a multiple of the player count, so nobody sitting
early in the seat order gets an extra song.

---

## 5. Socket protocol

**Client → server.** Every payload carries the durable `playerId`.

| Event | Payload | Notes |
|---|---|---|
| `room:create` | `name` | Creates a room, returns a four-letter code |
| `room:join` | `code`, `name` | Also the reconnect path; a known player may rejoin mid-game, a new one may not |
| `game:start` | `code`, optional `rounds` | Host only, needs 2+ players and a deck of at least 6 |
| `round:answer` | `code`, `gap`, `artist`, `title` | **Active player only.** One per round, final |
| `round:next` | `code` | Host only, and only while revealing |

**Server → client.**

| Event | Notes |
|---|---|
| `room:state` | The whole view, **sent per viewer** — see below |
| `round:audio` | Resolved source, sent to every socket and re-sent on rejoin |
| `game:over` | Final standings |
| `error` | Human-readable, e.g. "It is not your turn" |

### Why state is fanned out per viewer

`room:state` is built separately for each player (`rooms.serialize(room, viewer_id)`)
rather than broadcast once, because what each player may see differs:

- the current card — artist, title **and year** — is withheld from *everyone* until the
  reveal;
- a player is told only whether *they themselves* have answered, and gets only their own
  answer echoed back.

Anything in this payload is readable in devtools. A leak here would not fail loudly — it
would silently decide who wins — so it is covered by tests that assert the subject card's
id, title and artist appear nowhere in the serialized payload before the reveal, and that
a watcher never receives the answerer's guess.

---

## 6. Scoring

`game.score_answer()` grades one answer card out of 100.

| Half | Points | Judged by |
|---|---|---|
| The singer | **70** | `matching.player_artist_matches` against the card's Latin artist |
| The year | **30** | `game.is_correct_placement` against that player's own timeline |
| The song title | **0** | Captured, matched, and shown at the reveal — never scored |

The halves are independent on purpose. Naming the singer but misplacing the card scores
70, because knowing who sang it is most of what the game asks.

### The same-year rule

`is_correct_placement` uses **inclusive bounds on both sides** of the gap. That is not a
sloppy comparison — it is exactly the official rule that a card tying an existing year may
sit on either side of it. There is a test class named after the rule so nobody "fixes" it
into strict inequalities.

---

## 7. Name matching — two matchers, opposite temperaments

This is the least obvious part of the codebase, so it lives in one file (`matching.py`)
with both rules side by side.

**Catalogue matching (`artist_matches`) is strict.** It decides whether a Deezer search
result really is the artist a deck card names. A wrong match does not fail loudly — it
plays a completely different song mid-game.

A single similarity ratio cannot do this job, because the bands overlap:

```
"Teddy Afro"     vs "Teddy Karo"       0.90   ← a different artist
"Mulatu Astatke" vs "Mulatu Astatqe"   0.93   ← a transliteration variant we want
```

So it compares word by word. A wrong artist differs *wholly* in one word
(`afro`/`karo` = 0.50); a transliteration variant differs *slightly* in every word
(`astatke`/`astatqe` = 0.86).

**Player matching (`player_artist_matches`) is generous.** It decides whether a human
typing into a text box meant this artist. Amharic names reach Latin script with no agreed
spelling, and a player must never lose 70 points to a transliteration they had no way to
guess. A single distinctive name counts, in either direction:

```
Tilahun Gessesse  ✓    Telahun Gesesse  ✓    Gessesse  ✓    Tilahun  ✓
Aster Aweke       ✗ (a different artist)     mul       ✗ (under 4 chars)
"The Band" vs "The Walias Band"  ✗ (stopwords carry no identifying weight)
```

The known edge: two artists genuinely sharing a name would both match a one-word guess.
Accepted for a party game — the alternative robs players far more often than it helps.

**Do not collapse these into one function.** They are asymmetric by design: a wrong track
plays the wrong song silently, while a rejected true answer merely annoys someone.

---

## 8. Music sources

Deezer is primary, YouTube is the per-card fallback, and neither needs an API key.

Three findings from [FINDINGS.md](../FINDINGS.md) shape this code and are easy to undo by
accident:

1. **Search Deezer with field-scoped track search** (`q=artist:"…" track:"…"`). The
   `/search/artist` endpoint is unreliable for Amharic names — it answers "Teddy Afro"
   with "Teddy Karo", an unrelated artist. This single choice moves catalogue coverage of
   major Amharic artists from 37% to 87%.
2. **Amharic-script search returns nothing.** `አስቴር አወቀ` yields zero results. Query by
   Latin transliteration; the Amharic strings are carried alongside purely for display.
3. **Preview URLs are HMAC-signed and expire 15 minutes after issue.** The deck therefore
   stores Deezer *track ids*, never URLs, and `audio_for()` resolves a fresh one per
   round. Baking URLs into the deck produces a game that works in testing and dies twenty
   minutes into the first real session.

A card with neither a Deezer match nor a YouTube id is rejected at build time rather than
silently added as unplayable.

---

## 9. The deck

Release years **cannot** be taken from an API. MusicBrainz returns three different answers
for "Billie Jean"; Deezer and iTunes both report reissue dates. So every year is confirmed
by a human, once, offline, and the deck is then a committed asset the game just reads.

```bash
cd server
./.venv/bin/python tools/build_deck.py add            # one at a time, interactive
./.venv/bin/python tools/build_deck.py import x.tsv   # bulk
./.venv/bin/python tools/build_deck.py list
./.venv/bin/python tools/build_deck.py check          # re-probe every card's sources
```

Seed format, tab-separated, `#` comments allowed:

```
year <TAB> artist_latin <TAB> title_latin [<TAB> artist_am <TAB> title_am <TAB> youtube_url]
```

Artist, title and year are enough — a YouTube URL is only needed for songs Deezer does not
carry. The shipped starter deck is 16 Amharic songs spanning 1966–2026.

> **The starter deck's years are unverified.** They are a best effort so the game is
> playable, and the file says so at the top. They need a human pass before the deck is
> fair to play with.

---

## 10. Testing

106 tests. `cd server && ./.venv/bin/python -m pytest tests/ -q`

| File | Covers |
|---|---|
| `test_game.py` | Placement validation including every same-year edge case; round resolution; 70/30 independence |
| `test_matching.py` | Both matchers, in both directions — what must match and what must not |
| `test_rooms.py` | Seating, reconnect, turn order, and that no unrevealed card leaks into a payload |
| `test_sources.py` | URL parsing, decoration stripping, catalogue matching |
| `test_integration.py` | Real sockets against the real ASGI app: full rounds, out-of-turn refusal, reconnect, watchers receiving audio |

The integration suite exists because the bugs that actually bit during development were
all in the wiring rather than the rules — who is told what, when a round advances, and
whether a reconnecting player is put back together completely.

---

## 11. Deliberately not built

- **Voice chat.** Players use WhatsApp, Discord or Meet alongside. The lobby reminds
  everyone to wear headphones, or the music echoes through their microphones.
- **Tokens to spend.** The field exists on `Player` but nothing spends it yet.
- **Pro/Expert modes.** They would need exact-year or title matching.
- **Accounts, matchmaking, public rooms.** Private rooms among friends only.
