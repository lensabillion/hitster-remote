"""End-to-end tests against a live server.

These drive the real ASGI app over real sockets, because the bugs that matter
here live in the wiring rather than the rules: who is told what, when a round
advances, and whether a reconnecting player is put back together correctly.

Skipped automatically unless the Socket.IO client extras are installed
(`pip install -r requirements-dev.txt`).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import socket
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

aiohttp = pytest.importorskip("aiohttp", reason="needs python-socketio[asyncio_client]")
socketio = pytest.importorskip("socketio")

import uvicorn

import db as db_module
import main
import rooms as rooms_module
import sources
from deck import export_text

# One distinctive artist across the whole harness deck, so a test can type a
# name that is definitely right (or definitely wrong) without knowing which card
# the shuffle dealt.
HARNESS_ARTIST = "Kuku Sebsibe"
HARNESS_DECK_SIZE = 12
HARNESS_YOUTUBE_ID = "ADc9JPeLYi4"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Harness:
    """A server on a random port with a temporary database and a seeded deck."""

    def __init__(self, tmp_path: Path) -> None:
        self.port = free_port()
        self.tmp_path = tmp_path
        self.server: uvicorn.Server | None = None
        self.task: asyncio.Task | None = None

    async def __aenter__(self) -> Harness:
        db_module.db.path = self.tmp_path / "test.db"
        # Short phases keep the suite fast; the logic under test is unchanged.
        main.CLIP_SECONDS = 0.2
        main.ANSWER_SECONDS = 5

        config = uvicorn.Config(main.app, host="127.0.0.1", port=self.port, log_level="error")
        self.server = uvicorn.Server(config)
        self.task = asyncio.create_task(self.server.serve())
        while not self.server.started:
            await asyncio.sleep(0.02)

        await db_module.db.upsert_cards(
            [
                {
                    "id": f"card{i}",
                    "year": 1960 + i * 4,
                    "artist_latin": HARNESS_ARTIST,
                    "title_latin": f"Nebiyat {i}",
                    "artist_am": "አርቲስት",
                    "title_am": "ርዕስ",
                    # A YouTube id resolves without a network call; a card
                    # with nothing to play is skipped, so the deck needs one.
                    "youtube_id": HARNESS_YOUTUBE_ID,
                    "deezer_track_id": None,
                    "added_by": "test",
                    # Only cards with a confirmed year are dealt.
                    "year_confirmed": True,
                }
                for i in range(HARNESS_DECK_SIZE)
            ]
        )
        return self

    async def __aexit__(self, *_) -> None:
        for task in list(main._timers.values()):
            task.cancel()
        main._timers.clear()
        rooms_module.rooms.clear()

        if self.server:
            self.server.should_exit = True
        if self.task:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await asyncio.wait_for(self.task, timeout=5)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.url, timeout=10)


class Client:
    """A player. Records every room:state so tests can assert on the sequence."""

    def __init__(self, player_id: str, name: str) -> None:
        self.player_id = player_id
        self.name = name
        self.sio = socketio.AsyncClient()
        self.states: list[dict] = []
        self.audio: list[dict] = []
        self.errors: list[str] = []
        self.code: str | None = None

        @self.sio.on("room:state")
        def _state(data):
            self.states.append(data)

        @self.sio.on("round:audio")
        def _audio(data):
            self.audio.append(data)

        @self.sio.on("room:joined")
        def _joined(data):
            self.code = data["code"]

        @self.sio.on("error")
        def _error(data):
            self.errors.append(data["message"])

    @property
    def state(self) -> dict:
        return self.states[-1]

    async def connect(self, url: str) -> None:
        await self.sio.connect(url, transports=["websocket"])

    async def disconnect(self) -> None:
        await self.sio.disconnect()

    async def emit(self, event: str, payload: dict | None = None) -> None:
        await self.sio.emit(event, {**(payload or {}), "playerId": self.player_id})

    async def wait_for(self, predicate: Callable[[dict], bool], timeout: float = 6.0) -> dict:
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            if self.states and predicate(self.state):
                return self.state
            await asyncio.sleep(0.05)
        raise AssertionError(
            f"timed out; last phase={self.state.get('phase') if self.states else 'no state'}"
        )


async def two_player_game(h: Harness, tag: str) -> tuple[Client, Client, str]:
    """A host and a guest, connected, in a room, with the game started.

    Round 1 belongs to the host. Returns (host, guest, room code).
    """
    host, guest = Client(f"host-{tag}", "Lensa"), Client(f"guest-{tag}", "Sara")
    await host.connect(h.url)
    await guest.connect(h.url)

    await host.emit("room:create", {"name": "Lensa"})
    await host.wait_for(lambda s: s["phase"] == "lobby")
    code = host.state["code"]
    await guest.emit("room:join", {"code": code, "name": "Sara"})
    await guest.wait_for(lambda s: len(s["players"]) == 2)

    await host.emit("game:start", {"code": code})
    await host.wait_for(lambda s: s["phase"] == "answering")
    await guest.wait_for(lambda s: s["phase"] == "answering")
    return host, guest, code


async def test_full_round_and_no_spontaneous_advance(tmp_path):
    """A round resolves when the answer is in, and then STAYS there.

    The round must not advance until the host asks for the next song. This is
    the regression test for a round that appeared to advance on its own during
    manual play.
    """
    async with Harness(tmp_path) as h:
        host, guest, code = await two_player_game(h, "1")
        assert host.state["roundNo"] == 1

        # The year must not be disclosed while placing.
        assert host.state["card"] is None
        assert guest.state["card"] is None

        # Only the active player may answer; the guest's attempt is refused.
        await guest.emit("round:answer", {"code": code, "gap": 0})
        await asyncio.sleep(0.3)
        assert guest.errors, "an out-of-turn answer should be refused"
        assert host.state["phase"] == "answering"

        await host.emit("round:answer", {"code": code, "gap": 0})
        revealed = await host.wait_for(lambda s: s["phase"] == "revealing")
        assert revealed["card"] is not None
        assert isinstance(revealed["card"]["year"], int)
        assert revealed["roundNo"] == 1

        # Hold well past the clip: nothing may advance on its own.
        await asyncio.sleep(1.0)
        assert host.state["phase"] == "revealing"
        assert host.state["roundNo"] == 1, "round advanced without round:next"

        await host.emit("round:next", {"code": code})
        await host.wait_for(lambda s: s["roundNo"] == 2)
        assert not host.errors

        await host.disconnect()
        await guest.disconnect()


async def test_only_the_host_may_advance(tmp_path):
    async with Harness(tmp_path) as h:
        host, guest, code = await two_player_game(h, "2")
        await host.emit("round:answer", {"code": code, "gap": 0})
        await host.wait_for(lambda s: s["phase"] == "revealing")

        await guest.emit("round:next", {"code": code})
        await asyncio.sleep(0.4)
        assert guest.errors, "a non-host advancing should be refused"
        assert host.state["roundNo"] == 1

        await host.disconnect()
        await guest.disconnect()


async def test_reconnecting_player_gets_seat_timeline_and_audio(tmp_path):
    """A reconnecting player must be able to keep playing the current round.

    Seat and timeline are restored -- and so is the audio cue, which is what
    makes the round playable rather than merely visible.
    """
    async with Harness(tmp_path) as h:
        host, guest, code = await two_player_game(h, "3")

        before = next(p for p in guest.state["players"] if p["id"] == guest.player_id)
        assert len(before["timeline"]) == 1

        await guest.disconnect()
        await asyncio.sleep(0.3)

        returning = Client(guest.player_id, "Sara")
        await returning.connect(h.url)
        await returning.emit("room:join", {"code": code, "name": "Sara"})
        state = await returning.wait_for(lambda s: s["phase"] == "answering")

        after = next(p for p in state["players"] if p["id"] == guest.player_id)
        assert after["timeline"] == before["timeline"], "timeline lost on reconnect"
        assert len(state["players"]) == 2, "reconnect created a duplicate seat"

        # Without this the player can see the round but cannot hear the song.
        assert returning.audio, "no audio cue replayed to the reconnecting player"

        await host.disconnect()
        await returning.disconnect()


async def test_year_scores_alone_when_the_artist_is_wrong(tmp_path):
    """The halves are independent: a wrong singer must not void a right year."""
    async with Harness(tmp_path) as h:
        host, guest, code = await two_player_game(h, "4")
        await host.emit(
            "round:answer", {"code": code, "gap": 0, "artist": "Bob Marley", "title": ""}
        )
        revealed = await host.wait_for(lambda s: s["phase"] == "revealing")

        outcome = revealed["outcome"]
        assert outcome["playerId"] == host.player_id
        assert outcome["artistRight"] is False
        assert outcome["points"] == (revealed["yearPoints"] if outcome["yearRight"] else 0)

        await host.disconnect()
        await guest.disconnect()


async def test_artist_alone_is_worth_seventy(tmp_path):
    """Naming the singer pays even when the card is misplaced."""
    async with Harness(tmp_path) as h:
        host, guest, code = await two_player_game(h, "5")
        # A surname alone, misspelled, still counts -- that is the point.
        await host.emit("round:answer", {"code": code, "gap": 0, "artist": "Sebsibe", "title": ""})
        revealed = await host.wait_for(lambda s: s["phase"] == "revealing")

        outcome = revealed["outcome"]
        artist, year = revealed["artistPoints"], revealed["yearPoints"]
        assert outcome["artistRight"] is True, "a surname alone should score"
        assert outcome["points"] == (artist + year if outcome["yearRight"] else artist)

        await host.disconnect()
        await guest.disconnect()


async def test_watchers_hear_the_song_and_the_turn_rotates(tmp_path):
    """Everyone hears every clip; only the player whose turn it is answers."""
    async with Harness(tmp_path) as h:
        host, guest, code = await two_player_game(h, "6")

        # Round 1 belongs to the host, but BOTH players are sent the audio.
        assert host.state["isMyTurn"] is True
        assert guest.state["isMyTurn"] is False
        assert host.audio, "the answering player got no audio"
        assert guest.audio, "the watching player got no audio"

        await host.emit("round:answer", {"code": code, "gap": 0, "artist": "x"})
        await host.wait_for(lambda s: s["phase"] == "revealing")
        await host.emit("round:next", {"code": code})
        await guest.wait_for(lambda s: s["roundNo"] == 2)

        # Round 2 belongs to the guest.
        assert guest.state["isMyTurn"] is True
        assert host.state["isMyTurn"] is False
        assert len(guest.audio) >= 2, "the watcher stopped receiving audio"

        await host.disconnect()
        await guest.disconnect()


async def test_the_answer_deadline_is_published_and_the_audio_shared(tmp_path):
    """Every screen shows the same clock, and every socket gets the same cue."""
    async with Harness(tmp_path) as h:
        host, guest, code = await two_player_game(h, "8")
        ends = host.state["answerEndsAt"]
        assert isinstance(ends, int)
        assert ends == guest.state["answerEndsAt"], "the deadline differs between players"
        assert host.audio[-1] == guest.audio[-1], "players were sent different audio"
        assert host.audio[-1]["source"] == "youtube"

        await host.emit("round:answer", {"code": code, "gap": 0})
        revealed = await host.wait_for(lambda s: s["phase"] == "revealing")
        assert revealed["answerEndsAt"] is None, "no window to count down once revealed"

        await host.disconnect()
        await guest.disconnect()


async def test_no_client_sees_a_round_zero_or_a_zero_deadline(tmp_path):
    """Starting the game must not leak an 'answering' state before round 1."""
    async with Harness(tmp_path) as h:
        host, guest, _ = await two_player_game(h, "10")
        for client in (host, guest):
            answering = [s for s in client.states if s["phase"] == "answering"]
            assert answering, "no answering state at all"
            assert all(s["roundNo"] >= 1 for s in answering), "round 0 was pushed"
            assert all(s["answerEndsAt"] for s in answering), "a zero deadline was pushed"
        await host.disconnect()
        await guest.disconnect()


async def test_a_card_with_nothing_to_play_is_skipped(tmp_path, monkeypatch):
    """A round is never silent: a card whose source has gone is passed over.

    The deal is pinned to deck order so it is known: cards 0 and 1 are the seeds,
    cards 2-6 have no source, card 7 is the first playable draw. Round 1 must
    land on card 7 without counting the five skips as rounds.
    """
    monkeypatch.setattr(rooms_module, "deal_across_eras", list)  # deal in deck order
    async with Harness(tmp_path) as h:
        rows = await db_module.db.all_cards()
        for i, row in enumerate(rows):
            row["youtube_id"] = "" if 2 <= i <= 6 else HARNESS_YOUTUBE_ID
        await db_module.db.upsert_cards(rows)

        host, guest, _ = await two_player_game(h, "9")
        assert host.state["roundNo"] == 1
        assert host.audio[-1]["source"] == "youtube"

        await host.emit("round:answer", {"code": host.state["code"], "gap": 0})
        revealed = await host.wait_for(lambda s: s["phase"] == "revealing")
        assert revealed["card"]["id"] == "card7", "the silent cards were not all skipped"

        await host.disconnect()
        await guest.disconnect()


async def test_a_deck_of_silence_ends_the_game_rather_than_looping(tmp_path, monkeypatch):
    monkeypatch.setattr(rooms_module, "deal_across_eras", list)  # deal in deck order
    async with Harness(tmp_path) as h:
        rows = await db_module.db.all_cards()
        for i, row in enumerate(rows):
            row["youtube_id"] = HARNESS_YOUTUBE_ID if i < 2 else ""
        await db_module.db.upsert_cards(rows)

        host, guest = Client("host-11", "Lensa"), Client("guest-11", "Sara")
        await host.connect(h.url)
        await guest.connect(h.url)
        await host.emit("room:create", {"name": "Lensa"})
        await host.wait_for(lambda s: s["phase"] == "lobby")
        code = host.state["code"]
        await guest.emit("room:join", {"code": code, "name": "Sara"})
        await guest.wait_for(lambda s: len(s["players"]) == 2)

        await host.emit("game:start", {"code": code})
        ended = await host.wait_for(lambda s: s["phase"] == "over")
        assert all(s["phase"] != "answering" for s in host.states), "a silent round was played"
        assert ended["roundNo"] == 0

        await host.disconnect()
        await guest.disconnect()


async def test_an_unconfirmed_year_is_never_dealt(tmp_path, monkeypatch):
    """A proposed year is a guess; a game scored against it would be decided by
    evidence nobody has checked. Such cards wait on /deck, out of the deal.

    Deck order is pinned: cards 0 and 1 are the seeds, cards 2-6 are unconfirmed,
    so round 1 must land on card 7.
    """
    monkeypatch.setattr(rooms_module, "deal_across_eras", list)  # deal in deck order
    async with Harness(tmp_path) as h:
        rows = await db_module.db.all_cards()
        for i, row in enumerate(rows):
            row["year_confirmed"] = not (2 <= i <= 6)
        await db_module.db.upsert_cards(rows)

        host, guest, _ = await two_player_game(h, "13")
        await host.emit("round:answer", {"code": host.state["code"], "gap": 0})
        revealed = await host.wait_for(lambda s: s["phase"] == "revealing")
        assert revealed["card"]["id"] == "card7", "an unconfirmed card was dealt"

        await host.disconnect()
        await guest.disconnect()


async def test_a_deck_without_confirmed_years_does_not_start(tmp_path):
    async with Harness(tmp_path) as h:
        rows = await db_module.db.all_cards()
        for row in rows:
            row["year_confirmed"] = False
        await db_module.db.upsert_cards(rows)

        host, guest = Client("host-14", "Lensa"), Client("guest-14", "Sara")
        await host.connect(h.url)
        await guest.connect(h.url)
        await host.emit("room:create", {"name": "Lensa"})
        await host.wait_for(lambda s: s["phase"] == "lobby")
        code = host.state["code"]
        await guest.emit("room:join", {"code": code, "name": "Sara"})
        await guest.wait_for(lambda s: len(s["players"]) == 2)

        await host.emit("game:start", {"code": code})
        for _ in range(50):
            if host.errors:
                break
            await asyncio.sleep(0.02)
        assert host.errors and "confirm" in host.errors[-1], "the start should be refused"
        assert host.state["phase"] == "lobby"

        await host.disconnect()
        await guest.disconnect()


async def test_an_absent_player_cannot_stall_the_table(tmp_path):
    """The answer window is a ceiling: when it expires the round reveals itself."""
    async with Harness(tmp_path) as h:
        main.ANSWER_SECONDS = 0.5
        host, guest, _ = await two_player_game(h, "7")
        revealed = await guest.wait_for(lambda s: s["phase"] == "revealing", timeout=3)
        assert revealed["outcome"]["points"] == 0
        assert revealed["outcome"]["playerId"] == host.player_id

        await host.disconnect()
        await guest.disconnect()


# ---------- the deck editor ----------


async def test_deck_reports_unsaved_songs_and_exports_them(tmp_path, monkeypatch):
    """A song added through /deck is flagged as unsaved, and the download holds it.

    This is the whole safety net for a deployed server: its database is thrown
    away on deploy, restart and spin-down, so the editor has to know what is not
    yet in deck.json and hand it over in a form that can be committed as-is.
    """
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("DECK_STORAGE", raising=False)

    async with Harness(tmp_path) as h:
        # The committed deck is exactly what the harness seeded.
        committed = tmp_path / "deck.json"
        committed.write_text(export_text(await db_module.db.all_cards()), encoding="utf-8")
        monkeypatch.setattr(main, "COMMITTED_DECK", committed)

        async with h.http() as http:
            before = (await http.get("/deck")).json()
            assert before["storage"] == "ephemeral"
            assert before["unsaved"] == {"added": [], "removed": [], "changed": []}

            added = await http.post(
                "/deck",
                json={
                    "artist_latin": "Bizunesh Bekele", "title_latin": "Tizita",
                    "year": 1970, "deezer_track_id": 123456,
                },
            )
            assert added.status_code == 200, added.text
            new_id = added.json()["id"]

            after = (await http.get("/deck")).json()
            assert [c["id"] for c in after["unsaved"]["added"]] == [new_id]

            exported = await http.get("/deck/export")
            assert exported.status_code == 200
            assert 'filename="deck.json"' in exported.headers["content-disposition"]
            rows = json.loads(exported.text)
            assert new_id in {r["id"] for r in rows}
            assert len(rows) == HARNESS_DECK_SIZE + 1

            # Committing the download clears the warning.
            committed.write_text(exported.text, encoding="utf-8")
            saved = (await http.get("/deck")).json()
            assert saved["unsaved"] == {"added": [], "removed": [], "changed": []}


async def test_deck_without_a_committed_file_reports_unknown_not_everything(tmp_path, monkeypatch):
    """No baseline means 'can't tell', never 'every card is unsaved'."""
    async with Harness(tmp_path) as h:
        monkeypatch.setattr(main, "COMMITTED_DECK", tmp_path / "missing.json")
        async with h.http() as http:
            assert (await http.get("/deck")).json()["unsaved"] is None


async def test_a_card_needs_a_source_and_a_real_name(tmp_path):
    async with Harness(tmp_path) as h, h.http() as http:
        no_source = await http.post(
            "/deck", json={"artist_latin": "Aster Aweke", "title_latin": "Gela Gela", "year": 1991}
        )
        assert no_source.status_code == 400

        blank = await http.post(
            "/deck",
            json={"artist_latin": "   ", "title_latin": "x", "year": 1991, "deezer_track_id": 1},
        )
        assert blank.status_code == 422


async def test_deck_token_gates_writes_but_not_reads(tmp_path, monkeypatch):
    """With DECK_TOKEN set, anyone can read the deck and nobody can edit it blind."""
    monkeypatch.setattr(main, "DECK_TOKEN", "s3cret")
    card = {
        "artist_latin": "Aster Aweke", "title_latin": "Gela Gela",
        "year": 1991, "deezer_track_id": 1,
    }

    async with Harness(tmp_path) as h, h.http() as http:
        assert (await http.get("/deck")).status_code == 200
        assert (await http.post("/deck", json=card)).status_code == 403
        assert (await http.post("/deck?token=wrong", json=card)).status_code == 403

        added = await http.post("/deck?token=s3cret", json=card)
        assert added.status_code == 200
        card_id = added.json()["id"]

        assert (await http.delete(f"/deck/{card_id}")).status_code == 403
        assert (await http.delete(f"/deck/{card_id}?token=s3cret")).status_code == 200
        assert (await http.delete(f"/deck/{card_id}?token=s3cret")).status_code == 404


async def test_deck_search_flags_a_wrong_artist_instead_of_hiding_it(tmp_path, monkeypatch):
    """The editor shows every candidate and marks the doubtful ones; a person decides."""
    tracks = [
        {"id": 1, "title": "Tikur Sew", "artist": {"name": "Teddy Afro"}, "preview": "u1",
         "album": {"title": "Tikur Sew"}},
        {"id": 2, "title": "Something", "artist": {"name": "Teddy Karo"}, "preview": "u2"},
        {"id": 3, "title": "No preview", "artist": {"name": "Teddy Afro"}, "preview": ""},
    ]

    def fake(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": tracks})

    monkeypatch.setattr(
        sources, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(fake))
    )

    async with Harness(tmp_path) as h, h.http() as http:
        found = (await http.get("/deck/search", params={"artist": "Teddy Afro"})).json()
        assert [(c["deezerTrackId"], c["artistMatches"]) for c in found["candidates"]] == [
            (1, True),
            (2, False),
        ]
        assert found["candidates"][0]["album"] == "Tikur Sew"
        assert found["note"] == ""

        assert (await http.get("/deck/search")).json()["candidates"] == []


async def test_a_harvested_year_is_confirmed_in_place(tmp_path):
    """The curation loop: a proposed year shows as unconfirmed, one PATCH
    settles it, and the count the editor leads with drops."""
    async with Harness(tmp_path) as h, h.http() as http:
        # Make the whole harness deck unconfirmed, like a fresh harvest.
        rows = await db_module.db.all_cards()
        for row in rows:
            row["year_confirmed"] = False
        await db_module.db.upsert_cards(rows)
        before = (await http.get("/deck")).json()
        assert before["unconfirmed"] == HARNESS_DECK_SIZE
        assert all(c["yearConfirmed"] is False for c in before["cards"])

        target = before["cards"][0]
        fixed = await http.patch(
            f"/deck/{target['id']}", json={"year": 1972, "year_confirmed": True}
        )
        assert fixed.status_code == 200, fixed.text

        after = (await http.get("/deck")).json()
        assert after["unconfirmed"] == HARNESS_DECK_SIZE - 1
        card = next(c for c in after["cards"] if c["id"] == target["id"])
        assert (card["year"], card["yearConfirmed"]) == (1972, True)
        # Nothing else about the card moved.
        assert card["titleLatin"] == target["titleLatin"]

        assert (await http.patch("/deck/nope", json={"year_confirmed": True})).status_code == 404
        assert (await http.patch(f"/deck/{target['id']}", json={"year": 1800})).status_code == 422


async def test_a_year_typed_into_the_editor_counts_as_confirmed(tmp_path):
    async with Harness(tmp_path) as h, h.http() as http:
        added = await http.post(
            "/deck",
            json={"artist_latin": "Aster Aweke", "title_latin": "Kabu",
                  "year": 1991, "deezer_track_id": 5},
        )
        card = next(
            c for c in (await http.get("/deck")).json()["cards"] if c["id"] == added.json()["id"]
        )
        assert card["yearConfirmed"] is True


async def test_deck_token_gates_patches_too(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DECK_TOKEN", "s3cret")
    async with Harness(tmp_path) as h, h.http() as http:
        card = (await http.get("/deck")).json()["cards"][0]
        blind = await http.patch(f"/deck/{card['id']}", json={"year_confirmed": True})
        assert blind.status_code == 403
        ok = await http.patch(f"/deck/{card['id']}?token=s3cret", json={"year_confirmed": True})
        assert ok.status_code == 200
