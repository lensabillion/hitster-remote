import { socket } from "../lib/socket.js";

export default function RoundResult({ room, result, isHost, mySid }) {
  const next = () => socket.emit("round:next", { code: room.code });
  const showFinal = () => socket.emit("game:show_final", { code: room.code });

  return (
    <div className="min-h-screen p-6 flex flex-col items-center justify-center">
      <div className="card p-8 w-full max-w-xl animate-pop">
        <p className="text-white/50 text-sm uppercase tracking-widest text-center">
          Round {result.round + 1} answer
        </p>
        <h2 className="mt-2 text-center text-4xl font-bold bg-gradient-to-r from-accent to-accent2 bg-clip-text text-transparent">
          {result.artist || "Unknown"}
        </h2>
        {result.songTitle && (
          <p className="mt-1 text-center text-white/70">{result.songTitle}</p>
        )}

        <div className="mt-6">
          <h3 className="font-semibold mb-3">Leaderboard</h3>
          <ul className="space-y-2">
            {result.leaderboard.map((p, i) => (
              <li
                key={p.sid}
                className={`flex items-center gap-3 px-3 py-2 rounded-xl ${
                  p.sid === mySid ? "bg-accent/20" : "bg-white/5"
                }`}
              >
                <span className="w-6 text-center font-bold text-white/60">
                  {i + 1}
                </span>
                <span className="font-medium flex-1 truncate">{p.name}</span>
                <span className="font-bold tabular-nums">{p.score}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-8 flex justify-center">
          {isHost ? (
            result.isFinal ? (
              <button onClick={showFinal} className="btn-primary text-lg px-10">
                Show final results 🏆
              </button>
            ) : (
              <button onClick={next} className="btn-primary text-lg px-10">
                Next round →
              </button>
            )
          ) : (
            <p className="text-white/50">
              {result.isFinal
                ? "Waiting for the host to reveal the podium…"
                : "Waiting for the host to start the next round…"}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
