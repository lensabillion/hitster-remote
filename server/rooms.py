"""Live room state.

Players are keyed by a durable id the client keeps in localStorage, never by
socket id. A refresh, a tunnel, or a dropped connection therefore costs a player
nothing: the socket is re-bound to the same seat and the timeline is still there.

Everything here is in memory. It changes several times a second and is worthless
once a round resolves; db.py holds the part that must outlive the process.
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, field

from game import (
    MAX_ROUND_SCORE,
    STARTING_TOKENS,
    Answer,
    Card,
    Phase,
    RoundOutcome,
    insert_card,
    now_ms,
    resolve_round,
)

CLIP_SECONDS = 30
# A ceiling, not a pace. The round ends as soon as everyone has answered; this
# only stops one absent player from stalling the table.
ANSWER_SECONDS = 90
DEFAULT_ROUNDS = 12
# A room is not destroyed the moment its last socket drops. Two players on the
# same flaky connection can both blink out at once, and deleting the room there
# would throw away a live game -- scores, timelines and all -- for a hiccup that
# resolves in two seconds.
EMPTY_ROOM_GRACE_MS = 15 * 60 * 1000


@dataclass(slots=True)
class Player:
    id: str
    name: str
    sid: str | None = None
    tokens: int = STARTING_TOKENS
    score: int = 0
    # Title hits score nothing, but they break ties. See standings().
    title_hits: int = 0
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
    rounds_planned: int = DEFAULT_ROUNDS
    active_seat: int = 0
    deck: list[Card] = field(default_factory=list)
    draw_index: int = 0
    current_card: Card | None = None
    answers: dict[str, Answer] = field(default_factory=dict)
    clip_started_ms: int = 0
    last_outcome: RoundOutcome | None = None
    empty_since_ms: int | None = None

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

    def start_game(self, deck: list[Card], rounds: int | None = None) -> None:
        self.deck = list(deck)
        random.shuffle(self.deck)
        self.draw_index = 0
        self.round_no = 0
        self.active_seat = 0
        # One seed card each, then one card per round.
        seats = max(1, len(self.players))
        playable = max(1, len(self.deck) - seats)
        # One song per turn, so plan a whole number of turns each -- otherwise
        # whoever sits early in the order gets more songs than everyone else.
        wanted = min(rounds or DEFAULT_ROUNDS, playable)
        turns_each = max(1, wanted // seats)
        self.rounds_planned = turns_each * seats
        self.phase = Phase.ANSWERING
        for player in self.players.values():
            player.tokens = STARTING_TOKENS
            player.score = 0
            player.title_hits = 0
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
        if card is None or self.round_no >= self.rounds_planned:
            self.phase = Phase.OVER
            return None
        self.current_card = card
        self.answers = {}
        self.last_outcome = None
        self.round_no += 1
        # Answering opens with the clip, not after it.
        self.phase = Phase.ANSWERING
        self.clip_started_ms = now_ms()
        return card

    def submit_answer(
        self,
        player_id: str,
        gap: int,
        artist_guess: str,
        title_guess: str,
        declined: bool = False,
    ) -> bool:
        """Seal the answer for this turn.

        One song, one answer: only the player whose turn it is may answer.
        Everyone else hears the clip and watches, and gets their own song on
        their own turn.
        """
        if self.phase is not Phase.ANSWERING:
            return False
        if player_id != self.active_player_id:
            return False
        if player_id not in self.players or player_id in self.answers:
            return False
        self.answers[player_id] = Answer(
            player_id=player_id,
            gap=gap,
            artist_guess="" if declined else artist_guess.strip(),
            title_guess="" if declined else title_guess.strip(),
            declined=declined,
        )
        return True

    def active_answered(self) -> bool:
        """The turn is over once its one player has sealed an answer."""
        active = self.active_player_id
        return bool(active) and active in self.answers

    def reveal(self) -> RoundOutcome | None:
        """Resolve the round and apply points, then the card itself."""
        if self.current_card is None:
            return None
        active_id = self.active_player_id or ""
        timelines = {pid: p.timeline for pid, p in self.players.items()}

        outcome = resolve_round(active_id, timelines, self.answers, self.current_card)

        if player := self.players.get(active_id):
            player.score += outcome.points
            if outcome.score and outcome.score.title_right:
                player.title_hits += 1
            if outcome.keeps_card and (answer := self.answers.get(active_id)):
                player.timeline = insert_card(
                    player.timeline, self.current_card, answer.gap
                )

        self.phase = Phase.REVEALING
        self.last_outcome = outcome
        return outcome

    def is_last_round(self) -> bool:
        return self.round_no >= self.rounds_planned or self.draw_index >= len(self.deck)

    def standings(self) -> list[Player]:
        """Rank by score, then by title hits, then by cards held.

        Titles are worth no points on purpose, so that naming one never feels
        compulsory — but knowing the title as well as the singer is more
        knowledge, and it settles a draw.
        """
        return sorted(
            self.players.values(),
            key=lambda p: (p.score, p.title_hits, len(p.timeline)),
            reverse=True,
        )

    def leader(self) -> Player | None:
        ranked = self.standings()
        return ranked[0] if ranked else None


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
    """Reap rooms nobody has come back to, after a grace period.

    Deleting on the last disconnect looks correct and is not: a shared wifi
    blip drops every socket at once, and the game would be gone before anyone
    could reconnect. Players hold durable ids, so the room only has to survive
    long enough for them to return.
    """
    now = now_ms()
    for code, room in list(rooms.items()):
        if room.connected_players():
            room.empty_since_ms = None
            continue
        if room.empty_since_ms is None:
            room.empty_since_ms = now
        elif now - room.empty_since_ms >= EMPTY_ROOM_GRACE_MS:
            del rooms[code]


def _card_json(card: Card) -> dict:
    return {
        "id": card.id,
        "year": card.year,
        "artistAm": card.artist_am,
        "titleAm": card.title_am,
        "artistLatin": card.artist_latin,
        "titleLatin": card.title_latin,
    }


def serialize(room: Room, viewer_id: str) -> dict:
    """Room state as one player may see it.

    The current card is withheld entirely until the reveal. Anything sent here
    is readable in devtools, so an unrevealed answer must not appear in this
    payload under any circumstances.
    """
    revealing = room.phase is Phase.REVEALING
    card = room.current_card
    own_answer = room.answers.get(viewer_id)

    return {
        "code": room.code,
        "hostId": room.host_id,
        "phase": room.phase.value,
        "roundNo": room.round_no,
        "roundsPlanned": room.rounds_planned,
        "activePlayerId": room.active_player_id,
        "viewerId": viewer_id,
        "maxRoundScore": MAX_ROUND_SCORE,
        "clipSeconds": CLIP_SECONDS,
        "isLastRound": room.is_last_round(),
        "players": [
            {
                "id": p.id,
                "name": p.name,
                "tokens": p.tokens,
                "score": p.score,
                "titleHits": p.title_hits,
                "connected": p.connected,
                "isHost": p.id == room.host_id,
                "timeline": [_card_json(c) for c in p.timeline],
            }
            for p in (room.players[pid] for pid in room.seats if pid in room.players)
        ],
        # Who has sealed an answer -- but never what they wrote.
        "isMyTurn": viewer_id == room.active_player_id,
        "hasAnswered": viewer_id in room.answers,
        "myAnswer": (
            {
                "gap": own_answer.gap,
                "artistGuess": own_answer.artist_guess,
                "titleGuess": own_answer.title_guess,
            }
            if own_answer
            else None
        ),
        "card": _card_json(card) | {"addedBy": card.added_by} if card and revealing else None,
        "outcome": (
            {
                "playerId": room.last_outcome.active_player_id,
                "keptCard": room.last_outcome.keeps_card,
                "points": room.last_outcome.points,
                "artistRight": bool(
                    room.last_outcome.score and room.last_outcome.score.artist_right
                ),
                "yearRight": bool(
                    room.last_outcome.score and room.last_outcome.score.year_right
                ),
                "titleRight": bool(
                    room.last_outcome.score and room.last_outcome.score.title_right
                ),
                "declined": bool(
                    room.last_outcome.active_player_id in room.answers
                    and room.answers[room.last_outcome.active_player_id].declined
                ),
                "artistGuess": (
                    room.answers[room.last_outcome.active_player_id].artist_guess
                    if room.last_outcome.active_player_id in room.answers
                    else ""
                ),
                "titleGuess": (
                    room.answers[room.last_outcome.active_player_id].title_guess
                    if room.last_outcome.active_player_id in room.answers
                    else ""
                ),
            }
            if revealing and room.last_outcome
            else None
        ),
        "standings": [
            {"id": p.id, "name": p.name, "score": p.score, "titleHits": p.title_hits}
            for p in room.standings()
        ],
    }
