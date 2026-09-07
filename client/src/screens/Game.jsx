import { useEffect, useMemo, useRef, useState } from "react";
import Fuse from "fuse.js";
import { socket } from "../lib/socket.js";
import YouTubePlayer from "../components/YouTubePlayer.jsx";
import CountdownRing from "../components/CountdownRing.jsx";

const PHASE_PLAYING = "playing";
const PHASE_GUESSING = "guessing";

export default function Game({ room, roundData, isHost, mySid }) {
  const [phase, setPhase] = useState(PHASE_PLAYING);
  const [guess, setGuess] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [feedback, setFeedback] = useState(null); // { correct, points }
  const [submittedCount, setSubmittedCount] = useState(0);
  const [now, setNow] = useState(Date.now());
  const inputRef = useRef(null);

  const totalGuessSeconds = roundData.guessWindowSeconds || 15;

  // Reset state for each new round
  useEffect(() => {
    setPhase(PHASE_PLAYING);
    setGuess("");
    setSubmitted(false);
    setFeedback(null);
    setSubmittedCount(0);
  }, [roundData.round, roundData.videoId]);

  // Socket subscriptions
  useEffect(() => {
    const onResult = (r) => setFeedback(r);
    const onReceived = ({ submittedCount }) =>
      setSubmittedCount(submittedCount);
    socket.on("guess:result", onResult);
    socket.on("guess:received", onReceived);
    return () => {
      socket.off("guess:result", onResult);
      socket.off("guess:received", onReceived);
    };
  }, []);

  // Tick once per 100ms while guessing for the ring animation
  useEffect(() => {
    if (phase !== PHASE_GUESSING) return;
    const id = setInterval(() => setNow(Date.now()), 100);
    return () => clearInterval(id);
  }, [phase]);

  // The guess window starts after the 10s clip ends.
  const guessStartedAt = roundData.startedAt + 10_000;
  const elapsedGuessSec = Math.max(0, (now - guessStartedAt) / 1000);
  const remainingSec = Math.max(0, totalGuessSeconds - elapsedGuessSec);

  // fuse.js fuzzy match against the artist name (frontend primary check).
  const fuse = useMemo(() => {
    const artist = room.playlist[roundData.round]?.artist || "";
    return new Fuse([{ artist }], {
      keys: ["artist"],
      threshold: 0.4,
      includeScore: true,
    });
  }, [room.playlist, roundData.round]);

  const submitGuess = () => {
    if (submitted || phase !== PHASE_GUESSING) return;
    const trimmed = guess.trim();
    if (!trimmed) return;
    const matches = fuse.search(trimmed);
    const correct = matches.length > 0 && (matches[0].score ?? 1) <= 0.4;
    socket.emit("guess:submit", {
      code: room.code,
      guess: trimmed,
      correct,
    });
    setSubmitted(true);
  };

  const onClipEnded = () => {
    setPhase(PHASE_GUESSING);
    setNow(Date.now());
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const totalPlayers = room.players.length;

  return (
    <div className="min-h-screen p-6 flex flex-col items-center justify-center">
      {phase === PHASE_PLAYING && (
        <YouTubePlayer videoId={roundData.videoId} onEnded={onClipEnded} />
      )}

      <div className="text-center mb-6">
        <p className="text-white/50 text-sm tracking-widest uppercase">
          Round {roundData.round + 1} / {roundData.totalRounds}
        </p>
        {phase === PHASE_PLAYING ? (
          <h2 className="text-4xl md:text-5xl font-bold mt-2">
            <span className="bg-gradient-to-r from-accent to-accent2 bg-clip-text text-transparent">
              Listen…
            </span>
          </h2>
        ) : (
          <h2 className="text-4xl md:text-5xl font-bold mt-2">
            Who is the artist?
          </h2>
        )}
      </div>

      {phase === PHASE_GUESSING && (
        <CountdownRing
          remaining={remainingSec}
          total={totalGuessSeconds}
          label="seconds"
        />
      )}

      {phase === PHASE_PLAYING && (
        <div className="w-56 h-56 rounded-full bg-gradient-to-br from-accent/30 to-accent2/30 animate-glow flex items-center justify-center">
          <div className="text-6xl">🎵</div>
        </div>
      )}

      <div className="card p-6 mt-8 w-full max-w-md">
        {!submitted ? (
          <div className="space-y-3">
            <input
              ref={inputRef}
              className="input text-center text-xl"
              placeholder={
                phase === PHASE_PLAYING
                  ? "Guess unlocks when clip ends…"
                  : "Type the artist name"
              }
              value={guess}
              onChange={(e) => setGuess(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submitGuess()}
              disabled={phase !== PHASE_GUESSING}
              maxLength={60}
            />
            <button
              onClick={submitGuess}
              disabled={phase !== PHASE_GUESSING || !guess.trim()}
              className="btn-primary w-full text-lg"
            >
              Submit
            </button>
          </div>
        ) : (
          <div className="text-center py-4">
            {feedback ? (
              <div className="animate-pop">
                <div className="text-5xl mb-2">
                  {feedback.correct ? "🎯" : "😬"}
                </div>
                <p className="text-xl font-semibold">
                  {feedback.correct
                    ? `+${feedback.points} points`
                    : "Not quite"}
                </p>
              </div>
            ) : (
              <p className="text-white/60">Submitted! Awaiting result…</p>
            )}
          </div>
        )}
        <div className="mt-4 text-center text-sm text-white/50">
          {submittedCount} / {totalPlayers} have guessed
        </div>
      </div>

      {isHost && phase === PHASE_GUESSING && (
        <p className="mt-4 text-xs text-white/40">
          You're the host — sit tight, the round will auto-advance.
        </p>
      )}
    </div>
  );
}
