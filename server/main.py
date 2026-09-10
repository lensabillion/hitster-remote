"""Socket layer.

Room state is fanned out per viewer rather than broadcast, because what a player
may see differs: the current card is withheld from everyone until the reveal,
and each player is told only whether they themselves have sealed an answer.
Broadcasting one payload would leak the answer into devtools.
"""

from __future__ import annotations

import asyncio
import contextlib
import os

import socketio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db import card_id, db
from game import Card, Phase
from rooms import (
    ANSWER_SECONDS,
    CLIP_SECONDS,
    Room,
    create_room,
    drop_empty_rooms,
    get_room,
    rooms,
    serialize,
)
from sources import artist_matches, deezer_fresh_preview, extract_youtube_id

load_dotenv()

PORT = int(os.getenv("PORT", "3001"))
ORIGINS = os.getenv("CORS_ORIGINS", "*")
MIN_DECK = 6
EARLIEST_YEAR, LATEST_YEAR = 1900, 2030
# Optional shared secret for editing the deck. Unset means open, which matches
# the rest of the game — there are no accounts anywhere. Set it if the URL ever
# escapes the group.
DECK_TOKEN = os.getenv("DECK_TOKEN", "")

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=ORIGINS)
api = FastAPI()
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ORIGINS == "*" else ORIGINS.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# One timer task per room, so a new round always cancels the previous schedule.
_timers: dict[str, asyncio.Task] = {}


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    await db.connect()
    yield
    await db.close()


api.router.lifespan_context = lifespan


@api.get("/health")
async def health() -> dict:
    return {"ok": True, "rooms": len(rooms), "cards": await db.card_count()}


# ---------- deck editing ----------
#
# Every project that builds this game curates its songs by hand — Timtam ships
# 7,239 entries in a committed YAML. The only real question is whether the
# tooling makes it pleasant, so the deck is editable from the game itself rather
# than only from a text file. That also lets a player on another continent add
# the songs they actually know.


class NewCard(BaseModel):
    artist_latin: str = Field(min_length=1, max_length=120)
    title_latin: str = Field(min_length=1, max_length=160)
    year: int = Field(ge=EARLIEST_YEAR, le=LATEST_YEAR)
    artist_am: str = Field(default="", max_length=160)
    title_am: str = Field(default="", max_length=200)
    youtube_url: str = Field(default="", max_length=300)
    added_by: str = Field(default="", max_length=60)


def _check_token(token: str | None) -> None:
    if DECK_TOKEN and token != DECK_TOKEN:
        raise HTTPException(status_code=403, detail="Wrong deck token")


@api.get("/deck")
async def deck_list() -> dict:
    cards = await db.all_cards()
    return {
        "count": len(cards),
        "cards": [
            {
                "id": c["id"], "year": c["year"],
                "artistLatin": c["artist_latin"], "titleLatin": c["title_latin"],
                "artistAm": c["artist_am"], "titleAm": c["title_am"],
                "youtubeId": c["youtube_id"], "deezerTrackId": c["deezer_track_id"],
                "addedBy": c["added_by"],
            }
            for c in cards
        ],
    }


@api.get("/deck/search")
async def deck_search(artist: str = "", title: str = "") -> dict:
    """Look a song up on Deezer so the player does not have to hunt for a link.

    Returns candidates rather than picking one: a wrong match plays a different
    song mid-game, and only a person can tell which of these is the song they
    meant.
    """
    if not artist.strip():
        return {"candidates": [], "note": "Type an artist name first."}
    import httpx

    query = f'artist:"{artist.strip()}"'
    if title.strip():
        query += f' track:"{title.strip()}"'
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.get(
                "https://api.deezer.com/search", params={"q": query, "limit": 8}
            )
            data = r.json().get("data", [])
    except Exception:
        return {"candidates": [], "note": "Deezer did not answer. Add a YouTube link instead."}

    out = [
        {
            "deezerTrackId": t["id"],
            "artist": t["artist"]["name"],
            "title": t["title"],
            "album": (t.get("album") or {}).get("title", ""),
            "preview": t.get("preview", ""),
            "artistMatches": artist_matches(artist, t["artist"]["name"]),
        }
        for t in data
        if t.get("preview")
    ]
    note = "" if out else (
        "Nothing found. Deezer rate-limits in bursts and answers with an empty "
        "list rather than an error — try again shortly, or add a YouTube link."
    )
    return {"candidates": out, "note": note}


@api.post("/deck")
async def deck_add(card: NewCard, deezer_track_id: int | None = None, token: str | None = None) -> dict:
    _check_token(token)
    youtube = extract_youtube_id(card.youtube_url) if card.youtube_url else None
    if not deezer_track_id and not youtube:
        raise HTTPException(
            status_code=400,
            detail="A card needs a playable source: pick a Deezer match or add a YouTube link.",
        )
    row = {
        "id": card_id(card.artist_latin, card.title_latin),
        "year": card.year,
        "artist_latin": card.artist_latin.strip(),
        "title_latin": card.title_latin.strip(),
        "artist_am": card.artist_am.strip(),
        "title_am": card.title_am.strip(),
        "youtube_id": youtube or "",
        "deezer_track_id": deezer_track_id,
        "added_by": card.added_by.strip(),
    }
    await db.upsert_cards([row])
    return {"ok": True, "id": row["id"], "count": await db.card_count()}


@api.delete("/deck/{card}")
async def deck_delete(card: str, token: str | None = None) -> dict:
    _check_token(token)
    removed = await db.delete_card(card)
    if not removed:
        raise HTTPException(status_code=404, detail="No card with that id")
    return {"ok": True, "count": await db.card_count()}


app = socketio.ASGIApp(sio, other_asgi_app=api)


# ---------- fan-out ----------


async def audio_for(card: Card) -> dict:
    """Resolve a playable source. Deezer preview URLs expire ~15 minutes after
    issue, so this runs per round and the URL is never stored."""
    if card.deezer_track_id:
        if url := await deezer_fresh_preview(card.deezer_track_id):
            return {"source": "deezer", "url": url, "clipSeconds": CLIP_SECONDS}
    if card.youtube_id:
        return {
            "source": "youtube",
            "youtubeId": card.youtube_id,
            "clipSeconds": CLIP_SECONDS,
        }
    return {"source": "none", "clipSeconds": CLIP_SECONDS}


async def send_audio(room: Room, sid: str) -> None:
    """Give one socket the current round's audio.

    Called at round start and again whenever a player (re)joins mid-round --
    without this a reconnecting player can see the round but not hear the song.
    Resolving fresh each time also sidesteps Deezer's 15-minute URL expiry.
    """
    if room.current_card is None or room.phase is not Phase.ANSWERING:
        return
    cue = await audio_for(room.current_card)
    await sio.emit(
        "round:audio",
        {**cue, "roundNo": room.round_no, "startAt": room.clip_started_ms},
        to=sid,
    )


async def push_state(room: Room) -> None:
    for player in room.players.values():
        if player.sid:
            await sio.emit("room:state", serialize(room, player.id), to=player.sid)


async def fail(sid: str, message: str) -> None:
    await sio.emit("error", {"message": message}, to=sid)


# ---------- round scheduling ----------


def cancel_timer(code: str) -> None:
    if task := _timers.pop(code, None):
        task.cancel()


async def run_round(code: str) -> None:
    """The answer window is a ceiling, not a pace.

    Answering is open from the moment the clip starts, so a player who knows the
    song in two seconds can say so and stop listening. This timer only exists so
    one absent player cannot stall the table.
    """
    try:
        await asyncio.sleep(ANSWER_SECONDS)
        room = get_room(code)
        if room and room.phase is Phase.ANSWERING:
            await do_reveal(room)
    except asyncio.CancelledError:
        pass


async def start_round(room: Room) -> None:
    card = room.begin_round()
    if card is None:
        await finish_game(room)
        return

    for player in room.players.values():
        if player.sid:
            await send_audio(room, player.sid)
    await push_state(room)

    cancel_timer(room.code)
    _timers[room.code] = asyncio.create_task(run_round(room.code))


async def do_reveal(room: Room) -> None:
    cancel_timer(room.code)
    room.reveal()
    await push_state(room)
    await persist(room)


async def finish_game(room: Room) -> None:
    # Otherwise the round's answer-window task outlives the game it belonged to.
    cancel_timer(room.code)
    room.phase = Phase.OVER
    leader = room.leader()
    await sio.emit(
        "game:over",
        {
            "winnerId": leader.id if leader else None,
            "winnerName": leader.name if leader else None,
            "standings": [
                {"id": p.id, "name": p.name, "score": p.score} for p in room.standings()
            ],
        },
        room=room.code,
    )
    await push_state(room)


async def persist(room: Room) -> None:
    """Snapshot what a returning player needs; live round state stays in memory."""
    await db.save_room_state(
        room.code, room.phase.value, room.round_no, room.active_seat
    )
    for player in room.players.values():
        await db.save_player_state(
            room.code, player.id, player.tokens, [c.id for c in player.timeline]
        )


# ---------- events ----------


@sio.event
async def connect(sid, environ):  # noqa: ANN001
    pass


@sio.event
async def disconnect(sid):  # noqa: ANN001
    """A dropped socket must never cost a seat, a timeline, or a score."""
    for room in list(rooms.values()):
        if room.detach_socket(sid) is not None:
            room.promote_host_if_needed()
            await push_state(room)
    drop_empty_rooms()


@sio.on("room:create")
async def on_create(sid, data):  # noqa: ANN001
    player_id = (data or {}).get("playerId", "").strip()
    name = ((data or {}).get("name") or "Host").strip()
    if not player_id:
        return await fail(sid, "Missing player id")

    room = create_room(player_id)
    room.add_player(player_id, name, sid)
    await sio.enter_room(sid, room.code)

    await db.upsert_player(player_id, name)
    await db.create_room(room.code, player_id)
    await db.seat_player(room.code, player_id, 0, room.players[player_id].tokens)

    await sio.emit("room:joined", {"code": room.code}, to=sid)
    await push_state(room)


@sio.on("room:join")
async def on_join(sid, data):  # noqa: ANN001
    code = (data or {}).get("code", "")
    player_id = (data or {}).get("playerId", "").strip()
    name = ((data or {}).get("name") or "Player").strip()
    room = get_room(code)

    if not room:
        return await fail(sid, "No room with that code")
    if not player_id:
        return await fail(sid, "Missing player id")
    if player_id not in room.players and room.phase is not Phase.LOBBY:
        return await fail(sid, "That game has already started")

    room.add_player(player_id, name, sid)
    room.promote_host_if_needed()
    await sio.enter_room(sid, room.code)

    await db.upsert_player(player_id, name)
    await db.seat_player(
        room.code, player_id, room.seats.index(player_id), room.players[player_id].tokens
    )

    await sio.emit("room:joined", {"code": room.code}, to=sid)
    await push_state(room)
    await send_audio(room, sid)


@sio.on("game:start")
async def on_start(sid, data):  # noqa: ANN001
    room = get_room((data or {}).get("code", ""))
    if not room:
        return await fail(sid, "No room with that code")
    if (data or {}).get("playerId", "") != room.host_id:
        return await fail(sid, "Only the host can start")
    if len(room.connected_players()) < 2:
        return await fail(sid, "Need at least two players")

    rows = await db.all_cards()
    if len(rows) < MIN_DECK:
        return await fail(
            sid, f"Deck needs at least {MIN_DECK} cards — run tools/build_deck.py"
        )

    deck = [
        Card(
            id=r["id"],
            year=r["year"],
            artist_latin=r["artist_latin"],
            title_latin=r["title_latin"],
            artist_am=r["artist_am"],
            title_am=r["title_am"],
            youtube_id=r["youtube_id"],
            deezer_track_id=r["deezer_track_id"],
            added_by=r["added_by"],
        )
        for r in rows
    ]
    rounds = (data or {}).get("rounds")
    room.start_game(deck, rounds if isinstance(rounds, int) else None)
    await push_state(room)
    await start_round(room)


@sio.on("round:answer")
async def on_answer(sid, data):  # noqa: ANN001
    """Seal an answer card: where it goes, who sang it, what it is called."""
    room = get_room((data or {}).get("code", ""))
    if not room:
        return
    player_id = (data or {}).get("playerId", "")
    gap = (data or {}).get("gap")
    if player_id != room.active_player_id:
        return await fail(sid, "It is not your turn — this song belongs to someone else")
    # A declined answer needs no placement — that is the point of it.
    if not bool((data or {}).get("declined")) and not isinstance(gap, int):
        return await fail(sid, "Pick where it goes on your timeline first")
    gap = gap if isinstance(gap, int) else 0

    artist = str((data or {}).get("artist", ""))[:120]
    title = str((data or {}).get("title", ""))[:120]
    declined = bool((data or {}).get("declined"))

    if not room.submit_answer(player_id, gap, artist, title, declined):
        return

    await push_state(room)
    if room.active_answered():
        await do_reveal(room)


@sio.on("round:next")
async def on_next(sid, data):  # noqa: ANN001
    room = get_room((data or {}).get("code", ""))
    if not room:
        return
    if (data or {}).get("playerId", "") != room.host_id:
        return await fail(sid, "Only the host can advance")
    if room.phase is not Phase.REVEALING:
        return
    if room.is_last_round():
        await finish_game(room)
        return
    room.advance_seat()
    await start_round(room)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
