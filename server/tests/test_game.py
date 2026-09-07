"""Tests for the placement validator and round resolution.

The validator is the correctness core of the game: if it is wrong, players lose
cards they earned and keep cards they did not.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import (  # noqa: E402
    Card,
    Placement,
    correct_gaps,
    insert_card,
    is_correct_placement,
    resolve_round,
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
    def setup_method(self):
        self.subject = card(1985, "subject")
        # Both players hold the same two-card timeline, so gap 1 is correct.
        self.timelines = {
            "a": [card(1970), card(1990)],
            "b": [card(1970), card(1990)],
            "c": [card(1970), card(1990)],
        }

    def test_active_correct_keeps_the_card_and_nobody_steals(self):
        out = resolve_round(
            "a",
            self.timelines,
            {"a": Placement("a", 1), "b": Placement("b", 0)},
            self.subject,
        )
        assert out.active_correct
        assert out.card_winner == "a"
        assert not out.stolen
        assert "b" not in out.token_awards

    def test_shadow_guess_earns_a_token_even_when_active_is_right(self):
        out = resolve_round(
            "a",
            self.timelines,
            {"a": Placement("a", 1), "b": Placement("b", 1)},
            self.subject,
        )
        assert out.card_winner == "a"
        assert out.token_awards == {"b": 1}

    def test_active_wrong_and_one_correct_shadow_steals_it(self):
        out = resolve_round(
            "a",
            self.timelines,
            {"a": Placement("a", 0), "b": Placement("b", 1)},
            self.subject,
        )
        assert not out.active_correct
        assert out.card_winner == "b"
        assert out.stolen

    def test_earliest_sealed_submission_wins_between_two_stealers(self):
        out = resolve_round(
            "a",
            self.timelines,
            {
                "a": Placement("a", 0),
                "b": Placement("b", 1, submitted_ms=500),
                "c": Placement("c", 1, submitted_ms=200),
            },
            self.subject,
        )
        assert out.card_winner == "c"
        assert out.stolen
        # Both were right, so both are paid.
        assert out.token_awards == {"b": 1, "c": 1}

    def test_nobody_correct_means_the_card_goes_nowhere(self):
        out = resolve_round(
            "a",
            self.timelines,
            {"a": Placement("a", 0), "b": Placement("b", 2)},
            self.subject,
        )
        assert out.card_winner is None
        assert not out.stolen
        assert out.token_awards == {}

    def test_active_player_never_pays_itself_a_shadow_token(self):
        out = resolve_round(
            "a", self.timelines, {"a": Placement("a", 1)}, self.subject
        )
        assert out.token_awards == {}

    def test_missing_active_placement_counts_as_wrong(self):
        out = resolve_round(
            "a", self.timelines, {"b": Placement("b", 1)}, self.subject
        )
        assert not out.active_correct
        assert out.card_winner == "b"

    def test_shadow_guess_is_judged_against_the_guessers_own_timeline(self):
        # c holds a different timeline, so gap 1 is wrong for c but right for b.
        self.timelines["c"] = [card(1990), card(1995)]
        out = resolve_round(
            "a",
            self.timelines,
            {"a": Placement("a", 0), "b": Placement("b", 1), "c": Placement("c", 1)},
            self.subject,
        )
        assert out.token_awards == {"b": 1}
        assert out.card_winner == "b"
