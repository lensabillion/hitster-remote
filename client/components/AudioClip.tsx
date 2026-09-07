"use client";

import { useEffect, useRef, useState } from "react";
import type { AudioCue } from "@/lib/room";

/* Each client plays its own copy of the clip from a shared start timestamp.
 * Nothing is streamed peer to peer: sub-second drift is invisible in a game
 * where nobody compares waveforms, and a mesh would cost far more than it buys.
 *
 * Browsers refuse to start audio without a gesture, so the first round shows a
 * play button and every round after that starts on its own. */

declare global {
  interface Window {
    YT?: any;
    onYouTubeIframeAPIReady?: () => void;
  }
}

let ytApiPromise: Promise<any> | null = null;

function loadYouTubeApi(): Promise<any> {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  ytApiPromise ??= new Promise((resolve) => {
    const tag = document.createElement("script");
    tag.src = "https://www.youtube.com/iframe_api";
    window.onYouTubeIframeAPIReady = () => resolve(window.YT);
    document.head.appendChild(tag);
  });
  return ytApiPromise;
}

export default function AudioClip({
  cue,
  onEnded,
}: {
  cue: AudioCue | null;
  onEnded?: () => void;
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const ytHost = useRef<HTMLDivElement | null>(null);
  const ytPlayer = useRef<any>(null);
  const [needsGesture, setNeedsGesture] = useState(false);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!cue || cue.source === "none") return;
    let cancelled = false;
    setNeedsGesture(false);

    const stopAt = window.setTimeout(() => {
      stop();
      onEnded?.();
    }, cue.clipSeconds * 1000);

    async function start() {
      if (cue!.source === "deezer" && cue!.url) {
        const el = audioRef.current;
        if (!el) return;
        el.src = cue!.url;
        try {
          await el.play();
          if (!cancelled) setPlaying(true);
        } catch {
          if (!cancelled) setNeedsGesture(true);
        }
        return;
      }
      if (cue!.source === "youtube" && cue!.youtubeId) {
        const YT = await loadYouTubeApi();
        if (cancelled || !ytHost.current) return;
        ytPlayer.current?.destroy?.();
        ytPlayer.current = new YT.Player(ytHost.current, {
          height: "1",
          width: "1",
          videoId: cue!.youtubeId,
          playerVars: { autoplay: 1, controls: 0, playsinline: 1, start: 0 },
          events: {
            onReady: (e: any) => {
              try {
                e.target.setVolume(80);
                e.target.playVideo();
                setPlaying(true);
              } catch {
                setNeedsGesture(true);
              }
            },
          },
        });
      }
    }

    start();
    return () => {
      cancelled = true;
      window.clearTimeout(stopAt);
      stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cue?.roundNo, cue?.source]);

  function stop() {
    setPlaying(false);
    const el = audioRef.current;
    if (el) {
      el.pause();
      el.currentTime = 0;
    }
    try {
      ytPlayer.current?.stopVideo?.();
    } catch {
      /* player may already be torn down */
    }
  }

  async function playFromGesture() {
    setNeedsGesture(false);
    try {
      await audioRef.current?.play();
      setPlaying(true);
    } catch {
      setNeedsGesture(true);
    }
  }

  function replay() {
    const el = audioRef.current;
    if (el && cue?.source === "deezer") {
      el.currentTime = 0;
      el.play().catch(() => setNeedsGesture(true));
      return;
    }
    try {
      ytPlayer.current?.seekTo?.(0);
      ytPlayer.current?.playVideo?.();
    } catch {
      /* nothing to replay yet */
    }
  }

  if (!cue || cue.source === "none") {
    return (
      <p style={{ color: "var(--ink-faint)", fontSize: "var(--t-sm)", margin: 0 }}>
        No audio for this card.
      </p>
    );
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <audio ref={audioRef} preload="auto" />
      <div
        ref={ytHost}
        aria-hidden
        style={{ position: "absolute", left: -9999, top: -9999 }}
      />

      {needsGesture ? (
        <button
          onClick={playFromGesture}
          style={{
            background: "var(--gold)",
            color: "#20170a",
            fontWeight: 700,
            padding: "9px 16px",
            borderRadius: "var(--radius)",
          }}
        >
          ▶ Play the clip
        </button>
      ) : (
        <span
          className="label"
          style={{ color: playing ? "var(--gold)" : "var(--ink-faint)" }}
        >
          {playing ? "♪ playing" : "clip ended"}
        </span>
      )}

      {playing && (
        <button
          onClick={() => stop()}
          style={{
            border: "1px solid var(--rule)",
            color: "var(--ink-soft)",
            padding: "7px 12px",
            borderRadius: "var(--radius)",
            fontSize: "var(--t-sm)",
          }}
        >
          Stop
        </button>
      )}
      <button
        onClick={replay}
        style={{
          border: "1px solid var(--rule)",
          color: "var(--ink-soft)",
          padding: "7px 12px",
          borderRadius: "var(--radius)",
          fontSize: "var(--t-sm)",
        }}
      >
        Replay
      </button>
      <span style={{ fontSize: "var(--t-xs)", color: "var(--ink-faint)" }}>
        replay is free — answer whenever you like
      </span>
    </div>
  );
}
