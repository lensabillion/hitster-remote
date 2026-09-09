"""Pure game rules. No I/O, no state — everything here is testable in isolation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from matching import player_artist_matches, player_title_matches

TOKEN_CAP = 5
STARTING_TOKENS = 2

# Knowing who sang it is the game; knowing exactly when is the tiebreaker.
#
# The song title scores NOTHING in the running total -- deliberately, so it never
# feels compulsory -- but a title hit is counted and breaks a tie. Someone who
# knew the title as well as the singer has shown more, and that should settle a
# draw rather than evaporating at the reveal.
ARTIST_POINTS = 70
YEAR_POINTS = 30
MAX_ROUND_SCORE = ARTIST_POINTS + YEAR_POINTS


class Phase(str, Enum):
    """Where a room is in the round cycle.

    There is no separate "listening" phase: the answer card is open from the
    moment the clip starts, so a player may answer over the music or stop it and
    answer afterwards. Gating answers behind the end of the clip made the round
    feel rigid and punished anyone who recognised the song in two seconds.
    """

    LOBBY = "lobby"
    ANSWERING = "answering"
    REVEALING = "revealing"
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
class Answer:
    """A sealed answer card. Hidden from everyone until the reveal.

    `declined` is an explicit "I don't know" rather than a silent timeout. It
    scores nothing and keeps no card, but it ends the turn immediately instead
    of making everyone wait out the clock for an answer that is not coming.
    """

    player_id: str
    gap: int
    artist_guess: str = ""
    title_guess: str = ""
    declined: bool = False
    submitted_ms: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass(slots=True)
class AnswerScore:
    artist_right: bool
    year_right: bool
    title_right: bool
    points: int

    @property
    def anything_right(self) -> bool:
        return self.artist_right or self.year_right


def is_correct_placement(timeline: list[Card], card: Card, gap: int) -> bool:
    """True if `card` belongs in `gap` of a chronologically ordered `timeline`.

    `gap` is an insertion index in 0..len(timeline): gap 0 is before every card,
    gap len(timeline) is after every card.

    Both bounds are inclusive, which is exactly the official same-year rule --
    "if the year matches an existing card, either side of it counts as correct".
    """
    if not 0 <= gap <= len(timeline):
        return False
    if gap > 0 and timeline[gap - 1].year > card.year:
        return False
    if gap < len(timeline) and card.year > timeline[gap].year:
        return False
    return True


def insert_card(timeline: list[Card], card: Card, gap: int) -> list[Card]:
    return timeline[:gap] + [card] + timeline[gap:]


def correct_gaps(timeline: list[Card], card: Card) -> list[int]:
    """Every gap that would count as correct. Usually one, two when years tie."""
    return [g for g in range(len(timeline) + 1) if is_correct_placement(timeline, card, g)]


def score_answer(answer: Answer, card: Card, timeline: list[Card]) -> AnswerScore:
    """Grade one answer card out of 100.

    The two halves are independent on purpose: naming the singer but misplacing
    the year still scores 70, because knowing who sang it is most of what the
    game is asking. Artist matching is deliberately generous about
    transliteration -- a player should never lose points to a spelling of an
    Amharic name that has no agreed Latin form.
    """
    if answer.declined:
        # Passing is a real choice, not a failure to submit. Nothing is right,
        # nothing is scored, and the round moves on.
        return AnswerScore(False, False, False, 0)

    artist_right = player_artist_matches(answer.artist_guess, card.artist_latin)
    year_right = is_correct_placement(timeline, card, answer.gap)
    title_right = player_title_matches(answer.title_guess, card.title_latin)

    points = (ARTIST_POINTS if artist_right else 0) + (YEAR_POINTS if year_right else 0)
    return AnswerScore(artist_right, year_right, title_right, points)


@dataclass(slots=True)
class RoundOutcome:
    """What the reveal resolved to.

    One song, one answer. Only the player whose turn it is answers the card;
    everyone else hears the clip and watches. The turn then passes on, so each
    song belongs to exactly one player.
    """

    active_player_id: str
    score: AnswerScore | None  # None when the active player never answered
    keeps_card: bool

    @property
    def points(self) -> int:
        return self.score.points if self.score else 0


def resolve_round(
    active_player_id: str,
    timelines: dict[str, list[Card]],
    answers: dict[str, Answer],
    card: Card,
) -> RoundOutcome:
    """Grade the turn.

    Only the active player's answer counts. Their card is graded against their
    own timeline, and they keep it when the year is right -- the timeline is
    both the play surface and the record of what they have won.
    """
    answer = answers.get(active_player_id)
    if answer is None:
        return RoundOutcome(active_player_id, None, False)

    score = score_answer(answer, card, timelines.get(active_player_id, []))
    return RoundOutcome(active_player_id, score, score.year_right)


def clamp_tokens(n: int) -> int:
    return max(0, min(n, TOKEN_CAP))


def now_ms() -> int:
    return int(time.time() * 1000)
