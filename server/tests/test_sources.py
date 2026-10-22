"""Tests for the music sources.

The catalogue rule is the one that matters: a Deezer track is attached to a card
only when its artist genuinely matches. A wrong id does not fail loudly -- it
silently plays a completely different song mid-game, which is worse than having
no Deezer id at all. These tests drive the real HTTP code against a fake Deezer.
"""

from __future__ import annotations

import httpx
import pytest

import sources
from sources import deezer_fresh_preview, deezer_probe, deezer_search, extract_youtube_id


class TestExtractYoutubeId:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://www.youtube.com/watch?v=ADc9JPeLYi4", "ADc9JPeLYi4"),
            ("https://youtu.be/ADc9JPeLYi4?t=30", "ADc9JPeLYi4"),
            ("https://www.youtube.com/shorts/ADc9JPeLYi4", "ADc9JPeLYi4"),
            ("https://www.youtube.com/embed/ADc9JPeLYi4", "ADc9JPeLYi4"),
            ("ADc9JPeLYi4", "ADc9JPeLYi4"),
            ("https://example.com/not-youtube", None),
            ("", None),
        ],
    )
    def test_extraction(self, url, expected):
        assert extract_youtube_id(url) == expected


def track(id_: int, artist: str, title: str = "Song", preview: str = "https://cdn/p.mp3") -> dict:
    return {"id": id_, "title": title, "artist": {"name": artist}, "preview": preview}


@pytest.fixture
def deezer(monkeypatch):
    """A fake api.deezer.com. Set `deezer.data` to answer /search; see requests in `deezer.seen`."""

    class Fake:
        def __init__(self) -> None:
            self.data: list[dict] = []
            self.status = 200
            self.seen: list[httpx.Request] = []

        def handler(self, request: httpx.Request) -> httpx.Response:
            self.seen.append(request)
            if request.url.path == "/search":
                return httpx.Response(self.status, json={"data": self.data})
            if request.url.path.startswith("/track/"):
                return httpx.Response(self.status, json={"id": 1, "preview": "https://cdn/fresh.mp3"})
            return httpx.Response(404)

    fake = Fake()
    monkeypatch.setattr(
        sources, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(fake.handler))
    )
    return fake


class TestDeezerSearch:
    async def test_uses_field_scoped_track_search(self, deezer):
        # The whole catalogue finding in one assertion: never /search/artist.
        await deezer_search("Teddy Afro", "Tikur Sew")
        (request,) = deezer.seen
        assert request.url.path == "/search"
        assert request.url.params["q"] == 'artist:"Teddy Afro" track:"Tikur Sew"'

    async def test_tracks_without_a_preview_are_dropped(self, deezer):
        deezer.data = [track(1, "Aster Aweke", preview=""), track(2, "Aster Aweke")]
        assert [t["id"] for t in await deezer_search("Aster Aweke")] == [2]

    async def test_no_answer_is_none_not_an_empty_list(self, deezer):
        # The editor tells the player to try again vs. to add a YouTube link.
        deezer.status = 503
        assert await deezer_search("Aster Aweke") is None

    async def test_an_empty_answer_is_an_empty_list(self, deezer):
        assert await deezer_search("Nobody") == []


class TestDeezerProbe:
    async def test_returns_the_first_track_by_the_right_artist(self, deezer):
        deezer.data = [track(10, "Teddy Karo"), track(11, "Teddy Afro"), track(12, "Teddy Afro")]
        assert await deezer_probe("Teddy Afro", "Tikur Sew") == 11

    async def test_refuses_a_wrong_artist_rather_than_guessing(self, deezer):
        # Deezer's own top answer for "Teddy Afro" was "Teddy Karo". Attaching
        # it would play the wrong song in every game, silently.
        deezer.data = [track(10, "Teddy Karo")]
        assert await deezer_probe("Teddy Afro", "Tikur Sew") is None

    async def test_accepts_a_transliteration_variant(self, deezer):
        deezer.data = [track(5, "Mulatu Astatqe")]
        assert await deezer_probe("Mulatu Astatke", "Yekermo Sew") == 5

    async def test_no_answer_is_no_id(self, deezer):
        deezer.status = 500
        assert await deezer_probe("Aster Aweke", "Gela Gela") is None


class TestFreshPreview:
    async def test_resolves_a_url_per_call(self, deezer):
        assert await deezer_fresh_preview(224802) == "https://cdn/fresh.mp3"
        assert deezer.seen[-1].url.path == "/track/224802"

    async def test_failure_is_none(self, deezer):
        deezer.status = 500
        assert await deezer_fresh_preview(224802) is None
