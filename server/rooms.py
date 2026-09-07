from __future__ import annotations

import random
import string
from typing import Optional

rooms: dict[str, dict] = {}


def generate_room_code() -> str:
    while True:
        code = "".join(random.choices(string.ascii_uppercase, k=4))
        if code not in rooms:
            return code


def create_room(host_sid: str) -> str:
    code = generate_room_code()
    rooms[code] = {
        "host": host_sid,
        "players": {},
        "playlist": [],
        "current_round": 0,
        "round_active": False,
        "round_started_at": None,
        "guesses": {},
        "rounds_per_game": None,  # None = use full playlist
    }
    return code


def get_room(code: str) -> Optional[dict]:
    return rooms.get(code)


def add_player(code: str, sid: str, name: str) -> Optional[dict]:
    room = rooms.get(code)
    if not room:
        return None
    room["players"][sid] = {"name": name, "score": 0}
    return room


def remove_player(sid: str) -> list[str]:
    affected = []
    for code, room in list(rooms.items()):
        if sid in room["players"]:
            del room["players"][sid]
            affected.append(code)
        if room["host"] == sid:
            # If host leaves and no players remain, drop the room.
            if not room["players"]:
                del rooms[code]
            else:
                # Promote first remaining player to host.
                room["host"] = next(iter(room["players"].keys()))
            if code not in affected:
                affected.append(code)
    return affected


def serialize_room(code: str) -> Optional[dict]:
    room = rooms.get(code)
    if not room:
        return None
    return {
        "code": code,
        "host": room["host"],
        "players": [
            {"sid": sid, "name": p["name"], "score": p["score"]}
            for sid, p in room["players"].items()
        ],
        "playlist": room["playlist"],
        "current_round": room["current_round"],
        "round_active": room["round_active"],
        "total_rounds": len(room["playlist"]),
        "rounds_per_game": room.get("rounds_per_game"),
    }
