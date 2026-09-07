"use client";

import { use, useEffect } from "react";
import AnswerCard from "@/components/AnswerCard";
import AudioClip from "@/components/AudioClip";
import Timeline from "@/components/Timeline";
import { getPlayerName } from "@/lib/identity";
import { useRoom, type PlayerView, type RoomState } from "@/lib/room";

const ARTIST_POINTS = 70;
const YEAR_POINTS = 30;

type Tone = "" | "gold" | "good" | "bad";
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
        </div>
      ))}
    </div>
  );
}

function PlayerRow({ player, state }: { player: PlayerView; state: RoomState }) {
  const isActive = state.activePlayerId === player.id;
  return (
    <div className={`player${isActive ? " player-active" : ""}`}>
      <div className="player-head">
        <span className="player-name">
          {player.name}
          {player.id === state.viewerId ? " (you)" : ""}
        </span>
        {isActive && state.phase !== "lobby" && <Pill tone="gold">their turn</Pill>}
        {player.isHost && <Pill>host</Pill>}
        {!player.connected && <Pill tone="bad">offline</Pill>}
        <span className="hint" style={{ marginLeft: "auto" }}>
          {player.score} pts · {player.timeline.length}{" "}
          {player.timeline.length === 1 ? "card" : "cards"}
        </span>
      </div>
      <Timeline cards={player.timeline} />
    </div>
  );
}

export default function RoomPage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = use(params);
  const roomCode = code.toUpperCase();
  const { state, audio, error, connected, playerId, joinRoom, startGame, answer, nextRound } =
    useRoom();

  // Join, and rejoin on every reconnect. Identity is durable, so the server puts
  // us back in the same seat with our score and timeline.
  useEffect(() => {
    if (connected) joinRoom(roomCode, getPlayerName() || "Player");
  }, [connected, roomCode, joinRoom]);

  if (!state) {
    return (
      <main className="page">
        <p className="muted">{connected ? `Joining ${roomCode}…` : "Connecting…"}</p>
        {error && <p style={{ color: "var(--red)" }}>{error}</p>}
      </main>
    );
  }

  const you = state.players.find((p) => p.id === state.viewerId);
  const isHost = state.hostId === playerId;
  const outcome = state.outcome;
  const activeName =
    state.players.find((p) => p.id === state.activePlayerId)?.name ?? "Someone";
  const hostName = state.players.find((p) => p.isHost)?.name ?? "the host";
  const connectedCount = state.players.filter((p) => p.connected).length;

  return (
    <main className="page">
      <header className="topbar">
        <div className="brand">
          <span className="display am" style={{ fontSize: "var(--t-xl)" }}>
            ዜማ
          </span>
          <span className="code">{state.code}</span>
        </div>
        <div className="row">
          {state.phase !== "lobby" && (
            <Pill>
              round {state.roundNo} / {state.roundsPlanned}
            </Pill>
          )}
          <Pill tone={connected ? "good" : "bad"}>
            {connected ? "connected" : "reconnecting"}
          </Pill>
        </div>
      </header>

      {error && (
        <div
          className="card"
          style={{
            borderColor: "var(--red)",
            background: "var(--red-wash)",
            padding: "12px 16px",
          }}
        >
          <span style={{ color: "var(--red)", fontSize: "var(--t-sm)" }}>{error}</span>
        </div>
      )}

      {state.phase !== "lobby" && <Scoreboard state={state} />}

      {/* ---------- lobby ---------- */}
      {state.phase === "lobby" && (
        <section className="hero">
          <div className="stack" style={{ gap: 6 }}>
            <span className="label">Waiting to start</span>
            <h2 className="display" style={{ fontSize: "var(--t-2xl)", margin: 0 }}>
              Share the code{" "}
              <span style={{ color: "var(--gold)", letterSpacing: "0.1em" }}>
                {state.code}
              </span>
            </h2>
          </div>
          <p className="muted">
            You take turns. On your turn a song plays and you name the singer (
            {ARTIST_POINTS} points) and place it on your timeline ({YEAR_POINTS}).
            Everyone hears every song. Highest score wins.
          </p>

          <div className="stack">
            <span className="label">{connectedCount} in the room</span>
            <div className="row">
              {state.players.map((p) => (
                <span key={p.id} className="score">
                  <span className="score-name">{p.name}</span>
                  {p.isHost && <Pill>host</Pill>}
                  {!p.connected && <Pill tone="bad">offline</Pill>}
                </span>
              ))}
            </div>
          </div>

          <p className="hint">
            Wear headphones if you are on a call together, or the music echoes through
            everyone&apos;s microphone.
          </p>

          {isHost ? (
            <button
              className="btn"
              style={{ alignSelf: "flex-start" }}
              onClick={() => startGame(state.code)}
              disabled={connectedCount < 2}
            >
              {connectedCount < 2 ? "Need one more player" : "Start the game"}
            </button>
          ) : (
            <p className="hint">Waiting for {hostName} to start.</p>
          )}
        </section>
      )}

      {/* ---------- answering ---------- */}
      {state.phase === "answering" && you && (
        <>
          <div className="card" style={{ padding: "16px 20px" }}>
            <AudioClip cue={audio} />
          </div>

          {state.isMyTurn ? (
            <AnswerCard
              key={state.roundNo}
              timeline={you.timeline}
              artistPoints={ARTIST_POINTS}
              yearPoints={YEAR_POINTS}
              sealed={state.hasAnswered}
              sealedAnswer={state.myAnswer}
              onSeal={(gap, artistGuess, titleGuess) =>
                answer(state.code, gap, artistGuess, titleGuess)
              }
            />
          ) : (
            /* Watching. They hear the same clip and answer on their own turn. */
            <section className="hero">
              <span className="label">Listening</span>
              <h2 className="display" style={{ fontSize: "var(--t-2xl)", margin: 0 }}>
                <span style={{ color: "var(--gold)" }}>{activeName}</span> is naming this
                one
              </h2>
              <p className="muted">Follow along — your song comes on your turn.</p>
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
              <span className="display am" style={{ fontSize: "var(--t-xl)" }}>
                {state.card.artistAm || state.card.artistLatin}
              </span>
              <span
                className="am"
                style={{ color: "var(--ink-soft)", fontSize: "var(--t-md)" }}
              >
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
                  singer {outcome.artistRight ? `+${ARTIST_POINTS}` : "0"}
                </Pill>
                <Pill tone={outcome.yearRight ? "good" : "bad"}>
                  year {outcome.yearRight ? `+${YEAR_POINTS}` : "0"}
                </Pill>
                {outcome.titleRight && <Pill tone="gold">knew the title</Pill>}
                <span className="points">+{outcome.points}</span>
              </div>
              <p className="hint">
                Said “{outcome.artistGuess || "nothing"}”
                {outcome.titleGuess ? ` · “${outcome.titleGuess}”` : ""} ·{" "}
                {outcome.keptCard ? "kept the card" : "lost the card"}
              </p>
            </>
          )}

          {isHost && (
            <button
              className="btn"
              style={{ alignSelf: "flex-start" }}
              onClick={() => nextRound(state.code)}
            >
              {state.isLastRound ? "See the final scores" : "Next song"}
            </button>
          )}
        </section>
      )}

      {/* ---------- over ---------- */}
      {state.phase === "over" && (
        <section className="hero">
          <span className="label">Final</span>
          <h2
            className="display"
            style={{ fontSize: "var(--t-3xl)", margin: 0, color: "var(--gold)" }}
          >
            {state.standings[0]?.name} wins
          </h2>
          <div className="stack" style={{ gap: 6 }}>
            {state.standings.map((p, i) => (
              <div key={p.id} className="row" style={{ gap: 12 }}>
                <span className="num" style={{ color: "var(--ink-faint)", width: 22 }}>
                  {i + 1}
                </span>
                <span style={{ color: "var(--ink-soft)" }}>{p.name}</span>
                <span className="score-val" style={{ marginLeft: "auto" }}>
                  {p.score}
                </span>
              </div>
            ))}
          </div>
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
