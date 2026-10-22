"""The deck as data.

Every card's year is confirmed by a human, once, and the deck is then a committed
asset -- decks/deck.json -- that every deploy seeds its database from. This module
owns that file's shape: the stable card id, the export, and the diff that tells the
/deck editor what exists only in a live database and would be lost.

The CLI export and the HTTP download both go through export_text(), so the file a
player downloads is byte-identical to the one the CLI writes, and committing it
produces a diff of real changes only.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path
from typing import Any

from game import Card

# A release year outside this range is a typo, not a song. The ceiling is this
# year: nothing in the deck can have come out later than today.
EARLIEST_YEAR = 1900
LATEST_YEAR = date.today().year

EXPORT_FIELDS = (
    "id", "year", "artist_latin", "title_latin",
    "artist_am", "title_am", "youtube_id", "deezer_track_id", "added_by",
)


def card_id(artist: str, title: str) -> str:
    """Stable id from artist and title, so re-adding a song updates it in place
    rather than creating a duplicate."""
    key = f"{artist.lower().strip()}|{title.lower().strip()}"
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def is_playable(card: Mapping[str, Any]) -> bool:
    """A card needs a source, or it comes up mid-game with nothing to play."""
    return bool(card.get("deezer_track_id") or card.get("youtube_id"))


def card_from_row(row: Mapping[str, Any]) -> Card:
    """A database row or deck.json entry, as the rules engine sees it."""
    return Card(
        id=row["id"],
        year=row["year"],
        artist_latin=row["artist_latin"],
        title_latin=row["title_latin"],
        artist_am=row.get("artist_am", ""),
        title_am=row.get("title_am", ""),
        youtube_id=row.get("youtube_id", ""),
        deezer_track_id=row.get("deezer_track_id"),
        added_by=row.get("added_by", ""),
    )


def export_rows(cards: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Cards in deck.json form, in a deterministic order.

    Sorted by (year, id) rather than year alone: SQLite promises no order for
    ties, and two cards sharing a year could otherwise swap places between
    exports and show up as a change when nothing changed.
    """
    rows = [{k: c[k] for k in EXPORT_FIELDS} for c in cards]
    rows.sort(key=lambda r: (r["year"], r["id"]))
    return rows


def export_text(cards: Iterable[Mapping[str, Any]]) -> str:
    return json.dumps(export_rows(cards), ensure_ascii=False, indent=2) + "\n"


def load_deck_file(path: Path) -> list[dict[str, Any]] | None:
    """The committed deck, or None when there is no file to compare against."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def diff_decks(
    committed: Iterable[Mapping[str, Any]], live: Iterable[Mapping[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """What the live deck has that the committed file does not, and vice versa.

    A card counts as changed when any exported field differs -- a corrected year
    is exactly the kind of edit that must not be lost.
    """
    before = {r["id"]: {k: r.get(k) for k in EXPORT_FIELDS} for r in committed}
    after = {r["id"]: {k: r.get(k) for k in EXPORT_FIELDS} for r in live}

    def brief(row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"], "year": row["year"],
            "artistLatin": row["artist_latin"], "titleLatin": row["title_latin"],
        }

    return {
        "added": [brief(after[i]) for i in sorted(after.keys() - before.keys())],
        "removed": [brief(before[i]) for i in sorted(before.keys() - after.keys())],
        "changed": [
            brief(after[i])
            for i in sorted(after.keys() & before.keys())
            if after[i] != before[i]
        ],
    }
