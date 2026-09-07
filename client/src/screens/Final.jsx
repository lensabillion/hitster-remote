export default function Final({ room, finalData, isHost, onPlayAgain }) {
  const board = finalData.leaderboard;
  const winner = board[0];
  const podium = board.slice(0, 3);
  const rest = board.slice(3);

  const heights = ["h-40", "h-32", "h-24"];
  const order = [1, 0, 2]; // visual order: 2nd, 1st, 3rd
  const podiumOrdered = order
    .map((i) => podium[i])
    .filter(Boolean)
    .map((p, idx) => ({
      ...p,
      place: order[idx] + 1,
      barClass: heights[order[idx]],
    }));

  return (
    <div className="min-h-screen p-6 flex flex-col items-center justify-center">
      <div className="text-center mb-8 animate-pop">
        <p className="text-white/50 uppercase tracking-widest text-sm">
          Winner
        </p>
        <h1 className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-accent to-accent2 bg-clip-text text-transparent">
          {winner?.name || "—"}
        </h1>
        <p className="mt-2 text-2xl">
          🏆 {winner?.score ?? 0} points
        </p>
      </div>

      <div className="flex items-end gap-4 mb-10">
        {podiumOrdered.map((p) => (
          <div key={p.sid} className="flex flex-col items-center">
            <div className="text-3xl mb-2">
              {p.place === 1 ? "🥇" : p.place === 2 ? "🥈" : "🥉"}
            </div>
            <div className="font-medium">{p.name}</div>
            <div className="text-white/50 text-sm">{p.score} pts</div>
            <div
              className={`${p.barClass} w-20 mt-2 rounded-t-2xl bg-gradient-to-t from-accent2 to-accent`}
            />
          </div>
        ))}
      </div>

      {rest.length > 0 && (
        <div className="card p-6 w-full max-w-md mb-8">
          <ul className="space-y-2">
            {rest.map((p, i) => (
              <li
                key={p.sid}
                className="flex items-center gap-3 px-3 py-2 rounded-xl bg-white/5"
              >
                <span className="w-6 text-center font-bold text-white/60">
                  {i + 4}
                </span>
                <span className="font-medium flex-1 truncate">{p.name}</span>
                <span className="font-bold tabular-nums">{p.score}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {isHost && (
        <button onClick={onPlayAgain} className="btn-primary text-lg px-10">
          Play Again
        </button>
      )}
      {!isHost && (
        <p className="text-white/50">Thanks for playing!</p>
      )}
    </div>
  );
}
