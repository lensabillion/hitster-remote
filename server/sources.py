"""Music sources.

Deezer is primary, YouTube is the per-card fallback. A 30-second preview is
~500 KB against a video stream, which matters on a thin connection, and neither
source needs an API key.

Amharic coverage on Deezer is good -- 21 of 24 major artists have playable,
correctly-attributed tracks -- but ONLY through field-scoped track search
(`artist:"..." track:"..."`). The `/search/artist` endpoint is unreliable for
these names: it answers "Teddy Afro" with "Teddy Karo", an unrelated artist,
while the field-scoped search returns 23 playable Teddy Afro tracks. Do not
reach for `/search/artist` here.

Amharic *script* search does not work either: "አስቴር አወቀ" and "ማህሙድ አህመድ" both
return nothing. Search by Latin transliteration and carry the Amharic strings
separately for display.

Deezer preview URLs are HMAC-signed and expire 15 minutes after issue, so they
are resolved per round and never stored.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

# Matching lives in matching.py so the strict catalogue rule and the generous
# player-input rule sit side by side and cannot drift apart.
from matching import artist_matches

DEEZER_API = "https://api.deezer.com"
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


async def deezer_search(
    artist: str, title: str = "", limit: int = 8
) -> list[dict[str, Any]] | None:
    """Field-scoped track search. None when Deezer did not answer.

    Only tracks with a preview come back; one with nothing to play is useless
    here. An empty list is a real answer -- possibly a throttled one, since
    Deezer answers a throttled query with an empty result set, not an error.
    """
    query = f'artist:"{artist.strip()}"'
    if title.strip():
        query += f' track:"{title.strip()}"'
    try:
        async with _client() as client:
            r = await client.get(f"{DEEZER_API}/search", params={"q": query, "limit": limit})
            r.raise_for_status()
            tracks = r.json().get("data", [])
    except Exception:  # a third-party API: any failure means "no answer"
        return None
    return [t for t in tracks if t.get("preview")]


async def deezer_probe(artist_latin: str, title_latin: str) -> int | None:
    """Find a Deezer track id, but only when the artist genuinely matches.

    Returns None rather than a wrong track: a mis-attributed card is worse than
    no Deezer id at all, because playback would serve a different song entirely.
    """
    for track in await deezer_search(artist_latin, title_latin, limit=5) or []:
        if artist_matches(artist_latin, track["artist"]["name"]):
            return int(track["id"])
    return None


async def deezer_fresh_preview(track_id: int) -> str | None:
    """Resolve a playable preview URL. Valid for ~15 minutes, so call per round."""
    try:
        async with _client() as client:
            r = await client.get(f"{DEEZER_API}/track/{track_id}")
            r.raise_for_status()
            return r.json().get("preview") or None
    except Exception:  # see deezer_search
        return None
