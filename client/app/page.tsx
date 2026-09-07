"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Timeline, { type Card } from "@/components/Timeline";
import { getPlayerName, setPlayerName } from "@/lib/identity";
import { onRoomJoined, useRoom } from "@/lib/room";

/* Sample timeline. Real artists with verified catalogue entries; the years are
 * illustrative, and confirming them is exactly what the deck builder makes a
 * human do before a card is playable. */
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
  const { createRoom, joinRoom, error, connected } = useRoom();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");

  useEffect(() => setName(getPlayerName()), []);
  useEffect(() => onRoomJoined((joined) => router.push(`/room/${joined}`)), [router]);

  function remember(value: string) {
    setName(value);
    setPlayerName(value);
  }

  const ready = Boolean(name.trim()) && connected;

  return (
    <main className="page" style={{ gap: 40, paddingTop: 56 }}>
      <header className="stack" style={{ gap: 14 }}>
        <span className="label">የዜማ ጨዋታ · a music timeline game</span>
        <div className="row" style={{ gap: 16, alignItems: "baseline" }}>
          <h1 className="display am" style={{ fontSize: "var(--t-3xl)", margin: 0 }}>
            ዜማ
          </h1>
          <span className="display" style={{ fontSize: "var(--t-xl)", color: "var(--gold)" }}>
            Zema
          </span>
        </div>
        <p className="muted" style={{ fontSize: "var(--t-md)" }}>
          Take turns. On your turn a song plays: name the singer, and slot it into your
          timeline. Everyone hears every song, so you are always listening — even when it
          is not your go.
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
          />
        </div>

        <span className="label">2 · Then either</span>

        <div className="grid-2">
          <div className="card stack" style={{ gap: 12 }}>
            <h2 className="display" style={{ fontSize: "var(--t-lg)", margin: 0 }}>
              Start a room
            </h2>
            <p className="hint">You get a four-letter code to send your friends.</p>
            <button className="btn" disabled={!ready} onClick={() => createRoom(name.trim())}>
              Create room
            </button>
          </div>

          <div className="card stack" style={{ gap: 12 }}>
            <h2 className="display" style={{ fontSize: "var(--t-lg)", margin: 0 }}>
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
            />
            <button
              className="btn"
              disabled={!ready || code.length !== 4}
              onClick={() => joinRoom(code, name.trim())}
            >
              Join
            </button>
          </div>
        </div>

        {!name.trim() && <p className="hint">Enter your name above to create or join.</p>}
        {!connected && <p className="hint">Connecting to the game server…</p>}
        {error && <p style={{ color: "var(--red)", fontSize: "var(--t-sm)" }}>{error}</p>}
      </section>

      <section className="stack" style={{ gap: 12 }}>
        <span className="label">What a turn looks like</span>
        <p className="hint" style={{ maxWidth: "58ch" }}>
          Name the singer for 70 points, tap where the song belongs for 30. You can answer
          while the music is still playing, or stop it first. A year that ties a card
          already down may sit on either side of it.
        </p>
        <Timeline cards={SAMPLE} interactive />
      </section>
    </main>
  );
}
