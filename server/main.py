from __future__ import annotations

import asyncio
import os
import random

import httpx
import socketio
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from game import (
    extract_playlist_id,
    extract_video_id,
    fuzzy_match,
    now_ms,
    parse_artist_song,
    score_guess,
)
from rooms import (
    add_player,
    create_room,
    get_room,
    remove_player,
    rooms,
    serialize_room,
)

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
PORT = int(os.getenv("PORT", "3001"))
GUESS_WINDOW_SECONDS = 15

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
fastapi_app = FastAPI()
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@fastapi_app.get("/health")
async def health():
    return {"ok": True, "rooms": len(rooms)}


app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)


async def fetch_youtube_title(video_id: str) -> str | None:
    """Use YouTube Data API if a key is configured, else fall back to oEmbed."""
    if YOUTUBE_API_KEY:
        url = (
            "https://www.googleapis.com/youtube/v3/videos"
            f"?part=snippet&id={video_id}&key={YOUTUBE_API_KEY}"
        )
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(url)
                r.raise_for_status()
                items = r.json().get("items", [])
                if items:
                    return items[0]["snippet"]["title"]
        except Exception:
            pass

    # Fallback: oEmbed (no key required)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://www.youtube.com/oembed",
                params={
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "format": "json",
                },
            )
            r.raise_for_status()
            return r.json().get("title")
    except Exception:
        return None


async def fetch_youtube_playlist(playlist_id: str) -> list[dict] | None:
    """Expand a YouTube playlist into [{videoId, title}]. Requires API key.

    Returns None on auth/availability failure (caller should surface a hint),
    or [] for an empty/unreachable playlist.
    """
    if not YOUTUBE_API_KEY:
        return None
    items: list[dict] = []
    page_token = ""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for _ in range(10):  # Cap at 500 items.
                params = {
                    "part": "snippet",
                    "maxResults": 50,
                    "playlistId": playlist_id,
                    "key": YOUTUBE_API_KEY,
                }
                if page_token:
                    params["pageToken"] = page_token
                r = await client.get(
                    "https://www.googleapis.com/youtube/v3/playlistItems",
                    params=params,
                )
                if r.status_code == 404:
                    return []
                r.raise_for_status()
                data = r.json()
                for item in data.get("items", []):
                    sn = item.get("snippet", {})
                    vid = sn.get("resourceId", {}).get("videoId")
                    title = sn.get("title", "")
                    if not vid or title in ("Private video", "Deleted video"):
                        continue
                    items.append({"videoId": vid, "title": title})
                page_token = data.get("nextPageToken", "")
                if not page_token:
                    break
        return items
    except Exception:
        return None


async def broadcast_room(code: str):
    payload = serialize_room(code)
    if payload:
        await sio.emit("room:update", payload, room=code)


@sio.event
async def connect(sid, environ):
    pass


@sio.event
async def disconnect(sid):
    affected = remove_player(sid)
    for code in affected:
        if code in rooms:
            await broadcast_room(code)


@sio.on("room:create")
async def on_create(sid, data):
    name = (data or {}).get("name", "Host").strip() or "Host"
    code = create_room(sid)
    add_player(code, sid, name)
    await sio.enter_room(sid, code)
    await sio.emit("room:created", {"code": code}, to=sid)
    await broadcast_room(code)


@sio.on("room:join")
async def on_join(sid, data):
    code = (data or {}).get("code", "").upper().strip()
    name = (data or {}).get("name", "Player").strip() or "Player"
    room = get_room(code)
    if not room:
        await sio.emit("error", {"message": "Room not found"}, to=sid)
        return
    if room["round_active"]:
        await sio.emit("error", {"message": "Game already in progress"}, to=sid)
        return
    add_player(code, sid, name)
    await sio.enter_room(sid, code)
    await sio.emit("room:joined", {"code": code}, to=sid)
    await broadcast_room(code)


@sio.on("playlist:add")
async def on_playlist_add(sid, data):
    code = (data or {}).get("code", "").upper().strip()
    url = (data or {}).get("youtube_url", "").strip()
    room = get_room(code)
    if not room or room["host"] != sid:
        await sio.emit("error", {"message": "Only the host can add songs"}, to=sid)
        return

    playlist_id = extract_playlist_id(url)
    video_id = extract_video_id(url)

    # Playlist URL → expand all videos.
    if playlist_id and not video_id:
        if not YOUTUBE_API_KEY:
            await sio.emit(
                "error",
                {"message": "Set YOUTUBE_API_KEY on the server to use playlist URLs"},
                to=sid,
            )
            return
        items = await fetch_youtube_playlist(playlist_id)
        if items is None:
            await sio.emit(
                "error",
                {"message": "Could not load playlist (private or invalid?)"},
                to=sid,
            )
            return
        if not items:
            await sio.emit("error", {"message": "Playlist is empty"}, to=sid)
            return
        for item in items:
            artist, song = parse_artist_song(item["title"])
            room["playlist"].append(
                {
                    "videoId": item["videoId"],
                    "artist": artist,
                    "songTitle": song,
                    "rawTitle": item["title"],
                }
            )
        await sio.emit(
            "playlist:update", {"playlist": room["playlist"]}, room=code
        )
        await broadcast_room(code)
        return

    # Single video.
    if not video_id:
        await sio.emit("error", {"message": "Invalid YouTube URL"}, to=sid)
        return
    title = await fetch_youtube_title(video_id)
    if not title:
        await sio.emit("error", {"message": "Could not fetch video title"}, to=sid)
        return
    artist, song = parse_artist_song(title)
    room["playlist"].append(
        {
            "videoId": video_id,
            "artist": artist,
            "songTitle": song,
            "rawTitle": title,
        }
    )
    await sio.emit(
        "playlist:update", {"playlist": room["playlist"]}, room=code
    )
    await broadcast_room(code)


@sio.on("room:set_rounds")
async def on_set_rounds(sid, data):
    code = (data or {}).get("code", "").upper().strip()
    rounds = (data or {}).get("rounds")
    room = get_room(code)
    if not room or room["host"] != sid:
        return
    try:
        rounds = int(rounds)
    except (TypeError, ValueError):
        return
    room["rounds_per_game"] = max(1, min(rounds, 50))
    await broadcast_room(code)


@sio.on("playlist:remove")
async def on_playlist_remove(sid, data):
    code = (data or {}).get("code", "").upper().strip()
    index = (data or {}).get("index", -1)
    room = get_room(code)
    if not room or room["host"] != sid:
        return
    if 0 <= index < len(room["playlist"]):
        room["playlist"].pop(index)
        await sio.emit(
            "playlist:update", {"playlist": room["playlist"]}, room=code
        )
        await broadcast_room(code)


async def end_round(code: str):
    room = get_room(code)
    if not room or not room["round_active"]:
        return
    room["round_active"] = False
    idx = room["current_round"]
    if idx >= len(room["playlist"]):
        return
    track = room["playlist"][idx]
    leaderboard = sorted(
        [
            {"sid": s, "name": p["name"], "score": p["score"]}
            for s, p in room["players"].items()
        ],
        key=lambda x: x["score"],
        reverse=True,
    )
    is_final = idx + 1 >= len(room["playlist"])
    await sio.emit(
        "round:end",
        {
            "round": idx,
            "artist": track["artist"],
            "songTitle": track["songTitle"],
            "rawTitle": track.get("rawTitle", ""),
            "leaderboard": leaderboard,
            "isFinal": is_final,
        },
        room=code,
    )
    # Note: even on the final round we don't auto-emit game:end. The host
    # advances from RoundResult so the answer is visible first.


async def start_round(code: str, index: int):
    room = get_room(code)
    if not room:
        return
    if index >= len(room["playlist"]):
        return
    track = room["playlist"][index]
    room["current_round"] = index
    room["round_active"] = True
    room["round_started_at"] = now_ms()
    room["guesses"] = {}
    await sio.emit(
        "round:start",
        {
            "round": index,
            "totalRounds": len(room["playlist"]),
            "videoId": track["videoId"],
            "startedAt": room["round_started_at"],
            "guessWindowSeconds": GUESS_WINDOW_SECONDS,
        },
        room=code,
    )

    async def auto_end():
        # 10s playback + 15s guessing window + tiny buffer
        await asyncio.sleep(10 + GUESS_WINDOW_SECONDS + 1)
        if room.get("round_active") and room["current_round"] == index:
            await end_round(code)

    asyncio.create_task(auto_end())


@sio.on("game:start")
async def on_game_start(sid, data):
    code = (data or {}).get("code", "").upper().strip()
    room = get_room(code)
    if not room or room["host"] != sid:
        return
    if not room["playlist"]:
        await sio.emit("error", {"message": "Add at least one song"}, to=sid)
        return
    for p in room["players"].values():
        p["score"] = 0

    # Shuffle and trim the playlist to rounds_per_game (kept on the room so
    # the rest of the round logic — round indexing, leaderboards — is unchanged).
    rounds = room.get("rounds_per_game") or len(room["playlist"])
    rounds = max(1, min(rounds, len(room["playlist"])))
    room["full_playlist"] = list(room["playlist"])
    room["playlist"] = random.sample(room["playlist"], rounds)
    await broadcast_room(code)
    await start_round(code, 0)


@sio.on("round:next")
async def on_round_next(sid, data):
    code = (data or {}).get("code", "").upper().strip()
    room = get_room(code)
    if not room or room["host"] != sid:
        return
    next_index = room["current_round"] + 1
    if next_index >= len(room["playlist"]):
        return
    await start_round(code, next_index)


@sio.on("game:show_final")
async def on_show_final(sid, data):
    """Host advances from the final-round result screen to the podium."""
    code = (data or {}).get("code", "").upper().strip()
    room = get_room(code)
    if not room or room["host"] != sid:
        return
    leaderboard = sorted(
        [
            {"sid": s, "name": p["name"], "score": p["score"]}
            for s, p in room["players"].items()
        ],
        key=lambda x: x["score"],
        reverse=True,
    )
    await sio.emit("game:end", {"leaderboard": leaderboard}, room=code)


@sio.on("game:reset")
async def on_game_reset(sid, data):
    """Restore the full playlist for a Play Again."""
    code = (data or {}).get("code", "").upper().strip()
    room = get_room(code)
    if not room or room["host"] != sid:
        return
    if room.get("full_playlist"):
        room["playlist"] = list(room["full_playlist"])
        room["full_playlist"] = None
    room["current_round"] = 0
    room["round_active"] = False
    room["guesses"] = {}
    for p in room["players"].values():
        p["score"] = 0
    await broadcast_room(code)
    await sio.emit("playlist:update", {"playlist": room["playlist"]}, room=code)


@sio.on("guess:submit")
async def on_guess_submit(sid, data):
    code = (data or {}).get("code", "").upper().strip()
    guess = (data or {}).get("guess", "").strip()
    correct_client = bool((data or {}).get("correct", False))
    room = get_room(code)
    if not room or not room["round_active"]:
        return
    if sid in room["guesses"]:
        return  # Already guessed
    if sid not in room["players"]:
        return
    started = room["round_started_at"] or now_ms()
    # Guess window starts after the 10s clip ends. Anything submitted before
    # the clip ends is treated as instant (elapsed=0) for scoring.
    elapsed_total = (now_ms() - started) / 1000.0
    elapsed_in_window = max(0.0, elapsed_total - 10.0)

    track = room["playlist"][room["current_round"]]
    server_correct = fuzzy_match(guess, track["artist"])
    correct = bool(correct_client or server_correct)

    points = score_guess(elapsed_in_window, correct)
    room["players"][sid]["score"] += points
    room["guesses"][sid] = {
        "guess": guess,
        "elapsed": elapsed_in_window,
        "correct": correct,
        "points": points,
    }

    # Tell the guesser their result.
    await sio.emit(
        "guess:result",
        {"correct": correct, "points": points},
        to=sid,
    )
    # Tell everyone someone has guessed (for live UI), without revealing answer.
    await sio.emit(
        "guess:received",
        {
            "sid": sid,
            "name": room["players"][sid]["name"],
            "submittedCount": len(room["guesses"]),
            "totalPlayers": len(room["players"]),
        },
        room=code,
    )
    await sio.emit(
        "scores:update",
        {
            "scores": [
                {"sid": s, "name": p["name"], "score": p["score"]}
                for s, p in room["players"].items()
            ]
        },
        room=code,
    )

    # End early if everyone has guessed.
    if len(room["guesses"]) >= len(room["players"]):
        await end_round(code)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
