"use client";

import { useState } from "react";
import Timeline, { type Card } from "@/components/Timeline";

/* The answer card — the thing that leads the screen on your turn.
 *
 * Open from the moment the clip starts, so you can answer over the music or stop
 * it first. Nothing here waits for the song to finish.
 *
 * Ordered by what it is worth. The singer is 70 points so it comes first; the
 * placement is 30; the title scores nothing, so it sits last, smaller, and says
 * "optional" rather than looking compulsory. Nothing autofocuses: on a phone the
 * keyboard would cover the timeline you need to tap.
 *
 * The turn resolves the moment the answer is sealed, so this card is replaced by
 * the reveal rather than by a "waiting" state. */

export default function AnswerCard({
  timeline,
  artistPoints,
  yearPoints,
  onSeal,
  onDecline,
}: {
  timeline: Card[];
  artistPoints: number;
  yearPoints: number;
  onSeal: (gap: number, artist: string, title: string) => void;
  onDecline: () => void;
}) {
  const [artist, setArtist] = useState("");
  const [title, setTitle] = useState("");
  const [gap, setGap] = useState<number | null>(null);

  return (
    <div className="hero">
      <div className="stack" style={{ gap: 4 }}>
        <span className="label" style={{ color: "var(--gold)" }}>
          Your turn
        </span>
        <h2 className="display" style={{ fontSize: "var(--t-xl)", margin: 0 }}>
          Who sang it, and when?
        </h2>
      </div>

      <div className="stack">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <span className="label">1 · The singer</span>
          <span className="pill pill-gold">{artistPoints} points</span>
        </div>
        <input
          className="field"
          placeholder="Artist name, in Latin letters"
          value={artist}
          onChange={(e) => setArtist(e.target.value)}
          aria-label="Artist name"
          autoComplete="off"
          maxLength={120}
        />
        <p className="hint">
          Spelling is forgiving — “Telahun Gesesse” or just “Gessesse” both count.
        </p>
      </div>

      <div className="stack">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <span className="label">2 · Where it goes</span>
          <span className="pill pill-gold">{yearPoints} points</span>
        </div>
        <Timeline cards={timeline} interactive onPlace={setGap} />
        <p className="hint">
          Tap a gap. If the year ties one already down, either side counts.
        </p>
      </div>

      <div className="stack">
        <span className="label">3 · Song title — optional, not scored</span>
        <input
          className="field"
          style={{ fontSize: "var(--t-sm)", padding: "10px 14px" }}
          placeholder="If you know it"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          aria-label="Song title, optional"
          autoComplete="off"
          maxLength={120}
        />
      </div>

      <div className="row" style={{ gap: 12 }}>
        <button
          className="btn"
          disabled={gap === null}
          onClick={() => gap !== null && onSeal(gap, artist.trim(), title.trim())}
        >
          {gap === null ? "Pick where it goes first" : "Seal my answer"}
        </button>
        {/* Always available. Passing scores zero, but it ends the turn straight
            away rather than leaving everyone waiting on the clock. */}
        <button className="btn-ghost" onClick={onDecline}>
          I don’t know — pass
        </button>
      </div>
    </div>
  );
}
