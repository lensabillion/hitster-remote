"use client";

import { useState } from "react";
import Timeline, { type Card } from "@/components/Timeline";

/* Sample timeline. These are real artists with verified Deezer catalogue
 * entries; the years are illustrative and are exactly the thing the deck
 * builder makes a human confirm before a card is playable. */
const SAMPLE: Card[] = [
  {
    id: "1",
    year: 1972,
    artistAm: "ሙላቱ አስታጥቄ",
    titleAm: "የከርሞ ሰው",
    artistLatin: "Mulatu Astatke",
    titleLatin: "Yekermo Sew",
  },
  {
    id: "2",
    year: 1975,
    artistAm: "ማህሙድ አህመድ",
    titleAm: "ትዝታ",
    artistLatin: "Mahmoud Ahmed",
    titleLatin: "Tezeta",
  },
  {
    id: "3",
    year: 1991,
    artistAm: "አስቴር አወቀ",
    titleAm: "ይሸበሉ",
    artistLatin: "Aster Aweke",
    titleLatin: "Y'shebellu",
  },
  {
    id: "4",
    year: 2005,
    artistAm: "ቴዲ አፍሮ",
    titleAm: "ጃህ ያስተሰርያል",
    artistLatin: "Teddy Afro",
    titleLatin: "Jah Yastesereyal",
  },
];

function Rule() {
  return (
    <div
      style={{
        height: 1,
        background:
          "linear-gradient(90deg, var(--rule) 0%, var(--gold-dim) 35%, var(--rule) 100%)",
        opacity: 0.6,
      }}
    />
  );
}

export default function Home() {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");

  const field: React.CSSProperties = {
    background: "var(--surface)",
    border: "1px solid var(--rule)",
    borderRadius: "var(--radius)",
    padding: "11px 13px",
    color: "var(--ink)",
    width: "100%",
    outline: "none",
  };

  return (
    <main
      style={{
        position: "relative",
        zIndex: 1,
        maxWidth: 940,
        margin: "0 auto",
        padding: "64px 24px 96px",
        display: "flex",
        flexDirection: "column",
        gap: 56,
      }}
    >
      <header style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <span className="label">የዜማ ጨዋታ · a music timeline game</span>
        <div style={{ display: "flex", alignItems: "baseline", gap: 18, flexWrap: "wrap" }}>
          <h1
            className="display amharic"
            style={{ fontSize: "var(--t-3xl)", margin: 0, color: "var(--ink)" }}
          >
            ዜማ
          </h1>
          <span
            className="display"
            style={{ fontSize: "var(--t-xl)", color: "var(--gold)" }}
          >
            Zema
          </span>
        </div>
        <p
          style={{
            fontSize: "var(--t-md)",
            color: "var(--ink-soft)",
            maxWidth: "54ch",
            margin: 0,
          }}
        >
          Hear a song. Guess when it came out. Slot it into your timeline before
          anyone steals it from you. Everyone places every round, so nobody sits
          waiting for a turn.
        </p>
      </header>

      <Rule />

      <section style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <span className="label">Your timeline</span>
          <p
            style={{
              fontSize: "var(--t-sm)",
              color: "var(--ink-faint)",
              margin: 0,
              maxWidth: "58ch",
            }}
          >
            Tap the space where the song belongs. A year that ties with a card
            already down may sit on either side of it.
          </p>
        </div>
        <Timeline cards={SAMPLE} interactive />
      </section>

      <Rule />

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(268px, 1fr))",
          gap: 20,
        }}
      >
        <div
          className="surface"
          style={{ padding: 22, display: "flex", flexDirection: "column", gap: 14 }}
        >
          <h2
            className="display"
            style={{ fontSize: "var(--t-lg)", margin: 0, color: "var(--ink)" }}
          >
            Start a room
          </h2>
          <input
            style={field}
            placeholder="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            aria-label="Your name"
          />
          <button
            style={{
              background: "var(--gold)",
              color: "#20170a",
              fontWeight: 700,
              padding: "11px 18px",
              borderRadius: "var(--radius)",
              letterSpacing: "0.02em",
            }}
          >
            Create room
          </button>
        </div>

        <div
          className="surface"
          style={{ padding: 22, display: "flex", flexDirection: "column", gap: 14 }}
        >
          <h2
            className="display"
            style={{ fontSize: "var(--t-lg)", margin: 0, color: "var(--ink)" }}
          >
            Join a room
          </h2>
          <input
            style={{ ...field, letterSpacing: "0.35em", textTransform: "uppercase" }}
            placeholder="CODE"
            maxLength={4}
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            aria-label="Four letter room code"
          />
          <button
            style={{
              border: "1px solid var(--gold-dim)",
              color: "var(--gold)",
              fontWeight: 600,
              padding: "11px 18px",
              borderRadius: "var(--radius)",
            }}
          >
            Join
          </button>
        </div>
      </section>
    </main>
  );
}
