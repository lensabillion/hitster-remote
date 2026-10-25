"use client";

import { useEffect, useRef, useState } from "react";
import type { AudioCue } from "@/lib/room";

/* Each client plays its own copy of the clip. Nothing is streamed peer to peer:
 * sub-second drift is invisible in a game where nobody compares waveforms, and a
 * mesh would cost far more than it buys.
 *
 * The whole clip plays — a Deezer preview is about 30 seconds and that is all
 * there is of it. Replay is free and unlimited; Stop is there for anyone who
 * would rather kill the music and think.
 *
 * Browsers refuse to start audio without a gesture, so the first round shows a
 * play button and later rounds start on their own. */

/* The slice of the YouTube IFrame API this component touches. The script has no
 * published types, so the shape is declared here rather than left as `any`. */
type YTPlayer = {
  playVideo(): void;
  pauseVideo(): void;
  seekTo(seconds: number): void;
  setVolume(volume: number): void;
  destroy(): void;
};

type YTApi = {
  Player: new (
    host: HTMLElement,
    options: {
      height: string;
      width: string;
      videoId: string;
      playerVars?: Record<string, number>;
      events?: { onReady?: (event: { target: YTPlayer }) => void };
    },
  ) => YTPlayer;
};

declare global {
  interface Window {
    YT?: YTApi;
    onYouTubeIframeAPIReady?: () => void;
  }
}

let ytApiPromise: Promise<YTApi> | null = null;

function loadYouTubeApi(): Promise<YTApi> {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  ytApiPromise ??= new Promise((resolve) => {
    const tag = document.createElement("script");
    tag.src = "https://www.youtube.com/iframe_api";
    window.onYouTubeIframeAPIReady = () => resolve(window.YT!);
    document.head.appendChild(tag);
  });
  return ytApiPromise;
}

export default function AudioClip({ cue }: { cue: AudioCue | null }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const ytHost = useRef<HTMLDivElement | null>(null);
  const ytPlayer = useRef<YTPlayer | null>(null);
  const [needsGesture, setNeedsGesture] = useState(false);
  const [playing, setPlaying] = useState(false);

  function stop() {
    setPlaying(false);
    audioRef.current?.pause();
    try {
      ytPlayer.current?.pauseVideo();
    } catch {
      /* player may already be torn down */
    }
  }

  useEffect(() => {
    const current = cue;
    if (!current || current.source === "none") return;
    let cancelled = false;
    // A new cue withdraws the tap-to-play prompt the previous one may have left; the
    // player set up below decides, in this same effect, whether it is needed again.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setNeedsGesture(false);

    const endTimer = window.setTimeout(() => stop(), current.clipSeconds * 1000);

    async function start() {
      if (current!.source === "deezer" && current!.url) {
        const el = audioRef.current;
        if (!el) return;
        el.src = current!.url;
        el.currentTime = 0;
        try {
          await el.play();
          if (!cancelled) setPlaying(true);
        } catch {
          if (!cancelled) setNeedsGesture(true);
        }
        return;
      }
      if (current!.source === "youtube" && current!.youtubeId) {
        const YT = await loadYouTubeApi();
        if (cancelled || !ytHost.current) return;
        ytPlayer.current?.destroy();
        ytPlayer.current = new YT.Player(ytHost.current, {
          height: "1",
          width: "1",
          videoId: current!.youtubeId,
          playerVars: { autoplay: 1, controls: 0, playsinline: 1, start: 0 },
          events: {
            onReady: (e) => {
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
      window.clearTimeout(endTimer);
      stop();
    };
    // A new round is a new cue; nothing else about the cue should restart playback.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cue?.roundNo, cue?.source]);

  async function resume() {
    setNeedsGesture(false);
    try {
      if (cue?.source === "deezer") await audioRef.current?.play();
      else ytPlayer.current?.playVideo();
      setPlaying(true);
    } catch {
      setNeedsGesture(true);
    }
  }

  function replay() {
    if (cue?.source === "deezer" && audioRef.current) {
      audioRef.current.currentTime = 0;
    } else {
      try {
        ytPlayer.current?.seekTo(0);
      } catch {
        /* not ready yet */
      }
    }
    resume();
  }

  if (!cue || cue.source === "none") {
    return <p className="hint">No audio for this card.</p>;
  }

  return (
    <div className="row" style={{ gap: 10 }}>
      <audio ref={audioRef} preload="auto" />
      <div ref={ytHost} aria-hidden style={{ position: "absolute", left: -9999, top: -9999 }} />

      {needsGesture ? (
        <button className="btn" onClick={resume} style={{ padding: "10px 18px" }}>
          ▶ Play the clip
        </button>
      ) : (
        <span className={`pill${playing ? " pill-accent" : ""}`}>
          {playing ? "♪ playing" : "clip ended"}
        </span>
      )}

      {playing && (
        <button className="btn-ghost" onClick={stop}>
          Stop
        </button>
      )}
      <button className="btn-ghost" onClick={replay}>
        Replay
      </button>
      <span className="hint">replay is free — answer whenever you like</span>
    </div>
  );
}
