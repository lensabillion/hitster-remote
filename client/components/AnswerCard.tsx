"use client";

import { useState } from "react";
import Timeline, { type Card } from "@/components/Timeline";

/* The answer card.
 *
 * Open from the moment the clip starts, so you can answer over the music or
 * stop it and answer afterwards. Nothing here waits for the song to finish.
 *
 * Weighting follows the grade: the singer is most of the game, the year is the
 * rest, and the song title is captured but scores nothing -- so it is last,
 * smallest, and marked optional rather than sitting there looking compulsory.
 *
 * Artist is typed in Latin script deliberately. Amharic titles have no agreed
 * Latin spelling, so the server matches generously: "Telahun Gesesse" and
 * "Gessesse" both count for Tilahun Gessesse. */

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

  const field: React.CSSProperties = {
    background: "var(--ground)",
    border: "1px solid var(--rule)",
    borderRadius: "var(--radius)",
    padding: "11px 13px",
    color: "var(--ink)",
    width: "100%",
    outline: "none",
  };

  if (sealed) {
    return (
      <div
        className="surface"
        style={{
          padding: 20,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          borderColor: "var(--verd)",
        }}
      >
        <span className="label" style={{ color: "var(--verd)" }}>
          Sealed — waiting for the others
        </span>
        <span style={{ color: "var(--ink-soft)" }}>
          You said{" "}
          <strong style={{ color: "var(--ink)" }}>
            {sealedAnswer?.artistGuess || "— no artist —"}
          </strong>
          {sealedAnswer?.titleGuess ? ` · “${sealedAnswer.titleGuess}”` : ""}
        </span>
        <span style={{ fontSize: "var(--t-xs)", color: "var(--ink-faint)" }}>
          Nothing is revealed until everyone has answered.
        </span>
      </div>
    );
  }

  const canSeal = gap !== null;

  return (
    <div
      className="surface"
      style={{ padding: 20, display: "flex", flexDirection: "column", gap: 20 }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <span className="label">Who sang it?</span>
          <span className="label" style={{ color: "var(--gold)" }}>
            {artistPoints} pts
          </span>
        </div>
        <input
          style={field}
          placeholder="Artist name, in Latin letters"
          value={artist}
          onChange={(e) => setArtist(e.target.value)}
          aria-label="Artist name"
          autoComplete="off"
          autoFocus
        />
        <span style={{ fontSize: "var(--t-xs)", color: "var(--ink-faint)" }}>
          Spelling is forgiving — “Telahun Gesesse” or just “Gessesse” both count.
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <span className="label">When? Tap where it goes</span>
          <span className="label" style={{ color: "var(--gold)" }}>
            {yearPoints} pts
          </span>
        </div>
        <Timeline cards={timeline} interactive onPlace={setGap} />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <span className="label">Song title — optional, not scored</span>
        <input
          style={{ ...field, padding: "9px 13px", fontSize: "var(--t-sm)" }}
          placeholder="If you know it"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          aria-label="Song title, optional"
          autoComplete="off"
        />
      </div>

      <button
        disabled={!canSeal}
        onClick={() => onSeal(gap!, artist.trim(), title.trim())}
        style={{
          background: canSeal ? "var(--gold)" : "var(--surface-lift)",
          color: canSeal ? "#20170a" : "var(--ink-faint)",
          fontWeight: 700,
          padding: "12px 20px",
          borderRadius: "var(--radius)",
          alignSelf: "flex-start",
          cursor: canSeal ? "pointer" : "not-allowed",
        }}
      >
        {canSeal ? "Seal my answer" : "Pick where it goes first"}
      </button>
    </div>
  );
}
