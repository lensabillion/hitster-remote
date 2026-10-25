"""Tests for the music sources.

The catalogue rule is the one that matters: a Deezer track is attached to a card
only when its artist AND title genuinely match. A wrong id does not fail loudly --
it silently plays a completely different song mid-game, which is worse than
having no Deezer id at all. These tests drive the real HTTP code against a fake
Deezer.
"""

from __future__ import annotations

import httpx
import pytest

import sources
from sources import (
    deezer_album,
    deezer_artist_albums,
    deezer_artist_tracks,
    deezer_fresh_preview,
    deezer_probe,
    deezer_search,
    extract_youtube_id,
)


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


def track(
    id_: int,
    artist: str,
    title: str = "Song",
    preview: str = "https://cdn/p.mp3",
    rank: int = 0,
    album_id: int = 1,
) -> dict:
    return {
        "id": id_, "title": title, "artist": {"id": 7, "name": artist},
        "preview": preview, "rank": rank, "album": {"id": album_id, "title": "Album"},
    }


@pytest.fixture
def deezer(monkeypatch):
    """A fake api.deezer.com.

    `deezer.data` answers /search (sliced by index/limit so paging is real),
    `deezer.albums` answers /artist/{id}/albums; see requests in `deezer.seen`.
    """

    class Fake:
        def __init__(self) -> None:
            self.data: list[dict] = []
            self.albums: list[dict] = []
            self.status = 200
            self.seen: list[httpx.Request] = []

        def handler(self, request: httpx.Request) -> httpx.Response:
            self.seen.append(request)
            if request.url.path == "/search":
                return httpx.Response(self.status, json=self._page(self.data, request))
            if request.url.path.startswith("/artist/"):
                return httpx.Response(self.status, json=self._page(self.albums, request))
            if request.url.path.startswith("/album/"):
                return httpx.Response(
                    self.status,
                    json={"id": 9, "title": "Ethiopiques, Vol. 7", "release_date": "2004-07-04",
                          "record_type": "album", "tracks": {}},
                )
            if request.url.path.startswith("/track/"):
                return httpx.Response(
                    self.status, json={"id": 1, "preview": "https://cdn/fresh.mp3"}
                )
            return httpx.Response(404)

        @staticmethod
        def _page(rows: list[dict], request: httpx.Request) -> dict:
            index = int(request.url.params.get("index", 0))
            limit = int(request.url.params.get("limit", 25))
            page = rows[index : index + limit]
            body = {"data": page, "total": len(rows)}
            if index + limit < len(rows):
                body["next"] = "more"
            return body

    fake = Fake()
    monkeypatch.setattr(
        sources, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(fake.handler))
    )
    return fake


class TestDeezerSearch:
    async def test_uses_a_plain_query_not_the_dead_field_syntax(self, deezer):
        # Deezer stopped honouring artist:"..." / track:"..." in October 2026:
        # every field-scoped query returns zero results. The plain query works.
        await deezer_search("Teddy Afro", "Tikur Sew")
        (request,) = deezer.seen
        assert request.url.path == "/search"
        assert request.url.params["q"] == "Teddy Afro Tikur Sew"

    async def test_artist_alone_is_a_plain_query_too(self, deezer):
        await deezer_search("Aster Aweke")
        assert deezer.seen[0].url.params["q"] == "Aster Aweke"

    async def test_tracks_without_a_preview_are_dropped(self, deezer):
        deezer.data = [track(1, "Aster Aweke", preview=""), track(2, "Aster Aweke")]
        assert [t["id"] for t in await deezer_search("Aster Aweke")] == [2]

    async def test_no_answer_is_none_not_an_empty_list(self, deezer):
        # The editor tells the player to try again vs. to add a YouTube link.
        deezer.status = 503
        assert await deezer_search("Aster Aweke") is None

    async def test_an_empty_answer_is_an_empty_list(self, deezer):
        assert await deezer_search("Nobody") == []

    async def test_a_deezer_error_body_is_no_answer(self, monkeypatch):
        # Deezer reports quota errors with HTTP 200 and an "error" object.
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"error": {"type": "Exception", "code": 4}})

        monkeypatch.setattr(
            sources, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
        )
        assert await deezer_search("Aster Aweke") is None


class TestDeezerProbe:
    async def test_returns_the_track_by_the_right_artist(self, deezer):
        deezer.data = [
            track(10, "Teddy Karo", "Tikur Sew"),
            track(11, "Teddy Afro", "Tikur Sew"),
        ]
        assert await deezer_probe("Teddy Afro", "Tikur Sew") == 11

    async def test_refuses_a_wrong_artist_rather_than_guessing(self, deezer):
        # Deezer's own top answer for "Teddy Afro" was "Teddy Karo". Attaching
        # it would play the wrong song in every game, silently.
        deezer.data = [track(10, "Teddy Karo", "Tikur Sew")]
        assert await deezer_probe("Teddy Afro", "Tikur Sew") is None

    async def test_refuses_a_different_song_by_the_right_artist(self, deezer):
        # A plain query for "Aster Aweke Gela Gela" also returns her other
        # songs. If Gela Gela is not on Deezer the answer is None, not one of them.
        deezer.data = [track(5, "Aster Aweke", "Demam Gelayewa")]
        assert await deezer_probe("Aster Aweke", "Gela Gela") is None

    async def test_accepts_a_transliteration_variant(self, deezer):
        deezer.data = [track(5, "Mulatu Astatqe", "Yèkèrmo Sèw")]
        assert await deezer_probe("Mulatu Astatke", "Yekermo Sew") == 5

    async def test_accepts_a_subtitled_album_cut(self, deezer):
        deezer.data = [track(5, "Mahmoud Ahmed", "Tezeta (Nostalgia)")]
        assert await deezer_probe("Mahmoud Ahmed", "Tezeta") == 5

    async def test_prefers_the_most_popular_version(self, deezer):
        # The same song on an album, a compilation and a live record: the one
        # people actually play is the original.
        deezer.data = [
            track(1, "Aster Aweke", "Kabu", rank=1000),
            track(2, "Aster Aweke", "Kabu", rank=90000),
            track(3, "Aster Aweke", "Kabu (Live)", rank=5000),
        ]
        assert await deezer_probe("Aster Aweke", "Kabu") == 2

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


class TestArtistTracks:
    """The harvest's raw material: a verified, paged, rank-ordered catalogue."""

    async def test_pages_through_and_keeps_only_the_artist(self, deezer):
        deezer.data = [track(i, "Mahmoud Ahmed", f"Song {i}", rank=i) for i in range(150)]
        deezer.data[3] = track(3, "Mahmoud Shakur", "Other", rank=10**6)
        deezer.data[7] = track(7, "Mahmoud Ahmed", "Silent", preview="", rank=10**6)

        found = await deezer_artist_tracks("Mahmoud Ahmed")

        assert [r.url.params["index"] for r in deezer.seen] == ["0", "100"]
        assert len(found) == 148
        assert all(t["artist"]["name"] == "Mahmoud Ahmed" for t in found)
        assert found[0]["id"] == 149, "most popular first"

    async def test_stops_at_the_cap(self, deezer):
        deezer.data = [track(i, "Aster Aweke", f"Song {i}") for i in range(250)]
        found = await deezer_artist_tracks("Aster Aweke", max_results=100)
        assert len(found) == 100
        assert len(deezer.seen) == 1

    async def test_no_answer_at_all_is_none(self, deezer):
        deezer.status = 503
        assert await deezer_artist_tracks("Aster Aweke") is None


class TestArtistAlbums:
    async def test_pages_through_the_discography(self, deezer):
        deezer.albums = [
            {"id": i, "title": f"Album {i}", "release_date": "1989-01-01", "record_type": "album"}
            for i in range(120)
        ]
        albums = await deezer_artist_albums(84315)
        assert len(albums) == 120
        assert deezer.seen[0].url.path == "/artist/84315/albums"

    async def test_no_answer_is_an_empty_list(self, deezer):
        deezer.status = 500
        assert await deezer_artist_albums(84315) == []


class TestAlbum:
    async def test_returns_just_the_dating_fields(self, deezer):
        assert await deezer_album(9) == {
            "id": 9, "title": "Ethiopiques, Vol. 7", "release_date": "2004-07-04",
            "record_type": "album",
        }

    async def test_no_answer_is_none(self, deezer):
        deezer.status = 500
        assert await deezer_album(9) is None
