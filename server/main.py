"""Socket layer.

Room state is fanned out per viewer rather than broadcast, because what a player
may see differs: the current card is withheld from everyone until the reveal.
Broadcasting one payload would leak the answer into devtools.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import secrets
from pathlib import Path
from typing import Annotated

import socketio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, StringConstraints

from db import db
from deck import (
    EARLIEST_YEAR,
    LATEST_YEAR,
    card_from_row,
    card_id,
    diff_decks,
    export_text,
    is_playable,
    load_deck_file,
)
from game import Card, Phase
from matching import artist_matches
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
from sources import deezer_fresh_preview, deezer_search, extract_youtube_id

load_dotenv()

# Comma-separated origins, or "*" (the default) while testing. Socket.IO wants
# the wildcard as the bare string, FastAPI as a one-element list.
_origins = os.getenv("CORS_ORIGINS", "*").strip()
ALLOWED_ORIGINS: str | list[str] = (
    "*" if _origins in ("", "*") else [o.strip() for o in _origins.split(",") if o.strip()]
)
MIN_DECK = 6
# Optional shared secret for editing the deck. Unset means open, which matches
# the rest of the game -- there are no accounts anywhere. Set it if the URL ever
# escapes the group; the /deck page picks it up from ?token=.
DECK_TOKEN = os.getenv("DECK_TOKEN", "")
# The deck as committed to the repo -- what the next deploy will seed from, and
# so the baseline for "what would be lost".
COMMITTED_DECK = Path(os.getenv("COMMITTED_DECK", Path(__file__).parent / "decks" / "deck.json"))
# How often rooms nobody has come back to are reaped.
REAP_INTERVAL_SECONDS = 60
# A player name is shown on every screen; cap it so a joke does not become a layout.
MAX_NAME_LENGTH = 40


def storage_is_ephemeral() -> bool:
    """Whether this server's database will be thrown away.

    Render sets RENDER=true and Fly sets FLY_APP_NAME on every service, and
    neither keeps a local file across a deploy unless a disk or volume has been
    attached -- so on either host the deck's live edits are lost on every deploy,
    restart and free-tier spin-down. DECK_STORAGE overrides the detection: set it
    to "persistent" once a disk is attached, or "ephemeral" on a host not listed.
    """
    override = os.getenv("DECK_STORAGE", "").strip().lower()
    if override in ("persistent", "ephemeral"):
        return override == "ephemeral"
    return os.getenv("RENDER") == "true" or bool(os.getenv("FLY_APP_NAME"))


sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=ALLOWED_ORIGINS)

# One timer task per room, so a new round always cancels the previous schedule.
_timers: dict[str, asyncio.Task] = {}


async def reap_rooms_forever() -> None:
    """Run the reaper on a clock, not only on disconnects.

    A room empties when its last socket drops, but the grace period can only
    expire on a later event -- and a quiet server may not see another disconnect
    for hours. Without this loop the documented 15-minute grace was in practice
    "until somebody else leaves".
    """
    while True:
        await asyncio.sleep(REAP_INTERVAL_SECONDS)
        drop_empty_rooms()


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    await db.connect()
    reaper = asyncio.create_task(reap_rooms_forever())
    try:
        yield
    finally:
        reaper.cancel()
        for task in _timers.values():
            task.cancel()
        _timers.clear()
        await db.close()


api = FastAPI(lifespan=lifespan)
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ALLOWED_ORIGINS == "*" else ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
app = socketio.ASGIApp(sio, other_asgi_app=api)


@api.get("/health")
async def health() -> dict:
    return {"ok": True, "rooms": len(rooms), "cards": await db.card_count()}


# ---------- deck editing ----------
#
# Every project that builds this game curates its songs by hand -- Timtam ships
# 7,239 entries in a committed YAML. The only real question is whether the
# tooling makes it pleasant, so the deck is editable from the game itself rather
# than only from a text file. That also lets a player on another continent add
# the songs they actually know.

# Whitespace-only input is not a name: pydantic strips before it checks length.
NameText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
OptionalText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
UrlText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
ByText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)]


class NewCard(BaseModel):
    artist_latin: NameText
    title_latin: NameText
    year: int = Field(ge=EARLIEST_YEAR, le=LATEST_YEAR)
    artist_am: OptionalText = ""
    title_am: OptionalText = ""
    youtube_url: UrlText = ""
    deezer_track_id: int | None = None
    added_by: ByText = ""


def _check_token(token: str | None) -> None:
    if DECK_TOKEN and not secrets.compare_digest(token or "", DECK_TOKEN):
        raise HTTPException(status_code=403, detail="Wrong deck token")


@api.get("/deck")
async def deck_list() -> dict:
    cards = await db.all_cards()
    committed = load_deck_file(COMMITTED_DECK)
    return {
        "count": len(cards),
        # Songs that exist only in this server's database. On an ephemeral host
        # they disappear on the next deploy, restart, or idle spin-down, so the
        # editor has to say so rather than let them vanish quietly.
        "storage": "ephemeral" if storage_is_ephemeral() else "persistent",
        "unsaved": None if committed is None else diff_decks(committed, cards),
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


@api.get("/deck/export")
async def deck_export() -> Response:
    """The live deck as a deck.json file, ready to commit.

    Downloading this and committing it to server/decks/deck.json is how a song
    added on a deployed server survives the next deploy. It is byte-identical to
    `build_deck.py export`, so the resulting diff shows only real changes.
    """
    return Response(
        content=export_text(await db.all_cards()),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="deck.json"'},
    )


@api.get("/deck/search")
async def deck_search(artist: str = "", title: str = "") -> dict:
    """Look a song up on Deezer so the player does not have to hunt for a link.

    Returns candidates rather than picking one: a wrong match plays a different
    song mid-game, and only a person can tell which of these is the song they
    meant.
    """
    if not artist.strip():
        return {"candidates": [], "note": "Type an artist name first."}
    tracks = await deezer_search(artist, title)
    if tracks is None:
        return {"candidates": [], "note": "Deezer did not answer. Add a YouTube link instead."}
    candidates = [
        {
            "deezerTrackId": t["id"],
            "artist": t["artist"]["name"],
            "title": t["title"],
            "album": (t.get("album") or {}).get("title", ""),
            "preview": t["preview"],
            "artistMatches": artist_matches(artist, t["artist"]["name"]),
        }
        for t in tracks
    ]
    note = "" if candidates else (
        "Nothing found. Deezer rate-limits in bursts and answers with an empty "
        "list rather than an error -- try again shortly, or add a YouTube link."
    )
    return {"candidates": candidates, "note": note}


@api.post("/deck")
async def deck_add(card: NewCard, token: str | None = None) -> dict:
    _check_token(token)
    row = {
        "id": card_id(card.artist_latin, card.title_latin),
        "year": card.year,
        "artist_latin": card.artist_latin,
        "title_latin": card.title_latin,
        "artist_am": card.artist_am,
        "title_am": card.title_am,
        "youtube_id": extract_youtube_id(card.youtube_url) or "",
        "deezer_track_id": card.deezer_track_id,
        "added_by": card.added_by,
    }
    if not is_playable(row):
        raise HTTPException(
            status_code=400,
            detail="A card needs a playable source: pick a Deezer match or add a YouTube link.",
        )
    await db.upsert_cards([row])
    return {"ok": True, "id": row["id"], "count": await db.card_count()}


@api.delete("/deck/{card}")
async def deck_delete(card: str, token: str | None = None) -> dict:
    _check_token(token)
    if not await db.delete_card(card):
        raise HTTPException(status_code=404, detail="No card with that id")
    return {"ok": True, "count": await db.card_count()}


# ---------- fan-out ----------


async def audio_for(card: Card) -> dict:
    """Resolve a playable source. Deezer preview URLs expire ~15 minutes after
    issue, so this runs per round and the URL is never stored."""
    if card.deezer_track_id and (url := await deezer_fresh_preview(card.deezer_track_id)):
        return {"source": "deezer", "url": url, "clipSeconds": CLIP_SECONDS}
    if card.youtube_id:
        return {"source": "youtube", "youtubeId": card.youtube_id, "clipSeconds": CLIP_SECONDS}
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
    await sio.emit("round:audio", {**cue, "roundNo": room.round_no}, to=sid)


async def push_state(room: Room) -> None:
    for player in room.players.values():
        if player.sid:
            await sio.emit("room:state", serialize(room, player.id), to=player.sid)


async def fail(sid: str, message: str) -> None:
    await sio.emit("error", {"message": message}, to=sid)


# ---------- round scheduling ----------


def cancel_timer(code: str) -> None:
    """Forget the room's answer-window task, and stop it if it is still waiting.

    The timer itself calls this through do_reveal() when the window expires, and
    a task must not cancel itself there: the cancellation would land on the next
    await, inside push_state(), and the reveal would be applied to the room but
    never reach a single client. Everyone then sat on "answering" until somebody
    reconnected -- the exact stall the timer exists to prevent.
    """
    task = _timers.pop(code, None)
    if task is not None and task is not asyncio.current_task():
        task.cancel()


async def run_round(code: str) -> None:
    """The answer window is a ceiling, not a pace.

    Answering is open from the moment the clip starts, so a player who knows the
    song in two seconds can say so and stop listening. This timer only exists so
    one absent player cannot stall the table.
    """
    await asyncio.sleep(ANSWER_SECONDS)
    room = get_room(code)
    if room and room.phase is Phase.ANSWERING:
        await do_reveal(room)


async def start_round(room: Room) -> None:
    if room.begin_round() is None:
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


async def finish_game(room: Room) -> None:
    # Otherwise the round's answer-window task outlives the game it belonged to.
    cancel_timer(room.code)
    room.phase = Phase.OVER
    await push_state(room)


# ---------- events ----------


@sio.event
async def connect(sid, environ):
    pass


@sio.event
async def disconnect(sid):
    """A dropped socket must never cost a seat, a timeline, or a score."""
    for room in list(rooms.values()):
        if room.detach_socket(sid) is not None:
            room.promote_host_if_needed()
            await push_state(room)
    drop_empty_rooms()


def _player_name(data: dict, default: str) -> str:
    return (str(data.get("name") or "").strip() or default)[:MAX_NAME_LENGTH]


@sio.on("room:create")
async def on_create(sid, data):
    data = data or {}
    player_id = str(data.get("playerId", "")).strip()
    if not player_id:
        return await fail(sid, "Missing player id")

    room = create_room(player_id)
    room.add_player(player_id, _player_name(data, "Host"), sid)
    await sio.enter_room(sid, room.code)
    await sio.emit("room:joined", {"code": room.code}, to=sid)
    await push_state(room)


@sio.on("room:join")
async def on_join(sid, data):
    data = data or {}
    room = get_room(str(data.get("code", "")))
    player_id = str(data.get("playerId", "")).strip()

    if not room:
        return await fail(sid, "No room with that code")
    if not player_id:
        return await fail(sid, "Missing player id")
    if player_id not in room.players and room.phase is not Phase.LOBBY:
        return await fail(sid, "That game has already started")

    room.add_player(player_id, _player_name(data, "Player"), sid)
    room.promote_host_if_needed()
    await sio.enter_room(sid, room.code)
    await sio.emit("room:joined", {"code": room.code}, to=sid)
    await push_state(room)
    await send_audio(room, sid)


@sio.on("game:start")
async def on_start(sid, data):
    data = data or {}
    room = get_room(str(data.get("code", "")))
    if not room:
        return await fail(sid, "No room with that code")
    if data.get("playerId", "") != room.host_id:
        return await fail(sid, "Only the host can start")
    if len(room.connected_players()) < 2:
        return await fail(sid, "Need at least two players")

    rows = await db.all_cards()
    if len(rows) < MIN_DECK:
        return await fail(sid, f"Deck needs at least {MIN_DECK} cards -- add some at /deck")

    rounds = data.get("rounds")
    room.start_game([card_from_row(r) for r in rows], rounds if isinstance(rounds, int) else None)
    await push_state(room)
    await start_round(room)


@sio.on("round:answer")
async def on_answer(sid, data):
    """Seal an answer card: where it goes, who sang it, what it is called."""
    data = data or {}
    room = get_room(str(data.get("code", "")))
    if not room:
        return
    player_id = data.get("playerId", "")
    declined = bool(data.get("declined"))
    gap = data.get("gap")
    if player_id != room.active_player_id:
        return await fail(sid, "It is not your turn -- this song belongs to someone else")
    # A declined answer needs no placement -- that is the point of it.
    if not declined and not isinstance(gap, int):
        return await fail(sid, "Pick where it goes on your timeline first")

    artist = str(data.get("artist", ""))[:120]
    title = str(data.get("title", ""))[:120]
    placement = gap if isinstance(gap, int) else 0
    if not room.submit_answer(player_id, placement, artist, title, declined):
        return
    # One song, one answer: the turn resolves the moment its one answer lands.
    if room.active_answered():
        await do_reveal(room)


@sio.on("round:next")
async def on_next(sid, data):
    data = data or {}
    room = get_room(str(data.get("code", "")))
    if not room:
        return
    if data.get("playerId", "") != room.host_id:
        return await fail(sid, "Only the host can advance")
    if room.phase is not Phase.REVEALING:
        return
    if room.is_last_round():
        await finish_game(room)
        return
    room.advance_seat()
    await start_round(room)
