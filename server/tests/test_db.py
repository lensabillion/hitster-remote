"""Tests for the deck's storage: the schema migration and in-place edits.

The database on a deployed host with a disk attached outlives the code, so a
column added later has to be added to an existing table too -- otherwise the
first SELECT after the deploy fails and the whole game is down.
"""

from __future__ import annotations

import sqlite3

import pytest

from db import Database

OLD_SCHEMA = """
CREATE TABLE cards (
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
"""


def card(id_: str, year: int, **overrides) -> dict:
    return {
        "id": id_, "year": year, "artist_latin": "Aster Aweke", "title_latin": f"Song {id_}",
        "deezer_track_id": 1,
    } | overrides


@pytest.fixture
async def database(tmp_path):
    database = Database(tmp_path / "deck.db")
    await database.connect()
    yield database
    await database.close()


class TestMigration:
    async def test_an_older_database_gains_the_confirmed_column(self, tmp_path):
        path = tmp_path / "old.db"
        with sqlite3.connect(path) as conn:
            conn.executescript(OLD_SCHEMA)
            conn.execute(
                "INSERT INTO cards (id, year, artist_latin, title_latin) VALUES (?,?,?,?)",
                ("a", 1991, "Aster Aweke", "Kabu"),
            )

        database = Database(path)
        await database.connect()
        try:
            (row,) = await database.all_cards()
            # Nobody has confirmed anything in a deck that predates the flag.
            assert row["year_confirmed"] is False
            assert await database.update_card("a", year_confirmed=True)
            assert (await database.all_cards())[0]["year_confirmed"] is True
        finally:
            await database.close()

    async def test_connecting_twice_is_harmless(self, tmp_path):
        path = tmp_path / "twice.db"
        for _ in range(2):
            database = Database(path)
            await database.connect()
            await database.close()


class TestUpsert:
    async def test_the_flag_round_trips_as_a_bool(self, database):
        await database.upsert_cards([card("a", 1991), card("b", 2005, year_confirmed=True)])
        rows = {r["id"]: r["year_confirmed"] for r in await database.all_cards()}
        assert rows == {"a": False, "b": True}

    async def test_re_adding_a_card_replaces_its_year_and_flag(self, database):
        await database.upsert_cards([card("a", 1991, year_confirmed=True)])
        await database.upsert_cards([card("a", 1989)])
        (row,) = await database.all_cards()
        assert (row["year"], row["year_confirmed"]) == (1989, False)


class TestUpdateCard:
    async def test_confirms_a_year_in_place(self, database):
        await database.upsert_cards([card("a", 1991)])
        assert await database.update_card("a", year=1989, year_confirmed=True)
        (row,) = await database.all_cards()
        assert (row["year"], row["year_confirmed"]) == (1989, True)

    async def test_untouched_fields_stay(self, database):
        await database.upsert_cards([card("a", 1991, artist_am="አስቴር አወቀ")])
        await database.update_card("a", year_confirmed=True)
        (row,) = await database.all_cards()
        assert (row["year"], row["artist_am"]) == (1991, "አስቴር አወቀ")

    async def test_fields_outside_the_editable_set_are_ignored(self, database):
        await database.upsert_cards([card("a", 1991)])
        assert await database.update_card("a", id="b", artist_latin="Nobody", year=1990)
        (row,) = await database.all_cards()
        assert (row["id"], row["artist_latin"], row["year"]) == ("a", "Aster Aweke", 1990)

    async def test_unknown_card_is_false(self, database):
        assert not await database.update_card("nope", year=1990)
        assert not await database.update_card("nope")

    async def test_an_empty_edit_reports_whether_the_card_exists(self, database):
        await database.upsert_cards([card("a", 1991)])
        assert await database.update_card("a")
