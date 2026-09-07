#!/usr/bin/env python3
"""Deck builder.

Release years cannot be taken from an API. MusicBrainz returns three different
answers for "Billie Jean"; Deezer and iTunes both report reissue dates. So every
card's year is confirmed by a human here, once, offline -- and the deck is then a
committed asset the game just reads.

Two ways in:

    python tools/build_deck.py add                 # one card at a time
    python tools/build_deck.py import cards.tsv    # bulk, from a seed file

Seed file is tab-separated, one card per line, '#' comments allowed:

    youtube_url <TAB> year <TAB> artist_latin <TAB> title_latin [<TAB> artist_am <TAB> title_am]

Anything omitted is inferred from the YouTube title via oEmbed, which needs no
API key. Deezer is probed opportunistically and attached only when the artist
genuinely matches.
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


def card_id(youtube_id: str) -> str:
    return hashlib.sha1(youtube_id.encode()).hexdigest()[:12]


def split_artist_title(raw: str) -> tuple[str, str]:
    """Best-effort 'Artist - Title' split from a YouTube title."""
    cleaned = strip_youtube_decorations(raw)
    for sep in (" - ", " – ", " — "):
        if sep in cleaned:
            artist, title = cleaned.split(sep, 1)
            return artist.strip(), title.strip()
    return "", cleaned


def valid_year(value: str) -> int | None:
    try:
        year = int(value)
    except ValueError:
        return None
    return year if EARLIEST_YEAR <= year <= THIS_YEAR else None


async def build_card(
    url: str,
    year: int | None = None,
    artist_latin: str = "",
    title_latin: str = "",
    artist_am: str = "",
    title_am: str = "",
    added_by: str = "",
    interactive: bool = False,
) -> dict | None:
    youtube_id = extract_youtube_id(url)
    if not youtube_id:
        print(f"  ✗ not a YouTube URL: {url}")
        return None

    meta = await youtube_title(youtube_id)
    if meta:
        guess_artist, guess_title = split_artist_title(meta["title"])
        artist_latin = artist_latin or guess_artist or meta["channel"]
        title_latin = title_latin or guess_title
    elif not (artist_latin and title_latin):
        print(f"  ✗ could not read the YouTube title for {youtube_id}")
        return None

    if interactive:
        print(f"  YouTube: {meta['title'] if meta else youtube_id}")
        artist_latin = input(f"  Artist (Latin) [{artist_latin}]: ").strip() or artist_latin
        title_latin = input(f"  Title  (Latin) [{title_latin}]: ").strip() or title_latin
        artist_am = input(f"  Artist (አማርኛ)  [{artist_am}]: ").strip() or artist_am
        title_am = input(f"  Title  (አማርኛ)  [{title_am}]: ").strip() or title_am
        while year is None:
            year = valid_year(input("  Original release year: ").strip())
            if year is None:
                print(f"    needs a year between {EARLIEST_YEAR} and {THIS_YEAR}")

    if year is None:
        print(f"  ✗ no year for {artist_latin} - {title_latin}")
        return None

    deezer_id = await deezer_probe(artist_latin, title_latin)

    return {
        "id": card_id(youtube_id),
        "year": year,
        "artist_latin": artist_latin,
        "title_latin": title_latin,
        "artist_am": artist_am,
        "title_am": title_am,
        "youtube_id": youtube_id,
        "deezer_track_id": deezer_id,
        "added_by": added_by,
    }


def describe(card: dict) -> str:
    artist = card["artist_am"] or card["artist_latin"]
    title = card["title_am"] or card["title_latin"]
    source = "youtube+deezer" if card["deezer_track_id"] else "youtube"
    return f"  ✓ {card['year']}  {artist} — {title}  [{source}]"


async def cmd_add(args: argparse.Namespace) -> int:
    await db.connect()
    added = 0
    try:
        while True:
            url = input("\nYouTube URL (blank to finish): ").strip()
            if not url:
                break
            card = await build_card(url, added_by=args.by, interactive=True)
            if card:
                await db.upsert_cards([card])
                print(describe(card))
                added += 1
    except (EOFError, KeyboardInterrupt):
        print()
    finally:
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
        if len(parts) < 2:
            print(f"  ✗ line {lineno}: need at least a URL and a year")
            failures += 1
            continue
        url, year_raw, *rest = parts
        year = valid_year(year_raw)
        if year is None:
            print(f"  ✗ line {lineno}: bad year {year_raw!r}")
            failures += 1
            continue
        rest += [""] * (4 - len(rest))
        card = await build_card(
            url, year, rest[0], rest[1], rest[2], rest[3], added_by=args.by
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

    with_deezer = sum(1 for c in cards if c["deezer_track_id"])
    print(f"\nImported {len(cards)} cards ({failures} failed).")
    print(f"{with_deezer} also playable from Deezer; the rest are YouTube-only.")
    print(f"Deck now holds {total} cards.")
    return 0 if not failures else 1


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
    span = f"{cards[0]['year']}–{cards[-1]['year']}"
    print(f"\nSpanning {span}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Hitster Remote deck.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="add cards interactively")
    p_add.add_argument("--by", default="", help="who is adding these cards")
    p_add.set_defaults(func=cmd_add)

    p_import = sub.add_parser("import", help="bulk import from a TSV seed file")
    p_import.add_argument("file")
    p_import.add_argument("--by", default="", help="who is adding these cards")
    p_import.set_defaults(func=cmd_import)

    p_list = sub.add_parser("list", help="show the current deck")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
