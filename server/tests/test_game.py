"""Tests for the placement validator and round resolution.

The validator is the correctness core of the game: if it is wrong, players lose
cards they earned and keep cards they did not.
"""

from __future__ import annotations

import random

from game import (
    ARTIST_POINTS,
    YEAR_POINTS,
    Answer,
    Card,
    correct_gaps,
    deal_across_eras,
    era_of,
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


class TestDealAcrossEras:
    """A game should range across the decades, however lopsided the deck."""

    def test_era_of_splits_at_1980_and_then_by_decade(self):
        years = (1966, 1979, 1980, 1995, 2000, 2010, 2026)
        assert [era_of(y) for y in years] == [0, 0, 1, 2, 3, 4, 5]

    def test_every_card_is_dealt_exactly_once(self):
        deck = [card(1960 + i, f"c{i}") for i in range(70)]
        dealt = deal_across_eras(deck, random.Random(3))
        assert sorted(c.id for c in dealt) == sorted(c.id for c in deck)

    def test_consecutive_cards_rotate_through_the_eras(self):
        decades = (1970, 1980, 1990, 2000, 2010, 2020)
        deck = [card(y + i, f"{y}-{i}") for y in decades for i in range(4)]
        for seed in range(20):
            dealt = deal_across_eras(deck, random.Random(seed))
            for start in range(0, 24, 6):
                window = dealt[start : start + 6]
                assert sorted(era_of(c.year) for c in window) == [0, 1, 2, 3, 4, 5]

    def test_a_thin_era_is_dealt_as_often_as_a_thick_one_while_it_lasts(self):
        deck = [card(2015, f"t{i}") for i in range(50)] + [card(1985, "eighties")]
        dealt = deal_across_eras(deck, random.Random(1))
        assert "eighties" in [c.id for c in dealt[:2]]
        assert len(dealt) == 51

    def test_no_era_always_opens_the_game(self):
        deck = [card(y, str(y)) for y in (1975, 1985, 1995, 2005, 2015, 2025)]
        openers = {deal_across_eras(deck, random.Random(seed))[0].year for seed in range(40)}
        assert len(openers) > 1
