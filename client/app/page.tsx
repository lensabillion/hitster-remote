"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Timeline, { type Card } from "@/components/Timeline";
import Logo from "@/components/Logo";
import { getPlayerName, setPlayerName } from "@/lib/identity";
import Link from "next/link";
import { onRoomJoined, useRoom } from "@/lib/room";
import { ConnectionBanner, ErrorBanner } from "@/components/Banner";

/* Sample timeline, taken from the starter deck so the home page never contradicts
 * the game. The starter years are themselves still unverified -- confirming them
 * is exactly what the deck builder makes a human do. */
const SAMPLE: Card[] = [
  {
    id: "1",
    year: 1969,
    artistAm: "ሙላቱ አስታጥቄ",
    titleAm: "የከርሞ ሰው",
    artistLatin: "Mulatu Astatke",
    titleLatin: "Yekermo Sew",
  },
  {
    id: "2",
    year: 1975,
    artistAm: "ማህሙድ አህመድ",
    titleAm: "እሬ መላ መላ",
    artistLatin: "Mahmoud Ahmed",
    titleLatin: "Ere Mela Mela",
  },
  {
    id: "3",
    year: 1991,
    artistAm: "አስቴር አወቀ",
    titleAm: "ገላ ገላ",
    artistLatin: "Aster Aweke",
    titleLatin: "Gela Gela",
  },
  {
    id: "4",
    year: 2019,
    artistAm: "ሮፍናን",
    titleAm: "ደሴ",
    artistLatin: "Rophnan",
    titleLatin: "Desse",
  },
];

export default function Home() {
  const router = useRouter();
  const { createRoom, joinRoom, error, clearError, connection, connected, serverUrl } =
    useRoom();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  // Guards against a double tap creating two rooms; cleared if the server never
  // answers, so a failed attempt does not lock the button forever.
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!busy) return;
    const t = window.setTimeout(() => setBusy(false), 6000);
    return () => window.clearTimeout(t);
  }, [busy]);

  // The stored name exists only in the browser. Reading it after mount keeps the
  // server and client markup identical; that single setState is the whole effect.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setName(getPlayerName()), []);
  useEffect(() => onRoomJoined((joined) => router.push(`/room/${joined}`)), [router]);

  function remember(value: string) {
    setName(value);
    setPlayerName(value);
  }

  const ready = Boolean(name.trim()) && connected && !busy;

  return (
    <main className="page" style={{ gap: 40, paddingTop: 56 }}>
      <ConnectionBanner connection={connection} serverUrl={serverUrl} />
      <ErrorBanner message={error} onDismiss={clearError} />

      <header className="stack" style={{ gap: 20 }}>
        <Logo />
        <div className="stack" style={{ gap: 4 }}>
          <p className="display am" style={{ fontSize: "var(--t-2xl)", margin: 0 }}>
            ማን ዘፈነው?
          </p>
          <h2 className="h" style={{ fontSize: "var(--t-xl)" }}>
            Who sang it? And when?
          </h2>
        </div>
        <p className="muted" style={{ fontSize: "var(--t-md)" }}>
          A song comes on and the table goes quiet. Name the singer, then slot the song
          into your timeline: before this one, after that one. Your friends hear every
          note, watch you sweat, and wait for their turn to do better.
        </p>
      </header>

      {/* One name field, above both actions. It used to live inside the "create"
          card, so anyone who only wanted to JOIN found the button disabled with no
          visible reason. */}
      <section className="stack" style={{ gap: 16 }}>
        <div className="stack" style={{ maxWidth: 420 }}>
          <label className="label" htmlFor="player-name">
            1 · Your name
          </label>
          <input
            id="player-name"
            className="field"
            placeholder="What should everyone call you?"
            value={name}
            onChange={(e) => remember(e.target.value)}
            autoComplete="off"
            maxLength={40}
          />
        </div>

        <span className="label">2 · Then either</span>

        <div className="grid-2">
          <div className="card stack" style={{ gap: 12 }}>
            <h2 className="h" style={{ fontSize: "var(--t-lg)" }}>
              Start a room
            </h2>
            <p className="hint">You get a four-letter code to send your friends.</p>
            <button
              className="btn"
              disabled={!ready}
              onClick={() => {
                setBusy(true);
                createRoom(name.trim());
              }}
            >
              {busy ? "Creating…" : "Create room"}
            </button>
          </div>

          <div className="card stack" style={{ gap: 12 }}>
            <h2 className="h" style={{ fontSize: "var(--t-lg)" }}>
              Join a room
            </h2>
            <input
              className="field field-code"
              placeholder="CODE"
              maxLength={4}
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              aria-label="Four letter room code"
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
            />
            <button
              className="btn"
              disabled={!ready || code.length !== 4}
              onClick={() => {
                setBusy(true);
                joinRoom(code, name.trim());
              }}
            >
              Join
            </button>
          </div>
        </div>

        {!name.trim() && connected && (
          <p className="hint">Enter your name above to create or join.</p>
        )}
      </section>

      <section className="stack" style={{ gap: 14 }}>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <span className="label">How a turn goes</span>
          <Link href="/deck" className="linkish">
            Edit the deck →
          </Link>
        </div>
        <ol className="steps">
          <li className="step">
            <span className="step-no num">1</span>
            <strong>The song plays.</strong>
            <span className="hint">
              Everyone hears it. Only you answer, and you can answer while it is still
              playing.
            </span>
          </li>
          <li className="step">
            <span className="step-no num">2</span>
            <strong>Name the singer.</strong>
            <span className="hint">
              70 points. Spelling does not count against you; we know how many ways there
              are to write Tilahun.
            </span>
          </li>
          <li className="step">
            <span className="step-no num">3</span>
            <strong>Place it.</strong>
            <span className="hint">
              Before 1992? After 2008? 30 points if the order holds, and a tie can sit on
              either side.
            </span>
          </li>
        </ol>
        <p className="hint" style={{ maxWidth: "58ch" }}>
          A handful of songs each, from the golden era to this year. Highest total wins,
          and knowing the title settles a draw.
        </p>
        <Timeline cards={SAMPLE} interactive />
      </section>
    </main>
  );
}
