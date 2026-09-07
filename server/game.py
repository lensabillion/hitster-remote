from __future__ import annotations

import re
import time
from difflib import SequenceMatcher

YOUTUBE_ID_RE = re.compile(
    r"(?:v=|youtu\.be/|/embed/|/shorts/)([0-9A-Za-z_-]{11})"
)
PLAYLIST_ID_RE = re.compile(r"[?&]list=([A-Za-z0-9_-]+)")


def extract_video_id(url: str) -> str | None:
    match = YOUTUBE_ID_RE.search(url)
    if match:
        return match.group(1)
    if len(url) == 11 and re.fullmatch(r"[0-9A-Za-z_-]{11}", url):
        return url
    return None


def extract_playlist_id(url: str) -> str | None:
    match = PLAYLIST_ID_RE.search(url)
    if match:
        pid = match.group(1)
        # Ignore the special "Mix" / radio playlists — they're per-user and
        # not addressable through the Data API.
        if pid.startswith("RD") or pid.startswith("UL"):
            return None
        return pid
    return None


def parse_artist_song(title: str) -> tuple[str, str]:
    """Parse 'Artist - Song' from a YouTube title.

    Strips common decorations like (Official Video), [HD], etc.
    """
    cleaned = re.sub(r"\s*[\(\[][^()\[\]]*[\)\]]", "", title).strip()
    # Try to split on dash variants
    for sep in [" - ", " – ", " — "]:
        if sep in cleaned:
            artist, song = cleaned.split(sep, 1)
            return artist.strip(), song.strip()
    return cleaned, ""


def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def fuzzy_match(guess: str, target: str, threshold: float = 0.6) -> bool:
    """Server-side guard. Frontend uses fuse.js as the primary check."""
    g, t = normalize(guess), normalize(target)
    if not g or not t:
        return False
    if g == t or g in t or t in g:
        return True
    return SequenceMatcher(None, g, t).ratio() >= threshold


def score_guess(elapsed_seconds: float, correct: bool) -> int:
    """1 point base + up to 5 speed bonus.

    Bonus drops by 1 every 3 seconds: <3s=5, <6s=4, <9s=3, <12s=2, <15s=1, else=0.
    """
    if not correct:
        return 0
    bonus = max(0, 5 - int(elapsed_seconds // 3))
    return 1 + bonus


def now_ms() -> int:
    return int(time.time() * 1000)
