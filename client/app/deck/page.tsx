"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { SERVER_URL } from "@/lib/room";
import { getPlayerName } from "@/lib/identity";

/* The deck editor.
 *
 * Every project that builds this game curates its songs by hand — Timtam ships
 * 7,239 entries in a committed YAML file. So the question was never whether to
 * curate manually, only whether the tooling makes it bearable. Editing a TSV in
 * a text editor does not; a page you can open on a phone does, and it lets a
 * player on another continent add the songs they actually grew up with.
 *
 * The year is typed by a person on purpose. No source reports original release
 * years reliably — not Deezer, not MusicBrainz, and not an MP3's DATE tag,
 * which describes the pressing rather than the song. */

type Card = {
  id: string;
  year: number;
  artistLatin: string;
  titleLatin: string;
  artistAm: string;
  titleAm: string;
  youtubeId: string;
  deezerTrackId: number | null;
  addedBy: string;
};

type Candidate = {
  deezerTrackId: number;
  artist: string;
  title: string;
  album: string;
  preview: string;
  artistMatches: boolean;
};

export default function DeckPage() {
  const [cards, setCards] = useState<Card[]>([]);
  const [artist, setArtist] = useState("");
  const [title, setTitle] = useState("");
  const [artistAm, setArtistAm] = useState("");
  const [titleAm, setTitleAm] = useState("");
  const [year, setYear] = useState("");
  const [youtube, setYoutube] = useState("");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [picked, setPicked] = useState<Candidate | null>(null);
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${SERVER_URL}/deck`);
      const d = await r.json();
      setCards(d.cards ?? []);
    } catch {
      setMsg("Can’t reach the server — the deck can’t be loaded.");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function search() {
    setNote("Searching…");
    setCandidates([]);
    setPicked(null);
    try {
      const r = await fetch(
        `${SERVER_URL}/deck/search?artist=${encodeURIComponent(artist)}&title=${encodeURIComponent(title)}`,
      );
      const d = await r.json();
      setCandidates(d.candidates ?? []);
      setNote(d.note ?? "");
    } catch {
      setNote("Search failed. Add a YouTube link instead.");
    }
  }

  async function add() {
    setBusy(true);
    setMsg("");
    try {
      const qs = picked ? `?deezer_track_id=${picked.deezerTrackId}` : "";
      const r = await fetch(`${SERVER_URL}/deck${qs}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          artist_latin: artist.trim(),
          title_latin: title.trim(),
          artist_am: artistAm.trim(),
          title_am: titleAm.trim(),
          year: Number(year),
          youtube_url: youtube.trim(),
          added_by: getPlayerName() || "",
        }),
      });
      const d = await r.json();
      if (!r.ok) {
        setMsg(d.detail ?? "That card was refused.");
      } else {
        setMsg(`Added. The deck now holds ${d.count} cards.`);
        setArtist("");
        setTitle("");
        setArtistAm("");
        setTitleAm("");
        setYear("");
        setYoutube("");
        setCandidates([]);
        setPicked(null);
        setNote("");
        load();
      }
    } catch {
      setMsg("Couldn’t reach the server.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    await fetch(`${SERVER_URL}/deck/${id}`, { method: "DELETE" });
    load();
  }

  const yearNum = Number(year);
  const yearOk = Number.isInteger(yearNum) && yearNum >= 1900 && yearNum <= 2030;
  const hasSource = Boolean(picked) || Boolean(youtube.trim());
  const canAdd = artist.trim() && title.trim() && yearOk && hasSource && !busy;

  return (
    <main className="page">
      <header className="topbar">
        <div className="brand">
          <span className="display am" style={{ fontSize: "var(--t-xl)" }}>
            ዜማ
          </span>
          <span className="label">the deck · {cards.length} cards</span>
        </div>
        <Link href="/" className="linkish">
          Back to the game
        </Link>
      </header>

      <section className="hero">
        <div className="stack" style={{ gap: 4 }}>
          <span className="label">Add a song</span>
          <h2 className="display" style={{ fontSize: "var(--t-xl)", margin: 0 }}>
            What should everyone have to place?
          </h2>
        </div>

        <div className="grid-2">
          <div className="stack">
            <span className="label">Artist — Latin</span>
            <input
              className="field"
              value={artist}
              onChange={(e) => setArtist(e.target.value)}
              placeholder="Mahmoud Ahmed"
              autoComplete="off"
            />
          </div>
          <div className="stack">
            <span className="label">Song — Latin</span>
            <input
              className="field"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ere Mela Mela"
              autoComplete="off"
            />
          </div>
          <div className="stack">
            <span className="label">Artist — አማርኛ, optional</span>
            <input
              className="field am"
              value={artistAm}
              onChange={(e) => setArtistAm(e.target.value)}
              placeholder="ማህሙድ አህመድ"
              autoComplete="off"
            />
          </div>
          <div className="stack">
            <span className="label">Song — አማርኛ, optional</span>
            <input
              className="field am"
              value={titleAm}
              onChange={(e) => setTitleAm(e.target.value)}
              placeholder="እሬ መላ መላ"
              autoComplete="off"
            />
          </div>
        </div>

        <div className="stack" style={{ maxWidth: 260 }}>
          <span className="label">Original release year</span>
          <input
            className="field"
            value={year}
            onChange={(e) => setYear(e.target.value.replace(/[^\d]/g, "").slice(0, 4))}
            placeholder="1975"
            inputMode="numeric"
          />
          <p className="hint">
            The year it first came out — not the year of a reissue or a compilation. No
            database gets this right, which is why you are typing it.
          </p>
        </div>

        <div className="stack">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <span className="label">Where the audio comes from</span>
            <button className="btn-ghost" onClick={search} disabled={!artist.trim()}>
              Search Deezer
            </button>
          </div>

          {note && <p className="hint">{note}</p>}

          {candidates.length > 0 && (
            <div className="stack" style={{ gap: 6 }}>
              {candidates.map((c) => (
                <button
                  key={c.deezerTrackId}
                  onClick={() => setPicked(c)}
                  className="card"
                  style={{
                    textAlign: "left",
                    padding: "10px 14px",
                    cursor: "pointer",
                    borderColor:
                      picked?.deezerTrackId === c.deezerTrackId
                        ? "var(--gold)"
                        : "var(--rule)",
                  }}
                >
                  <div className="row" style={{ gap: 8 }}>
                    <strong style={{ color: "var(--ink)" }}>{c.artist}</strong>
                    <span style={{ color: "var(--ink-soft)" }}>{c.title}</span>
                    {!c.artistMatches && (
                      <span className="pill pill-bad">different artist?</span>
                    )}
                    {picked?.deezerTrackId === c.deezerTrackId && (
                      <span className="pill pill-gold">chosen</span>
                    )}
                  </div>
                  <span className="hint">{c.album}</span>
                </button>
              ))}
              <p className="hint">
                Listen before choosing if you are unsure — a wrong pick plays a different
                song mid-game and nobody will know why.
              </p>
            </div>
          )}

          <div className="stack">
            <span className="label">…or a YouTube link</span>
            <input
              className="field"
              value={youtube}
              onChange={(e) => setYoutube(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=…"
              autoComplete="off"
            />
            <p className="hint">
              Needed for songs Deezer does not carry — which is most of the ones only
              found on YouTube.
            </p>
          </div>
        </div>

        <div className="row" style={{ gap: 12 }}>
          <button className="btn" disabled={!canAdd} onClick={add}>
            {busy ? "Adding…" : "Add to the deck"}
          </button>
          {!hasSource && (artist.trim() || title.trim()) && (
            <span className="hint">Pick a Deezer match or paste a YouTube link.</span>
          )}
          {year && !yearOk && <span className="hint">Year looks wrong.</span>}
        </div>

        {msg && <p style={{ margin: 0, color: "var(--gold)" }}>{msg}</p>}
      </section>

      <section className="stack">
        <span className="label">In the deck</span>
        {cards.length === 0 && <p className="hint">Nothing yet.</p>}
        {cards.map((c) => (
          <div
            key={c.id}
            className="row"
            style={{
              gap: 12,
              padding: "10px 0",
              borderTop: "1px solid var(--rule-soft)",
            }}
          >
            <span className="score-val" style={{ minWidth: 56 }}>
              {c.year}
            </span>
            <div className="stack" style={{ gap: 0, flex: 1, minWidth: 160 }}>
              <span className="am" style={{ color: "var(--ink)" }}>
                {c.artistAm || c.artistLatin} — {c.titleAm || c.titleLatin}
              </span>
              <span className="hint">
                {c.artistLatin} — {c.titleLatin}
                {c.addedBy ? ` · added by ${c.addedBy}` : ""}
              </span>
            </div>
            <span className="pill">
              {c.deezerTrackId && c.youtubeId
                ? "deezer + youtube"
                : c.deezerTrackId
                  ? "deezer"
                  : "youtube"}
            </span>
            <button className="linkish" onClick={() => remove(c.id)}>
              Remove
            </button>
          </div>
        ))}
      </section>
    </main>
  );
}
