"""Tests for the placement validator and round resolution.

The validator is the correctness core of the game: if it is wrong, players lose
cards they earned and keep cards they did not.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import (  # noqa: E402
    ARTIST_POINTS,
    YEAR_POINTS,
    Answer,
    Card,
    correct_gaps,
    insert_card,
    is_correct_placement,
    resolve_round,
    score_answer,
)


def card(year: int, name: str = "x") -> Card:
    return Card(id=name, year=year, artist_latin=name, title_latin=name)


class TestEmptyAndSingle:
    def test_any_gap_on_empty_timeline_is_correct(self):
        assert is_correct_placement([], card(1975), 0)

    def test_out_of_range_gap_is_rejected(self):
        assert not is_correct_placement([], card(1975), 1)
        assert not is_correct_placement([], card(1975), -1)

    def test_before_and_after_a_single_card(self):
        tl = [card(1980)]
        assert is_correct_placement(tl, card(1975), 0)
        assert not is_correct_placement(tl, card(1975), 1)
        assert is_correct_placement(tl, card(1985), 1)
        assert not is_correct_placement(tl, card(1985), 0)


class TestSameYearRule:
    """Official rule: a matching year may sit on either side of that card."""

    def test_both_sides_of_a_matching_card_count(self):
        tl = [card(1980)]
        assert is_correct_placement(tl, card(1980), 0)
        assert is_correct_placement(tl, card(1980), 1)
        assert correct_gaps(tl, card(1980)) == [0, 1]

    def test_tie_in_the_middle_of_a_longer_timeline(self):
        tl = [card(1970), card(1980), card(1990)]
        assert correct_gaps(tl, card(1980)) == [1, 2]

    def test_tie_at_the_left_edge(self):
        tl = [card(1970), card(1990)]
        assert correct_gaps(tl, card(1970)) == [0, 1]

    def test_tie_at_the_right_edge(self):
        tl = [card(1970), card(1990)]
        assert correct_gaps(tl, card(1990)) == [1, 2]

    def test_run_of_identical_years_admits_every_gap_in_the_run(self):
        tl = [card(1980), card(1980)]
        assert correct_gaps(tl, card(1980)) == [0, 1, 2]


class TestOrdinaryPlacement:
    def test_unique_year_has_exactly_one_correct_gap(self):
        tl = [card(1960), card(1975), card(1990)]
        assert correct_gaps(tl, card(1980)) == [2]

    def test_earlier_than_everything(self):
        tl = [card(1960), card(1975)]
        assert correct_gaps(tl, card(1950)) == [0]

    def test_later_than_everything(self):
        tl = [card(1960), card(1975)]
        assert correct_gaps(tl, card(1999)) == [2]

    def test_insert_keeps_the_timeline_ordered(self):
        tl = [card(1960), card(1990)]
        out = insert_card(tl, card(1975), 1)
        assert [c.year for c in out] == [1960, 1975, 1990]


class TestResolveRound:
    """One song, one answer.

    Only the player whose turn it is answers the card. Everyone else hears the
    clip and gets their own song on their own turn.
    """

    def setup_method(self):
        self.subject = card(1985, "subject")
        self.timelines = {
            "a": [card(1970), card(1990)],  # gap 1 is correct
            "b": [card(1970), card(1990)],
        }

    def test_correct_placement_keeps_the_card(self):
        out = resolve_round("a", self.timelines, {"a": Answer("a", 1)}, self.subject)
        assert out.active_player_id == "a"
        assert out.score.year_right
        assert out.keeps_card

    def test_wrong_placement_loses_the_card(self):
        out = resolve_round("a", self.timelines, {"a": Answer("a", 0)}, self.subject)
        assert not out.score.year_right
        assert not out.keeps_card

    def test_only_the_active_players_answer_is_graded(self):
        # b answered too -- an out-of-turn submission the server should never
        # have accepted. Even if it arrives, it must not be scored.
        out = resolve_round(
            "a", self.timelines, {"a": Answer("a", 0), "b": Answer("b", 1)}, self.subject
        )
        assert out.active_player_id == "a"
        assert not out.keeps_card
        assert out.points == 0

    def test_no_answer_scores_nothing_and_keeps_nothing(self):
        out = resolve_round("a", self.timelines, {}, self.subject)
        assert out.score is None
        assert out.points == 0
        assert not out.keeps_card

    def test_artist_alone_scores_seventy(self):
        out = resolve_round(
            "a",
            self.timelines,
            {"a": Answer("a", 0, artist_guess="subject")},
            self.subject,
        )
        assert out.score.artist_right
        assert not out.score.year_right
        assert out.points == ARTIST_POINTS

    def test_year_alone_scores_thirty(self):
        out = resolve_round(
            "a",
            self.timelines,
            {"a": Answer("a", 1, artist_guess="somebody else entirely")},
            self.subject,
        )
        assert not out.score.artist_right
        assert out.score.year_right
        assert out.points == YEAR_POINTS

    def test_both_right_scores_the_full_hundred(self):
        out = resolve_round(
            "a",
            self.timelines,
            {"a": Answer("a", 1, artist_guess="subject")},
            self.subject,
        )
        assert out.points == ARTIST_POINTS + YEAR_POINTS


class TestScoreAnswer:
    def test_title_is_captured_but_never_scored(self):
        subject = Card(
            id="s", year=1975, artist_latin="Mahmoud Ahmed", title_latin="Tezeta"
        )
        score = score_answer(
            Answer("a", 0, artist_guess="wrong", title_guess="Tezeta"), subject, []
        )
        assert score.title_right
        assert score.points == YEAR_POINTS  # empty timeline, so the gap is right
