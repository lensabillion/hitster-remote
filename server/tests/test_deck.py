"""Tests for the deck as data: export, diff, and storage detection.

On a deployed server the database is thrown away on every deploy, restart and
free-tier spin-down, so a song added through /deck survives only if it is
exported back into decks/deck.json and committed. These tests hold the two
things that make that safe: the export round-trips exactly, and the editor can
tell precisely what would be lost.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import main
from db import Database
from deck import (
    EXPORT_FIELDS,
    LATEST_YEAR,
    card_from_row,
    card_id,
    diff_decks,
    export_rows,
    export_text,
    is_playable,
    load_deck_file,
)

DECK_JSON = Path(__file__).resolve().parent.parent / "decks" / "deck.json"


def row(id_: str, year: int, **overrides) -> dict:
    base = {
        "id": id_,
        "year": year,
        "artist_latin": f"Artist {id_}",
        "title_latin": f"Song {id_}",
        "artist_am": "",
        "title_am": "",
        "youtube_id": "",
        "deezer_track_id": 1000 + year,
        "added_by": "test",
    }
    return base | overrides


class TestCardId:
    def test_is_stable_across_case_and_whitespace(self):
        assert card_id("Aster Aweke", "Gela Gela") == card_id("  aster aweke ", "GELA GELA")

    def test_differs_per_song(self):
        assert card_id("Aster Aweke", "Gela Gela") != card_id("Aster Aweke", "Y'shebellu")


class TestCardFromRow:
    def test_builds_the_rules_card_from_a_row(self):
        card = card_from_row(row("a", 1975, artist_am="ማህሙድ አህመድ"))
        assert (card.id, card.year, card.artist_am) == ("a", 1975, "ማህሙድ አህመድ")

    def test_optional_fields_default_when_absent(self):
        card = card_from_row({"id": "a", "year": 1975, "artist_latin": "A", "title_latin": "T"})
        assert (card.youtube_id, card.deezer_track_id, card.added_by) == ("", None, "")


class TestPlayable:
    def test_needs_a_source(self):
        assert is_playable(row("a", 1970))
        assert is_playable(row("a", 1970, deezer_track_id=None, youtube_id="ADc9JPeLYi4"))
        assert not is_playable(row("a", 1970, deezer_track_id=None))


class TestExportFormat:
    def test_exports_exactly_the_deck_fields(self):
        extra = row("a", 1970) | {"created_at": 123, "internal": "x"}
        (exported,) = export_rows([extra])
        assert tuple(exported) == EXPORT_FIELDS

    def test_order_is_deterministic_when_years_tie(self):
        # SQLite promises no order for ties. Without the id tiebreak, two cards
        # sharing a year could swap between exports and look like a change.
        a, b = row("b1f7", 1969), row("dc74", 1969)
        assert [r["id"] for r in export_rows([b, a])] == ["b1f7", "dc74"]
        assert [r["id"] for r in export_rows([a, b])] == ["b1f7", "dc74"]

    def test_amharic_is_written_as_text_not_escapes(self):
        text = export_text([row("a", 1975, artist_am="ማህሙድ አህመድ")])
        assert "ማህሙድ አህመድ" in text
        assert "\\u" not in text

    def test_ends_with_a_newline(self):
        assert export_text([row("a", 1975)]).endswith("\n")

    def test_the_committed_deck_is_already_in_canonical_form(self):
        # If this fails, deck.json was edited by hand or exported by an older
        # tool, and the next download will show spurious changes.
        on_disk = DECK_JSON.read_text(encoding="utf-8")
        assert export_text(json.loads(on_disk)) == on_disk

    def test_the_committed_deck_is_playable_and_within_the_year_bounds(self):
        for card in load_deck_file(DECK_JSON):
            assert is_playable(card), card["title_latin"]
            assert 1900 <= card["year"] <= LATEST_YEAR, card["title_latin"]


class TestRoundTrip:
    def test_export_then_seed_then_export_is_identical(self, tmp_path):
        """What a player downloads must reload into exactly the same deck."""
        original = [
            row("x1", 1966, artist_am="ጥላሁን ገሠሠ", title_am="ሁሉም በሀገር ነው"),
            row("x2", 1969),
            row("x3", 1969, youtube_id="ADc9JPeLYi4", deezer_track_id=None),
            row("x4", 2019, added_by="lensa"),
        ]
        first = export_text(original)

        async def reload() -> str:
            database = Database(tmp_path / "roundtrip.db")
            await database.connect()
            await database.upsert_cards(json.loads(first))
            again = export_text(await database.all_cards())
            await database.close()
            return again

        assert asyncio.run(reload()) == first


class TestLoadDeckFile:
    def test_missing_file_is_none_not_an_empty_deck(self, tmp_path):
        # An empty list would make every live card look unsaved.
        assert load_deck_file(tmp_path / "nope.json") is None

    def test_reads_the_file(self, tmp_path):
        path = tmp_path / "deck.json"
        path.write_text(export_text([row("a", 1970)]), encoding="utf-8")
        assert load_deck_file(path)[0]["id"] == "a"


class TestDiffDecks:
    def test_identical_decks_have_nothing_unsaved(self):
        deck = [row("a", 1970), row("b", 1980)]
        assert diff_decks(deck, [dict(r) for r in deck]) == {
            "added": [], "removed": [], "changed": [],
        }

    def test_a_song_added_live_is_reported(self):
        committed = [row("a", 1970)]
        live = [*committed, row("new", 1999)]
        out = diff_decks(committed, live)
        assert [c["id"] for c in out["added"]] == ["new"]
        assert out["removed"] == [] and out["changed"] == []

    def test_a_song_removed_live_is_reported(self):
        committed = [row("a", 1970), row("gone", 1980)]
        out = diff_decks(committed, [row("a", 1970)])
        assert [c["id"] for c in out["removed"]] == ["gone"]

    def test_a_corrected_year_is_a_change(self):
        # Fixing the unverified starter years is exactly the edit that must not
        # be lost to a spin-down.
        out = diff_decks([row("a", 1969)], [row("a", 1974)])
        assert [c["id"] for c in out["changed"]] == ["a"]
        assert out["changed"][0]["year"] == 1974

    def test_fields_outside_the_deck_do_not_count_as_changes(self):
        live = [row("a", 1970) | {"created_at": 999}]
        assert diff_decks([row("a", 1970)], live)["changed"] == []

    def test_entries_are_brief_and_client_shaped(self):
        (entry,) = diff_decks([], [row("n", 1990)])["added"]
        assert entry == {
            "id": "n", "year": 1990, "artistLatin": "Artist n", "titleLatin": "Song n",
        }


class TestStorageDetection:
    """The warning must be accurate: loud on a throwaway disk, quiet on a laptop."""

    def _ephemeral(self, monkeypatch, **env):
        for key in ("RENDER", "FLY_APP_NAME", "DECK_STORAGE"):
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return main.storage_is_ephemeral()

    def test_local_development_is_persistent(self, monkeypatch):
        assert self._ephemeral(monkeypatch) is False

    def test_render_is_detected_without_any_configuration(self, monkeypatch):
        # Render sets RENDER=true on every service.
        assert self._ephemeral(monkeypatch, RENDER="true") is True

    def test_fly_is_detected_without_any_configuration(self, monkeypatch):
        # Fly sets FLY_APP_NAME on every machine; without a volume the disk is lost.
        assert self._ephemeral(monkeypatch, FLY_APP_NAME="zema-server") is True

    def test_override_to_persistent_once_a_disk_is_attached(self, monkeypatch):
        assert self._ephemeral(monkeypatch, RENDER="true", DECK_STORAGE="persistent") is False

    def test_override_to_ephemeral_elsewhere(self, monkeypatch):
        assert self._ephemeral(monkeypatch, DECK_STORAGE="ephemeral") is True

    def test_an_unrecognised_override_falls_back_to_detection(self, monkeypatch):
        assert self._ephemeral(monkeypatch, RENDER="true", DECK_STORAGE="banana") is True
