"use client";

import { useEffect, useState } from "react";

/* The answer window, counted down on every screen.
 *
 * The server publishes one deadline per round, so the host, the player
 * answering and the watchers all see the same clock. It is a ceiling, not a
 * pace: nothing here hurries anyone, it only stops an absent player stalling
 * the table without warning. */

function secondsLeft(endsAt: number): number {
  return Math.max(0, Math.ceil((endsAt - Date.now()) / 1000));
}

export default function Countdown({ endsAt }: { endsAt: number | null }) {
  const [left, setLeft] = useState<number | null>(endsAt === null ? null : secondsLeft(endsAt));

  useEffect(() => {
    if (endsAt === null) return;
    const tick = () => setLeft(secondsLeft(endsAt));
    tick();
    const id = window.setInterval(tick, 500);
    return () => window.clearInterval(id);
  }, [endsAt]);

  if (endsAt === null || left === null) return null;
  const m = Math.floor(left / 60);
  const s = String(left % 60).padStart(2, "0");
  const urgent = left <= 10;
  return (
    <span
      className={`pill num${urgent ? " pill-bad" : ""}`}
      title="Time left to answer"
      aria-live={urgent ? "polite" : "off"}
    >
      {m}:{s}
    </span>
  );
}
