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
    python tools/build_deck.py playlist <url>       # YouTube playlist -> worksheet
    python tools/build_deck.py harvest <artists>    # Deezer catalogue -> worksheet
    python tools/build_deck.py list
    python tools/build_deck.py check                # re-probe sources
    python tools/build_deck.py export               # -> decks/deck.json
    python tools/build_deck.py seed                 # load decks/deck.json, no network

Seed file is tab-separated, '#' comments allowed (a '#' column ends the row):

    year <TAB> artist_latin <TAB> title_latin [<TAB> artist_am <TAB> title_am
         <TAB> youtube_url <TAB> deezer_track_id]

When a Deezer track id is given it is taken as is -- the harvest already
verified it -- so importing a worksheet makes no network calls. Otherwise the
song is looked up on Deezer. A card with neither a Deezer match nor a YouTube
URL is rejected, because it would be unplayable.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

# Runs as a script from server/, so the server modules are one directory up.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import db
from deck import (
    EARLIEST_YEAR,
    LATEST_YEAR,
    card_id,
    export_rows,
    export_text,
    is_playable,
    load_deck_file,
)
from matching import normalize, title_matches
from sources import (
    deezer_album,
    deezer_artist_albums,
    deezer_artist_tracks,
    deezer_probe,
    extract_youtube_id,
)


def valid_year(value: str) -> int | None:
    try:
        year = int(value)
    except (ValueError, TypeError):
        return None
    return year if EARLIEST_YEAR <= year <= LATEST_YEAR else None


async def build_card(
    year: int,
    artist_latin: str,
    title_latin: str,
    artist_am: str = "",
    title_am: str = "",
    youtube_url: str = "",
    added_by: str = "",
    deezer_track_id: int | None = None,
    year_confirmed: bool = False,
) -> dict | None:
    if not artist_latin or not title_latin:
        print("  ✗ needs both an artist and a title (in Latin script)")
        return None

    deezer_id = deezer_track_id or await deezer_probe(artist_latin, title_latin)
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
        "year_confirmed": year_confirmed,
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
    check = "" if card.get("year_confirmed") else "  (year unconfirmed)"
    return f"  ✓ {card['year']}  {artist} — {title}  [{'+'.join(sources)}]{who}{check}"


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
                    print(f"  needs a year between {EARLIEST_YEAR} and {LATEST_YEAR}")

            card = await build_card(
                year, artist, title, artist_am, title_am, added_by=args.by,
                year_confirmed=True,
            )
            if card is None:
                url = input("  YouTube URL for this song (blank to skip): ").strip()
                if url:
                    card = await build_card(
                        year, artist, title, artist_am, title_am, url, args.by,
                        year_confirmed=True,
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
        parts = split_row(line)
        if len(parts) < 3:
            print(f"  ✗ line {lineno}: need at least year, artist and title")
            failures += 1
            continue

        year = valid_year(parts[0])
        if year is None:
            print(f"  ✗ line {lineno}: bad year {parts[0]!r}")
            failures += 1
            continue

        parts += [""] * (7 - len(parts))
        card = await build_card(
            year, parts[1], parts[2], parts[3], parts[4], parts[5], args.by,
            deezer_track_id=int(parts[6]) if parts[6].isdigit() else None,
            year_confirmed=args.confirmed,
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
            "# year <TAB> artist_latin <TAB> title_latin <TAB> artist_am <TAB> title_am"
            " <TAB> youtube_url\n"
        )
        for artist, title, _deezer_id, vid, note in rows:
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



def split_row(line: str) -> list[str]:
    """A seed row's columns. A column starting with '#' is a comment and ends
    the row -- the worksheets put their notes there."""
    parts = []
    for part in line.split("\t"):
        part = part.strip()
        if part.startswith("#"):
            break
        parts.append(part)
    return parts


# ---------- harvest ----------
#
# An artist's Deezer catalogue, narrowed to the songs worth a card, with a
# PROPOSED year and a note on how far to trust it. Deezer's only year evidence
# is the date of the release a track sits on, and for the golden era that is an
# Ethiopiques reissue or a bulk upload decades after the song. So each
# proposal says where it came from, and nothing is written to the deck until a
# person has been through the worksheet.

# A release whose title says it is a retrospective: its date is not the song's.
COMPILATION_RE = re.compile(
    r"(?i)\b(ethiopiques|best of|greatest|hits|collection|anthology|ballads|"
    r"compilation|selection|vol\.?\s?\d+|volume|remaster(ed)?|tribute|classics|"
    r"singles?|retrospective|essential|golden|treasures|live|in concert|unplugged)\b"
)
# A take that is not the song as released: skipped when an original exists.
VERSION_RE = re.compile(
    r"(?i)\b(live|remix|version|edit|instrumental|acoustic|karaoke|cover|"
    r"slowed|sped up|dub|mix)\b"
)
# "Hagerae 1983": a release that carries its own year in the title.
YEAR_IN_TITLE_RE = re.compile(r"\b(19[2-9]\d|20[0-4]\d)\b")
# "Golden Years 1969-1975": a span, which only brackets the song's year.
YEAR_RANGE_RE = re.compile(r"\b(19[2-9]\d|20[0-4]\d)\s*[-–]\s*(19[2-9]\d|20[0-4]\d)\b")
# Three or more releases sharing one exact date were uploaded together; the
# date is the upload, not any of the records.
BULK_UPLOAD_MIN = 3

# How far to trust a proposal, best first, and the one-word label it gets.
TRUST_ORDER = ("title", "span", "release", "bulk", "compilation")
CONFIDENCE = {
    "title": "high", "span": "medium", "release": "medium", "bulk": "low", "compilation": "low",
}


def song_key(title: str) -> str:
    """One key per song, across its versions: brackets and noise stripped."""
    return normalize(re.sub(r"[\(\[][^()\[\]]*[\)\]]", " ", title))


def is_alternate_version(title: str) -> bool:
    inside = " ".join(re.findall(r"[\(\[]([^()\[\]]*)[\)\]]", title))
    return bool(VERSION_RE.search(inside) or VERSION_RE.search(title.split(" - ")[-1]))


def propose_year(
    versions: list[dict], releases: dict[int, dict], bulk_dates: set[str]
) -> tuple[int | None, str, str]:
    """(year, confidence, evidence) for one song, from the releases it sits on.

    A year named in a release title beats everything; the earliest ordinary
    release is the usual answer; a bulk-upload date or a compilation is a
    placeholder that a person has to replace.
    """
    dated: list[tuple[int, int, str]] = []
    for track in versions:
        release = releases.get(int(track["album"]["id"]))
        if not release:
            continue
        date = release.get("release_date") or ""
        if len(date) < 4 or not date[:4].isdigit():
            continue
        label = release.get("title", "")
        if m := YEAR_RANGE_RE.search(label):
            # The first year of the span: the song is somewhere inside it.
            dated.append((TRUST_ORDER.index("span"), int(m.group(1)), label))
            continue
        if m := YEAR_IN_TITLE_RE.search(label):
            dated.append((TRUST_ORDER.index("title"), int(m.group(1)), label))
            continue
        if release.get("record_type") == "compilation" or COMPILATION_RE.search(label):
            trust = "compilation"
        elif date in bulk_dates:
            trust = "bulk"
        else:
            trust = "release"
        dated.append((TRUST_ORDER.index(trust), int(date[:4]), label))
    if not dated:
        return None, "none", "no dated release"
    dated.sort()
    rank, year, label = dated[0]
    trust = TRUST_ORDER[rank]
    return year, CONFIDENCE[trust], f"{label} · {trust}"


def read_artists(args: argparse.Namespace) -> list[tuple[str, str]]:
    """(latin, amharic) pairs from the command line or a file of them."""
    pairs: list[tuple[str, str]] = []
    for item in args.artists:
        path = Path(item)
        if path.exists():
            for raw in path.read_text(encoding="utf-8").splitlines():
                parts = split_row(raw)
                if parts and parts[0]:
                    pairs.append((parts[0], parts[1] if len(parts) > 1 else ""))
        else:
            pairs.append((item, ""))
    return pairs


async def harvest_artist(
    latin: str, per_artist: int, known: list[dict], max_results: int
) -> list[dict]:
    """The songs worth a card for one artist, most popular first."""
    tracks = await deezer_artist_tracks(latin, max_results=max_results)
    if not tracks:
        return []

    # Everything the artist has released, by id, for dating. Tracks that sit on
    # releases outside the artist's own discography (a various-artists
    # compilation) are dated with one extra lookup each.
    artist_id = int(tracks[0]["artist"]["id"])
    releases = {int(a["id"]): a for a in await deezer_artist_albums(artist_id)}
    for track in tracks:
        album_id = int(track["album"]["id"])
        if album_id not in releases and (album := await deezer_album(album_id)):
            releases[album_id] = album
    date_counts: dict[str, int] = {}
    for release in releases.values():
        date = release.get("release_date") or ""
        date_counts[date] = date_counts.get(date, 0) + 1
    bulk_dates = {d for d, n in date_counts.items() if n >= BULK_UPLOAD_MIN and d}

    # One entry per song, originals before live takes and remixes.
    songs: dict[str, list[dict]] = {}
    for track in tracks:
        songs.setdefault(song_key(track["title"]), []).append(track)

    rows = []
    for versions in songs.values():
        originals = [t for t in versions if not is_alternate_version(t["title"])]
        pick_from = originals or versions
        best = max(pick_from, key=lambda t: t.get("rank", 0))
        title = best["title"]
        if any(title_matches(c["title_latin"], title) for c in known):
            continue  # already a card
        year, confidence, evidence = propose_year(pick_from, releases, bulk_dates)
        rows.append({
            "year": year, "confidence": confidence, "evidence": evidence,
            "title": title, "deezer_track_id": int(best["id"]),
            "rank": best.get("rank", 0), "versions": len(versions),
        })
    rows.sort(key=lambda r: r["rank"], reverse=True)
    return rows[:per_artist]


async def cmd_harvest(args: argparse.Namespace) -> int:
    """Turn artists into a worksheet of their most-played songs on Deezer.

    Like `playlist`, this writes NO cards. Every year here is a proposal with
    its evidence beside it; the confident ones still want a glance, the low
    ones want a person who knows the music. Fix the years, delete the songs
    nobody would recognise, then import the file.
    """
    artists = read_artists(args)
    if not artists:
        print("No artists given.")
        return 1

    await db.connect()
    deck = await db.all_cards()
    await db.close()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    total, by_confidence = 0, {"high": 0, "medium": 0, "low": 0, "none": 0}
    with out.open("w", encoding="utf-8") as fh:
        fh.write(
            "# Harvested from Deezer. Every YEAR here is a PROPOSAL -- the date of the\n"
            "# release Deezer has the song on -- with its evidence in the comment:\n"
            "#   high    the release names its own year in the title\n"
            "#   medium  an ordinary release, or a span of years the song falls in;\n"
            "#           right for digital-era songs, often a reissue for anything older\n"
            "#   low     a compilation or a bulk-upload date: NOT the song's year\n"
            "# Fix the years, delete songs nobody would recognise, then:\n"
            f"#     python tools/build_deck.py import {out}\n"
            "#\n"
            "# year <TAB> artist_latin <TAB> title_latin <TAB> artist_am <TAB> title_am"
            " <TAB> youtube_url <TAB> deezer_track_id <TAB> # confidence · evidence\n"
        )
        for latin, amharic in artists:
            known = [c for c in deck if normalize(c["artist_latin"]) == normalize(latin)]
            rows = await harvest_artist(latin, args.per_artist, known, args.max_results)
            print(f"{latin}: {len(rows)} songs" + ("" if rows else "  (nothing on Deezer)"))
            fh.write(f"\n# {latin}" + (f" · {amharic}" if amharic else "") + "\n")
            for r in rows:
                year = r["year"] if r["year"] is not None else "?"
                by_confidence[r["confidence"]] += 1
                total += 1
                fh.write(
                    f"{year}\t{latin}\t{r['title']}\t{amharic}\t\t\t{r['deezer_track_id']}"
                    f"\t# {r['confidence']} · {r['evidence']} · rank {r['rank']}\n"
                )
    print(f"\nWrote {out}: {total} songs from {len(artists)} artists.")
    print(
        f"  years: {by_confidence['high']} high · {by_confidence['medium']} medium"
        f" · {by_confidence['low']} low · {by_confidence['none']} undated"
    )
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
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Same function the /deck download uses, so the two are byte-identical.
    out.write_text(export_text(cards), encoding="utf-8")
    playable = sum(1 for c in export_rows(cards) if is_playable(c))
    print(f"Exported {len(cards)} cards to {out} ({playable} playable).")
    return 0


async def cmd_seed(args: argparse.Namespace) -> int:
    """Load a resolved deck JSON into SQLite. Makes NO network calls.

    This is what deployment runs. It cannot half-succeed because of someone
    else's rate limit.
    """
    cards = load_deck_file(Path(args.file))
    if cards is None:
        print(f"No such file: {args.file}")
        return 1
    unplayable = [c for c in cards if not is_playable(c)]
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
    unconfirmed = sum(1 for c in cards if not c["year_confirmed"])
    print(f"\nSpanning {cards[0]['year']}–{cards[-1]['year']}. {unconfirmed} years unconfirmed.")
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
    p_import.add_argument(
        "--confirmed", action="store_true",
        help="the years in this file have been checked by a person",
    )
    p_import.set_defaults(func=cmd_import)

    p_pl = sub.add_parser(
        "playlist", help="turn a YouTube playlist into a worksheet to fill in"
    )
    p_pl.add_argument("url")
    p_pl.add_argument("--out", default="decks/from-playlist.tsv")
    p_pl.set_defaults(func=cmd_playlist)

    p_hv = sub.add_parser(
        "harvest", help="turn artists' Deezer catalogues into a worksheet to fill in"
    )
    p_hv.add_argument("artists", nargs="+", help="artist names, or a file of them")
    p_hv.add_argument("--per-artist", type=int, default=10, help="songs per artist")
    p_hv.add_argument(
        "--max-results", type=int, default=300, help="how deep to page each artist"
    )
    p_hv.add_argument("--out", default="decks/harvest.tsv")
    p_hv.set_defaults(func=cmd_harvest)

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
