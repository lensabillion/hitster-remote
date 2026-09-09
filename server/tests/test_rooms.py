"""Tests for live room state.

Two properties matter most here and neither fails loudly in manual play:

1. An unrevealed card must never reach any client. A leak is invisible during a
   game and silently decides who wins.
2. A dropped socket must never cost a seat, a timeline, or a score. This is the
   connection the game is designed for.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import Card, Phase  # noqa: E402
from rooms import Room, create_room, get_room, rooms, serialize  # noqa: E402


def card(year: int, name: str = "c") -> Card:
    return Card(
        id=f"{name}{year}",
        year=year,
        artist_latin=f"Singer{name.upper()}",
        title_latin=f"Song{name.upper()}",
        artist_am="አርቲስት",
        title_am="ርዕስ",
    )


def make_room(n: int = 3) -> Room:
    rooms.clear()
    room = create_room("p0")
    for i in range(n):
        room.add_player(f"p{i}", f"Player {i}", f"sid{i}")
    return room


def deck(n: int = 12) -> list[Card]:
    return [card(1960 + i * 3, f"c{i}") for i in range(n)]


class TestSeating:
    def test_creator_is_host_and_first_seat(self):
        room = make_room(3)
        assert room.host_id == "p0"
        assert room.seats == ["p0", "p1", "p2"]
        assert room.active_player_id == "p0"

    def test_rejoining_rebinds_the_socket_without_taking_a_new_seat(self):
        room = make_room(2)
        room.players["p1"].timeline = [card(1970)]
        room.players["p1"].score = 140

        room.detach_socket("sid1")
        assert not room.players["p1"].connected
        assert room.seats == ["p0", "p1"]

        room.add_player("p1", "Player 1", "sid1-new")
        assert room.players["p1"].connected
        assert len(room.players["p1"].timeline) == 1
        assert room.players["p1"].score == 140
        assert room.seats == ["p0", "p1"]

    def test_host_migrates_when_the_host_drops(self):
        room = make_room(3)
        room.detach_socket("sid0")
        room.promote_host_if_needed()
        assert room.host_id == "p1"

    def test_host_does_not_migrate_while_still_connected(self):
        room = make_room(3)
        room.promote_host_if_needed()
        assert room.host_id == "p0"

    def test_turn_order_skips_disconnected_players(self):
        room = make_room(3)
        room.detach_socket("sid1")
        room.advance_seat()
        assert room.active_player_id == "p2"


class TestRoundFlow:
    def test_start_game_seeds_one_card_each_and_zeroes_scores(self):
        room = make_room(3)
        room.start_game(deck())
        assert room.phase is Phase.ANSWERING
        for player in room.players.values():
            assert len(player.timeline) == 1
            assert player.score == 0

    def test_answering_is_open_from_the_start_of_the_round(self):
        """No listen-then-place gate: a player who knows it can answer at once."""
        room = make_room(2)
        room.start_game(deck())
        room.begin_round()
        assert room.phase is Phase.ANSWERING
        assert room.submit_answer("p0", 0, "Someone", "")

    def test_answers_are_one_per_player_and_final(self):
        room = make_room(2)
        room.start_game(deck())
        room.begin_round()
        assert room.submit_answer("p0", 1, "First", "")
        assert not room.submit_answer("p0", 0, "Second", "")
        assert room.answers["p0"].gap == 1
        assert room.answers["p0"].artist_guess == "First"

    def test_answers_are_refused_outside_the_answering_phase(self):
        room = make_room(2)
        room.start_game(deck())
        room.begin_round()
        room.submit_answer("p0", 0, "", "")
        room.reveal()
        assert room.phase is Phase.REVEALING
        assert not room.submit_answer("p0", 0, "", "")

    def test_only_the_active_player_may_answer(self):
        """One song, one answer. Everyone else listens and waits their turn."""
        room = make_room(3)
        room.start_game(deck())
        room.begin_round()
        assert room.active_player_id == "p0"

        assert not room.submit_answer("p1", 0, "Someone", "")
        assert not room.submit_answer("p2", 0, "Someone", "")
        assert not room.active_answered()

        assert room.submit_answer("p0", 0, "Someone", "")
        assert room.active_answered()

    def test_the_turn_passes_to_the_next_player(self):
        room = make_room(3)
        room.start_game(deck())
        room.begin_round()
        assert room.active_player_id == "p0"
        room.advance_seat()
        room.begin_round()
        assert room.active_player_id == "p1"
        assert room.submit_answer("p1", 0, "Someone", "")
        assert not room.submit_answer("p0", 0, "Someone", "")

    def test_everyone_gets_the_same_number_of_turns(self):
        room = make_room(3)
        room.start_game(deck(20), rounds=10)
        # 10 wanted over 3 players would give someone an extra song.
        assert room.rounds_planned % 3 == 0
        assert room.rounds_planned == 9

    def test_reveal_scores_only_the_player_whose_turn_it_is(self):
        room = make_room(2)
        room.start_game(deck())
        subject = room.begin_round()
        room.submit_answer("p0", 0, subject.artist_latin, "")
        room.reveal()
        assert room.players["p0"].score >= 70  # artist alone is worth 70
        assert room.players["p1"].score == 0  # not their turn

    def test_standings_rank_by_score(self):
        room = make_room(3)
        room.players["p0"].score = 100
        room.players["p1"].score = 250
        room.players["p2"].score = 40
        assert [p.id for p in room.standings()] == ["p1", "p0", "p2"]
        assert room.leader().id == "p1"

    def test_game_ends_after_the_planned_rounds(self):
        room = make_room(2)
        room.start_game(deck(), rounds=2)
        assert room.begin_round() is not None
        assert room.begin_round() is not None
        assert room.is_last_round()
        assert room.begin_round() is None
        assert room.phase is Phase.OVER


class TestSerializeWithholdsTheAnswer:
    def setup_method(self):
        self.room = make_room(2)
        self.room.start_game(deck())
        self.subject = self.room.begin_round()

    def test_the_unrevealed_card_appears_nowhere_in_the_payload(self):
        blob = json.dumps(serialize(self.room, "p0"), ensure_ascii=False)
        state = serialize(self.room, "p0")
        assert state["card"] is None
        assert state["outcome"] is None
        assert self.subject.id not in blob
        assert self.subject.title_latin not in blob
        assert self.subject.artist_latin not in blob

    def test_card_is_disclosed_only_once_revealing(self):
        self.room.submit_answer("p0", 0, "", "")
        self.room.reveal()
        state = serialize(self.room, "p0")
        assert state["card"]["year"] == self.subject.year

    def test_the_answer_stays_hidden_from_the_watchers_until_the_reveal(self):
        self.room.submit_answer("p0", 2, "Aster Aweke", "Y'shebellu")
        blob = json.dumps(serialize(self.room, "p1"), ensure_ascii=False)
        assert serialize(self.room, "p1")["outcome"] is None
        assert "Aster Aweke" not in blob, "the answerer's guess leaked to a watcher"
        assert "Y'shebellu" not in blob

    def test_each_viewer_knows_only_whether_it_is_their_own_turn(self):
        assert serialize(self.room, "p0")["isMyTurn"] is True
        assert serialize(self.room, "p1")["isMyTurn"] is False

    def test_viewer_sees_only_its_own_answer_back(self):
        self.room.submit_answer("p0", 2, "Aster Aweke", "")
        assert serialize(self.room, "p0")["hasAnswered"] is True
        assert serialize(self.room, "p0")["myAnswer"]["artistGuess"] == "Aster Aweke"
        assert serialize(self.room, "p1")["hasAnswered"] is False
        assert serialize(self.room, "p1")["myAnswer"] is None

    def test_the_answer_is_disclosed_to_everyone_at_the_reveal(self):
        self.room.submit_answer("p0", 0, "Aster Aweke", "")
        self.room.reveal()
        outcome = serialize(self.room, "p1")["outcome"]
        assert outcome["playerId"] == "p0"
        assert outcome["artistGuess"] == "Aster Aweke"


class TestRoomRegistry:
    def test_lookup_is_case_insensitive_and_trimmed(self):
        room = make_room(1)
        assert get_room(room.code.lower()) is room
        assert get_room(f"  {room.code}  ") is room
        assert get_room("ZZZZ") is None
        assert get_room("") is None


class TestDeclinedAnswer:
    """"I don't know" is a real move: zero score, no card, turn ends at once."""

    def setup_method(self):
        self.room = make_room(2)
        self.room.start_game(deck())
        self.subject = self.room.begin_round()

    def test_declining_needs_no_placement_and_scores_nothing(self):
        assert self.room.submit_answer("p0", 0, "", "", declined=True)
        self.room.reveal()
        assert self.room.players["p0"].score == 0
        assert len(self.room.players["p0"].timeline) == 1  # no card gained

    def test_declining_ends_the_turn_immediately(self):
        self.room.submit_answer("p0", 0, "", "", declined=True)
        assert self.room.active_answered()

    def test_a_declined_answer_never_scores_even_by_accident(self):
        # Gap 0 might well be the correct placement; declining must still be 0.
        self.room.submit_answer("p0", 0, self.subject.artist_latin, "", declined=True)
        out = self.room.reveal()
        assert out.points == 0
        assert not out.score.artist_right
        assert not out.score.year_right
        assert not out.keeps_card

    def test_the_reveal_says_it_was_declined(self):
        self.room.submit_answer("p0", 0, "", "", declined=True)
        self.room.reveal()
        assert serialize(self.room, "p1")["outcome"]["declined"] is True


class TestTitleHitsBreakTies:
    """Titles score nothing but settle a draw."""

    def test_a_title_hit_is_tallied(self):
        room = make_room(2)
        room.start_game(deck())
        subject = room.begin_round()
        room.submit_answer("p0", 0, "", subject.title_latin)
        room.reveal()
        assert room.players["p0"].title_hits == 1

    def test_declining_never_earns_a_title_hit(self):
        room = make_room(2)
        room.start_game(deck())
        subject = room.begin_round()
        room.submit_answer("p0", 0, "", subject.title_latin, declined=True)
        room.reveal()
        assert room.players["p0"].title_hits == 0

    def test_equal_scores_are_broken_by_title_hits(self):
        room = make_room(3)
        for p in room.players.values():
            p.score = 100
        room.players["p1"].title_hits = 3
        room.players["p2"].title_hits = 1
        assert [p.id for p in room.standings()][:2] == ["p1", "p2"]
        assert room.leader().id == "p1"

    def test_title_hits_never_outrank_score(self):
        room = make_room(2)
        room.players["p0"].score = 200
        room.players["p0"].title_hits = 0
        room.players["p1"].score = 100
        room.players["p1"].title_hits = 9
        assert room.leader().id == "p0"

    def test_title_hits_are_exposed_to_clients(self):
        room = make_room(2)
        room.players["p0"].title_hits = 2
        state = serialize(room, "p0")
        assert state["standings"][0]["titleHits"] == 2
