"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { SERVER_URL } from "@/lib/room";
import { getPlayerName } from "@/lib/identity";
import UnsavedBanner, { type Storage, type Unsaved } from "@/components/UnsavedBanner";
import Logo from "@/components/Logo";

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
 * which describes the pressing rather than the song. The harvest proposes
 * years in bulk; this page is where a person confirms them, one tap each.
 *
 * So the list leads, with the unchecked years at the top, and adding a song is
 * folded away behind one button: with a few hundred cards in the deck,
 * confirming is the everyday job and adding is the occasional one. */

type Card = {
  id: string;
  year: number;
  yearConfirmed: boolean;
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

const EARLIEST_YEAR = 1900;
const LATEST_YEAR = new Date().getFullYear();

/* The server may require a shared secret for edits (DECK_TOKEN). It arrives once
 * as /deck?token=… and is remembered, so a link from the host is all it takes. */
const TOKEN_KEY = "zema.deckToken";

function rememberToken(): string {
  try {
    const fromUrl = new URLSearchParams(window.location.search).get("token");
    if (fromUrl) localStorage.setItem(TOKEN_KEY, fromUrl);
    return fromUrl ?? localStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

function validYear(text: string): number | null {
  const n = Number(text);
  return Number.isInteger(n) && n >= EARLIEST_YEAR && n <= LATEST_YEAR ? n : null;
}

/* One card in the list. An unconfirmed year is an open question with the
 * answer prefilled: fix it or just agree, either way one tap, and the song joins
 * the deal. A confirmed one
 * can still be reopened. */
function CardRow({
  card,
  onConfirm,
  onRemove,
}: {
  card: Card;
  onConfirm: (card: Card, year: number) => Promise<void>;
  onRemove: (card: Card) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [year, setYear] = useState(String(card.year));
  const [busy, setBusy] = useState(false);
  const open = !card.yearConfirmed || editing;
  const yearNum = validYear(year);
  const source =
    card.deezerTrackId && card.youtubeId
      ? "deezer + youtube"
      : card.deezerTrackId
        ? "deezer"
        : "youtube";

  async function confirm() {
    if (yearNum === null) return;
    setBusy(true);
    await onConfirm(card, yearNum);
    setBusy(false);
    setEditing(false);
  }

  return (
    <div className="deck-row">
      {open ? (
        <input
          className="field field-year"
          value={year}
          onChange={(e) => setYear(e.target.value.replace(/[^\d]/g, "").slice(0, 4))}
          onKeyDown={(e) => e.key === "Enter" && confirm()}
          inputMode="numeric"
          aria-label={`Year for ${card.artistLatin} — ${card.titleLatin}`}
        />
      ) : (
        <span className="score-val" style={{ paddingLeft: 4 }}>
          {card.year}
        </span>
      )}
      <div className="stack" style={{ gap: 0, minWidth: 0 }}>
        <span className="am">
          {card.artistAm || card.artistLatin} — {card.titleAm || card.titleLatin}
        </span>
        <span className="hint">
          {card.artistLatin} — {card.titleLatin}
          {card.addedBy ? ` · added by ${card.addedBy}` : ""}
        </span>
      </div>
      <div className="deck-row-actions">
        <span className="pill">{source}</span>
        {open ? (
          <button className="btn-line" onClick={confirm} disabled={busy || yearNum === null}>
            {busy ? "Saving…" : yearNum === card.year ? "Confirm" : "Fix year"}
          </button>
        ) : (
          <>
            <span className="pill pill-good" title="A person has checked this year">
              ✓ year
            </span>
            <button className="linkish" onClick={() => setEditing(true)}>
              Edit
            </button>
          </>
        )}
        <button className="linkish" onClick={() => onRemove(card)}>
          Remove
        </button>
      </div>
    </div>
  );
}

export default function DeckPage() {
  const [cards, setCards] = useState<Card[]>([]);
  const [loaded, setLoaded] = useState(false);
  /* Ids that were unconfirmed when this page first saw them. They stay at the
     top of the list after being confirmed, so the row you just tapped does not
     jump away and the next one is right below it. A reload re-sorts. */
  const [queue, setQueue] = useState<Set<string>>(() => new Set());
  const [adding, setAdding] = useState(false);
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
  const [storage, setStorage] = useState<Storage>("persistent");
  const [unsaved, setUnsaved] = useState<Unsaved | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [token, setToken] = useState("");
  const [filter, setFilter] = useState("");
  const [onlyUnconfirmed, setOnlyUnconfirmed] = useState(false);

  const withToken = (path: string) =>
    `${SERVER_URL}${path}${token ? `?token=${encodeURIComponent(token)}` : ""}`;

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${SERVER_URL}/deck`);
      if (!r.ok) throw new Error(String(r.status));
      const d = await r.json();
      const fresh: Card[] = d.cards ?? [];
      setCards(fresh);
      setQueue((prev) => {
        const next = new Set(prev);
        for (const c of fresh) if (!c.yearConfirmed) next.add(c.id);
        return next;
      });
      setStorage(d.storage === "ephemeral" ? "ephemeral" : "persistent");
      setUnsaved(d.unsaved ?? null);
      setLoaded(true);
      // An empty deck has nothing to confirm, so the form is the only job.
      if (fresh.length === 0) setAdding(true);
    } catch {
      setMsg("Can’t reach the server — the deck can’t be loaded.");
    }
  }, []);

  useEffect(() => {
    // The token comes from the page URL or browser storage, neither of which the
    // server render can see; reading it after mount keeps the markup identical.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setToken(rememberToken());
    load();
  }, [load]);

  function explainRefusal(status: number, detail: string | undefined) {
    if (status === 403) {
      setMsg(
        "This server only lets people with the deck token edit the deck. Open the /deck?token=… link the host shared.",
      );
    } else {
      setMsg(detail ?? "That was refused.");
    }
  }

  /* Hands over the live deck in exactly the form `build_deck.py export` writes,
     so committing it produces a diff of real changes only. */
  async function download() {
    setDownloading(true);
    try {
      const r = await fetch(`${SERVER_URL}/deck/export`);
      if (!r.ok) throw new Error(String(r.status));
      const blob = new Blob([await r.text()], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "deck.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setMsg(
        "Downloaded. Save it as server/decks/deck.json and commit it — the warning clears once that version is deployed.",
      );
    } catch {
      setMsg("Couldn’t download the deck — the server didn’t answer.");
    } finally {
      setDownloading(false);
    }
  }

  async function search() {
    setNote("Searching…");
    setCandidates([]);
    setPicked(null);
    try {
      const params = new URLSearchParams({ artist, title });
      const r = await fetch(`${SERVER_URL}/deck/search?${params}`);
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
      const r = await fetch(withToken("/deck"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          artist_latin: artist.trim(),
          title_latin: title.trim(),
          artist_am: artistAm.trim(),
          title_am: titleAm.trim(),
          year: Number(year),
          youtube_url: youtube.trim(),
          deezer_track_id: picked?.deezerTrackId ?? null,
          added_by: getPlayerName(),
        }),
      });
      const d = await r.json();
      if (!r.ok) {
        explainRefusal(r.status, typeof d.detail === "string" ? d.detail : undefined);
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

  /* Confirming is one PATCH: the year the person settled on, flagged checked. */
  async function confirm(card: Card, fixedYear: number) {
    setMsg("");
    try {
      const r = await fetch(withToken(`/deck/${card.id}`), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year: fixedYear, year_confirmed: true }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        explainRefusal(r.status, typeof d.detail === "string" ? d.detail : undefined);
        return;
      }
      // Patch the row in place rather than reloading: the list must not jump
      // while someone is working down it.
      setCards((all) =>
        all.map((c) => (c.id === card.id ? { ...c, year: fixedYear, yearConfirmed: true } : c)),
      );
      load();
    } catch {
      setMsg("Couldn’t reach the server.");
    }
  }

  async function remove(card: Card) {
    if (!window.confirm(`Remove “${card.artistLatin} — ${card.titleLatin}” from the deck?`)) {
      return;
    }
    try {
      const r = await fetch(withToken(`/deck/${card.id}`), { method: "DELETE" });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        explainRefusal(r.status, typeof d.detail === "string" ? d.detail : undefined);
      }
    } catch {
      setMsg("Couldn’t reach the server.");
    }
    load();
  }

  const yearNum = Number(year);
  const yearOk = Number.isInteger(yearNum) && yearNum >= EARLIEST_YEAR && yearNum <= LATEST_YEAR;
  const hasSource = Boolean(picked) || Boolean(youtube.trim());
  const canAdd = artist.trim() && title.trim() && yearOk && hasSource && !busy;

  const unconfirmedCount = cards.filter((c) => !c.yearConfirmed).length;
  const shown = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    const matching = cards.filter((c) => {
      if (onlyUnconfirmed && c.yearConfirmed) return false;
      if (!needle) return true;
      return [c.artistLatin, c.titleLatin, c.artistAm, c.titleAm, String(c.year)]
        .join(" ")
        .toLowerCase()
        .includes(needle);
    });
    // The server sends year order; keep it, with the queue partitioned to the top.
    return [...matching.filter((c) => queue.has(c.id)), ...matching.filter((c) => !queue.has(c.id))];
  }, [cards, filter, onlyUnconfirmed, queue]);

  return (
    <main className="page">
      <header className="topbar">
        <div className="brand">
          <Logo compact />
          <span className="label">the deck</span>
        </div>
        <Link href="/" className="linkish">
          Back to the game
        </Link>
      </header>

      <UnsavedBanner
        storage={storage}
        unsaved={unsaved}
        onDownload={download}
        downloading={downloading}
      />

      {msg && (
        <div className="banner" role="status">
          <span style={{ flex: 1 }}>{msg}</span>
          <button className="linkish" onClick={() => setMsg("")}>
            Dismiss
          </button>
        </div>
      )}

      <section className="stack" style={{ gap: 16 }}>
        <div className="row" style={{ justifyContent: "space-between", gap: 12 }}>
          <div className="stack" style={{ gap: 2 }}>
            <span className="label">In the deck</span>
            <h2 className="h" style={{ fontSize: "var(--t-2xl)" }}>
              {loaded ? `${cards.length} ${cards.length === 1 ? "song" : "songs"}` : "Loading…"}
            </h2>
          </div>
          <button
            className={adding ? "btn-ghost" : "btn"}
            onClick={() => setAdding((a) => !a)}
            aria-expanded={adding}
            aria-controls="add-song"
          >
            {adding ? "Close the form" : "Add a song"}
          </button>
        </div>

        {adding && (
          <section className="hero" id="add-song" aria-labelledby="add-heading">
            <div className="stack" style={{ gap: 4 }}>
              <span className="label">Add a song</span>
              <h3 id="add-heading" className="h" style={{ fontSize: "var(--t-xl)" }}>
                What should everyone have to place?
              </h3>
            </div>

            <div className="grid-2">
              <div className="stack">
                <label className="label" htmlFor="add-artist">
                  Artist — Latin
                </label>
                <input
                  id="add-artist"
                  className="field"
                  value={artist}
                  onChange={(e) => setArtist(e.target.value)}
                  placeholder="Mahmoud Ahmed"
                  autoComplete="off"
                  maxLength={160}
                />
              </div>
              <div className="stack">
                <label className="label" htmlFor="add-title">
                  Song — Latin
                </label>
                <input
                  id="add-title"
                  className="field"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Ere Mela Mela"
                  autoComplete="off"
                  maxLength={160}
                />
              </div>
              <div className="stack">
                <label className="label" htmlFor="add-artist-am">
                  Artist — አማርኛ, optional
                </label>
                <input
                  id="add-artist-am"
                  className="field am"
                  value={artistAm}
                  onChange={(e) => setArtistAm(e.target.value)}
                  placeholder="ማህሙድ አህመድ"
                  autoComplete="off"
                  maxLength={200}
                />
              </div>
              <div className="stack">
                <label className="label" htmlFor="add-title-am">
                  Song — አማርኛ, optional
                </label>
                <input
                  id="add-title-am"
                  className="field am"
                  value={titleAm}
                  onChange={(e) => setTitleAm(e.target.value)}
                  placeholder="እሬ መላ መላ"
                  autoComplete="off"
                  maxLength={200}
                />
              </div>
            </div>

            <div className="stack" style={{ maxWidth: 260 }}>
              <label className="label" htmlFor="add-year">
                Original release year
              </label>
              <input
                id="add-year"
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
                  {candidates.map((c) => {
                    const chosen = picked?.deezerTrackId === c.deezerTrackId;
                    return (
                      <button
                        key={c.deezerTrackId}
                        onClick={() => setPicked(c)}
                        className={`choice${chosen ? " choice-on" : ""}`}
                        aria-pressed={chosen}
                      >
                        <span className="row" style={{ gap: 8 }}>
                          <strong>{c.artist}</strong>
                          <span className="soft">{c.title}</span>
                          {!c.artistMatches && (
                            <span className="pill pill-bad">different artist?</span>
                          )}
                          {chosen && <span className="pill pill-accent">chosen</span>}
                        </span>
                        <span className="hint">{c.album}</span>
                      </button>
                    );
                  })}
                  <p className="hint">
                    Listen before choosing if you are unsure — a wrong pick plays a different
                    song mid-game and nobody will know why.
                  </p>
                </div>
              )}

              <div className="stack">
                <label className="label" htmlFor="add-youtube">
                  …or a YouTube link
                </label>
                <input
                  id="add-youtube"
                  className="field"
                  value={youtube}
                  onChange={(e) => setYoutube(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=…"
                  autoComplete="off"
                  maxLength={300}
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
          </section>
        )}

        <div className="row" style={{ justifyContent: "space-between", gap: 12 }}>
          <div className="row" style={{ gap: 10 }}>
            {unconfirmedCount > 0 ? (
              <span className="pill pill-accent">
                {unconfirmedCount} {unconfirmedCount === 1 ? "song waits" : "songs wait"} for a
                confirmed year before they are dealt
              </span>
            ) : (
              cards.length > 0 && <span className="pill pill-good">every year confirmed</span>
            )}
          </div>
          <div className="row" style={{ gap: 8 }}>
            <input
              className="field"
              style={{ width: 240 }}
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Find an artist, song or year"
              aria-label="Filter the deck"
              autoComplete="off"
            />
            <button
              className={`chip${onlyUnconfirmed ? " chip-on" : ""}`}
              aria-pressed={onlyUnconfirmed}
              onClick={() => setOnlyUnconfirmed((v) => !v)}
            >
              needs a look
            </button>
          </div>
        </div>
        {unconfirmedCount > 0 && (
          <p className="hint">
            A year without a tick was proposed by the harvest or guessed, not checked. The
            game plays it as is; confirm it, or fix it first — one tap either way. Unchecked
            years are listed first.
          </p>
        )}
        {loaded && cards.length === 0 && <p className="hint">Nothing yet.</p>}
        {cards.length > 0 && shown.length === 0 && <p className="hint">Nothing matches.</p>}
        <div>
          {shown.map((c) => (
            <CardRow key={c.id} card={c} onConfirm={confirm} onRemove={remove} />
          ))}
        </div>
      </section>
    </main>
  );
}
