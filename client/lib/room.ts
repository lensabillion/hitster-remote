"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { io, type Socket } from "socket.io-client";
import { getPlayerId } from "./identity";

export const SERVER_URL =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://localhost:3001";

/* How long to look like we are merely connecting before admitting the server
 * cannot be reached. Socket.IO retries forever and says nothing, which leaves a
 * misconfigured deployment looking like a frozen page. */
const CONNECTING_GRACE_MS = 4000;

export type Connection = "connecting" | "online" | "offline";

export type TimelineCard = {
  id: string;
  year: number;
  artistAm: string;
  titleAm: string;
  artistLatin: string;
  titleLatin: string;
};

export type PlayerView = {
  id: string;
  name: string;
  tokens: number;
  score: number;
  connected: boolean;
  isHost: boolean;
  timeline: TimelineCard[];
};

/* One song, one answer: the outcome describes the turn, not the table. */
export type Outcome = {
  playerId: string;
  keptCard: boolean;
  points: number;
  artistRight: boolean;
  yearRight: boolean;
  titleRight: boolean;
  artistGuess: string;
  titleGuess: string;
};

export type RoomState = {
  code: string;
  hostId: string;
  phase: "lobby" | "answering" | "revealing" | "over";
  roundNo: number;
  roundsPlanned: number;
  activePlayerId: string | null;
  viewerId: string;
  maxRoundScore: number;
  clipSeconds: number;
  isLastRound: boolean;
  players: PlayerView[];
  isMyTurn: boolean;
  hasAnswered: boolean;
  myAnswer: { gap: number; artistGuess: string; titleGuess: string } | null;
  card: (TimelineCard & { addedBy: string }) | null;
  outcome: Outcome | null;
  standings: { id: string; name: string; score: number }[];
};

export type AudioCue = {
  source: "deezer" | "youtube" | "none";
  url?: string;
  youtubeId?: string;
  clipSeconds: number;
  roundNo: number;
  startAt: number;
};

let socket: Socket | null = null;

function getSocket(): Socket {
  if (!socket) {
    socket = io(SERVER_URL, {
      transports: ["websocket", "polling"],
      // Reconnection is the point: identity is durable, so re-attaching a
      // socket puts the player back in the same seat.
      reconnection: true,
      reconnectionDelay: 500,
      reconnectionDelayMax: 4000,
    });
  }
  return socket;
}

export function useRoom() {
  const [state, setState] = useState<RoomState | null>(null);
  const [audio, setAudio] = useState<AudioCue | null>(null);
  const [error, setError] = useState("");
  const [connection, setConnection] = useState<Connection>("connecting");
  const playerId = useRef<string>("");

  useEffect(() => {
    playerId.current = getPlayerId();
    const s = getSocket();

    const onState = (next: RoomState) => setState(next);
    const onAudio = (cue: AudioCue) => setAudio(cue);
    // Errors persist until superseded or dismissed. They used to clear after
    // five seconds, which hid exactly the messages a player needed to act on --
    // "no room with that code" vanished before it could be read.
    const onError = ({ message }: { message: string }) => setError(message);

    const onConnect = () => {
      window.clearTimeout(graceTimer);
      setConnection("online");
      setError("");
    };
    // The grace timer is armed ONCE and only cleared by a successful connect.
    // Re-arming it on every connect_error was the bug: Socket.IO retries every
    // few hundred milliseconds, so the deadline was pushed back forever and the
    // banner sat on "connecting" indefinitely — the very state it exists to
    // escape.
    let graceTimer = 0;
    const armGrace = () => {
      window.clearTimeout(graceTimer);
      graceTimer = window.setTimeout(() => {
        if (!s.connected) setConnection("offline");
      }, CONNECTING_GRACE_MS);
    };

    const onDisconnect = () => {
      setConnection("connecting");
      armGrace();
    };
    const onConnectError = () => {
      if (!s.connected) setConnection((c) => (c === "online" ? "connecting" : c));
    };

    armGrace();

    s.on("connect", onConnect);
    s.on("disconnect", onDisconnect);
    s.on("connect_error", onConnectError);
    s.on("room:state", onState);
    s.on("round:audio", onAudio);
    s.on("error", onError);
    if (s.connected) setConnection("online");

    return () => {
      window.clearTimeout(graceTimer);
      s.off("connect", onConnect);
      s.off("disconnect", onDisconnect);
      s.off("connect_error", onConnectError);
      s.off("room:state", onState);
      s.off("round:audio", onAudio);
      s.off("error", onError);
    };
  }, []);

  const emit = useCallback((event: string, payload: Record<string, unknown> = {}) => {
    getSocket().emit(event, { ...payload, playerId: playerId.current });
  }, []);

  const createRoom = useCallback(
    (name: string) => emit("room:create", { name }),
    [emit],
  );
  const joinRoom = useCallback(
    (code: string, name: string) => emit("room:join", { code, name }),
    [emit],
  );
  const startGame = useCallback(
    (code: string) => emit("game:start", { code }),
    [emit],
  );
  const answer = useCallback(
    (code: string, gap: number, artist: string, title: string) =>
      emit("round:answer", { code, gap, artist, title }),
    [emit],
  );
  const nextRound = useCallback(
    (code: string) => emit("round:next", { code }),
    [emit],
  );

  return {
    state,
    audio,
    error,
    clearError: () => setError(""),
    connection,
    connected: connection === "online",
    serverUrl: SERVER_URL,
    playerId: playerId.current,
    createRoom,
    joinRoom,
    startGame,
    answer,
    nextRound,
  };
}

export function onRoomJoined(handler: (code: string) => void): () => void {
  const s = getSocket();
  const wrapped = ({ code }: { code: string }) => handler(code);
  s.on("room:joined", wrapped);
  return () => s.off("room:joined", wrapped);
}
