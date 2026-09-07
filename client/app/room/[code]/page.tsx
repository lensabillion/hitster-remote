"use client";

import { use, useEffect, useState } from "react";
import AudioClip from "@/components/AudioClip";
import Timeline from "@/components/Timeline";
import { getPlayerName } from "@/lib/identity";
import { useRoom, type PlayerView, type RoomState } from "@/lib/room";

function Pill({ children, tone = "faint" }: { children: React.ReactNode; tone?: string }) {
  const colors: Record<string, [string, string]> = {
    faint: ["var(--rule-soft)", "var(--ink-faint)"],
    gold: ["var(--gold-wash)", "var(--gold)"],
    good: ["var(--verd-wash)", "var(--verd)"],
    bad: ["var(--red-wash)", "var(--red)"],
  };
  const [bg, fg] = colors[tone] ?? colors.faint;
  return (
    <span
      className="label"
      style={{ background: bg, color: fg, padding: "3px 9px", borderRadius: 2 }}
    >
      {children}
    </span>
  );
}

function PlayerStrip({ player, state }: { player: PlayerView; state: RoomState }) {
  const isActive = state.activePlayerId === player.id;
  const sealed = state.placedPlayerIds.includes(player.id);
  const isYou = player.id === state.viewerId;

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
          {isYou ? " (you)" : ""}
        </span>
        {isActive && <Pill tone="gold">placing</Pill>}
        {player.isHost && <Pill>host</Pill>}
        {!player.connected && <Pill tone="bad">offline</Pill>}
        {sealed && state.phase === "placing" && <Pill tone="good">sealed</Pill>}
        <span style={{ fontSize: "var(--t-xs)", color: "var(--ink-faint)" }}>
          {player.timeline.length}/{state.cardsToWin} cards · {player.tokens} tokens
        </span>
      </div>
      <Timeline cards={player.timeline} />
    </div>
  );
}

export default function RoomPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = use(params);
  const roomCode = code.toUpperCase();
  const { state, audio, error, connected, playerId, joinRoom, startGame, place, nextRound } =
    useRoom();
  const [pendingGap, setPendingGap] = useState<number | null>(null);

  // Join (or rejoin) on mount and whenever the socket reconnects. Identity is
  // durable, so the server puts us back in the same seat.
  useEffect(() => {
    if (connected) joinRoom(roomCode, getPlayerName() || "Player");
  }, [connected, roomCode, joinRoom]);

  useEffect(() => {
    setPendingGap(null);
  }, [state?.roundNo]);

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
  const isActive = state.activePlayerId === playerId;
  const winner = state.players.find((p) => p.timeline.length >= state.cardsToWin);

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
        gap: 34,
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
            style={{ fontSize: "var(--t-lg)", color: "var(--gold)", letterSpacing: "0.2em" }}
          >
            {state.code}
          </span>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {state.phase !== "lobby" && <Pill>round {state.roundNo}</Pill>}
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

      {state.phase === "lobby" && (
        <section className="surface" style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
          <h2 className="display" style={{ margin: 0, fontSize: "var(--t-xl)" }}>
            Waiting for players
          </h2>
          <p style={{ color: "var(--ink-soft)", margin: 0, maxWidth: "56ch" }}>
            Share the code <strong style={{ color: "var(--gold)" }}>{state.code}</strong>.
            Everyone places a card every round, so nobody sits waiting for a turn.
            Wear headphones if you are on a call together — otherwise the music
            echoes through everyone&apos;s microphone.
          </p>
          <ul style={{ margin: 0, paddingLeft: 18, color: "var(--ink)" }}>
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

      {(state.phase === "playing" || state.phase === "placing") && (
        <section className="surface" style={{ padding: 24, display: "flex", flexDirection: "column", gap: 18 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span className="label">
              {state.phase === "playing" ? "Listen" : "Where does it go?"}
            </span>
            <p style={{ margin: 0, color: "var(--ink-soft)", maxWidth: "58ch" }}>
              {isActive
                ? "This one is yours. Place it correctly and you keep the card."
                : "Place it on your own timeline too — right earns a token, and if the active player is wrong you take the card."}
            </p>
          </div>

          <AudioClip cue={audio} />

          {state.phase === "placing" && you && (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <Timeline
                key={`place-${state.roundNo}`}
                cards={you.timeline}
                interactive={!state.hasPlaced}
                onPlace={setPendingGap}
              />
              {state.hasPlaced ? (
                <Pill tone="good">sealed — waiting for the others</Pill>
              ) : (
                <button
                  disabled={pendingGap === null}
                  onClick={() => place(state.code, pendingGap!)}
                  style={{
                    background: pendingGap === null ? "var(--surface-lift)" : "var(--gold)",
                    color: pendingGap === null ? "var(--ink-faint)" : "#20170a",
                    fontWeight: 700,
                    padding: "11px 20px",
                    borderRadius: "var(--radius)",
                    alignSelf: "flex-start",
                    cursor: pendingGap === null ? "not-allowed" : "pointer",
                  }}
                >
                  {pendingGap === null ? "Pick a spot" : "Seal my answer"}
                </button>
              )}
              <span style={{ fontSize: "var(--t-xs)", color: "var(--ink-faint)" }}>
                {state.placedPlayerIds.length} of {state.players.filter((p) => p.connected).length} sealed.
                Nothing is revealed until everyone has answered.
              </span>
            </div>
          )}
        </section>
      )}

      {state.phase === "revealing" && state.card && (
        <section
          className="surface"
          style={{
            padding: 28,
            display: "flex",
            flexDirection: "column",
            gap: 18,
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
                {state.card.titleAm || state.card.titleLatin}
              </span>
              <span className="amharic" style={{ color: "var(--ink-soft)" }}>
                {state.card.artistAm || state.card.artistLatin}
              </span>
              <span style={{ fontSize: "var(--t-sm)", color: "var(--ink-faint)" }}>
                {state.card.artistLatin} — {state.card.titleLatin}
              </span>
            </div>
          </div>

          {state.outcome && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
              <Pill tone={state.outcome.activeCorrect ? "good" : "bad"}>
                {state.outcome.activeCorrect ? "placed correctly" : "misplaced"}
              </Pill>
              {state.outcome.stolen && state.outcome.cardWinner && (
                <Pill tone="gold">
                  stolen by{" "}
                  {state.players.find((p) => p.id === state.outcome!.cardWinner)?.name}
                </Pill>
              )}
              {!state.outcome.cardWinner && <Pill tone="bad">nobody took it</Pill>}
              {Object.entries(state.outcome.tokenAwards).map(([pid, n]) => (
                <Pill key={pid} tone="good">
                  +{n} token · {state.players.find((p) => p.id === pid)?.name}
                </Pill>
              ))}
            </div>
          )}

          {isHost && !winner && (
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
              Next song
            </button>
          )}
        </section>
      )}

      {winner && (
        <section
          className="surface"
          style={{ padding: 28, borderColor: "var(--gold)", display: "flex", flexDirection: "column", gap: 8 }}
        >
          <span className="label">Winner</span>
          <span className="display" style={{ fontSize: "var(--t-2xl)", color: "var(--gold)" }}>
            {winner.name}
          </span>
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
