"""SQLite persistence for the deck.

Why SQLite: the audience is a handful of friends. A separate database service
would be pure operational cost for load this will never see. SQLite reads are
in-process and sub-millisecond, it deploys as one file, and there is no
connection pool or network hop to tune.

Only the deck lives here. Live game state -- rooms, seats, timelines, the sealed
answer, timers -- changes several times a second and is worthless once a round
resolves, so it stays in memory (see rooms.py). A server restart therefore ends a
game in progress; for a half-hour session among friends that is the right trade
against running a database for it.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import aiosqlite

DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).parent / "hitster.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    id              TEXT PRIMARY KEY,
    year            INTEGER NOT NULL,
    -- 0 until a person has checked the year. A harvested or guessed year is
    -- playable, but the editor shows it as still needing that look.
    year_confirmed  INTEGER NOT NULL DEFAULT 0,
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
        # for speed, which is the right call for data that is re-seeded on deploy.
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA synchronous=NORMAL")
        await self._conn.executescript(SCHEMA)
        await self._migrate()
        await self._conn.commit()

    async def _migrate(self) -> None:
        """Bring a database created by an older schema up to date.

        CREATE TABLE IF NOT EXISTS leaves an existing table alone, so a column
        added later has to be added here too, or every deploy that keeps its
        disk fails on the first SELECT.
        """
        cur = await self.conn.execute("PRAGMA table_info(cards)")
        columns = {row["name"] for row in await cur.fetchall()}
        if "year_confirmed" not in columns:
            await self.conn.execute(
                "ALTER TABLE cards ADD COLUMN year_confirmed INTEGER NOT NULL DEFAULT 0"
            )

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database.connect() has not been awaited")
        return self._conn

    async def upsert_cards(self, cards: Iterable[dict[str, Any]]) -> int:
        rows = [
            (
                c["id"], c["year"], int(bool(c.get("year_confirmed", False))),
                c["artist_latin"], c["title_latin"],
                c.get("artist_am", ""), c.get("title_am", ""),
                c.get("youtube_id", ""), c.get("deezer_track_id"),
                c.get("added_by", ""),
            )
            for c in cards
        ]
        await self.conn.executemany(
            """INSERT INTO cards
                 (id, year, year_confirmed, artist_latin, title_latin, artist_am, title_am,
                  youtube_id, deezer_track_id, added_by)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 year=excluded.year,
                 year_confirmed=excluded.year_confirmed,
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
        # The id tiebreak keeps the order stable between calls; SQLite promises
        # nothing for ties, and the export and the /deck listing both depend on it.
        cur = await self.conn.execute("SELECT * FROM cards ORDER BY year, id")
        rows = [dict(r) for r in await cur.fetchall()]
        for r in rows:
            r["year_confirmed"] = bool(r["year_confirmed"])
        return rows

    async def update_card(self, card_id: str, **fields: Any) -> bool:
        """Change some of a card's fields in place. False when there is no such card.

        This is how a proposed year becomes a confirmed one: the editor sends
        the year it settled on and year_confirmed=True in one call.
        """
        allowed = {"year", "year_confirmed", "artist_am", "title_am"}
        changes = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not changes:
            return await self.has_card(card_id)
        if "year_confirmed" in changes:
            changes["year_confirmed"] = int(bool(changes["year_confirmed"]))
        assignments = ", ".join(f"{k}=?" for k in changes)
        cur = await self.conn.execute(
            f"UPDATE cards SET {assignments} WHERE id=?", (*changes.values(), card_id)
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def has_card(self, card_id: str) -> bool:
        cur = await self.conn.execute("SELECT 1 FROM cards WHERE id=?", (card_id,))
        return await cur.fetchone() is not None

    async def delete_card(self, card_id: str) -> bool:
        cur = await self.conn.execute("DELETE FROM cards WHERE id=?", (card_id,))
        await self.conn.commit()
        return cur.rowcount > 0

    async def card_count(self) -> int:
        cur = await self.conn.execute("SELECT COUNT(*) AS n FROM cards")
        row = await cur.fetchone()
        return int(row["n"]) if row else 0


db = Database()
