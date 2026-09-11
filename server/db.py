"""SQLite persistence.

Why SQLite: the audience is a handful of friends. A separate database service
would be pure operational cost for load this will never see. SQLite reads are
in-process and sub-millisecond, it deploys as one file, and there is no
connection pool or network hop to tune.

What is stored here is only what must survive a process restart or a dropped
socket: the deck, player identities, and enough room state to seat a returning
player back where they were. Live round state -- sealed placements, timers, the
current clip -- changes several times a second and is worthless once the round
resolves, so it stays in memory (see rooms.py).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

import aiosqlite

DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).parent / "hitster.db"))


def card_id(artist: str, title: str) -> str:
    """Stable id from artist and title, so re-adding a song updates it in place
    rather than creating a duplicate."""
    return hashlib.sha1(f"{artist.lower().strip()}|{title.lower().strip()}".encode()).hexdigest()[:12]

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    id              TEXT PRIMARY KEY,
    year            INTEGER NOT NULL,
    artist_latin    TEXT NOT NULL,
    title_latin     TEXT NOT NULL,
    artist_am       TEXT NOT NULL DEFAULT '',
    title_am        TEXT NOT NULL DEFAULT '',
    youtube_id      TEXT NOT NULL DEFAULT '',
    deezer_track_id INTEGER,
    added_by        TEXT NOT NULL DEFAULT '',
    created_at      INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS idx_cards_year ON cards(year);

CREATE TABLE IF NOT EXISTS players (
    id         TEXT PRIMARY KEY,          -- client-held UUID, survives reconnects
    name       TEXT NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS rooms (
    code        TEXT PRIMARY KEY,
    host_id     TEXT NOT NULL,
    phase       TEXT NOT NULL DEFAULT 'lobby',
    round_no    INTEGER NOT NULL DEFAULT 0,
    active_seat INTEGER NOT NULL DEFAULT 0,
    created_at  INTEGER NOT NULL DEFAULT (unixepoch()),
    updated_at  INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS room_players (
    room_code     TEXT NOT NULL,
    player_id     TEXT NOT NULL,
    seat          INTEGER NOT NULL,
    tokens        INTEGER NOT NULL DEFAULT 2,
    -- Ordered card ids as a JSON array. One row per player beats a join table
    -- here: a timeline is read and written whole, never queried by element.
    timeline_json TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (room_code, player_id)
);
CREATE INDEX IF NOT EXISTS idx_room_players_room ON room_players(room_code);
"""


class Database:
    """One shared connection. SQLite serialises writes internally, and at this
    scale a pool would add contention without adding throughput."""

    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        # WAL lets reads proceed during writes; NORMAL trades an fsync per commit
        # for speed, which is the right call for a game that can replay a round.
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA synchronous=NORMAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database.connect() has not been awaited")
        return self._conn

    # ---------- cards ----------

    async def upsert_cards(self, cards: Iterable[dict[str, Any]]) -> int:
        rows = [
            (
                c["id"], c["year"], c["artist_latin"], c["title_latin"],
                c.get("artist_am", ""), c.get("title_am", ""),
                c.get("youtube_id", ""), c.get("deezer_track_id"),
                c.get("added_by", ""),
            )
            for c in cards
        ]
        await self.conn.executemany(
            """INSERT INTO cards
                 (id, year, artist_latin, title_latin, artist_am, title_am,
                  youtube_id, deezer_track_id, added_by)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 year=excluded.year,
                 artist_latin=excluded.artist_latin,
                 title_latin=excluded.title_latin,
                 artist_am=excluded.artist_am,
                 title_am=excluded.title_am,
                 youtube_id=excluded.youtube_id,
                 deezer_track_id=excluded.deezer_track_id,
                 added_by=excluded.added_by""",
            rows,
        )
        await self.conn.commit()
        return len(rows)

    async def all_cards(self) -> list[dict[str, Any]]:
        cur = await self.conn.execute("SELECT * FROM cards ORDER BY year")
        return [dict(r) for r in await cur.fetchall()]

    async def delete_card(self, card_id_: str) -> bool:
        cur = await self.conn.execute("DELETE FROM cards WHERE id=?", (card_id_,))
        await self.conn.commit()
        return cur.rowcount > 0

    async def card_count(self) -> int:
        cur = await self.conn.execute("SELECT COUNT(*) AS n FROM cards")
        row = await cur.fetchone()
        return int(row["n"]) if row else 0

    # ---------- players ----------

    async def upsert_player(self, player_id: str, name: str) -> None:
        await self.conn.execute(
            """INSERT INTO players (id, name) VALUES (?, ?)
               ON CONFLICT(id) DO UPDATE SET name=excluded.name""",
            (player_id, name),
        )
        await self.conn.commit()

    async def get_player(self, player_id: str) -> dict[str, Any] | None:
        cur = await self.conn.execute("SELECT * FROM players WHERE id=?", (player_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

    # ---------- rooms ----------

    async def create_room(self, code: str, host_id: str) -> None:
        await self.conn.execute(
            "INSERT INTO rooms (code, host_id) VALUES (?, ?)", (code, host_id)
        )
        await self.conn.commit()

    async def save_room_state(
        self, code: str, phase: str, round_no: int, active_seat: int
    ) -> None:
        await self.conn.execute(
            """UPDATE rooms
                  SET phase=?, round_no=?, active_seat=?, updated_at=unixepoch()
                WHERE code=?""",
            (phase, round_no, active_seat, code),
        )
        await self.conn.commit()

    async def seat_player(
        self, code: str, player_id: str, seat: int, tokens: int
    ) -> None:
        await self.conn.execute(
            """INSERT INTO room_players (room_code, player_id, seat, tokens)
               VALUES (?,?,?,?)
               ON CONFLICT(room_code, player_id) DO NOTHING""",
            (code, player_id, seat, tokens),
        )
        await self.conn.commit()

    async def save_player_state(
        self, code: str, player_id: str, tokens: int, timeline_ids: list[str]
    ) -> None:
        await self.conn.execute(
            """UPDATE room_players SET tokens=?, timeline_json=?
                WHERE room_code=? AND player_id=?""",
            (tokens, json.dumps(timeline_ids), code, player_id),
        )
        await self.conn.commit()

    async def room_snapshot(self, code: str) -> dict[str, Any] | None:
        """Everything needed to rebuild a room after a restart."""
        cur = await self.conn.execute("SELECT * FROM rooms WHERE code=?", (code,))
        room = await cur.fetchone()
        if not room:
            return None
        cur = await self.conn.execute(
            """SELECT rp.*, p.name
                 FROM room_players rp
                 JOIN players p ON p.id = rp.player_id
                WHERE rp.room_code=?
                ORDER BY rp.seat""",
            (code,),
        )
        players = [
            {**dict(r), "timeline": json.loads(r["timeline_json"])}
            for r in await cur.fetchall()
        ]
        return {**dict(room), "players": players}


db = Database()
