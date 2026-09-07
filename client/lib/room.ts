"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { io, type Socket } from "socket.io-client";
import { getPlayerId } from "./identity";

const SERVER_URL = process.env.NEXT_PUBLIC_SERVER_URL ?? "http://localhost:3001";

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

export type AnswerScore = {
  artistRight: boolean;
  yearRight: boolean;
  titleRight: boolean;
  points: number;
  artistGuess: string;
  titleGuess: string;
  gap: number;
};

export type Outcome = {
  cardWinner: string | null;
  stolen: boolean;
  scores: Record<string, AnswerScore>;
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
  answeredPlayerIds: string[];
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
  const [connected, setConnected] = useState(false);
  const playerId = useRef<string>("");

  useEffect(() => {
    playerId.current = getPlayerId();
    const s = getSocket();

    const onState = (next: RoomState) => setState(next);
    const onAudio = (cue: AudioCue) => setAudio(cue);
    const onError = ({ message }: { message: string }) => {
      setError(message);
      window.setTimeout(() => setError(""), 5000);
    };
    const onConnect = () => setConnected(true);
    const onDisconnect = () => setConnected(false);

    s.on("connect", onConnect);
    s.on("disconnect", onDisconnect);
    s.on("room:state", onState);
    s.on("round:audio", onAudio);
    s.on("error", onError);
    setConnected(s.connected);

    return () => {
      s.off("connect", onConnect);
      s.off("disconnect", onDisconnect);
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
    connected,
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
