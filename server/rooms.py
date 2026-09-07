"""Live room state.

Players are keyed by a durable id the client keeps in localStorage, never by
socket id. A refresh, a tunnel, or a dropped connection therefore costs a player
nothing: the socket is re-bound to the same seat and the timeline is still there.
Keying by socket id is the single change that would make this game unplayable on
an unreliable connection, which is the connection it is designed for.

Everything here is in memory. It changes several times a second and is worthless
once a round resolves; db.py holds the part that must outlive the process.
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, field

from game import (
    STARTING_TOKENS,
    Card,
    Phase,
    Placement,
    RoundOutcome,
    clamp_tokens,
    insert_card,
    now_ms,
    resolve_round,
)

CARDS_TO_WIN = 8
CLIP_SECONDS = 30
PLACEMENT_SECONDS = 25


@dataclass(slots=True)
class Player:
    id: str
    name: str
    sid: str | None = None
    tokens: int = STARTING_TOKENS
    timeline: list[Card] = field(default_factory=list)

    @property
    def connected(self) -> bool:
        return self.sid is not None


@dataclass(slots=True)
class Room:
    code: str
    host_id: str
    players: dict[str, Player] = field(default_factory=dict)
    seats: list[str] = field(default_factory=list)
    phase: Phase = Phase.LOBBY
    round_no: int = 0
    active_seat: int = 0
    deck: list[Card] = field(default_factory=list)
    draw_index: int = 0
    current_card: Card | None = None
    placements: dict[str, Placement] = field(default_factory=dict)
    clip_started_ms: int = 0
    last_outcome: RoundOutcome | None = None

    # ---------- seating ----------

    @property
    def active_player_id(self) -> str | None:
        if not self.seats:
            return None
        return self.seats[self.active_seat % len(self.seats)]

    def connected_players(self) -> list[Player]:
        return [p for p in self.players.values() if p.connected]

    def add_player(self, player_id: str, name: str, sid: str) -> Player:
        """Seat a new player, or re-bind an existing one to a new socket."""
        player = self.players.get(player_id)
        if player:
            player.sid = sid
            player.name = name or player.name
            return player
        player = Player(id=player_id, name=name, sid=sid)
        self.players[player_id] = player
        self.seats.append(player_id)
        return player

    def detach_socket(self, sid: str) -> str | None:
        """Mark a player disconnected without unseating them."""
        for player in self.players.values():
            if player.sid == sid:
                player.sid = None
                return player.id
        return None

    def promote_host_if_needed(self) -> None:
        host = self.players.get(self.host_id)
        if host and host.connected:
            return
        for seat_id in self.seats:
            candidate = self.players.get(seat_id)
            if candidate and candidate.connected:
                self.host_id = candidate.id
                return

    def advance_seat(self) -> None:
        """Move to the next seat, skipping players who have dropped."""
        if not self.seats:
            return
        for step in range(1, len(self.seats) + 1):
            seat = (self.active_seat + step) % len(self.seats)
            player = self.players.get(self.seats[seat])
            if player and player.connected:
                self.active_seat = seat
                return
        self.active_seat = (self.active_seat + 1) % len(self.seats)

    # ---------- round flow ----------

    def start_game(self, deck: list[Card]) -> None:
        self.deck = list(deck)
        random.shuffle(self.deck)
        self.draw_index = 0
        self.round_no = 0
        self.active_seat = 0
        self.phase = Phase.PLAYING
        # Each player is seeded with one card, face up, as their starting year.
        for player in self.players.values():
            player.tokens = STARTING_TOKENS
            player.timeline = []
            if seed := self.draw():
                player.timeline = [seed]

    def draw(self) -> Card | None:
        if self.draw_index >= len(self.deck):
            return None
        card = self.deck[self.draw_index]
        self.draw_index += 1
        return card

    def begin_round(self) -> Card | None:
        card = self.draw()
        if card is None:
            self.phase = Phase.OVER
            return None
        self.current_card = card
        self.placements = {}
        self.last_outcome = None
        self.round_no += 1
        self.phase = Phase.PLAYING
        self.clip_started_ms = now_ms()
        return card

    def open_placement(self) -> None:
        if self.phase is Phase.PLAYING:
            self.phase = Phase.PLACING

    def submit_placement(self, player_id: str, gap: int) -> bool:
        """Record a sealed placement. One per player per round, no changing it."""
        if self.phase is not Phase.PLACING:
            return False
        if player_id not in self.players or player_id in self.placements:
            return False
        self.placements[player_id] = Placement(player_id=player_id, gap=gap)
        return True

    def everyone_placed(self) -> bool:
        expected = {p.id for p in self.connected_players()}
        return bool(expected) and expected <= set(self.placements)

    def reveal(self) -> RoundOutcome | None:
        """Resolve the round and apply its effects to timelines and tokens."""
        if self.current_card is None:
            return None
        active_id = self.active_player_id or ""
        timelines = {pid: p.timeline for pid, p in self.players.items()}

        outcome = resolve_round(active_id, timelines, self.placements, self.current_card)

        for player_id, tokens in outcome.token_awards.items():
            if player := self.players.get(player_id):
                player.tokens = clamp_tokens(player.tokens + tokens)

        if outcome.card_winner and (winner := self.players.get(outcome.card_winner)):
            placement = self.placements.get(outcome.card_winner)
            if placement:
                winner.timeline = insert_card(
                    winner.timeline, self.current_card, placement.gap
                )

        self.phase = Phase.REVEALING
        self.last_outcome = outcome
        return outcome

    def winner(self) -> Player | None:
        for player in self.players.values():
            if len(player.timeline) >= CARDS_TO_WIN:
                return player
        return None


rooms: dict[str, Room] = {}


def generate_code() -> str:
    while True:
        code = "".join(random.choices(string.ascii_uppercase, k=4))
        if code not in rooms:
            return code


def create_room(host_id: str) -> Room:
    room = Room(code=generate_code(), host_id=host_id)
    rooms[room.code] = room
    return room


def get_room(code: str) -> Room | None:
    return rooms.get(code.upper().strip()) if code else None


def drop_empty_rooms() -> None:
    for code, room in list(rooms.items()):
        if not room.connected_players():
            del rooms[code]


def serialize(room: Room, viewer_id: str) -> dict:
    """Room state as one player may see it.

    The current card's year, artist and title are withheld until the reveal.
    Anything sent here is readable in devtools, so an unrevealed year must not
    appear in this payload under any circumstances.
    """
    revealing = room.phase is Phase.REVEALING
    card = room.current_card

    return {
        "code": room.code,
        "hostId": room.host_id,
        "phase": room.phase.value,
        "roundNo": room.round_no,
        "activePlayerId": room.active_player_id,
        "viewerId": viewer_id,
        "cardsToWin": CARDS_TO_WIN,
        "deckRemaining": max(0, len(room.deck) - room.draw_index),
        "players": [
            {
                "id": p.id,
                "name": p.name,
                "tokens": p.tokens,
                "connected": p.connected,
                "isHost": p.id == room.host_id,
                "timeline": [
                    {
                        "id": c.id,
                        "year": c.year,
                        "artistAm": c.artist_am,
                        "titleAm": c.title_am,
                        "artistLatin": c.artist_latin,
                        "titleLatin": c.title_latin,
                    }
                    for c in p.timeline
                ],
            }
            for p in (room.players[pid] for pid in room.seats if pid in room.players)
        ],
        # Who has sealed a placement -- but never what they chose.
        "placedPlayerIds": sorted(room.placements),
        "hasPlaced": viewer_id in room.placements,
        "card": (
            {
                "id": card.id,
                "year": card.year,
                "artistAm": card.artist_am,
                "titleAm": card.title_am,
                "artistLatin": card.artist_latin,
                "titleLatin": card.title_latin,
                "addedBy": card.added_by,
            }
            if card and revealing
            else None
        ),
        "outcome": (
            {
                "activeCorrect": room.last_outcome.active_correct,
                "cardWinner": room.last_outcome.card_winner,
                "stolen": room.last_outcome.stolen,
                "tokenAwards": room.last_outcome.token_awards,
                "placements": {
                    pid: p.gap for pid, p in room.placements.items()
                },
            }
            if revealing and room.last_outcome
            else None
        ),
    }
