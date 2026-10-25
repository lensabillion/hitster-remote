"""Tests for the deck builder's offline logic: the seed-row parser and the
harvest's judgement about which Deezer release dates to believe.

No network here. The harvest's one job that can go quietly wrong is proposing
a reissue date as a song's year -- an Ethiopiques volume from 2004 for a song
recorded in 1975 -- so these pin down which dates are trusted, which are
flagged, and how versions of one song collapse onto one card.
"""

from __future__ import annotations

from tools.build_deck import (
    guess_artist_title,
    is_alternate_version,
    propose_year,
    song_key,
    split_row,
)


class TestSplitRow:
    def test_a_hash_column_ends_the_row(self):
        assert split_row("1975\tMahmoud Ahmed\tTezeta\t\t\t\t224830\t# medium · x") == [
            "1975", "Mahmoud Ahmed", "Tezeta", "", "", "", "224830",
        ]

    def test_columns_are_stripped(self):
        assert split_row(" 1991 \t Aster Aweke \t Kabu ") == ["1991", "Aster Aweke", "Kabu"]


class TestSongKey:
    def test_versions_of_one_song_share_a_key(self):
        assert song_key("Tezeta (Nostalgia)") == song_key("Tezeta")
        assert song_key("Erè mèla mèla") == song_key("Ere Mela Mela")
        assert song_key("Kabu [Live]") == song_key("Kabu")

    def test_different_songs_do_not(self):
        assert song_key("Gela Gela") != song_key("Demam Gelayewa")


class TestAlternateVersion:
    def test_live_and_remix_takes_are_alternates(self):
        assert is_alternate_version("Kabu (Live)")
        assert is_alternate_version("Korkuma Africa (Reggae Mix)")
        assert is_alternate_version("Wedding Song - Remix")

    def test_an_ordinary_subtitle_is_not(self):
        assert not is_alternate_version("Tezeta (Nostalgia)")
        assert not is_alternate_version("Das Tal (Ansaw)")


def release(id_: int, title: str, date: str, kind: str = "album") -> dict:
    return {"id": id_, "title": title, "release_date": date, "record_type": kind}


def version(album_id: int, rank: int = 0) -> dict:
    return {"id": album_id * 10, "title": "Song", "rank": rank, "album": {"id": album_id}}


class TestProposeYear:
    def test_an_ordinary_release_is_a_medium_proposal(self):
        releases = {1: release(1, "Kabu", "1991-01-01")}
        assert propose_year([version(1)], releases, set()) == (1991, "medium", "Kabu · release")

    def test_the_earliest_ordinary_release_wins(self):
        releases = {
            1: release(1, "Aster's Ballads", "2004-01-01"),
            2: release(2, "Aster", "1989-01-01"),
        }
        year, confidence, _ = propose_year([version(1), version(2)], releases, set())
        assert (year, confidence) == (1989, "medium")

    def test_a_compilation_date_is_flagged_low_not_believed(self):
        # The whole reason the deck is curated by hand: Deezer dates Mahmoud
        # Ahmed's 1975 recording to the 2004 Ethiopiques reissue.
        releases = {7: release(7, "Ethiopiques, Vol. 7: Erè mèla mèla 1975-1978", "2004-07-04")}
        year, confidence, evidence = propose_year([version(7)], releases, set())
        # The title carries the recording years, and those beat the reissue
        # date -- but a span only brackets the song, so it is not "high".
        assert (year, confidence) == (1975, "medium")
        assert "Ethiopiques" in evidence and "span" in evidence

    def test_a_retrospective_without_a_year_in_its_title_is_low(self):
        releases = {7: release(7, "Best of Mahmoud Ahmed", "2010-05-05")}
        assert propose_year([version(7)], releases, set())[1] == "low"
        releases = {8: release(8, "Singles", "2012-04-01", kind="compilation")}
        assert propose_year([version(8)], releases, set())[1] == "low"
        # A live album is dated by the concert, not the song.
        releases = {9: release(9, "Live In Paris", "1997-01-01")}
        assert propose_year([version(9)], releases, set())[1] == "low"

    def test_a_bulk_upload_date_is_low(self):
        # Four of Aster Aweke's old albums all "released" 2017-06-30: the day
        # they were uploaded, not the year of any of them.
        releases = {3: release(3, "Chereka", "2017-06-30")}
        year, confidence, evidence = propose_year([version(3)], releases, {"2017-06-30"})
        assert (year, confidence) == (2017, "low")
        assert "bulk" in evidence

    def test_a_year_in_the_release_title_is_high(self):
        releases = {4: release(4, "Hagerae 1983", "2017-06-30")}
        assert propose_year([version(4)], releases, {"2017-06-30"}) == (
            1983, "high", "Hagerae 1983 · title",
        )

    def test_an_ordinary_release_beats_a_compilation_even_when_later(self):
        releases = {
            1: release(1, "Greatest Hits", "1999-01-01"),
            2: release(2, "Sugar", "2001-01-01"),
        }
        assert propose_year([version(1), version(2)], releases, set())[0] == 2001

    def test_no_dated_release_is_no_proposal(self):
        assert propose_year([version(1)], {}, set()) == (None, "none", "no dated release")


class TestGuessArtistTitle:
    def test_plain_dash_form(self):
        assert guess_artist_title("Teddy Afro - Lambadina [Official Video]") == (
            "Teddy Afro", "Lambadina",
        )

    def test_by_form(self):
        assert guess_artist_title("Hab Dahlak By Teddy Afro") == ("Teddy Afro", "Hab Dahlak")

    def test_never_invents_an_artist(self):
        assert guess_artist_title("Yebichaye") == ("", "Yebichaye")
