"""Tests for name matching -- both temperaments.

Catalogue matching must be strict: a wrong Deezer id silently plays a different
song. Player matching must be generous: Amharic names reach Latin script with no
agreed spelling, and a player who knows perfectly well that Tilahun Gessesse
sang a song should not lose 70 points for writing "Telahun Gesesse" -- but not
so generous that any string matches any artist.
"""

from __future__ import annotations

import pytest

from matching import (
    artist_matches,
    normalize,
    player_artist_matches,
    player_title_matches,
    title_matches,
)


class TestNormalize:
    def test_strips_accents_from_transliterations(self):
        assert normalize("Erè mèla mèla") == normalize("Ere mela mela")

    def test_casefolds_and_drops_punctuation(self):
        assert normalize("Aster  AWEKE!") == "aster aweke"

    def test_leaves_ethiopic_script_intact(self):
        assert normalize("ቴዲ አፍሮ") == "ቴዲ አፍሮ"


class TestCatalogueMatching:
    """The bands overlap on a whole-string ratio, so these are regression tests.

    "Teddy Afro" vs "Teddy Karo" scores 0.90 overall and "Mulatu Astatke" vs
    "Mulatu Astatqe" scores 0.93 -- a single threshold cannot separate a wrong
    artist from a transliteration variant. Word-level comparison can.
    """

    @pytest.mark.parametrize(
        "wanted,found",
        [
            ("Teddy Afro", "Teddy Karo"),  # real Deezer result, different artist
            ("Teddy Afro", "Teddy pro"),
            ("Teddy Afro", "Hewan Gebrewold"),  # what a loose search returns
            ("Gigi", "GIGI Rivera"),
            ("Aster Aweke", "Aster Aweke Band"),
            ("Betty G", "Betty Boo"),
        ],
    )
    def test_rejects_wrong_artists(self, wanted, found):
        assert not artist_matches(wanted, found)

    @pytest.mark.parametrize(
        "wanted,found",
        [
            ("Aster Aweke", "Aster Aweke"),
            ("Mahmoud Ahmed", "Mahmoud Ahmed"),
            ("Alemayehu Eshete", "Alemayehu Eshete"),
            ("Hailu Mergia", "Hailu Mergia"),
            ("Yehune Belay", "Yehunie Belay"),  # spelling variant
            ("Mulatu Astatke", "Mulatu Astatqe"),  # transliteration variant
            ("aster aweke", "Aster Aweke"),  # case only
        ],
    )
    def test_accepts_the_same_artist(self, wanted, found):
        assert artist_matches(wanted, found)

    def test_empty_input_never_matches(self):
        assert not artist_matches("", "Aster Aweke")
        assert not artist_matches("Aster Aweke", "")


class TestPlayerAcceptsWhatTheyMeant:
    @pytest.mark.parametrize(
        "guess",
        [
            "Tilahun Gessesse",
            "tilahun gessesse",
            "  Tilahun   Gessesse  ",
            "Telahun Gesesse",  # plausible transliteration
            "Tilahun",  # given name only
            "Gessesse",  # surname only
            "TILAHUN GESSESSE",
        ],
    )
    def test_tilahun(self, guess):
        assert player_artist_matches(guess, "Tilahun Gessesse")

    @pytest.mark.parametrize(
        "guess",
        ["Mulatu Astatke", "Mulatu Astatqe", "Astatke", "Mulatu", "mulatu astatke"],
    )
    def test_mulatu(self, guess):
        assert player_artist_matches(guess, "Mulatu Astatke")

    @pytest.mark.parametrize("guess", ["Teddy Afro", "teddy afro", "Tedy Afro", "Afro"])
    def test_teddy_afro(self, guess):
        assert player_artist_matches(guess, "Teddy Afro")

    def test_accents_are_ignored(self):
        assert player_artist_matches("Ere mela mela", "Erè mèla mèla")

    def test_punctuation_is_ignored(self):
        assert player_artist_matches("Aster-Aweke!", "Aster Aweke")


class TestPlayerRejectsWhatTheyDidNotMean:
    @pytest.mark.parametrize(
        "guess",
        [
            "",
            "   ",
            "Aster Aweke",  # a real but different artist
            "Mahmoud Ahmed",
            "Bob Marley",
            "x",
            "the",  # stopword alone
        ],
    )
    def test_rejects(self, guess):
        assert not player_artist_matches(guess, "Tilahun Gessesse")

    def test_short_fragments_do_not_match_everything(self):
        # Three letters is not evidence of knowing who sang it.
        assert not player_artist_matches("mul", "Mulatu Astatke")
        assert not player_artist_matches("as", "Aster Aweke")

    def test_a_stopword_shared_between_names_is_not_a_match(self):
        assert not player_artist_matches("The Band", "The Walias Band")

    def test_empty_answer_never_matches(self):
        assert not player_artist_matches("Anyone", "")


class TestTitleMatching:
    def test_accepts_the_same_title_however_spelled(self):
        assert player_title_matches("Tezeta", "Tezeta")
        assert player_title_matches("tezeta", "Tezeta")
        assert player_title_matches("Ere mela mela", "Erè mèla mèla")

    def test_rejects_a_different_title(self):
        assert not player_title_matches("Tezeta", "Muziqawi Silt")

    def test_blank_is_not_a_match(self):
        assert not player_title_matches("", "Tezeta")


class TestCatalogueTitleMatching:
    """Strict-ish: attaching a Deezer track automatically needs the title to
    agree too, since a plain search returns the artist's other songs as well."""

    @pytest.mark.parametrize(
        "wanted,found",
        [
            ("Ere Mela Mela", "Erè mèla mèla"),
            ("Tezeta", "Tezeta (Nostalgia)"),
            ("Yekermo Sew", "Yèkèrmo Sèw"),
            ("Tizita", "Tezeta"),
            ("Y'shebellu", "Yshebellu"),
            ("Darigne", "Darign (Bonus Track)"),
            ("Anarejim", "Anarejm"),
        ],
    )
    def test_accepts_spellings_and_subtitles(self, wanted, found):
        assert title_matches(wanted, found)

    @pytest.mark.parametrize(
        "wanted,found",
        [
            ("Gela Gela", "Demam Gelayewa"),
            ("Tikur Sew", "Abugida"),
            ("Endegena", "Endetefash"),
            ("Kabu", ""),
            ("", "Kabu"),
        ],
    )
    def test_rejects_a_different_song(self, wanted, found):
        assert not title_matches(wanted, found)
