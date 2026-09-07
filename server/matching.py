"""Name matching.

Two different jobs live here and they need opposite temperaments.

Catalogue matching (`artist_matches`) is strict: it decides whether a Deezer
result really is the artist a deck card names. A wrong match there silently
plays a different song, so it would rather reject a true match than accept a
false one.

Player matching (`player_artist_matches`) is generous: it decides whether a
human typing into a text box meant this artist. Amharic names reach Latin script
with no agreed spelling -- Tilahun/Telahun, Astatke/Astatqe, Yehune/Yehunie --
and a player should never lose a point to a transliteration they had no way to
guess. Surnames alone count, and so do given names, because that is how people
actually refer to these artists.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

# Catalogue: a wrong artist is worse than no artist.
ARTIST_OVERALL_MIN = 0.85
ARTIST_WORD_MIN = 0.80

# Player input: a rejected true answer is worse than a generous one.
PLAYER_FULL_MIN = 0.82
PLAYER_WORD_MIN = 0.85
PLAYER_MIN_WORD_LEN = 4

# Words that carry no identifying weight in a band or artist name.
STOPWORDS = {"the", "band", "group", "and", "of"}


def normalize(s: str) -> str:
    """Casefold and strip accents so 'Erè mèla mèla' matches 'Ere mela mela'."""
    s = unicodedata.normalize("NFKD", s.strip().casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def _words(s: str) -> list[str]:
    return [w for w in normalize(s).split() if w not in STOPWORDS]


def artist_matches(wanted: str, found: str) -> bool:
    """Strict: does `found` name the same catalogue artist as `wanted`?

    A single whole-string ratio cannot do this. "Teddy Afro" vs "Teddy Karo" (a
    different artist) scores 0.90, while "Mulatu Astatke" vs "Mulatu Astatqe" (a
    transliteration variant) scores 0.93 -- the bands overlap. Comparing word by
    word separates them: a wrong artist differs wholly in one word, a variant
    differs slightly in every word.
    """
    a_words, b_words = normalize(wanted).split(), normalize(found).split()
    if not a_words or len(a_words) != len(b_words):
        return False
    if similarity(wanted, found) < ARTIST_OVERALL_MIN:
        return False
    return all(
        SequenceMatcher(None, x, y).ratio() >= ARTIST_WORD_MIN
        for x, y in zip(a_words, b_words)
    )


def player_artist_matches(guess: str, answer: str) -> bool:
    """Generous: did the player mean this artist?

    Accepts, in order:
      - the whole name, however spelled ("tilahun gessesse", "Telahun Gesesse")
      - any single distinctive name from it ("Astatke", "Mulatu", "Aster")

    Rejects short fragments, so "a" or "the" cannot match everything. A player
    typing one real name of a two-name artist has demonstrated they know who it
    is, which is the thing being scored.
    """
    guess_norm, answer_norm = normalize(guess), normalize(answer)
    if not guess_norm or not answer_norm:
        return False
    if guess_norm == answer_norm:
        return True
    if similarity(guess_norm, answer_norm) >= PLAYER_FULL_MIN:
        return True

    answer_words = _words(answer)
    guess_words = _words(guess)
    if not answer_words or not guess_words:
        return False

    # A distinctive single name is enough, in either direction.
    for g in guess_words:
        if len(g) < PLAYER_MIN_WORD_LEN:
            continue
        for a in answer_words:
            if len(a) < PLAYER_MIN_WORD_LEN:
                continue
            if SequenceMatcher(None, g, a).ratio() >= PLAYER_WORD_MIN:
                return True
    return False


def player_title_matches(guess: str, answer: str) -> bool:
    """Same generosity, for song titles. Not scored, but shown at the reveal."""
    if not normalize(guess) or not normalize(answer):
        return False
    return (
        normalize(guess) == normalize(answer)
        or similarity(guess, answer) >= PLAYER_FULL_MIN
    )
