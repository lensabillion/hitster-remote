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
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import card_id, db  # noqa: E402
from sources import (  # noqa: E402
    deezer_probe,
    extract_youtube_id,
    strip_youtube_decorations,
    youtube_title,
)

THIS_YEAR = 2026
EARLIEST_YEAR = 1900


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


NOISE = re.compile(
    r"(?i)\b(official|lyrics?|video|clip|music|remastered|new|ethiopian|amharic"
    r"|audio|hd|full|album|with lyrics|ft\.?|feat\.?)\b"
)


def tidy(text: str) -> str:
    text = re.sub(r"[\(\[][^()\[\]]*[\)\]]", " ", text)
    text = NOISE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip(" -–—_|:,\"'")


def guess_artist_title(raw: str) -> tuple[str, str]:
    """Best guess at (artist, title) from a messy YouTube title.

    Real playlists are not tidy. Of 65 videos in the playlist this was built
    against, only 21 used a plain "Artist - Title" form; the rest hid the artist
    behind "By X", pipes, colons, or nothing at all. This recovers what it can
    and leaves the rest for a human -- it never invents an artist.
    """
    if m := re.search(r"(?i)^(.*?)\s+by\s+(.+)$", tidy(raw)):
        return tidy(m.group(2)), tidy(m.group(1))
    for sep in (" - ", " – ", " — ", " _ ", " | ", " : "):
        if sep in raw:
            parts = [tidy(p) for p in raw.split(sep)]
            parts = [p for p in parts if p]
            if len(parts) >= 2:
                return parts[0], parts[1]
    return "", tidy(raw)


def fetch_playlist(url: str) -> list[dict]:
    """List a playlist's videos. Metadata only -- nothing is downloaded."""
    try:
        from yt_dlp import YoutubeDL
    except ImportError:
        print("This needs yt-dlp:  pip install yt-dlp")
        return []
    opts = {"quiet": True, "extract_flat": True, "skip_download": True,
            "ignoreerrors": True, "no_warnings": True}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False) or {}
    return [e for e in (info.get("entries") or []) if e and e.get("id")]


async def cmd_playlist(args: argparse.Namespace) -> int:
    """Turn a YouTube playlist into a worksheet a human can finish.

    This deliberately does NOT write to the deck. No source gives a trustworthy
    original release year, and this playlist's titles carry no years at all, so
    every year has to come from a person. What the tool removes is the typing of
    ids, artists and titles -- not the judgement.
    """
    entries = fetch_playlist(args.url)
    if not entries:
        print("No videos found. Is the playlist public?")
        return 1

    print(f"{len(entries)} videos. Checking Deezer for lighter audio…\n")
    rows, deezer_hits, needs_artist = [], 0, 0

    for entry in entries:
        raw = (entry.get("title") or "").strip()
        vid = entry["id"]
        if not raw:
            rows.append(("", "", "", vid, "blank title — needs everything"))
            needs_artist += 1
            continue

        artist, title = guess_artist_title(raw)
        deezer_id = await deezer_probe(artist, title) if artist and title else None
        if deezer_id:
            deezer_hits += 1
        if not artist:
            needs_artist += 1
        note = raw[:60]
        rows.append((artist, title, deezer_id or "", vid, note))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        fh.write(
            "# Worksheet from a YouTube playlist. Fill in the YEAR on every line,\n"
            "# fix any artist/title the guesser got wrong, then:\n"
            f"#     python tools/build_deck.py import {out}\n"
            "#\n"
            "# No API gives a trustworthy original release year, and none of these\n"
            "# titles carry one, so the years have to be yours. Delete any line you\n"
            "# do not want in the deck.\n"
            "#\n"
            "# year <TAB> artist_latin <TAB> title_latin <TAB> artist_am <TAB> title_am <TAB> youtube_url\n"
        )
        for artist, title, deezer_id, vid, note in rows:
            fh.write(
                f"?\t{artist}\t{title}\t\t\t"
                f"https://www.youtube.com/watch?v={vid}\t# {note}\n"
            )

    print(f"Wrote {out}")
    print(f"  {len(rows)} rows")
    print(f"  {needs_artist} need an artist typed in by hand")
    print(f"  {deezer_hits} also found on Deezer (lighter audio; the rest play from YouTube)")
    print(f"  {len(rows)} need a year — every single one")
    return 0


async def cmd_export(args: argparse.Namespace) -> int:
    """Write the resolved deck to JSON so it can be shipped as data.

    Curation is expensive and already done: every card here has a
    human-confirmed year and, where one exists, a Deezer track id that was
    verified when it was added. Re-deriving that at deploy time makes the build
    depend on Deezer's search being healthy, and it is not always -- under
    throttling Deezer answers queries with an empty result set rather than an
    error, so an import silently produces a near-empty deck and the game then
    refuses to start.
    """
    await db.connect()
    cards = await db.all_cards()
    await db.close()
    if not cards:
        print("Deck is empty — nothing to export.")
        return 1
    payload = [
        {k: c[k] for k in (
            "id", "year", "artist_latin", "title_latin",
            "artist_am", "title_am", "youtube_id", "deezer_track_id", "added_by",
        )}
        for c in cards
    ]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    playable = sum(1 for c in payload if c["deezer_track_id"] or c["youtube_id"])
    print(f"Exported {len(payload)} cards to {out} ({playable} playable).")
    return 0


async def cmd_seed(args: argparse.Namespace) -> int:
    """Load a resolved deck JSON into SQLite. Makes NO network calls.

    This is what deployment runs. It cannot half-succeed because of someone
    else's rate limit.
    """
    path = Path(args.file)
    if not path.exists():
        print(f"No such file: {path}")
        return 1
    cards = json.loads(path.read_text(encoding="utf-8"))
    unplayable = [c for c in cards if not c.get("deezer_track_id") and not c.get("youtube_id")]
    if unplayable:
        for c in unplayable:
            print(f"  ✗ no source: {c['artist_latin']} — {c['title_latin']}")
        print(f"Refusing to seed: {len(unplayable)} card(s) have no playable source.")
        return 1

    await db.connect()
    await db.upsert_cards(cards)
    total = await db.card_count()
    await db.close()
    print(f"Seeded {len(cards)} cards. Deck now holds {total}.")
    return 0


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

    p_pl = sub.add_parser(
        "playlist", help="turn a YouTube playlist into a worksheet to fill in"
    )
    p_pl.add_argument("url")
    p_pl.add_argument("--out", default="decks/from-playlist.tsv")
    p_pl.set_defaults(func=cmd_playlist)

    p_exp = sub.add_parser("export", help="write the resolved deck to JSON")
    p_exp.add_argument("--out", default="decks/deck.json")
    p_exp.set_defaults(func=cmd_export)

    p_seed = sub.add_parser("seed", help="load a resolved deck JSON — no network")
    p_seed.add_argument("file", nargs="?", default="decks/deck.json")
    p_seed.set_defaults(func=cmd_seed)

    sub.add_parser("list", help="show the current deck").set_defaults(func=cmd_list)
    sub.add_parser("check", help="re-probe every card's sources").set_defaults(
        func=cmd_check
    )

    args = parser.parse_args()
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
