"""Pure game rules. No I/O, no state -- everything here is testable in isolation."""

from __future__ import annotations

import random
import time
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from matching import player_artist_matches, player_title_matches

# Knowing who sang it is the game; knowing exactly when is the tiebreaker.
#
# The song title scores NOTHING in the running total -- deliberately, so it never
# feels compulsory -- but a title hit is counted and breaks a tie. Someone who
# knew the title as well as the singer has shown more, and that should settle a
# draw rather than evaporating at the reveal.
ARTIST_POINTS = 70
YEAR_POINTS = 30


class Phase(StrEnum):
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


# A game should range across the decades rather than land wherever the deck is
# thick. Cards are dealt era by era in rotation: everything before 1980 as one
# era of classics, then each decade. A deck heavy in the 2010s still deals a
# 1980s song as often as a 2010s one, for as long as the thin era lasts.
ERA_STARTS = (1980, 1990, 2000, 2010, 2020)


def era_of(year: int) -> int:
    """Which era a year belongs to: 0 before 1980, then one per decade."""
    return sum(1 for start in ERA_STARTS if year >= start)


def deal_across_eras(cards: Sequence[Card], rng: random.Random | None = None) -> list[Card]:
    """Shuffle, then order the deck so consecutive cards rotate through the eras.

    Within an era the order is random, and the eras take turns in an order that
    is reshuffled on every pass, so no era always opens the game. An era that
    runs out drops out of the rotation. Every card is dealt exactly once.
    """
    shuffle = (rng or random).shuffle
    by_era: dict[int, list[Card]] = {}
    for card in cards:
        by_era.setdefault(era_of(card.year), []).append(card)
    for pile in by_era.values():
        shuffle(pile)
    dealt: list[Card] = []
    while by_era:
        eras = list(by_era)
        shuffle(eras)
        for era in eras:
            dealt.append(by_era[era].pop())
            if not by_era[era]:
                del by_era[era]
    return dealt


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


@dataclass(slots=True)
class AnswerScore:
    artist_right: bool
    year_right: bool
    title_right: bool
    points: int


def is_correct_placement(timeline: list[Card], card: Card, gap: int) -> bool:
    """True if `card` belongs in `gap` of a chronologically ordered `timeline`.

    `gap` is an insertion index in 0..len(timeline): gap 0 is before every card,
    gap len(timeline) is after every card.

    Both bounds are inclusive, which is exactly the official same-year rule --
    "if the year matches an existing card, either side of it counts as correct".
    """
    if not 0 <= gap <= len(timeline):
        return False
    after_left = gap == 0 or timeline[gap - 1].year <= card.year
    before_right = gap == len(timeline) or card.year <= timeline[gap].year
    return after_left and before_right


def insert_card(timeline: list[Card], card: Card, gap: int) -> list[Card]:
    return [*timeline[:gap], card, *timeline[gap:]]


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


def now_ms() -> int:
    return int(time.time() * 1000)
