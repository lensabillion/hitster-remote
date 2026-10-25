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
actually refer to these artists. The vowels are what vary most between spellings,
so a guess that agrees with the answer once the vowels are set aside counts too:
Makiya Bahilu is Mikaya Behailu.
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
# Player input with the vowels set aside: a skeleton this short says nothing.
PLAYER_MIN_SKELETON_LEN = 3

# Consonant spellings that reach Latin script for the same Amharic sound. The
# placeholders are upper case so a later rule cannot re-read them (input is
# casefolded by then). Digraphs come before their letters.
CONSONANT_VARIANTS = (
    ("tch", "C"),
    ("ch", "C"),
    ("sh", "S"),
    ("zh", "J"),
    ("ph", "f"),
    ("ts", "s"),
    ("tz", "s"),
    ("kh", "k"),
    ("q", "k"),
    ("c", "k"),
)

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
        for x, y in zip(a_words, b_words, strict=True)
    )


def _name_skeleton(s: str, drop_y: bool = False) -> str:
    """A normalized name with its vowels set aside and doubled letters folded.

    "makiya" and "mikaya" both become "mky"; "gessesse" and "gesese" both become
    "gs". With `drop_y`, y goes too: it stands in for i as often as not
    (Tsehaytu / Tsehaitu).
    """
    for variant, canonical in CONSONANT_VARIANTS:
        s = s.replace(variant, canonical)
    s = re.sub(r"[aeiouy\s]" if drop_y else r"[aeiou\s]", "", s)
    return re.sub(r"(.)\1+", r"\1", s)


def _skeletons_agree(a: str, b: str) -> bool:
    """Do two normalized names agree once their vowels are set aside?"""
    for drop_y in (False, True):
        sa, sb = _name_skeleton(a, drop_y), _name_skeleton(b, drop_y)
        if min(len(sa), len(sb)) >= PLAYER_MIN_SKELETON_LEN and sa == sb:
            return True
    return False


def player_artist_matches(guess: str, answer: str) -> bool:
    """Generous: did the player mean this artist?

    Accepts, in order:
      - the whole name, however spelled ("tilahun gessesse", "Telahun Gesesse")
      - the whole name with the vowels set aside ("Makiya Bahilu")
      - any single distinctive name from it ("Astatke", "Mulatu", "Aster"),
        again with the vowels set aside if need be ("Bahilu")

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
    # The vowels are the part of a transliteration that varies most, so a guess
    # that agrees once they are set aside counts: Makiya Bahilu is Mikaya Behailu.
    if _skeletons_agree(guess_norm, answer_norm):
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
            if _skeletons_agree(g, a):
                return True
    return False


def player_title_matches(guess: str, answer: str) -> bool:
    """Same generosity, for song titles. Not scored, but a tiebreak at the reveal."""
    g, a = normalize(guess), normalize(answer)
    if not g or not a:
        return False
    return g == a or similarity(guess, answer) >= PLAYER_FULL_MIN or _skeletons_agree(g, a)


# Catalogue, titles: the same song reaches Deezer under several spellings and
# with suffixes ("Tezeta (Nostalgia)", "Erè mèla mèla"), so containment counts,
# and so does agreeing once the vowels -- the part of a transliteration that
# varies most (Tizita / Tezeta / Tezita) -- are set aside.
TITLE_MIN = 0.75
TITLE_MIN_CONTAINED_LEN = 4
TITLE_MIN_SKELETON_LEN = 3


def _skeleton(s: str) -> str:
    """A normalized title with its vowels removed: 'tizita' and 'tezeta' agree."""
    return re.sub(r"[aeiou\s]", "", s)


def _strip_brackets(s: str) -> str:
    return re.sub(r"[\(\[][^()\[\]]*[\)\]]", " ", s)


def title_matches(wanted: str, found: str) -> bool:
    """Strict-ish: is `found` a version of the song titled `wanted`?

    Used when attaching a Deezer track to a card automatically. Accents and
    punctuation are ignored, a bracketed suffix on the found title is ignored
    ("Darign (Bonus Track)"), a title contained whole in the other counts, and
    otherwise the two must be close -- as spelled, or with the vowels set aside.
    """
    a = normalize(wanted)
    if not a:
        return False
    for candidate in (found, _strip_brackets(found)):
        b = normalize(candidate)
        if not b:
            continue
        if a == b:
            return True
        if min(len(a), len(b)) >= TITLE_MIN_CONTAINED_LEN and (a in b or b in a):
            return True
        if SequenceMatcher(None, a, b).ratio() >= TITLE_MIN:
            return True
        sa, sb = _skeleton(a), _skeleton(b)
        if min(len(sa), len(sb)) >= TITLE_MIN_SKELETON_LEN and sa == sb:
            return True
    return False
