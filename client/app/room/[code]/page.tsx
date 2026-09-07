"use client";

import { use, useEffect } from "react";
import AnswerCard from "@/components/AnswerCard";
import AudioClip from "@/components/AudioClip";
import Timeline from "@/components/Timeline";
import { getPlayerName } from "@/lib/identity";
import { useRoom, type PlayerView, type RoomState } from "@/lib/room";

const ARTIST_POINTS = 70;
const YEAR_POINTS = 30;

function Pill({
  children,
  tone = "faint",
}: {
  children: React.ReactNode;
  tone?: "faint" | "gold" | "good" | "bad";
}) {
  const colors = {
    faint: ["var(--rule-soft)", "var(--ink-faint)"],
    gold: ["var(--gold-wash)", "var(--gold)"],
    good: ["var(--verd-wash)", "var(--verd)"],
    bad: ["var(--red-wash)", "var(--red)"],
  } as const;
  const [bg, fg] = colors[tone];
  return (
    <span
      className="label"
      style={{ background: bg, color: fg, padding: "3px 9px", borderRadius: 2 }}
    >
      {children}
    </span>
  );
}

function Scoreboard({ state }: { state: RoomState }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
      {state.standings.map((p, i) => (
        <div
          key={p.id}
          className="surface"
          style={{
            padding: "8px 14px",
            display: "flex",
            alignItems: "baseline",
            gap: 10,
            borderColor: i === 0 ? "var(--gold-dim)" : "var(--rule)",
          }}
        >
          <span
            style={{
              fontSize: "var(--t-sm)",
              color: p.id === state.viewerId ? "var(--gold)" : "var(--ink-soft)",
            }}
          >
            {p.name}
          </span>
          <span
            className="display numeral"
            style={{ fontSize: "var(--t-md)", color: "var(--ink)" }}
          >
            {p.score}
          </span>
        </div>
      ))}
    </div>
  );
}

function PlayerStrip({ player, state }: { player: PlayerView; state: RoomState }) {
  const isActive = state.activePlayerId === player.id;
  const sealed = state.answeredPlayerIds.includes(player.id);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <span
          className="display"
          style={{
            fontSize: "var(--t-md)",
            color: isActive ? "var(--gold)" : "var(--ink)",
          }}
        >
          {player.name}
          {player.id === state.viewerId ? " (you)" : ""}
        </span>
        {isActive && <Pill tone="gold">their card</Pill>}
        {player.isHost && <Pill>host</Pill>}
        {!player.connected && <Pill tone="bad">offline</Pill>}
        {sealed && state.phase === "answering" && <Pill tone="good">sealed</Pill>}
        <span style={{ fontSize: "var(--t-xs)", color: "var(--ink-faint)" }}>
          {player.score} pts · {player.timeline.length} cards
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

  // Join (or rejoin) on mount and on every reconnect. Identity is durable, so
  // the server puts us back in the same seat with our score and timeline.
  useEffect(() => {
    if (connected) joinRoom(roomCode, getPlayerName() || "Player");
  }, [connected, roomCode, joinRoom]);

  if (!state) {
    return (
      <main style={{ padding: 64, maxWidth: 720, margin: "0 auto" }}>
        <p style={{ color: "var(--ink-soft)" }}>
          {connected ? `Joining ${roomCode}…` : "Connecting…"}
        </p>
        {error && <p style={{ color: "var(--red)" }}>{error}</p>}
      </main>
    );
  }

  const you = state.players.find((p) => p.id === state.viewerId);
  const isHost = state.hostId === playerId;
  const myScore = state.outcome?.scores[state.viewerId];

  return (
    <main
      style={{
        position: "relative",
        zIndex: 1,
        maxWidth: 980,
        margin: "0 auto",
        padding: "40px 24px 96px",
        display: "flex",
        flexDirection: "column",
        gap: 30,
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
          <span className="display amharic" style={{ fontSize: "var(--t-xl)" }}>
            ዜማ
          </span>
          <span
            className="display numeral"
            style={{
              fontSize: "var(--t-lg)",
              color: "var(--gold)",
              letterSpacing: "0.2em",
            }}
          >
            {state.code}
          </span>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {state.phase !== "lobby" && (
            <Pill>
              round {state.roundNo} of {state.roundsPlanned}
            </Pill>
          )}
          <Pill tone={connected ? "good" : "bad"}>
            {connected ? "connected" : "reconnecting"}
          </Pill>
        </div>
      </header>

      {error && (
        <div
          style={{
            background: "var(--red-wash)",
            border: "1px solid var(--red)",
            borderRadius: "var(--radius)",
            padding: "10px 14px",
            color: "var(--red)",
            fontSize: "var(--t-sm)",
          }}
        >
          {error}
        </div>
      )}

      {state.phase !== "lobby" && <Scoreboard state={state} />}

      {state.phase === "lobby" && (
        <section
          className="surface"
          style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}
        >
          <h2 className="display" style={{ margin: 0, fontSize: "var(--t-xl)" }}>
            Waiting for players
          </h2>
          <p style={{ color: "var(--ink-soft)", margin: 0, maxWidth: "58ch" }}>
            Share the code <strong style={{ color: "var(--gold)" }}>{state.code}</strong>.
            Each round you name the singer ({ARTIST_POINTS} points) and place the song on
            your timeline ({YEAR_POINTS} points). Everyone answers every round. Wear
            headphones if you are on a call together, or the music echoes through
            everyone&apos;s microphone.
          </p>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {state.players.map((p) => (
              <li key={p.id}>
                {p.name} {p.isHost && "· host"} {!p.connected && "· offline"}
              </li>
            ))}
          </ul>
          {isHost ? (
            <button
              onClick={() => startGame(state.code)}
              style={{
                background: "var(--gold)",
                color: "#20170a",
                fontWeight: 700,
                padding: "11px 20px",
                borderRadius: "var(--radius)",
                alignSelf: "flex-start",
              }}
            >
              Start the game
            </button>
          ) : (
            <p style={{ color: "var(--ink-faint)", margin: 0 }}>
              Waiting for the host to start.
            </p>
          )}
        </section>
      )}

      {state.phase === "answering" && you && (
        <section style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <AudioClip cue={audio} />
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
          <span style={{ fontSize: "var(--t-xs)", color: "var(--ink-faint)" }}>
            {state.answeredPlayerIds.length} of{" "}
            {state.players.filter((p) => p.connected).length} sealed.
          </span>
        </section>
      )}

      {state.phase === "revealing" && state.card && (
        <section
          className="surface"
          style={{
            padding: 28,
            display: "flex",
            flexDirection: "column",
            gap: 20,
            borderColor: "var(--gold-dim)",
          }}
        >
          <span className="label">The answer</span>
          <div style={{ display: "flex", alignItems: "baseline", gap: 22, flexWrap: "wrap" }}>
            <span
              className="display numeral"
              style={{ fontSize: "var(--t-3xl)", color: "var(--gold)", lineHeight: 1 }}
            >
              {state.card.year}
            </span>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span className="display amharic" style={{ fontSize: "var(--t-lg)" }}>
                {state.card.artistAm || state.card.artistLatin}
              </span>
              <span className="amharic" style={{ color: "var(--ink-soft)" }}>
                {state.card.titleAm || state.card.titleLatin}
              </span>
              <span style={{ fontSize: "var(--t-sm)", color: "var(--ink-faint)" }}>
                {state.card.artistLatin} — {state.card.titleLatin}
              </span>
            </div>
          </div>

          {myScore && (
            <div
              style={{
                display: "flex",
                gap: 10,
                flexWrap: "wrap",
                alignItems: "center",
                borderTop: "1px solid var(--rule)",
                paddingTop: 16,
              }}
            >
              <Pill tone={myScore.artistRight ? "good" : "bad"}>
                singer {myScore.artistRight ? `+${ARTIST_POINTS}` : "0"}
              </Pill>
              <Pill tone={myScore.yearRight ? "good" : "bad"}>
                year {myScore.yearRight ? `+${YEAR_POINTS}` : "0"}
              </Pill>
              {myScore.titleRight && <Pill tone="gold">you knew the title too</Pill>}
              <span style={{ color: "var(--ink-faint)", fontSize: "var(--t-sm)" }}>
                you said “{myScore.artistGuess || "nothing"}”
              </span>
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <span className="label">Everyone</span>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
              {Object.entries(state.outcome?.scores ?? {}).map(([pid, s]) => (
                <span
                  key={pid}
                  style={{ fontSize: "var(--t-sm)", color: "var(--ink-soft)" }}
                >
                  {state.players.find((p) => p.id === pid)?.name}:{" "}
                  <strong style={{ color: "var(--ink)" }}>+{s.points}</strong>
                  {s.artistGuess ? ` (“${s.artistGuess}”)` : ""}
                </span>
              ))}
            </div>
            {state.outcome?.stolen && state.outcome.cardWinner && (
              <Pill tone="gold">
                card taken by{" "}
                {state.players.find((p) => p.id === state.outcome!.cardWinner)?.name}
              </Pill>
            )}
          </div>

          {isHost && (
            <button
              onClick={() => nextRound(state.code)}
              style={{
                background: "var(--gold)",
                color: "#20170a",
                fontWeight: 700,
                padding: "11px 20px",
                borderRadius: "var(--radius)",
                alignSelf: "flex-start",
              }}
            >
              {state.isLastRound ? "See the final scores" : "Next song"}
            </button>
          )}
        </section>
      )}

      {state.phase === "over" && (
        <section
          className="surface"
          style={{
            padding: 28,
            borderColor: "var(--gold)",
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
        >
          <span className="label">Final</span>
          <span
            className="display"
            style={{ fontSize: "var(--t-2xl)", color: "var(--gold)" }}
          >
            {state.standings[0]?.name} wins
          </span>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {state.standings.map((p, i) => (
              <span key={p.id} style={{ color: "var(--ink-soft)" }}>
                <span className="numeral">{i + 1}.</span> {p.name} —{" "}
                <strong style={{ color: "var(--ink)" }}>{p.score}</strong>
              </span>
            ))}
          </div>
        </section>
      )}

      <section style={{ display: "flex", flexDirection: "column", gap: 26 }}>
        <span className="label">Timelines</span>
        {state.players.map((p) => (
          <PlayerStrip key={p.id} player={p} state={state} />
        ))}
      </section>
    </main>
  );
}
