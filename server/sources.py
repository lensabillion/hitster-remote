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

import httpx

# Matching lives in matching.py so the strict catalogue rule and the generous
# player-input rule sit side by side and cannot drift apart.
from matching import artist_matches, normalize, similarity  # noqa: F401

YOUTUBE_ID_RE = re.compile(r"(?:v=|youtu\.be/|/embed/|/shorts/)([0-9A-Za-z_-]{11})")
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def extract_youtube_id(url: str) -> str | None:
    if match := YOUTUBE_ID_RE.search(url):
        return match.group(1)
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", url.strip()):
        return url.strip()
    return None


def strip_youtube_decorations(title: str) -> str:
    """Remove '(Official Video)', '[HD]', '| Ethiopian Music 2024' and friends."""
    title = re.sub(r"\s*[\(\[][^()\[\]]*[\)\]]", "", title)
    title = re.split(r"\s*\|\s*", title)[0]
    return title.strip(" -–—")


async def youtube_title(video_id: str) -> dict[str, str] | None:
    """Title and channel via oEmbed -- no API key, no quota."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                "https://www.youtube.com/oembed",
                params={
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "format": "json",
                },
            )
            r.raise_for_status()
            data = r.json()
            return {
                "title": data.get("title", ""),
                "channel": data.get("author_name", ""),
                "thumbnail": data.get("thumbnail_url", ""),
            }
    except Exception:
        return None


async def deezer_probe(artist_latin: str, title_latin: str) -> int | None:
    """Find a Deezer track id, but only when the artist genuinely matches.

    Returns None rather than a wrong track: a mis-attributed card is worse than
    no Deezer id at all, because playback would serve a different song entirely.
    """
    query = f'artist:"{artist_latin}" track:"{title_latin}"'
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                "https://api.deezer.com/search", params={"q": query, "limit": 5}
            )
            r.raise_for_status()
            for track in r.json().get("data", []):
                if not track.get("preview"):
                    continue
                if artist_matches(artist_latin, track["artist"]["name"]):
                    return int(track["id"])
    except Exception:
        pass
    return None


async def deezer_fresh_preview(track_id: int) -> str | None:
    """Resolve a playable preview URL. Valid for ~15 minutes, so call per round."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(f"https://api.deezer.com/track/{track_id}")
            r.raise_for_status()
            return r.json().get("preview") or None
    except Exception:
        return None
