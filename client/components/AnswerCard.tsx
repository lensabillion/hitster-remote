"use client";

import { useState } from "react";
import Timeline, { type Card } from "@/components/Timeline";

/* The answer card — the thing that leads the screen on your turn.
 *
 * Open from the moment the clip starts, so you can answer over the music or stop
 * it first. Nothing here waits for the song to finish.
 *
 * Ordered by what it is worth. The singer is 70 points so it comes first and gets
 * the autofocus; the placement is 30; the title scores nothing, so it sits last,
 * smaller, and says "optional" rather than looking compulsory. */

export default function AnswerCard({
  timeline,
  artistPoints,
  yearPoints,
  onSeal,
  sealed,
  sealedAnswer,
}: {
  timeline: Card[];
  artistPoints: number;
  yearPoints: number;
  onSeal: (gap: number, artist: string, title: string) => void;
  sealed: boolean;
  sealedAnswer?: { gap: number; artistGuess: string; titleGuess: string } | null;
}) {
  const [artist, setArtist] = useState("");
  const [title, setTitle] = useState("");
  const [gap, setGap] = useState<number | null>(null);

  if (sealed) {
    return (
      <div className="hero" style={{ borderColor: "var(--green)" }}>
        <span className="label" style={{ color: "var(--green)" }}>
          Answer sealed
        </span>
        <p className="muted" style={{ fontSize: "var(--t-md)" }}>
          You said{" "}
          <strong style={{ color: "var(--ink)" }}>
            {sealedAnswer?.artistGuess || "— nothing —"}
          </strong>
          {sealedAnswer?.titleGuess ? ` · “${sealedAnswer.titleGuess}”` : ""}
        </p>
        <p className="hint">Nothing is revealed until the answer is in.</p>
      </div>
    );
  }

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
        />
      </div>

      <button
        className="btn"
        disabled={gap === null}
        onClick={() => onSeal(gap!, artist.trim(), title.trim())}
        style={{ alignSelf: "flex-start" }}
      >
        {gap === null ? "Pick where it goes first" : "Seal my answer"}
      </button>
    </div>
  );
}
