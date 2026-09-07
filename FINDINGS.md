# Research Findings — Hitster, Remotely

Working reference for rebuilding this project as a real Hitster game playable between
Addis Ababa and San Francisco. Every finding below was verified on **2026-09-07** by
calling the live APIs, not by reading documentation.

Issue IDs in brackets are tbd issues — run `tbd ready` to see what is unblocked.

---

## 1. What the game actually is

Published by Jumbo Games. 300+ tracks spanning 1908–2021, 2–10 players, playable in
teams. Each card carries a QR code on one face and artist / title / year on the other.
The Hitster app scans the QR and hands playback to Spotify — the app is a scanner and a
rights wrapper, not a music player.

| Rule | Detail |
|---|---|
| **Objective** | Build a chronological timeline. First to **10 correctly placed cards** wins. |
| **Setup** | One card face-up seeds each timeline. Original starts with 2 tokens, Pro 5, Expert 3. Cap 5. |
| **Turn** | DJ plays the song → active player places it **face-down** in a gap → flip. Right, they keep it; wrong, discard. |
| **Same-year rule** | If the card's year matches one already placed, **either side of it counts as correct**. |
| **Earn a token** | Name artist *and* title on your turn — even if you then misplace the card. |
| **Spend tokens** | 1 = skip the song. 3 = take the top card placed free (V3: then skip your next turn). |
| **The steal** | Shout **"HITSTER!"** before the flip, spend a token, point at the right gap. Right = steal the card. Wrong = lose the token. |
| **Modes** | Original (placement only) · Pro (+artist & title) · Expert (+exact year) · Co-op (shared timeline, 5 shared tokens) |

> **The steal is the load-bearing rule.** It forces every player to form an opinion on
> every card, because staying quiet while an opponent fumbles is how you lose. Drop it
> and this becomes a solitaire quiz with spectators. It is also the single hardest rule
> to move online — see §4.

---

## 2. Verified findings

### F1 — Spotify previews are gone ❌

Spotify removed `preview_url` from the Web API for any app not already in extended
quota mode on **27 Nov 2024**. Extended mode now requires 250k monthly active users,
so new apps cannot get it back. The route the retail game uses is closed to us.

### F2 — Spotify's Web Playback SDK needs Premium per listener ❌

It creates a Connect device in the browser and refuses to stream without a *full*
Premium subscription — mobile-only tiers such as Premium Mini are explicitly excluded.
Remotely every player is their own speaker, so this means Premium for both players plus
an OAuth handshake every session. Rejected.

### F3 — Deezer's public API needs no key at all ✅

Search and track lookup are open and unauthenticated, and return a real 30-second MP3.
Pulled end to end:

```
GET api.deezer.com/search?q=track:"Yesterday" artist:"The Beatles"
GET cdnt-preview.dzcdn.net/api/1/1/b/9/...mp3
  -> http=200  bytes=479827  type=audio/mpeg
```

~500 KB per round is the entire audio payload. No video stream, no player SDK, no login.
Deezer's developer terms permit non-commercial personal use of previews; a private game
between two friends sits inside that.

**→ Primary audio source.**

### F4 — Preview URLs expire in 15 minutes ⚠️

Every preview link is HMAC-signed with a short expiry. Decoded and timed:

```
exp=1788782138  ->  2026-09-07 11:55:38 UTC
fetched at      ->  2026-09-07 11:40:55 UTC
fresh fetch     ->  expires in 15.0 minutes
```

The deck therefore **cannot store playable URLs**. It stores Deezer track IDs, and the
server resolves a live URL when a round starts. Bake URLs into a JSON file and the game
works perfectly in testing, then dies about twenty minutes into the first real session.

**→ `[hitster-wtjw]` Resolve preview URLs server-side at round start.**

### F5 — Release years cannot be automated ⚠️

The finding that most shapes the build. MusicBrainz, asked for the first release date of
one of the best-documented singles in pop history:

```
Billie Jean | Michael Jackson | first-release-date = 1985
Billie Jean | Michael Jackson | first-release-date = None
Billie Jean | Michael Jackson | first-release-date = 1982
```

Three answers, one correct. Deezer's `album.release_date` fails from the other
direction — searching "Yesterday" returns it off *1 (Remastered)*, which would date the
Beatles to 2000. The iTunes Search API has the same defect: its `releaseDate` is the
iTunes availability date, not the original release.

Reissues, remasters and compilations poison every automated source. This is exactly why
Jumbo hand-curates 300 cards, and why the deck here has to be curated too.

**→ `[hitster-w8fp]` Build the deck-builder CLI · `[hitster-g1dh]` Curate the deck.**

### F6 — Deezer's Amharic catalogue is good, but only via the right endpoint ✅⚠️

Measured across 24 major Amharic artists, counting only playable tracks whose artist
name actually matches the one requested:

```
21/24 (87%)  field-scoped track search:  q=artist:"Teddy Afro"
 9/24 (37%)  artist endpoint:            /search/artist  +  /artist/{id}/top
```

**The endpoint choice decides the answer.** `/search/artist` is unreliable for these
names — it answers "Teddy Afro" with "Teddy Karo", an unrelated artist with no playable
tracks — while field-scoped track search returns 23 playable Teddy Afro tracks. An
earlier revision of this document used the artist endpoint, concluded contemporary
Amharic pop was largely absent, and was wrong. Never use `/search/artist` here.

Remaining gaps at 87%: Gigi, Munit Mesfin, Yehune Belay. These fall back to YouTube.

Two further constraints:

- **Amharic-script search returns nothing.** `አስቴር አወቀ` and `ማህሙድ አህመድ` both yield zero
  results. Search by Latin transliteration; carry the Amharic strings separately for
  display.
- **A returned artist must be verified, not trusted.** A whole-string similarity ratio
  cannot do this: "Teddy Afro" vs "Teddy Karo" (wrong artist) scores 0.90, while
  "Mulatu Astatke" vs "Mulatu Astatqe" (a transliteration variant we want) scores 0.93.
  Word-by-word comparison separates them, because a wrong artist differs wholly in one
  word while a variant differs slightly in every word. See `server/sources.py`.

This is the project's advantage over the retail box, which has no Amharic content at all.

### F7 — Unverified: does the Deezer CDN reach Ethiopia? ⚠️

Verified from the US only. Every other finding has a fallback; this one does not.

**→ `[hitster-ci18]` Verify before building on it. Blocks the audio architecture.**

### F8 — Source comparison

| Source | Auth | Cost to player | Clip | Verdict |
|---|---|---|---|---|
| **Deezer public API** | none | free | 30 s MP3 | **Primary** |
| YouTube IFrame API | none to embed | free | full video | Per-card fallback |
| Spotify Web Playback SDK | OAuth each | Premium each | full track | Rejected (F2) |
| Spotify `preview_url` | — | — | — | Withdrawn (F1) |
| iTunes Search API | none | free | 30 s M4A | Year data unusable (F5) |
| Self-hosted MP3s | none | free | anything | Best audio, worst legality |

---

## 3. What breaks when you go remote

Five assumptions in the boxed game stop holding once players are 12,000 km apart.

1. **One phone, one room, one speaker.** Remotely every player is their own speaker.
   Do *not* stream audio peer-to-peer — the server broadcasts a track id and a start
   timestamp, and each browser plays its own copy. Sub-second drift is invisible in a
   game where nobody compares waveforms. `[hitster-fvtg]`
2. **Cards on a table are public.** Every timeline must render on every screen, live.
   An opponent's row is not decorative — it is the information the steal is played on.
   `[hitster-pdhg]`
3. **"First to shout" is unfair over latency.** See §4. `[hitster-r80t]`
4. **Face-down placement is a physical secret.** The server must withhold the pending
   card and reveal to everyone at once. Anyone can open devtools. `[hitster-sces]`
5. **Nobody disconnects from a table.** A dropped socket must not cost a timeline.
   `[hitster-3tq3]` `[hitster-nq2l]`

---

## 4. Design decision: the sealed challenge window

Addis Ababa ↔ San Francisco is a few hundred milliseconds each way, and it is not
symmetric. A click race hands the steal to whoever has better transit — permanently.
This needs a *different mechanism*, not a faster one.

**Replace the shout race with a sealed window:**

- The active player commits a face-down placement.
- A 10-second window opens. Every other player privately marks the gap they believe is
  correct.
- Everything reveals at once — placement and challenges together.
- Nothing is first-come-first-served, so no latency advantage exists.
- If two challengers are both correct, award by earliest server receipt and refund both
  tokens.

Same tension, no unfairness. Arguably a better rule than the original. `[hitster-r80t]`

---

## 5. Disposition of the existing code

The plumbing survives; the game does not. What is in `server/` today is a speed quiz —
race to type an artist, scored on reaction time — and Hitster is turn-based and
positional with no clock at its core.

| Piece | Fate | Why |
|---|---|---|
| FastAPI + python-socketio ASGI mount | **Keep** | Right shape for this. |
| Room codes, lobby, join flow | **Keep** | `rooms.py` needs its state swapped, not its lifecycle. |
| Vite + React + Tailwind, `socket.js` | **Keep** | Screens get replaced; the shell is sound. |
| `YouTubePlayer.jsx` | **Demote** | Becomes a per-card fallback behind `<audio>`. `[hitster-e08z]` |
| Players keyed by socket `sid` | **Replace** | A refresh destroys the player. Fatal here. `[hitster-3tq3]` |
| `score_guess`, speed bonus, fuse.js | **Delete** | Wrong game. `[hitster-kxwr]` |
| `parse_artist_song` off YouTube titles | **Delete** | Deezer returns clean structured fields. |
| Round auto-advance timers | **Replace** | Turn order and a challenge window, not a countdown. |

`fuzzy_match()` is worth keeping — it becomes relevant again for Pro/Expert naming.

---

## 6. Build order

Run `tbd ready` for the live list. The intended sequence:

1. `[hitster-ci18]` Verify Deezer reaches Ethiopia — **do this before anything else**
2. `[hitster-3tq3]` Durable UUID player identity — small now, a rewrite later
3. `[hitster-w8fp]` Deck-builder CLI → `[hitster-g1dh]` curate 80–120 cards
4. `[hitster-e7v4]` Hitster game model → `[hitster-zaxj]` placement validator
5. `[hitster-wtjw]` + `[hitster-fvtg]` Audio path
6. `[hitster-pdhg]` Timeline UI — the centrepiece
7. `[hitster-r80t]` + `[hitster-8fix]` Tokens and the sealed challenge
8. `[hitster-d1sj]` + `[hitster-nq2l]` Deploy and resilience

---

## 7. Prior art worth reading

- [Timtam/hitster](https://github.com/Timtam/hitster) — most complete web
  implementation. Rust/Rocket + React/TS + SQLite + Docker. Sources audio by
  downloading from YouTube with `yt-dlp` and normalising via ffmpeg — heavier and
  legally murkier than Deezer previews, but its game-state modelling is the closest to
  what we need.
- [ruuda/hitsgame](https://github.com/ruuda/hitsgame) — generates printable QR cards
  from your own library. Good reference for the deck-builder.
- [Born2Root/HitStar](https://github.com/Born2Root/HitStar),
  [david-auk/Mixster](https://github.com/david-auk/Mixster) — fully self-hosted with
  local music files. Useful if licensing ever pushes that way.
- [mholzi/beatify](https://github.com/mholzi/beatify) — Home Assistant integration
  spanning six streaming backends; worth skimming for how it abstracts music sources.

Jumbo ships no remote mode and the official FAQ does not mention online play. Players on
BoardGameGeek improvise it over video calls with one person holding the deck. Nobody has
built the version described here.

---

## 8. Open questions

| Question | Current answer |
|---|---|
| Does Deezer's CDN reach Ethiopia? | **Unverified — blocking.** `[hitster-ci18]` |
| How big is the first deck? | 80–120 cards, global/Ethiopian interleaved. `[hitster-g1dh]` |
| Which modes ship first? | Original alone. Pro needs free-text matching across two languages and transliterated Amharic titles — genuinely hard. Expert is a stretch; co-op is a different game. |
| Voice chat: build or borrow? | **Borrow.** Run WhatsApp or Meet alongside; put a headphone reminder in the lobby or the mics will echo the music at each other. WebRTC voice would cost more than the rest of the game combined. |

---

## Sources

Rules: [official](https://hitstergame.com/en-us/how-to-play/) ·
[V3](https://hitstergame.com/en-us/how-to-play-v3/) ·
[FAQ](https://hitstergame.com/en-us/faq/) ·
[BGG](https://boardgamegeek.com/boardgame/318243/hitster) —
APIs: [Spotify API changes](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api) ·
[Web Playback SDK](https://developer.spotify.com/documentation/web-playback-sdk) ·
[Deezer terms](https://developers.deezer.com/termsofuse) ·
[MusicBrainz](https://musicbrainz.org/doc/MusicBrainz_API)
