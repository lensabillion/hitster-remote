"""Music sources.

Deezer is primary, YouTube is the per-card fallback. A 30-second preview is
~500 KB against a video stream, which matters on a thin connection, and neither
source needs an API key.

Amharic coverage on Deezer is good -- most major artists have playable,
correctly-attributed tracks -- but the search has to be driven carefully:

- Search with a PLAIN query ("Aster Aweke Gela Gela"), never the documented
  field syntax. `artist:"Aster Aweke"` returned exactly the right tracks when
  this project started (September 2026) and returns nothing at all since
  October 2026: Deezer now ignores the field prefixes, so `track:"Gela Gela"`
  matches "Moving Gelatine Plates". A plain query ranks by popularity across
  every artist, which is why every result is verified with `artist_matches`
  before it is attached to a card.
- `/search/artist` is unreliable for these names -- it answers "Teddy Afro"
  with "Teddy Karo". Artist ids are taken from verified track results instead.
- Amharic *script* search does not work: "አስቴር አወቀ" returns nothing. Search by
  Latin transliteration and carry the Amharic strings separately for display.
- Deezer answers a throttled query with an empty result set, not an error.

Deezer preview URLs are HMAC-signed and expire 15 minutes after issue, so they
are resolved per round and never stored.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

# Matching lives in matching.py so the strict catalogue rule and the generous
# player-input rule sit side by side and cannot drift apart.
from matching import artist_matches, title_matches

DEEZER_API = "https://api.deezer.com"
# Deezer's page size ceiling.
DEEZER_PAGE = 100
YOUTUBE_ID_RE = re.compile(r"(?:v=|youtu\.be/|/embed/|/shorts/)([0-9A-Za-z_-]{11})")
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _client() -> httpx.AsyncClient:
    """The one place an HTTP client is built, so tests can swap the transport."""
    return httpx.AsyncClient(timeout=_TIMEOUT)


def extract_youtube_id(url: str) -> str | None:
    if match := YOUTUBE_ID_RE.search(url):
        return match.group(1)
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", url.strip()):
        return url.strip()
    return None


async def _get(path: str, **params: Any) -> dict[str, Any] | None:
    """One Deezer call. None when Deezer did not answer; the parsed body otherwise."""
    try:
        async with _client() as client:
            r = await client.get(f"{DEEZER_API}{path}", params=params)
            r.raise_for_status()
            body = r.json()
    except Exception:  # a third-party API: any failure means "no answer"
        return None
    # Deezer reports its own errors in a 200 body ({"error": {...}}).
    return None if not isinstance(body, dict) or body.get("error") else body


async def deezer_search(
    artist: str, title: str = "", limit: int = 8
) -> list[dict[str, Any]] | None:
    """Plain track search for an artist and, optionally, a title.

    None when Deezer did not answer. Only tracks with a preview come back; one
    with nothing to play is useless here. An empty list is a real answer --
    possibly a throttled one, since Deezer answers a throttled query with an
    empty result set, not an error.

    Results are not filtered by artist: the deck editor shows every candidate
    and flags the doubtful ones, because only a person can tell which of them
    is the song they meant. `deezer_probe` is the strict, automatic version.
    """
    query = f"{artist.strip()} {title.strip()}".strip()
    body = await _get("/search", q=query, limit=limit)
    if body is None:
        return None
    return [t for t in body.get("data", []) if t.get("preview")]


async def deezer_probe(artist_latin: str, title_latin: str) -> int | None:
    """Find a Deezer track id, but only when artist AND title genuinely match.

    Returns None rather than a wrong track: a mis-attributed card is worse than
    no Deezer id at all, because playback would serve a different song entirely.
    The title check matters now that the query is plain text -- "Aster Aweke
    Gela Gela" also returns "Demam Gelayewa", and without it a song Deezer does
    not carry would be attached to whichever of the artist's songs came first.

    Among several matching versions (an album cut, a compilation, a live take)
    the most popular one is taken, which is almost always the original.
    """
    best: dict[str, Any] | None = None
    for track in await deezer_search(artist_latin, title_latin, limit=15) or []:
        if not artist_matches(artist_latin, track["artist"]["name"]):
            continue
        if not title_matches(title_latin, track["title"]):
            continue
        if best is None or track.get("rank", 0) > best.get("rank", 0):
            best = track
    return int(best["id"]) if best else None


async def deezer_fresh_preview(track_id: int) -> str | None:
    """Resolve a playable preview URL. Valid for ~15 minutes, so call per round."""
    body = await _get(f"/track/{track_id}")
    return (body or {}).get("preview") or None


async def deezer_artist_tracks(
    artist: str, max_results: int = 300
) -> list[dict[str, Any]] | None:
    """Every playable track Deezer attributes to `artist`, verified, in rank order.

    Pages through the plain search for the artist's name and keeps only tracks
    whose artist genuinely matches -- a plain query for "Teddy Afro" leads with
    Teddy Robb and Teddy Grossman. None when Deezer did not answer at all.

    This is the raw material of a harvest: the artist's catalogue as Deezer has
    it, which the deck builder then narrows to the songs worth a card.
    """
    found: list[dict[str, Any]] = []
    index = 0
    while index < max_results:
        body = await _get("/search", q=artist.strip(), limit=DEEZER_PAGE, index=index)
        if body is None:
            return found or None
        page = body.get("data", [])
        found += [
            t for t in page
            if t.get("preview") and artist_matches(artist, t["artist"]["name"])
        ]
        index += DEEZER_PAGE
        if not page or not body.get("next"):
            break
    found.sort(key=lambda t: t.get("rank", 0), reverse=True)
    return found


async def deezer_artist_albums(artist_id: int) -> list[dict[str, Any]]:
    """An artist's releases with their dates -- the only year evidence Deezer has.

    Each entry carries `release_date` and `record_type` (album, single, ep,
    compilation). The date is the date of THAT release, which for a reissue or
    an "Ethiopiques" compilation is decades after the song; the harvest treats
    it as a proposal to be confirmed, never as the answer.
    """
    albums: list[dict[str, Any]] = []
    index = 0
    while True:
        body = await _get(f"/artist/{artist_id}/albums", limit=DEEZER_PAGE, index=index)
        if body is None:
            break
        page = body.get("data", [])
        albums += page
        index += DEEZER_PAGE
        if not page or not body.get("next"):
            break
    return albums


async def deezer_album(album_id: int) -> dict[str, Any] | None:
    """One release's date and kind, for a track found on an album that is not
    in its artist's own discography -- a various-artists compilation, say."""
    body = await _get(f"/album/{album_id}")
    if body is None:
        return None
    return {
        "id": body.get("id"),
        "title": body.get("title", ""),
        "release_date": body.get("release_date", ""),
        "record_type": body.get("record_type", ""),
    }
