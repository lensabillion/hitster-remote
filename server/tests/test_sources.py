"""Tests for source helpers.

The artist matcher is the important one. A wrong Deezer id does not fail loudly
-- it silently plays a completely different song mid-game, which is worse than
having no Deezer id at all.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import (  # noqa: E402
    artist_matches,
    extract_youtube_id,
    normalize,
    strip_youtube_decorations,
)


class TestExtractYoutubeId:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://www.youtube.com/watch?v=ADc9JPeLYi4", "ADc9JPeLYi4"),
            ("https://youtu.be/ADc9JPeLYi4?t=30", "ADc9JPeLYi4"),
            ("https://www.youtube.com/shorts/ADc9JPeLYi4", "ADc9JPeLYi4"),
            ("https://www.youtube.com/embed/ADc9JPeLYi4", "ADc9JPeLYi4"),
            ("ADc9JPeLYi4", "ADc9JPeLYi4"),
            ("https://example.com/not-youtube", None),
            ("", None),
        ],
    )
    def test_extraction(self, url, expected):
        assert extract_youtube_id(url) == expected


class TestNormalize:
    def test_strips_accents_from_transliterations(self):
        assert normalize("Erè mèla mèla") == normalize("Ere mela mela")

    def test_casefolds_and_drops_punctuation(self):
        assert normalize("Aster  AWEKE!") == "aster aweke"

    def test_leaves_ethiopic_script_intact(self):
        assert normalize("ቴዲ አፍሮ") == "ቴዲ አፍሮ"


class TestStripYoutubeDecorations:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            (
                "Teddy Afro - Tikur Sew (Official Video) | Ethiopian Music 2012",
                "Teddy Afro - Tikur Sew",
            ),
            ("Aster Aweke - Bayne Mulu [HD]", "Aster Aweke - Bayne Mulu"),
            ("Mahmoud Ahmed - Tezeta", "Mahmoud Ahmed - Tezeta"),
        ],
    )
    def test_stripping(self, raw, expected):
        assert strip_youtube_decorations(raw) == expected


class TestArtistMatches:
    """The bands overlap on a whole-string ratio, so these are regression tests.

    "Teddy Afro" vs "Teddy Karo" scores 0.90 overall and "Mulatu Astatke" vs
    "Mulatu Astatqe" scores 0.93 -- a single threshold cannot separate a wrong
    artist from a transliteration variant. Word-level comparison can.
    """

    @pytest.mark.parametrize(
        "wanted,found",
        [
            ("Teddy Afro", "Teddy Karo"),      # real Deezer result, different artist
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
            ("Yehune Belay", "Yehunie Belay"),      # spelling variant
            ("Mulatu Astatke", "Mulatu Astatqe"),   # transliteration variant
            ("aster aweke", "Aster Aweke"),         # case only
        ],
    )
    def test_accepts_the_same_artist(self, wanted, found):
        assert artist_matches(wanted, found)

    def test_empty_input_never_matches(self):
        assert not artist_matches("", "Aster Aweke")
        assert not artist_matches("Aster Aweke", "")
