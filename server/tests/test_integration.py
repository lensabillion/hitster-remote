"""End-to-end socket tests against a live server.

These drive the real ASGI app over real sockets, because the bugs that matter
here live in the wiring rather than the rules: who is told what, when a round
advances, and whether a reconnecting player is put back together correctly.

Skipped automatically unless the client extras are installed.
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

aiohttp = pytest.importorskip("aiohttp", reason="needs python-socketio[asyncio_client]")
socketio = pytest.importorskip("socketio")

import uvicorn  # noqa: E402


# One distinctive artist across the whole harness deck, so a test can type a
# name that is definitely right (or definitely wrong) without knowing which card
# the shuffle dealt.
HARNESS_ARTIST = "Kuku Sebsibe"


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

    async def __aenter__(self) -> "Harness":
        import db as db_module

        db_module.db.path = self.tmp_path / "test.db"

        import main

        # Short phases keep the suite fast; the logic under test is unchanged.
        main.CLIP_SECONDS = 0.2
        main.ANSWER_SECONDS = 5

        config = uvicorn.Config(
            main.app, host="127.0.0.1", port=self.port, log_level="error"
        )
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
                    "youtube_id": "",
                    "deezer_track_id": None,
                    "added_by": "test",
                }
                for i in range(12)
            ]
        )
        return self

    async def __aexit__(self, *_) -> None:
        import main
        import rooms as rooms_module

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
        def _state(data):  # noqa: ANN001
            self.states.append(data)

        @self.sio.on("round:audio")
        def _audio(data):  # noqa: ANN001
            self.audio.append(data)

        @self.sio.on("room:joined")
        def _joined(data):  # noqa: ANN001
            self.code = data["code"]

        @self.sio.on("error")
        def _error(data):  # noqa: ANN001
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

    async def wait_for(self, predicate, timeout: float = 6.0) -> dict:
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            if self.states and predicate(self.state):
                return self.state
            await asyncio.sleep(0.05)
        raise AssertionError(
            f"timed out; last phase="
            f"{self.state.get('phase') if self.states else 'no state'}"
        )


@pytest.mark.asyncio
async def test_full_round_and_no_spontaneous_advance(tmp_path):
    """A round resolves when everyone has placed, and then STAYS there.

    The round must not advance until the host asks for the next song. This is
    the regression test for a round that appeared to advance on its own during
    manual play.
    """
    async with Harness(tmp_path) as h:
        host = Client("host-1", "Lensa")
        guest = Client("guest-1", "Sara")
        await host.connect(h.url)
        await guest.connect(h.url)

        await host.emit("room:create", {"name": "Lensa"})
        await host.wait_for(lambda s: s["phase"] == "lobby")
        code = host.state["code"]

        await guest.emit("room:join", {"code": code, "name": "Sara"})
        await guest.wait_for(lambda s: len(s["players"]) == 2)

        await host.emit("game:start", {"code": code})
        await host.wait_for(lambda s: s["phase"] == "answering")
        assert host.state["roundNo"] == 1

        # The year must not be disclosed while placing.
        assert host.state["card"] is None
        assert guest.state["card"] is None

        await host.emit("round:answer", {"code": code, "gap": 0})
        await guest.emit("round:answer", {"code": code, "gap": 0})

        revealed = await host.wait_for(lambda s: s["phase"] == "revealing")
        assert revealed["card"] is not None
        assert isinstance(revealed["card"]["year"], int)
        assert revealed["roundNo"] == 1

        # Hold well past ANSWER_SECONDS: nothing may advance on its own.
        await asyncio.sleep(1.0)
        assert host.state["phase"] == "revealing"
        assert host.state["roundNo"] == 1, "round advanced without round:next"

        await host.emit("round:next", {"code": code})
        await host.wait_for(lambda s: s["roundNo"] == 2)
        assert not host.errors

        await host.disconnect()
        await guest.disconnect()


@pytest.mark.asyncio
async def test_only_the_host_may_advance(tmp_path):
    async with Harness(tmp_path) as h:
        host = Client("host-2", "Lensa")
        guest = Client("guest-2", "Sara")
        await host.connect(h.url)
        await guest.connect(h.url)

        await host.emit("room:create", {"name": "Lensa"})
        await host.wait_for(lambda s: s["phase"] == "lobby")
        code = host.state["code"]
        await guest.emit("room:join", {"code": code, "name": "Sara"})
        await guest.wait_for(lambda s: len(s["players"]) == 2)

        await host.emit("game:start", {"code": code})
        await host.wait_for(lambda s: s["phase"] == "answering")
        await host.emit("round:answer", {"code": code, "gap": 0})
        await guest.emit("round:answer", {"code": code, "gap": 0})
        await host.wait_for(lambda s: s["phase"] == "revealing")

        await guest.emit("round:next", {"code": code})
        await asyncio.sleep(0.4)
        assert guest.errors, "a non-host advancing should be refused"
        assert host.state["roundNo"] == 1

        await host.disconnect()
        await guest.disconnect()


@pytest.mark.asyncio
async def test_reconnecting_player_gets_seat_timeline_and_audio(tmp_path):
    """A reconnecting player must be able to keep playing the current round.

    Seat, tokens and timeline are restored -- and so is the audio cue, which is
    what makes the round playable rather than merely visible.
    """
    async with Harness(tmp_path) as h:
        host = Client("host-3", "Lensa")
        guest = Client("guest-3", "Sara")
        await host.connect(h.url)
        await guest.connect(h.url)

        await host.emit("room:create", {"name": "Lensa"})
        await host.wait_for(lambda s: s["phase"] == "lobby")
        code = host.state["code"]
        await guest.emit("room:join", {"code": code, "name": "Sara"})
        await guest.wait_for(lambda s: len(s["players"]) == 2)

        await host.emit("game:start", {"code": code})
        await host.wait_for(lambda s: s["phase"] == "answering")

        before = next(p for p in guest.state["players"] if p["id"] == "guest-3")
        assert len(before["timeline"]) == 1

        await guest.disconnect()
        await asyncio.sleep(0.3)

        returning = Client("guest-3", "Sara")
        await returning.connect(h.url)
        await returning.emit("room:join", {"code": code, "name": "Sara"})
        state = await returning.wait_for(lambda s: s["phase"] == "answering")

        after = next(p for p in state["players"] if p["id"] == "guest-3")
        assert after["timeline"] == before["timeline"], "timeline lost on reconnect"
        assert after["tokens"] == before["tokens"], "tokens lost on reconnect"
        assert len(state["players"]) == 2, "reconnect created a duplicate seat"

        # Without this the player can see the round but cannot hear the song.
        assert returning.audio, "no audio cue replayed to the reconnecting player"

        await host.disconnect()
        await returning.disconnect()


@pytest.mark.asyncio
async def test_year_scores_alone_when_the_artist_is_wrong(tmp_path):
    """The halves are independent: a wrong singer must not void a right year."""
    async with Harness(tmp_path) as h:
        host, guest = Client("host-4", "Lensa"), Client("guest-4", "Sara")
        await host.connect(h.url)
        await guest.connect(h.url)
        await host.emit("room:create", {"name": "Lensa"})
        await host.wait_for(lambda s: s["phase"] == "lobby")
        code = host.state["code"]
        await guest.emit("room:join", {"code": code, "name": "Sara"})
        await guest.wait_for(lambda s: len(s["players"]) == 2)

        await host.emit("game:start", {"code": code})
        await host.wait_for(lambda s: s["phase"] == "answering")

        await host.emit(
            "round:answer", {"code": code, "gap": 0, "artist": "Bob Marley", "title": ""}
        )
        await guest.emit(
            "round:answer", {"code": code, "gap": 1, "artist": "Bob Marley", "title": ""}
        )
        revealed = await host.wait_for(lambda s: s["phase"] == "revealing")

        for entry in revealed["outcome"]["scores"].values():
            assert entry["artistRight"] is False
            assert entry["points"] == (30 if entry["yearRight"] else 0)

        await host.disconnect()
        await guest.disconnect()


@pytest.mark.asyncio
async def test_artist_alone_is_worth_seventy(tmp_path):
    """Naming the singer pays even when the card is misplaced."""
    async with Harness(tmp_path) as h:
        host, guest = Client("host-5", "Lensa"), Client("guest-5", "Sara")
        await host.connect(h.url)
        await guest.connect(h.url)
        await host.emit("room:create", {"name": "Lensa"})
        await host.wait_for(lambda s: s["phase"] == "lobby")
        code = host.state["code"]
        await guest.emit("room:join", {"code": code, "name": "Sara"})
        await guest.wait_for(lambda s: len(s["players"]) == 2)

        await host.emit("game:start", {"code": code})
        await host.wait_for(lambda s: s["phase"] == "answering")

        # A surname alone, misspelled, still counts -- that is the point.
        await host.emit(
            "round:answer", {"code": code, "gap": 0, "artist": "Sebsibe", "title": ""}
        )
        await guest.emit(
            "round:answer", {"code": code, "gap": 0, "artist": HARNESS_ARTIST, "title": ""}
        )
        revealed = await host.wait_for(lambda s: s["phase"] == "revealing")

        for pid, entry in revealed["outcome"]["scores"].items():
            assert entry["artistRight"] is True, f"{pid} lost the artist points"
            assert entry["points"] == (100 if entry["yearRight"] else 70)

        await host.disconnect()
        await guest.disconnect()
