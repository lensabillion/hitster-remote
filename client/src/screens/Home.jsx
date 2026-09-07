import { useState } from "react";
import { socket } from "../lib/socket.js";

export default function Home() {
  const [mode, setMode] = useState(null); // null | 'create' | 'join'
  const [name, setName] = useState("");
  const [code, setCode] = useState("");

  const create = () => {
    if (!name.trim()) return;
    socket.emit("room:create", { name: name.trim() });
  };
  const join = () => {
    if (!name.trim() || code.length !== 4) return;
    socket.emit("room:join", { name: name.trim(), code: code.toUpperCase() });
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6">
      <div className="text-center mb-10 animate-pop">
        <h1 className="text-6xl md:text-7xl font-bold tracking-tight bg-gradient-to-r from-accent to-accent2 bg-clip-text text-transparent">
          Hitster
        </h1>
        <p className="mt-2 text-white/60 text-lg">
          Name that artist before the clock runs out.
        </p>
      </div>

      <div className="card p-8 w-full max-w-md animate-pop">
        {!mode && (
          <div className="space-y-3">
            <button
              onClick={() => setMode("create")}
              className="btn-primary w-full text-lg animate-glow"
            >
              Create Room
            </button>
            <button
              onClick={() => setMode("join")}
              className="btn-secondary w-full text-lg"
            >
              Join Room
            </button>
          </div>
        )}

        {mode === "create" && (
          <div className="space-y-4">
            <label className="block text-sm text-white/60">Your name</label>
            <input
              autoFocus
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={20}
              placeholder="DJ Lensa"
            />
            <div className="flex gap-2">
              <button onClick={() => setMode(null)} className="btn-secondary flex-1">
                Back
              </button>
              <button onClick={create} className="btn-primary flex-1">
                Create
              </button>
            </div>
          </div>
        )}

        {mode === "join" && (
          <div className="space-y-4">
            <label className="block text-sm text-white/60">Your name</label>
            <input
              autoFocus
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={20}
              placeholder="Player 2"
            />
            <label className="block text-sm text-white/60">Room code</label>
            <input
              className="input uppercase tracking-[0.5em] text-center text-2xl font-bold"
              value={code}
              onChange={(e) =>
                setCode(e.target.value.toUpperCase().replace(/[^A-Z]/g, "").slice(0, 4))
              }
              maxLength={4}
              placeholder="ABCD"
            />
            <div className="flex gap-2">
              <button onClick={() => setMode(null)} className="btn-secondary flex-1">
                Back
              </button>
              <button onClick={join} className="btn-primary flex-1">
                Join
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
