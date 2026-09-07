"""Pure game rules. No I/O, no state — everything here is testable in isolation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

# Hitster constants.
TOKEN_CAP = 5
STARTING_TOKENS = 2
SKIP_COST = 1
BUY_CARD_COST = 3


class Phase(str, Enum):
    """Where a room is in the round cycle."""

    LOBBY = "lobby"
    PLAYING = "playing"  # Clip is audible.
    PLACING = "placing"  # Everyone is sealing a placement.
    REVEALING = "revealing"  # Simultaneous flip.
    OVER = "over"


@dataclass(slots=True)
class Card:
    """One song. `year` is the human-confirmed original release year."""

    id: str
    year: int
    artist_latin: str
    title_latin: str
    artist_am: str = ""
    title_am: str = ""
    youtube_id: str = ""
    deezer_track_id: int | None = None
    added_by: str = ""

    def display_artist(self) -> str:
        return self.artist_am or self.artist_latin

    def display_title(self) -> str:
        return self.title_am or self.title_latin


@dataclass(slots=True)
class Placement:
    """A sealed guess. Hidden from everyone until the reveal."""

    player_id: str
    gap: int
    submitted_ms: int = field(default_factory=lambda: int(time.time() * 1000))


def is_correct_placement(timeline: list[Card], card: Card, gap: int) -> bool:
    """True if `card` belongs in `gap` of a chronologically ordered `timeline`.

    `gap` is an insertion index in 0..len(timeline): gap 0 is before every card,
    gap len(timeline) is after every card.

    Both bounds are inclusive, which is exactly the official same-year rule --
    "if the year matches an existing card, either side of it counts as correct".
    A card from 1975 may sit on either side of another 1975 card because equality
    satisfies the lower bound and the upper bound alike.
    """
    if not 0 <= gap <= len(timeline):
        return False
    if gap > 0 and timeline[gap - 1].year > card.year:
        return False
    if gap < len(timeline) and card.year > timeline[gap].year:
        return False
    return True


def insert_card(timeline: list[Card], card: Card, gap: int) -> list[Card]:
    """Return a new timeline with `card` inserted at `gap`."""
    return timeline[:gap] + [card] + timeline[gap:]


def correct_gaps(timeline: list[Card], card: Card) -> list[int]:
    """Every gap that would count as correct. Usually one, two when years tie."""
    return [g for g in range(len(timeline) + 1) if is_correct_placement(timeline, card, g)]


@dataclass(slots=True)
class RoundOutcome:
    """What the reveal resolved to."""

    active_correct: bool
    card_winner: str | None  # Who ends up with the card, if anyone.
    stolen: bool
    token_awards: dict[str, int]  # player_id -> tokens gained
    correct_gaps: list[int]


def resolve_round(
    active_player_id: str,
    timelines: dict[str, list[Card]],
    placements: dict[str, Placement],
    card: Card,
) -> RoundOutcome:
    """Resolve one round of simultaneous shadow placement.

    The active player's placement is real: correct and they keep the card.
    Everyone else placed on their own timeline as a shadow guess, which earns a
    token when right, and steals the card when right *and* the active player was
    wrong.

    Ties between stealers go to the earliest sealed submission. Because every
    placement is sealed before any is revealed, submission time only ever breaks
    a tie between two already-correct guesses -- it never decides whether a guess
    counts, so no player gains an advantage from lower latency.
    """
    active_placement = placements.get(active_player_id)
    active_timeline = timelines.get(active_player_id, [])
    active_correct = bool(
        active_placement
        and is_correct_placement(active_timeline, card, active_placement.gap)
    )

    token_awards: dict[str, int] = {}
    correct_shadows: list[Placement] = []

    for player_id, placement in placements.items():
        if player_id == active_player_id:
            continue
        if is_correct_placement(timelines.get(player_id, []), card, placement.gap):
            token_awards[player_id] = 1
            correct_shadows.append(placement)

    card_winner: str | None = None
    stolen = False
    if active_correct:
        card_winner = active_player_id
    elif correct_shadows:
        correct_shadows.sort(key=lambda p: p.submitted_ms)
        card_winner = correct_shadows[0].player_id
        stolen = True

    return RoundOutcome(
        active_correct=active_correct,
        card_winner=card_winner,
        stolen=stolen,
        token_awards=token_awards,
        correct_gaps=correct_gaps(active_timeline, card),
    )


def clamp_tokens(n: int) -> int:
    return max(0, min(n, TOKEN_CAP))


def now_ms() -> int:
    return int(time.time() * 1000)
