#!/usr/bin/env python3
"""Deck builder.

Release years cannot be taken from an API. MusicBrainz returns three different
answers for "Billie Jean"; Deezer and iTunes both report reissue dates. So every
year is confirmed by a human here, once, offline -- and the deck is then a
committed asset the game just reads.

Deezer is the primary source, so a card needs only artist, title and year. A
YouTube URL is optional and is the fallback for the ~13% of Amharic artists
Deezer does not carry.

    python tools/build_deck.py add                  # one card at a time
    python tools/build_deck.py import cards.tsv     # bulk
    python tools/build_deck.py list
    python tools/build_deck.py check                # re-probe sources

Seed file is tab-separated, '#' comments allowed:

    year <TAB> artist_latin <TAB> title_latin [<TAB> artist_am <TAB> title_am <TAB> youtube_url]

A card with neither a Deezer match nor a YouTube URL is rejected, because it
would be unplayable.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import db  # noqa: E402
from sources import (  # noqa: E402
    deezer_probe,
    extract_youtube_id,
    strip_youtube_decorations,
    youtube_title,
)

THIS_YEAR = 2026
EARLIEST_YEAR = 1900


def card_id(artist: str, title: str) -> str:
    return hashlib.sha1(f"{artist.lower()}|{title.lower()}".encode()).hexdigest()[:12]


def valid_year(value: str) -> int | None:
    try:
        year = int(value)
    except (ValueError, TypeError):
        return None
    return year if EARLIEST_YEAR <= year <= THIS_YEAR else None


def split_artist_title(raw: str) -> tuple[str, str]:
    cleaned = strip_youtube_decorations(raw)
    for sep in (" - ", " – ", " — "):
        if sep in cleaned:
            artist, title = cleaned.split(sep, 1)
            return artist.strip(), title.strip()
    return "", cleaned


async def build_card(
    year: int,
    artist_latin: str,
    title_latin: str,
    artist_am: str = "",
    title_am: str = "",
    youtube_url: str = "",
    added_by: str = "",
) -> dict | None:
    if not artist_latin or not title_latin:
        print("  ✗ needs both an artist and a title (in Latin script)")
        return None

    deezer_id = await deezer_probe(artist_latin, title_latin)
    youtube_id = extract_youtube_id(youtube_url) if youtube_url else None

    if not deezer_id and not youtube_id:
        print(
            f"  ✗ {artist_latin} — {title_latin}: not on Deezer and no YouTube URL. "
            "Add a YouTube link for this one."
        )
        return None

    return {
        "id": card_id(artist_latin, title_latin),
        "year": year,
        "artist_latin": artist_latin,
        "title_latin": title_latin,
        "artist_am": artist_am,
        "title_am": title_am,
        "youtube_id": youtube_id or "",
        "deezer_track_id": deezer_id,
        "added_by": added_by,
    }


def describe(card: dict) -> str:
    artist = card["artist_am"] or card["artist_latin"]
    title = card["title_am"] or card["title_latin"]
    sources = []
    if card["deezer_track_id"]:
        sources.append("deezer")
    if card["youtube_id"]:
        sources.append("youtube")
    who = f"  ·  {card['added_by']}" if card.get("added_by") else ""
    return f"  ✓ {card['year']}  {artist} — {title}  [{'+'.join(sources)}]{who}"


async def cmd_add(args: argparse.Namespace) -> int:
    await db.connect()
    added = 0
    try:
        while True:
            print()
            artist = input("Artist (Latin, blank to finish): ").strip()
            if not artist:
                break
            title = input("Title  (Latin): ").strip()
            artist_am = input("Artist (አማርኛ, optional): ").strip()
            title_am = input("Title  (አማርኛ, optional): ").strip()

            year = None
            while year is None:
                year = valid_year(input("Original release year: ").strip())
                if year is None:
                    print(f"  needs a year between {EARLIEST_YEAR} and {THIS_YEAR}")

            card = await build_card(
                year, artist, title, artist_am, title_am, added_by=args.by
            )
            if card is None:
                url = input("  YouTube URL for this song (blank to skip): ").strip()
                if url:
                    card = await build_card(
                        year, artist, title, artist_am, title_am, url, args.by
                    )
            if card:
                await db.upsert_cards([card])
                print(describe(card))
                added += 1
    except (EOFError, KeyboardInterrupt):
        print()
    total = await db.card_count()
    await db.close()
    print(f"\nAdded {added}. Deck now holds {total} cards.")
    return 0


async def cmd_import(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if not path.exists():
        print(f"No such file: {path}")
        return 1

    await db.connect()
    cards, failures = [], 0
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 3:
            print(f"  ✗ line {lineno}: need at least year, artist and title")
            failures += 1
            continue

        year = valid_year(parts[0])
        if year is None:
            print(f"  ✗ line {lineno}: bad year {parts[0]!r}")
            failures += 1
            continue

        parts += [""] * (6 - len(parts))
        card = await build_card(
            year, parts[1], parts[2], parts[3], parts[4], parts[5], args.by
        )
        if card:
            cards.append(card)
            print(describe(card))
        else:
            failures += 1

    if cards:
        await db.upsert_cards(cards)
    total = await db.card_count()
    await db.close()

    both = sum(1 for c in cards if c["deezer_track_id"] and c["youtube_id"])
    deezer_only = sum(1 for c in cards if c["deezer_track_id"] and not c["youtube_id"])
    yt_only = sum(1 for c in cards if c["youtube_id"] and not c["deezer_track_id"])
    print(f"\nImported {len(cards)} cards ({failures} failed).")
    print(f"  deezer only: {deezer_only}   youtube only: {yt_only}   both: {both}")
    print(f"Deck now holds {total} cards.")
    return 1 if failures else 0


async def cmd_list(_: argparse.Namespace) -> int:
    await db.connect()
    cards = await db.all_cards()
    await db.close()
    if not cards:
        print("Deck is empty. Add cards with: python tools/build_deck.py add")
        return 0
    print(f"{len(cards)} cards\n")
    for c in cards:
        print(describe(c))
    print(f"\nSpanning {cards[0]['year']}–{cards[-1]['year']}.")
    return 0


async def cmd_check(_: argparse.Namespace) -> int:
    """Re-probe every card, so a source that has gone away surfaces before a game."""
    await db.connect()
    cards = await db.all_cards()
    broken = 0
    for c in cards:
        deezer_id = await deezer_probe(c["artist_latin"], c["title_latin"])
        has_yt = bool(c["youtube_id"])
        if not deezer_id and not has_yt:
            print(f"  ✗ unplayable: {c['artist_latin']} — {c['title_latin']}")
            broken += 1
        elif deezer_id != c["deezer_track_id"]:
            print(
                f"  ~ deezer id changed: {c['artist_latin']} — {c['title_latin']} "
                f"{c['deezer_track_id']} → {deezer_id}"
            )
    await db.close()
    print(f"\nChecked {len(cards)} cards. {broken} unplayable.")
    return 1 if broken else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Zema deck.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="add cards interactively")
    p_add.add_argument("--by", default="", help="who is adding these cards")
    p_add.set_defaults(func=cmd_add)

    p_import = sub.add_parser("import", help="bulk import from a TSV seed file")
    p_import.add_argument("file")
    p_import.add_argument("--by", default="", help="who is adding these cards")
    p_import.set_defaults(func=cmd_import)

    sub.add_parser("list", help="show the current deck").set_defaults(func=cmd_list)
    sub.add_parser("check", help="re-probe every card's sources").set_defaults(
        func=cmd_check
    )

    args = parser.parse_args()
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
