# Feature: Hitster Remote — Game Design

**Date:** 2026-09-07

**Author:** Lensa Billion Mudda (with Claude)

**Status:** Draft — awaiting review

## Overview

Design for a remote music timeline game for a group of friends, inspired by
[Hitster](https://hitstergame.com). Players hear a song, guess when it came out, and
build a chronological timeline. This document covers the *game* design — what makes it
fun over a video call with 3–6 people — not the infrastructure, which is in
[FINDINGS.md](../../../../FINDINGS.md).

**The design thesis in one line:** a faithful Hitster port would be a bad remote game,
because Hitster is turn-based and turn-based means dead air. The fix is to make every
player act on every round while keeping the timeline economy intact.

## Goals

- Fun for **3–6 friends on a video call**, not just two people.
- **Nobody is ever idle.** Every player does something every round.
- **Latency-fair.** A player in Addis Ababa and a player in San Francisco have equal
  chances on every mechanic.
- **No install, no accounts, no subscriptions.** Room code in a browser, phone-friendly.
- **The deck is personal to the group.** Their music, not a stranger's list of hits.
- Survives a dropped connection without ending the game.

## Non-Goals

- **Voice chat.** Players use WhatsApp, Discord or Meet alongside. Building WebRTC voice
  would cost more than the rest of the game combined.
- **Public matchmaking or accounts.** Private rooms among friends only.
- **Pro/Expert modes at first.** They need free-text artist and title matching across
  two languages and transliterated Amharic titles. Deferred, not abandoned.
- **Replicating the physical deck.** No QR codes, no printed cards, no Spotify.
- **Mobile apps.** Browser only.

## Background

### What the physical game does well

Hitster's real engine is not the trivia. It is the **steal**: you may interrupt an
opponent's placement, spend a token, and take the card if you know better. That forces
every player to form an opinion on every card, because staying quiet while an opponent
fumbles is how you lose. The full rules are summarised in
[FINDINGS.md §1](../../../../FINDINGS.md).

### Why a faithful port would fail

Around a table, the players who are not placing a card are still *in the game* — they
watch, heckle, argue, and reach for the steal. On a video call, a player with nothing to
do is a player looking at their other monitor.

Board-game design treats downtime as the primary enemy, and the standard remedy is
simultaneous play: making everyone act at once is the most direct way to eliminate it,
and it keeps engagement at 100% of participants rather than 1/N.

This gets *worse* as the group grows. At 6 players a strict turn order means each person
is idle for five rounds out of six.

### What the successful remote games actually do

| Game | Mechanic | Lesson |
|---|---|---|
| **Jackbox** | Shared screen + everyone's phone as a private controller; room code, no install | Private per-player information is the thing phones are *good* at |
| **Jackbox (remote adaptations)** | Extended timers for lag; avatars that raise hands and point | Recreate the in-room physicality explicitly, or it is simply absent |
| **Gartic Phone** | Everyone draws simultaneously, then one communal reveal | The reveal is reliably the funniest moment of the night — make it a production |
| **skribbl.io** | Guess in a shared channel while one person draws | Even spectators need an input |
| **Music trivia generally** | Decade and nostalgia framing | The hook is shared memory, not knowledge |

Jackbox's own summary of its design philosophy is the most useful sentence in the
research: **winning is secondary; the objective is to make the group laugh.** A design
that optimises for competitive fairness at the cost of the social moment has optimised
the wrong thing.

## Design

### Approach

Three changes turn Hitster into a remote group game.

#### 1. Simultaneous shadow placement — the core change

Every round, **every player privately places the card**, not just the active one.

- The **active player's** placement is real. Correct → they keep the card on their
  timeline. Wrong → they lose it.
- **Everyone else's** placement is a *shadow guess* on their own timeline. It does not
  earn them a card outright. It resolves two things at once:
  - **Right shadow guess → +1 token.** This replaces "name the artist and title for a
    token" as the main token source, and it means paying attention always pays.
  - **Active player wrong + your shadow guess right → you steal the card.** This is the
    HITSTER steal, but nobody has to shout.

All placements are sealed until the reveal, so nothing is first-come-first-served and
**no latency advantage exists**. This is the same mechanism as the sealed challenge
window in [FINDINGS.md §4](../../../../FINDINGS.md), promoted from an edge case to the
core loop.

Card economy stays intact: at most one card enters a timeline per round, so the game
does not accelerate as the group grows.

**Why this works:** it converts N−1 idle players into N engaged players without adding a
single new rule for a player to learn. From the player's seat the instruction is always
the same — *where does this song go?* — and only the stakes change depending on whose
turn it is.

#### 2. The group builds the deck

Before the first game, each player contributes ~15 songs. The deck is then **their
group's music**, and after each reveal the game shows **who added the song**.

This is the single highest-value fun mechanic in the design and it costs almost nothing
to build. It turns an abstract trivia question into a social one — *who put this in?* —
and it solves the cultural-fairness problem directly. A deck of Western hits makes the
game a memory test for whoever grew up with them; a deck each friend stocked personally
cannot be one-sided, and Deezer's Ethiopian catalogue is well covered
([FINDINGS.md §F6](../../../../FINDINGS.md)).

Contributions stay hidden until reveal.

#### 3. The reveal is a production

Gartic Phone's lesson. When the window closes, do not quietly update state. Run a
sequence on every screen at once:

1. All sealed placements flip simultaneously.
2. The year lands, big, with the album art.
3. Correct placements highlight; near-misses show how close.
4. Steals resolve visibly — *"Sara took that card from you."*
5. Who added the song is revealed last.

This is the moment the group talks over each other. It is worth more engineering
attention than the placement UI.

### Components

| Component | Responsibility |
|---|---|
| Room + identity | Room codes, durable player UUIDs, reconnect. `[hitster-3tq3]` |
| Deck service | Curated `deck.json`, per-group contributions, draw order. `[hitster-w8fp]` |
| Audio | Server resolves fresh Deezer preview per round; clients play locally in sync. `[hitster-wtjw]` `[hitster-fvtg]` |
| Round engine | Phase machine, sealed placement collection, reveal resolution. `[hitster-e7v4]` |
| Placement validator | Gap correctness including the same-year rule. `[hitster-zaxj]` |
| Timeline UI | Every player's timeline on every screen; tap-to-place gaps. `[hitster-pdhg]` |
| Reveal sequence | The simultaneous flip, scoring animation, attribution. |
| Reactions | Lightweight emoji pings during playback. |

### Round state machine

```
lobby → drawing → playing (30s clip) → placing (sealed, all players)
      → revealing (simultaneous flip + resolution) → scoring → drawing …
                                                            → over (win condition)
```

Only `placing` accepts player input, and it accepts it from **everyone**.

### Rules that carry over unchanged

- Timeline is chronological, earliest at the left.
- **Same-year rule:** if the card's year matches an adjacent card, either side counts.
  `[hitster-zaxj]`
- Tokens cap at 5.
- Spend 1 token to skip a song you have no idea about.
- Spend 3 tokens to take a card placed for free.

### Rules that change for remote group play

| Physical rule | Remote replacement | Why |
|---|---|---|
| Shout "HITSTER!" first | Sealed simultaneous challenge | Click races are unfair across asymmetric latency |
| Only the active player acts | Everyone places every round | Removes N−1 idle players |
| Earn a token by naming artist + title | Earn a token by a correct shadow guess | Free-text naming is unreliable across languages; keep naming for Pro mode later |
| First to 10 cards | **First to 8**, or most cards after a set round count | 10 cards × 6 players is too long for one call |
| DJ scans a card | Server draws; no DJ role | The DJ role exists only because of physical QR codes |

### Social presence

Jackbox explicitly rebuilt hand-raising and pointing as on-screen actions for remote
play, because the physical versions simply vanish. Cheap equivalents here:

- **Reaction pings** during playback (😍 🤢 🔥 ❓) shown on all screens.
- **"I know this one"** confidence tap before placing — bluffable, visible to others,
  and free tension.
- **Extended timer option**, as Jackbox added for lag. Host-adjustable, not fixed.

### Audio and the parallel call

Each client plays its own copy of the same 30-second preview, started from a common
timestamp. Sub-second drift is invisible in this game and this avoids peer-to-peer audio
entirely ([FINDINGS.md §3](../../../../FINDINGS.md)).

**The echo problem:** if players sit on a voice call without headphones, each person's
microphone rebroadcasts the music. Mitigations, in order of preference:

1. Headphone prompt in the lobby (default).
2. **Host-only audio** toggle — one player unmutes and the call carries the song. Lower
   quality, but it always works and needs no coordination.

## Implementation Plan

Beads already exist for the infrastructure. This plan adds the game-design work on top
and sequences both.

### Phase 1: Playable core

The smallest thing that is actually the game.

- [ ] Durable player identity and reconnect `[hitster-3tq3]`
- [ ] Deck-builder CLI and a first curated deck `[hitster-w8fp]` `[hitster-g1dh]`
- [ ] Round engine with the sealed simultaneous placement loop `[hitster-e7v4]`
- [ ] Placement validator with same-year handling `[hitster-zaxj]`
- [ ] Audio path: server-side preview resolution + client prefetch `[hitster-wtjw]` `[hitster-fvtg]`
- [ ] Timeline UI, tap-to-place, all timelines visible `[hitster-pdhg]`
- [ ] Basic reveal: simultaneous flip and resolution
- [ ] Withhold unrevealed years from clients `[hitster-sces]`

**Exit criteria:** four people in three locations play a full game without anyone being
idle and without anyone seeing a year early.

### Phase 2: The fun layer

What turns a working prototype into something they ask to play again.

- [ ] Collaborative deck contribution + "who added this" attribution
- [ ] Full reveal sequence with album art and near-miss display
- [ ] Reaction pings and the confidence tap
- [ ] Token economy: skip, buy-a-card, shadow-guess rewards `[hitster-8fix]`
- [ ] Host-adjustable timers and host-only audio toggle

### Phase 3: Hardening

- [ ] Reconnect resync, host migration, generous timers `[hitster-nq2l]`
- [ ] Deploy reachable from both continents `[hitster-d1sj]`
- [ ] Remove speed-quiz remnants `[hitster-kxwr]`
- [ ] YouTube per-card fallback `[hitster-e08z]`

## Testing Strategy

- **Unit:** placement validator is the correctness core — empty timeline, single card,
  duplicate years, ties at both ends, inserts at either extreme.
- **Unit:** reveal resolution — active correct, active wrong with one stealer, active
  wrong with several stealers, nobody correct.
- **Integration:** a simulated 6-player room driven through a full round, asserting no
  client receives an unrevealed year.
- **Manual, throttled:** play a round with one client on a deliberately degraded
  connection; confirm reconnect restores the timeline.
- **Playtest:** the real group, on a real call. The only test that can tell us whether
  it is fun. Watch for dead air, confusion at the reveal, and whether anyone reaches for
  their phone mid-round.

## Rollout Plan

Deploy to a small instance reachable from both continents; the server moves only JSON,
since audio comes from Deezer's CDN directly to each client. Share a room code. No
staged rollout — the audience is a handful of friends.

The blocking prerequisite is `[hitster-ci18]`: confirm a Deezer preview actually plays
from Addis Ababa. Everything else has a fallback; that does not.

## Open Questions

1. **Win condition** — first to 8 cards, or fixed round count with most cards winning?
   Fixed rounds makes session length predictable, which matters when people have to
   leave a call. Recommendation: fixed round count, configurable.
2. **Does a wrong active placement discard the card, or return it to the deck?**
   Discarding is the physical rule; returning it keeps a good song in play.
3. **Should shadow guesses cost anything?** Currently free, which maximises engagement.
   Charging a token to steal is more faithful but punishes participation.
4. **Deck size per player.** 15 songs each × 5 friends = 75 cards. Enough for several
   sessions before repeats become noticeable.
5. **Do we show whose timeline is closest to winning?** Visible pressure is fun but can
   make a runaway leader dispiriting.
6. **Teams for 7+?** Out of scope now; worth not designing ourselves out of.

## References

- [FINDINGS.md](../../../../FINDINGS.md) — API verification, music sources, rules summary
- [Hitster official rules](https://hitstergame.com/en-us/how-to-play/) ·
  [V3 rules](https://hitstergame.com/en-us/how-to-play-v3/)
- [Jackbox design principles](https://www.builtinchicago.org/articles/jackbox-games-design-party-pack)
- [How Jackbox built a remote-play version](https://news.xbox.com/en-us/2024/09/13/how-jackbox-games-took-a-beloved-party-game-and-made-a-new-remote-play-version/)
- [Reducing downtime in game design](https://boardgamedesigncourse.com/how-to-reduce-downtime-in-your-game/) ·
  [7 ways to reduce downtime](https://entrogames.substack.com/p/7-ways-to-reduce-downtime)
- [Drawing game architectures: skribbl, Gartic Phone](https://dev.to/adzhydra/comparing-drawing-game-architectures-skribbl-gartic-phone-and-artbitrator-36j2)
- Prior art: [Timtam/hitster](https://github.com/Timtam/hitster) ·
  [ruuda/hitsgame](https://github.com/ruuda/hitsgame) ·
  [Born2Root/HitStar](https://github.com/Born2Root/HitStar)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
