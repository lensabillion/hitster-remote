"""Tests for player-typed artist matching.

Amharic names reach Latin script with no agreed spelling. A player who knows
perfectly well that Tilahun Gessesse sang a song should not lose 70 points for
writing "Telahun Gesesse", so this matcher is deliberately generous -- but not
so generous that any string matches any artist.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from matching import player_artist_matches, player_title_matches  # noqa: E402


class TestAcceptsWhatThePlayerMeant:
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


class TestRejectsWhatThePlayerDidNotMean:
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
