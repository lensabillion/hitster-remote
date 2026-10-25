"""Tests for live room state.

Two properties matter most here and neither fails loudly in manual play:

1. An unrevealed card must never reach any client. A leak is invisible during a
   game and silently decides who wins.
2. A dropped socket must never cost a seat, a timeline, or a score. This is the
   connection the game is designed for.
"""

from __future__ import annotations

import json

import rooms as rooms_module
from game import ARTIST_POINTS, YEAR_POINTS, Card, Phase
from rooms import (
    EMPTY_ROOM_GRACE_MS,
    Room,
    create_room,
    drop_empty_rooms,
    get_room,
    rooms,
    serialize,
)


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
        assert room.players["p0"].score >= ARTIST_POINTS
        assert room.players["p1"].score == 0  # not their turn

    def test_standings_rank_by_score(self):
        room = make_room(3)
        room.players["p0"].score = 100
        room.players["p1"].score = 250
        room.players["p2"].score = 40
        assert [p.id for p in room.standings()] == ["p1", "p0", "p2"]

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

    def test_the_answer_is_disclosed_to_everyone_at_the_reveal(self):
        self.room.submit_answer("p0", 0, "Aster Aweke", "")
        self.room.reveal()
        outcome = serialize(self.room, "p1")["outcome"]
        assert outcome["playerId"] == "p0"
        assert outcome["artistGuess"] == "Aster Aweke"

    def test_the_rules_tell_the_client_what_each_half_is_worth(self):
        # The client renders these rather than hardcoding 70/30 a second time.
        state = serialize(self.room, "p0")
        assert (state["artistPoints"], state["yearPoints"]) == (ARTIST_POINTS, YEAR_POINTS)


class TestRoomRegistry:
    def test_lookup_is_case_insensitive_and_trimmed(self):
        room = make_room(1)
        assert get_room(room.code.lower()) is room
        assert get_room(f"  {room.code}  ") is room
        assert get_room("ZZZZ") is None
        assert get_room("") is None


class TestEmptyRoomsSurviveAGracePeriod:
    """A shared wifi blip must not destroy a live game.

    Deleting a room on its last disconnect looked correct and was not: two
    players on the same connection blink out together, and the game was gone
    before either could reconnect.
    """

    def _clock(self, monkeypatch, start: int = 1_000_000):
        now = {"ms": start}
        monkeypatch.setattr(rooms_module, "now_ms", lambda: now["ms"])
        return now

    def test_a_room_with_nobody_connected_survives_the_grace_period(self, monkeypatch):
        clock = self._clock(monkeypatch)
        room = make_room(2)
        room.players["p0"].score = 170
        room.detach_socket("sid0")
        room.detach_socket("sid1")

        drop_empty_rooms()
        clock["ms"] += EMPTY_ROOM_GRACE_MS - 1
        drop_empty_rooms()
        assert get_room(room.code) is room
        assert room.players["p0"].score == 170

    def test_a_room_nobody_returns_to_is_reaped(self, monkeypatch):
        clock = self._clock(monkeypatch)
        room = make_room(2)
        room.detach_socket("sid0")
        room.detach_socket("sid1")

        drop_empty_rooms()
        clock["ms"] += EMPTY_ROOM_GRACE_MS
        drop_empty_rooms()
        assert get_room(room.code) is None

    def test_a_reconnect_resets_the_clock(self, monkeypatch):
        clock = self._clock(monkeypatch)
        room = make_room(2)
        room.detach_socket("sid0")
        room.detach_socket("sid1")
        drop_empty_rooms()

        clock["ms"] += EMPTY_ROOM_GRACE_MS - 1
        room.add_player("p1", "Player 1", "sid1-new")
        drop_empty_rooms()
        assert room.empty_since_ms is None

        room.detach_socket("sid1-new")
        clock["ms"] += EMPTY_ROOM_GRACE_MS - 1
        drop_empty_rooms()
        assert get_room(room.code) is room

    def test_a_room_with_someone_connected_is_never_reaped(self, monkeypatch):
        clock = self._clock(monkeypatch)
        room = make_room(2)
        room.detach_socket("sid0")
        drop_empty_rooms()
        clock["ms"] += EMPTY_ROOM_GRACE_MS * 10
        drop_empty_rooms()
        assert get_room(room.code) is room


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

    def test_title_hits_never_outrank_score(self):
        room = make_room(2)
        room.players["p0"].score = 200
        room.players["p0"].title_hits = 0
        room.players["p1"].score = 100
        room.players["p1"].title_hits = 9
        assert room.standings()[0].id == "p0"

    def test_title_hits_are_exposed_to_clients(self):
        room = make_room(2)
        room.players["p0"].title_hits = 2
        state = serialize(room, "p0")
        assert state["standings"][0]["titleHits"] == 2


class TestDiscardRound:
    """A drawn card that cannot be played gives its round number back."""

    def test_the_round_number_is_returned_and_the_card_consumed(self):
        room = make_room()
        room.start_game(deck(8), rounds=4)
        room.begin_round()
        drawn_before = room.draw_index
        room.discard_round()
        assert room.round_no == 0
        assert room.current_card is None
        assert room.draw_index == drawn_before, "the card is not put back"
        card = room.begin_round()
        assert card is not None
        assert room.round_no == 1
