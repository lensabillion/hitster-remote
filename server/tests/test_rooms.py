"""Tests for live room state.

Two properties matter most here and neither fails loudly in manual play:

1. An unrevealed year must never reach any client. A leak is invisible during a
   game and silently decides who wins.
2. A dropped socket must never cost a seat, a timeline, or tokens. This is the
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
        artist_latin=f"{name} artist",
        title_latin=f"{name} title",
        artist_am="አርቲስት",
        title_am="ርዕስ",
    )


def make_room(n: int = 3) -> Room:
    rooms.clear()
    room = create_room("p0")
    for i in range(n):
        room.add_player(f"p{i}", f"Player {i}", f"sid{i}")
    return room


class TestSeating:
    def test_creator_is_host_and_first_seat(self):
        room = make_room(3)
        assert room.host_id == "p0"
        assert room.seats == ["p0", "p1", "p2"]
        assert room.active_player_id == "p0"

    def test_rejoining_rebinds_the_socket_without_taking_a_new_seat(self):
        room = make_room(2)
        room.players["p1"].timeline = [card(1970)]
        room.players["p1"].tokens = 4

        room.detach_socket("sid1")
        assert not room.players["p1"].connected
        assert room.seats == ["p0", "p1"]  # seat is kept

        room.add_player("p1", "Player 1", "sid1-new")
        assert room.players["p1"].connected
        assert room.players["p1"].sid == "sid1-new"
        assert len(room.players["p1"].timeline) == 1  # timeline survived
        assert room.players["p1"].tokens == 4  # tokens survived
        assert room.seats == ["p0", "p1"]  # still no duplicate seat

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
    def test_start_game_seeds_one_card_each_and_resets_tokens(self):
        room = make_room(3)
        room.start_game([card(1960 + i, f"c{i}") for i in range(12)])
        assert room.phase is Phase.PLAYING
        for player in room.players.values():
            assert len(player.timeline) == 1
            assert player.tokens == 2

    def test_placements_are_one_per_player_and_final(self):
        room = make_room(2)
        room.start_game([card(1960 + i, f"c{i}") for i in range(10)])
        room.begin_round()
        room.open_placement()

        assert room.submit_placement("p0", 1)
        assert not room.submit_placement("p0", 0)  # no second bite
        assert room.placements["p0"].gap == 1

    def test_placement_is_refused_outside_the_placing_phase(self):
        room = make_room(2)
        room.start_game([card(1960 + i, f"c{i}") for i in range(10)])
        room.begin_round()
        assert room.phase is Phase.PLAYING
        assert not room.submit_placement("p0", 0)

    def test_everyone_placed_ignores_disconnected_players(self):
        room = make_room(3)
        room.start_game([card(1960 + i, f"c{i}") for i in range(12)])
        room.begin_round()
        room.open_placement()
        room.detach_socket("sid2")

        room.submit_placement("p0", 0)
        assert not room.everyone_placed()
        room.submit_placement("p1", 0)
        assert room.everyone_placed()  # p2 is gone; the game does not stall

    def test_winner_is_detected_at_the_card_threshold(self):
        room = make_room(2)
        assert room.winner() is None
        room.players["p1"].timeline = [card(1900 + i, f"w{i}") for i in range(8)]
        assert room.winner() is room.players["p1"]


class TestSerializeWithholdsTheAnswer:
    def setup_method(self):
        self.room = make_room(2)
        self.room.start_game([card(1960 + i * 5, f"c{i}") for i in range(12)])
        self.subject = self.room.begin_round()
        self.room.open_placement()

    def test_no_unrevealed_year_appears_anywhere_in_the_payload(self):
        blob = json.dumps(serialize(self.room, "p0"))
        # Timelines legitimately contain years, so assert on the card field.
        assert serialize(self.room, "p0")["card"] is None
        assert serialize(self.room, "p0")["outcome"] is None
        # The subject card's own identifiers must not be present at all.
        assert self.subject.id not in blob
        assert self.subject.title_latin not in blob

    def test_card_is_disclosed_only_once_revealing(self):
        self.room.submit_placement("p0", 0)
        self.room.submit_placement("p1", 0)
        self.room.reveal()
        state = serialize(self.room, "p0")
        assert self.room.phase is Phase.REVEALING
        assert state["card"] is not None
        assert state["card"]["year"] == self.subject.year

    def test_other_players_choices_stay_hidden_before_the_reveal(self):
        self.room.submit_placement("p1", 2)
        state = serialize(self.room, "p0")
        # p0 learns that p1 has sealed something, never what.
        assert state["placedPlayerIds"] == ["p1"]
        assert state["outcome"] is None
        assert "2" not in json.dumps(state.get("outcome"))

    def test_viewer_only_learns_its_own_placement_status(self):
        self.room.submit_placement("p1", 2)
        assert serialize(self.room, "p0")["hasPlaced"] is False
        assert serialize(self.room, "p1")["hasPlaced"] is True

    def test_placements_are_disclosed_at_the_reveal(self):
        self.room.submit_placement("p0", 0)
        self.room.submit_placement("p1", 1)
        self.room.reveal()
        outcome = serialize(self.room, "p0")["outcome"]
        assert outcome["placements"] == {"p0": 0, "p1": 1}


class TestRoomRegistry:
    def test_lookup_is_case_insensitive_and_trimmed(self):
        room = make_room(1)
        assert get_room(room.code.lower()) is room
        assert get_room(f"  {room.code}  ") is room
        assert get_room("ZZZZ") is None
        assert get_room("") is None
