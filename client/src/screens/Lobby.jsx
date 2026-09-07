import { useState } from "react";
import { socket } from "../lib/socket.js";

export default function Lobby({ room, isHost, mySid }) {
  const [url, setUrl] = useState("");

  const addSong = () => {
    if (!url.trim()) return;
    socket.emit("playlist:add", { code: room.code, youtube_url: url.trim() });
    setUrl("");
  };

  const removeSong = (index) => {
    socket.emit("playlist:remove", { code: room.code, index });
  };

  const startGame = () => {
    if (room.playlist.length === 0) return;
    socket.emit("game:start", { code: room.code });
  };

  const setRounds = (n) => {
    const v = Math.max(1, Math.min(n, room.playlist.length || 1));
    socket.emit("room:set_rounds", { code: room.code, rounds: v });
  };

  const effectiveRounds = Math.min(
    room.rounds_per_game || room.playlist.length,
    room.playlist.length || 1
  );

  return (
    <div className="min-h-screen p-6 flex flex-col items-center">
      <div className="w-full max-w-3xl">
        <header className="flex items-center justify-between mb-6">
          <div>
            <p className="text-white/50 text-sm">Room code</p>
            <h1 className="text-5xl font-bold tracking-[0.3em] bg-gradient-to-r from-accent to-accent2 bg-clip-text text-transparent">
              {room.code}
            </h1>
          </div>
          <div className="text-right">
            <p className="text-white/50 text-sm">Players</p>
            <p className="text-2xl font-bold">{room.players.length}</p>
          </div>
        </header>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="card p-6">
            <h2 className="font-semibold text-lg mb-3">Players</h2>
            <ul className="space-y-2">
              {room.players.map((p) => (
                <li
                  key={p.sid}
                  className="flex items-center gap-3 px-3 py-2 rounded-xl bg-white/5"
                >
                  <span className="w-2 h-2 rounded-full bg-green-400" />
                  <span className="font-medium">{p.name}</span>
                  {p.sid === room.host && (
                    <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-accent/20 text-accent">
                      Host
                    </span>
                  )}
                  {p.sid === mySid && (
                    <span className="text-xs text-white/40">you</span>
                  )}
                </li>
              ))}
            </ul>
          </div>

          <div className="card p-6">
            <h2 className="font-semibold text-lg mb-3">
              Playlist ({room.playlist.length})
            </h2>
            {isHost && (
              <>
                <div className="flex gap-2 mb-2">
                  <input
                    className="input"
                    placeholder="YouTube video or playlist URL"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addSong()}
                  />
                  <button onClick={addSong} className="btn-primary">
                    Add
                  </button>
                </div>
                <p className="text-xs text-white/40 mb-3">
                  Tip: paste a full YouTube playlist link to import it all at
                  once (server needs YOUTUBE_API_KEY).
                </p>
              </>
            )}
            {room.playlist.length === 0 ? (
              <p className="text-white/40 text-sm">
                {isHost
                  ? "Paste YouTube links to build the playlist."
                  : "Waiting for the host to add songs…"}
              </p>
            ) : (
              <ul className="space-y-2 max-h-64 overflow-auto pr-1">
                {room.playlist.map((t, i) => (
                  <li
                    key={i}
                    className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/5"
                  >
                    <span className="text-white/40 text-xs w-5">{i + 1}.</span>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{t.artist}</p>
                      {t.songTitle && (
                        <p className="text-xs text-white/50 truncate">
                          {t.songTitle}
                        </p>
                      )}
                    </div>
                    {isHost && (
                      <button
                        onClick={() => removeSong(i)}
                        className="text-white/40 hover:text-red-400 text-sm"
                      >
                        ✕
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {isHost && (
          <div className="mt-6 flex flex-col items-center gap-4">
            <div className="card px-5 py-3 flex items-center gap-4">
              <label className="text-sm text-white/70">Rounds</label>
              <button
                onClick={() => setRounds(effectiveRounds - 1)}
                disabled={effectiveRounds <= 1}
                className="btn-secondary px-3 py-1 text-lg"
              >
                −
              </button>
              <input
                type="number"
                className="w-16 text-center bg-transparent text-2xl font-bold tabular-nums focus:outline-none"
                value={effectiveRounds}
                min={1}
                max={room.playlist.length || 1}
                onChange={(e) =>
                  setRounds(parseInt(e.target.value, 10) || 1)
                }
                disabled={room.playlist.length === 0}
              />
              <button
                onClick={() => setRounds(effectiveRounds + 1)}
                disabled={effectiveRounds >= room.playlist.length}
                className="btn-secondary px-3 py-1 text-lg"
              >
                +
              </button>
              <span className="text-xs text-white/40">
                of {room.playlist.length}
              </span>
            </div>
            <button
              onClick={startGame}
              disabled={room.playlist.length === 0}
              className="btn-primary text-lg px-10 animate-glow"
            >
              Start Game
            </button>
          </div>
        )}
        {!isHost && (
          <div className="mt-6 text-center text-white/50">
            <p>Waiting for the host to start…</p>
            {room.playlist.length > 0 && (
              <p className="text-xs mt-1">
                {effectiveRounds} of {room.playlist.length} songs this game
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
