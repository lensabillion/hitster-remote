"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AnswerCard from "@/components/AnswerCard";
import Logo from "@/components/Logo";
import AudioClip from "@/components/AudioClip";
import Countdown from "@/components/Countdown";
import Timeline from "@/components/Timeline";
import { getPlayerName, setPlayerName } from "@/lib/identity";
import { SERVER_URL, useRoom, type PlayerView, type RoomState } from "@/lib/room";
import { ConnectionBanner, ErrorBanner } from "@/components/Banner";

/* How many songs each player gets. Four is a half-hour game for three people;
   the host can go shorter or longer. The server deals a whole number of
   turns each, so this is multiplied by the seats at the table. */
const SONGS_EACH = [2, 3, 4, 5, 6, 8];
const DEFAULT_SONGS_EACH = 4;

type Tone = "" | "accent" | "good" | "bad";
const Pill = ({ children, tone = "" }: { children: React.ReactNode; tone?: Tone }) => (
  <span className={`pill${tone ? ` pill-${tone}` : ""}`}>{children}</span>
);

function Scoreboard({ state }: { state: RoomState }) {
  return (
    <div className="scores">
      {state.standings.map((p, i) => (
        <div
          key={p.id}
          className={`score${i === 0 && p.score > 0 ? " score-lead" : ""}${
            p.id === state.viewerId ? " score-you" : ""
          }`}
        >
          <span className="score-name">
            {p.name}
            {p.id === state.viewerId ? " (you)" : ""}
          </span>
          <span className="score-val">{p.score}</span>
          {p.titleHits > 0 && (
            <span
              className="pill"
              title={`${p.titleHits} song title${p.titleHits === 1 ? "" : "s"} named — breaks a tie`}
            >
              ♪{p.titleHits}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function PlayerRow({ player, state }: { player: PlayerView; state: RoomState }) {
  // The server keeps activePlayerId set before the first round and after the
  // last, but a turn only exists while a song is being answered or revealed.
  const hasTurn = state.phase === "answering" || state.phase === "revealing";
  const isActive = hasTurn && state.activePlayerId === player.id;
  // At the reveal, pick out the card that just landed on the active timeline.
  // Only a kept card is on it, and the server has revealed it by then.
  const landed =
    state.phase === "revealing" && isActive && state.outcome?.keptCard
      ? state.card?.id
      : undefined;
  return (
    <div className={`player${isActive ? " player-active" : ""}`}>
      <div className="player-head">
        <span className="player-name">
          {player.name}
          {player.id === state.viewerId ? " (you)" : ""}
        </span>
        {isActive && <Pill tone="accent">their turn</Pill>}
        {player.isHost && <Pill>host</Pill>}
        {!player.connected && <Pill tone="bad">offline</Pill>}
        <span className="hint" style={{ marginLeft: "auto" }}>
          {player.score} pts · {player.timeline.length}{" "}
          {player.timeline.length === 1 ? "card" : "cards"}
        </span>
      </div>
      <Timeline cards={player.timeline} highlightId={landed} />
    </div>
  );
}

/* Someone who followed an invite link straight here has never been asked their
   name. Ask before joining, rather than seating them as "Player". */
function NameGate({ code, onDone }: { code: string; onDone: (name: string) => void }) {
  const [draft, setDraft] = useState("");
  const ready = Boolean(draft.trim());
  return (
    <section className="hero" style={{ maxWidth: 480 }}>
      <div className="stack" style={{ gap: 6 }}>
        <span className="label">Joining room {code}</span>
        <h2 className="h" style={{ fontSize: "var(--t-xl)" }}>
          What should everyone call you?
        </h2>
      </div>
      <form
        className="stack"
        onSubmit={(e) => {
          e.preventDefault();
          if (ready) onDone(draft.trim());
        }}
      >
        <label className="label" htmlFor="gate-name">
          Your name
        </label>
        <input
          id="gate-name"
          className="field"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          autoComplete="off"
          maxLength={40}
          autoFocus
        />
        <button className="btn" type="submit" disabled={!ready} style={{ alignSelf: "flex-start" }}>
          Join the room
        </button>
      </form>
    </section>
  );
}

export default function RoomPage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = use(params);
  const roomCode = code.toUpperCase();
  const router = useRouter();
  const {
    state, audio, error, clearError, connection, connected, serverUrl,
    joinRoom, startGame, answer, decline, nextRound,
  } = useRoom();
  const [songsEach, setSongsEach] = useState(DEFAULT_SONGS_EACH);
  const [deckSize, setDeckSize] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  // null until read after mount: the stored name exists only in the browser,
  // so reading it during render would make server and client markup differ.
  const [name, setName] = useState<string | null>(null);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setName(getPlayerName()), []);

  // Join once named, and rejoin on every reconnect. Identity is durable, so the
  // server puts us back in the same seat with our score and timeline.
  useEffect(() => {
    if (connected && name) joinRoom(roomCode, name);
  }, [connected, roomCode, joinRoom, name]);

  // How many songs there are to draw from, so the lobby can point at /deck when
  // it is thin. One fetch; the deck does not change mid-lobby.
  const inLobby = state?.phase === "lobby";
  useEffect(() => {
    if (!inLobby || !connected) return;
    let cancelled = false;
    fetch(`${SERVER_URL}/health`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!cancelled && d && typeof d.cards === "number") setDeckSize(d.cards);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [inLobby, connected]);

  async function copyInvite(roomCodeToShare: string) {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/room/${roomCodeToShare}`);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* no clipboard access: the code is on screen to read out instead */
    }
  }

  if (name === "") {
    return (
      <main className="page">
        <ConnectionBanner connection={connection} serverUrl={serverUrl} />
        <NameGate
          code={roomCode}
          onDone={(chosen) => {
            setPlayerName(chosen);
            setName(chosen);
          }}
        />
      </main>
    );
  }

  // No room state yet. Previously this said "Joining XXXX…" forever when the
  // code was wrong, because the error toast faded after five seconds and there
  // was no way back to the home page.
  if (!state) {
    return (
      <main className="page">
        <ConnectionBanner connection={connection} serverUrl={serverUrl} />
        <ErrorBanner message={error} onDismiss={clearError} />
        {connected && !error && <p className="muted">Joining {roomCode}…</p>}
        {error && (
          <button className="btn" style={{ alignSelf: "flex-start" }} onClick={() => router.push("/")}>
            Back to the start
          </button>
        )}
      </main>
    );
  }

  const you = state.players.find((p) => p.id === state.viewerId);
  const isHost = state.hostId === state.viewerId;
  const outcome = state.outcome;
  // The rules own these numbers; the page only renders them.
  const { artistPoints, yearPoints } = state;
  const activeName =
    state.players.find((p) => p.id === state.activePlayerId)?.name ?? "Someone";
  const hostName = state.players.find((p) => p.isHost)?.name ?? "the host";
  const connectedCount = state.players.filter((p) => p.connected).length;

  return (
    <main className="page">
      <header className="topbar">
        <div className="brand">
          <Logo compact />
          <span className="code">{state.code}</span>
        </div>
        <div className="row">
          {state.phase !== "lobby" && (
            <Pill>
              round {state.roundNo} / {state.roundsPlanned}
            </Pill>
          )}
          {state.phase === "answering" && <Countdown endsAt={state.answerEndsAt} />}
          <Pill tone={connected ? "good" : "bad"}>
            {connected ? "connected" : "reconnecting"}
          </Pill>
          <button className="linkish" onClick={() => router.push("/")}>
            Leave
          </button>
        </div>
      </header>

      <ConnectionBanner connection={connection} serverUrl={serverUrl} />
      <ErrorBanner message={error} onDismiss={clearError} />

      {state.phase !== "lobby" && <Scoreboard state={state} />}

      {/* ---------- lobby ---------- */}
      {state.phase === "lobby" && (
        <section className="hero">
          <div className="row" style={{ justifyContent: "space-between", gap: 16 }}>
            <h2 className="h" style={{ fontSize: "var(--t-2xl)" }}>
              Share the code{" "}
              <span className="accent num" style={{ letterSpacing: "0.1em" }}>
                {state.code}
              </span>
            </h2>
            <button className="btn-ghost" onClick={() => copyInvite(state.code)}>
              {copied ? "Copied" : "Copy invite link"}
            </button>
          </div>

          <div className="row">
            {state.players.map((p) => (
              <span key={p.id} className="score">
                <span className="score-name">{p.name}</span>
                {!p.connected && <Pill tone="bad">offline</Pill>}
              </span>
            ))}
          </div>

          {isHost ? (
            <div className="stack" style={{ gap: 14 }}>
              <div className="row" style={{ gap: 12 }}>
                <span className="label" id="songs-each-label">
                  Songs each
                </span>
                <div className="row" style={{ gap: 6 }} role="group" aria-labelledby="songs-each-label">
                  {SONGS_EACH.map((n) => (
                    <button
                      key={n}
                      className={`chip${n === songsEach ? " chip-on" : ""}`}
                      onClick={() => setSongsEach(n)}
                      aria-pressed={n === songsEach}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>
              <button
                className="btn"
                style={{ alignSelf: "flex-start" }}
                onClick={() => startGame(state.code, songsEach * state.players.length)}
                disabled={connectedCount < 2}
              >
                {connectedCount < 2 ? "Need one more player" : "Start the game"}
              </button>
              {deckSize !== null && deckSize < songsEach * state.players.length + 12 && (
                <p className="hint">
                  Not many songs for that many rounds.{" "}
                  <Link href="/deck" className="link">
                    Add some
                  </Link>
                </p>
              )}
            </div>
          ) : (
            <p className="hint">Waiting for {hostName} to start.</p>
          )}
        </section>
      )}

      {/* The clip outlives the answer: it keeps playing through the reveal, so
          the name lands while the song is still in the air. */}
      {(state.phase === "answering" || state.phase === "revealing") && (
        <div className="card" style={{ padding: "12px 20px" }}>
          <AudioClip cue={audio} />
        </div>
      )}

      {/* ---------- answering ---------- */}
      {state.phase === "answering" && you && (
        <>
          {state.isMyTurn ? (
            <AnswerCard
              key={state.roundNo}
              timeline={you.timeline}
              artistPoints={artistPoints}
              yearPoints={yearPoints}
              onSeal={(gap, artistGuess, titleGuess) =>
                answer(state.code, gap, artistGuess, titleGuess)
              }
              onDecline={() => decline(state.code)}
            />
          ) : (
            /* Watching. They hear the same clip and answer on their own turn. */
            <section className="hero">
              <span className="label">Listening</span>
              <h2 className="h" style={{ fontSize: "var(--t-2xl)" }}>
                <span className="accent">{activeName}</span> is on the spot
              </h2>
              <p className="muted">Play along in your head. Your song is coming.</p>
            </section>
          )}
        </>
      )}

      {/* ---------- reveal ---------- */}
      {state.phase === "revealing" && state.card && (
        <section className="hero">
          <span className="label">The answer</span>
          <div className="row" style={{ gap: 24, alignItems: "baseline" }}>
            <span className="reveal-year">{state.card.year}</span>
            <div className="stack" style={{ gap: 2 }}>
              <span className="h am" style={{ fontSize: "var(--t-xl)" }}>
                {state.card.artistAm || state.card.artistLatin}
              </span>
              <span className="am soft" style={{ fontSize: "var(--t-md)" }}>
                {state.card.titleAm || state.card.titleLatin}
              </span>
              <span className="hint">
                {state.card.artistLatin} — {state.card.titleLatin}
              </span>
            </div>
          </div>

          {outcome && (
            <>
              <div className="verdict">
                <span className="label">
                  {outcome.playerId === state.viewerId ? "You" : activeName}
                </span>
                <Pill tone={outcome.artistRight ? "good" : "bad"}>
                  singer {outcome.artistRight ? `+${artistPoints}` : "0"}
                </Pill>
                <Pill tone={outcome.yearRight ? "good" : "bad"}>
                  year {outcome.yearRight ? `+${yearPoints}` : "0"}
                </Pill>
                {outcome.titleRight && <Pill tone="good">knew the title · tiebreak +1</Pill>}
                <span className={`points${outcome.points === 0 ? " points-zero" : ""}`}>
                  +{outcome.points}
                </span>
              </div>
              <p className="hint">
                {outcome.declined
                  ? "Passed on this one — no points, no card."
                  : `Said “${outcome.artistGuess || "nothing"}”${
                      outcome.titleGuess ? ` · “${outcome.titleGuess}”` : ""
                    } · ${outcome.keptCard ? "kept the card" : "lost the card"}`}
              </p>
            </>
          )}

          {isHost ? (
            <button
              className="btn"
              style={{ alignSelf: "flex-start" }}
              onClick={() => nextRound(state.code)}
            >
              {state.isLastRound ? "See the final scores" : "Next song"}
            </button>
          ) : (
            <p className="hint">
              {hostName} moves the table on to the {state.isLastRound ? "final scores" : "next song"}.
            </p>
          )}
        </section>
      )}

      {/* ---------- over ---------- */}
      {state.phase === "over" && (
        <section className="hero">
          <span className="label">Final</span>
          <h2 className="h accent" style={{ fontSize: "var(--t-3xl)" }}>
            {state.standings[0]?.name} wins
          </h2>
          <div className="stack" style={{ gap: 6 }}>
            {state.standings.map((p, i) => (
              <div key={p.id} className="row" style={{ gap: 12 }}>
                <span className="num faint" style={{ width: 22 }}>
                  {i + 1}
                </span>
                <span className={p.id === state.viewerId ? "" : "soft"}>
                  {p.name}
                  {p.id === state.viewerId ? " (you)" : ""}
                </span>
                {p.titleHits > 0 && <span className="hint">♪{p.titleHits} titles</span>}
                <span className="score-val" style={{ marginLeft: "auto" }}>
                  {p.score}
                </span>
              </div>
            ))}
          </div>
          <button
            className="btn-ghost"
            style={{ alignSelf: "flex-start" }}
            onClick={() => router.push("/")}
          >
            Back to the start
          </button>
        </section>
      )}

      <section className="stack" style={{ gap: 0, marginTop: 8 }}>
        <span className="label" style={{ marginBottom: 6 }}>
          Timelines
        </span>
        {state.players.map((p) => (
          <PlayerRow key={p.id} player={p} state={state} />
        ))}
      </section>
    </main>
  );
}
