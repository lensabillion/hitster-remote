"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Timeline, { type Card } from "@/components/Timeline";
import { getPlayerName, setPlayerName } from "@/lib/identity";
import { onRoomJoined, useRoom } from "@/lib/room";

/* Sample timeline for the front page. Real artists with verified Deezer
 * entries; the years are illustrative, and confirming them is exactly what the
 * deck builder makes a human do before a card is playable. */
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
  const router = useRouter();
  const { createRoom, joinRoom, error, connected } = useRoom();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");

  useEffect(() => setName(getPlayerName()), []);
  useEffect(() => onRoomJoined((joined) => router.push(`/room/${joined}`)), [router]);

  function remember(value: string) {
    setName(value);
    setPlayerName(value);
  }

  const field: React.CSSProperties = {
    background: "var(--surface)",
    border: "1px solid var(--rule)",
    borderRadius: "var(--radius)",
    padding: "11px 13px",
    color: "var(--ink)",
    width: "100%",
    outline: "none",
  };

  const canAct = Boolean(name.trim()) && connected;

  const primary: React.CSSProperties = {
    background: "var(--gold)",
    color: "#20170a",
    fontWeight: 700,
    padding: "11px 18px",
    borderRadius: "var(--radius)",
    letterSpacing: "0.02em",
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
          <h1 className="display amharic" style={{ fontSize: "var(--t-3xl)", margin: 0 }}>
            ዜማ
          </h1>
          <span className="display" style={{ fontSize: "var(--t-xl)", color: "var(--gold)" }}>
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
          Take turns. On your turn a song plays: name the singer and slot it into
          your timeline. Everyone hears every song, so you are always listening
          even when it is not your go.
        </p>
      </header>

      <Rule />

      <section style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <span className="label">How it plays</span>
          <p
            style={{
              fontSize: "var(--t-sm)",
              color: "var(--ink-faint)",
              margin: 0,
              maxWidth: "58ch",
            }}
          >
            On your turn: name the singer — worth 70 points — and tap where the song
            belongs on your timeline, worth 30. You can answer while the music is
            still playing, or stop it first. A year that ties with a card already
            down may sit on either side of it.
          </p>
        </div>
        <Timeline cards={SAMPLE} interactive />
      </section>

      <Rule />

      {/* One name field, shared. It previously sat inside the "Start a room"
          card, so anyone who only wanted to JOIN found the button disabled with
          no visible reason. */}
      <section style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 420 }}>
          <label className="label" htmlFor="player-name">
            1 · Your name
          </label>
          <input
            id="player-name"
            style={field}
            placeholder="What should everyone call you?"
            value={name}
            onChange={(e) => remember(e.target.value)}
            autoComplete="off"
          />
        </div>

        <span className="label">2 · Then either</span>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(268px, 1fr))",
            gap: 20,
          }}
        >
          <div
            className="surface"
            style={{ padding: 22, display: "flex", flexDirection: "column", gap: 12 }}
          >
            <h2 className="display" style={{ fontSize: "var(--t-lg)", margin: 0 }}>
              Start a room
            </h2>
            <p style={{ margin: 0, fontSize: "var(--t-sm)", color: "var(--ink-faint)" }}>
              You get a four-letter code to send your friends.
            </p>
            <button
              style={{ ...primary, opacity: canAct ? 1 : 0.45 }}
              disabled={!canAct}
              onClick={() => createRoom(name.trim())}
            >
              Create room
            </button>
          </div>

          <div
            className="surface"
            style={{ padding: 22, display: "flex", flexDirection: "column", gap: 12 }}
          >
            <h2 className="display" style={{ fontSize: "var(--t-lg)", margin: 0 }}>
              Join a room
            </h2>
            <input
              style={{ ...field, letterSpacing: "0.35em", textTransform: "uppercase" }}
              placeholder="CODE"
              maxLength={4}
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              aria-label="Four letter room code"
              autoComplete="off"
            />
            <button
              style={{
                border: "1px solid var(--gold-dim)",
                color: "var(--gold)",
                fontWeight: 600,
                padding: "11px 18px",
                borderRadius: "var(--radius)",
                opacity: canAct && code.length === 4 ? 1 : 0.45,
              }}
              disabled={!canAct || code.length !== 4}
              onClick={() => joinRoom(code, name.trim())}
            >
              Join
            </button>
          </div>
        </div>

        {!name.trim() && (
          <span style={{ fontSize: "var(--t-sm)", color: "var(--ink-faint)" }}>
            Enter your name above to create or join a room.
          </span>
        )}
      </section>

      {error && (
        <p style={{ color: "var(--red)", fontSize: "var(--t-sm)", margin: 0 }}>{error}</p>
      )}
      {!connected && (
        <p style={{ color: "var(--ink-faint)", fontSize: "var(--t-sm)", margin: 0 }}>
          Connecting to the game server…
        </p>
      )}
    </main>
  );
}
