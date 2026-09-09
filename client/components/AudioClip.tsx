"use client";

import { useEffect, useRef, useState } from "react";
import type { AudioCue } from "@/lib/room";

/* Each client plays its own copy of the clip from a shared start timestamp.
 * Nothing is streamed peer to peer: sub-second drift is invisible in a game
 * where nobody compares waveforms.
 *
 * LISTENING IS PROGRESSIVE. A Deezer preview is about 30 seconds and that is
 * the whole of it — there is no more audio to fetch. So instead of spending all
 * 30 up front, the clip opens with a short burst and you extend it when you need
 * to. Recognising a song in six seconds should feel different from needing the
 * lot, and this is the only way to offer "let me hear more" honestly within what
 * the source actually provides.
 *
 * Browsers refuse to start audio without a gesture, so the first round shows a
 * play button and later rounds start on their own. */

const STEPS = [8, 16, 30] as const;

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

export default function AudioClip({ cue }: { cue: AudioCue | null }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const ytHost = useRef<HTMLDivElement | null>(null);
  const ytPlayer = useRef<any>(null);
  const stopAt = useRef<number>(0);

  const [step, setStep] = useState(0);
  const [needsGesture, setNeedsGesture] = useState(false);
  const [playing, setPlaying] = useState(false);

  const max = cue?.clipSeconds ?? 30;
  const limit = Math.min(STEPS[step], max);
  const atEnd = limit >= max;

  // New round: back to the shortest burst.
  useEffect(() => {
    setStep(0);
    setPlaying(false);
    setNeedsGesture(false);
  }, [cue?.roundNo]);

  useEffect(() => {
    if (!cue || cue.source === "none") return;
    let cancelled = false;

    async function start() {
      if (cue!.source === "deezer" && cue!.url) {
        const el = audioRef.current;
        if (!el) return;
        if (el.src !== cue!.url) {
          el.src = cue!.url;
          el.currentTime = 0;
        }
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
      halt();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cue?.roundNo, cue?.source]);

  // Stop at the current limit, and only there. Re-runs when the limit grows, so
  // extending resumes rather than restarting.
  useEffect(() => {
    if (!playing) return;
    stopAt.current = limit;
    const tick = window.setInterval(() => {
      const at = position();
      if (at >= stopAt.current) halt();
    }, 200);
    return () => window.clearInterval(tick);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, limit]);

  function position(): number {
    if (cue?.source === "deezer") return audioRef.current?.currentTime ?? 0;
    try {
      return ytPlayer.current?.getCurrentTime?.() ?? 0;
    } catch {
      return 0;
    }
  }

  function halt() {
    setPlaying(false);
    audioRef.current?.pause();
    try {
      ytPlayer.current?.pauseVideo?.();
    } catch {
      /* already gone */
    }
  }

  async function resume() {
    setNeedsGesture(false);
    try {
      if (cue?.source === "deezer") await audioRef.current?.play();
      else ytPlayer.current?.playVideo?.();
      setPlaying(true);
    } catch {
      setNeedsGesture(true);
    }
  }

  function hearMore() {
    if (atEnd) return;
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
    resume();
  }

  function restart() {
    if (cue?.source === "deezer" && audioRef.current) audioRef.current.currentTime = 0;
    else
      try {
        ytPlayer.current?.seekTo?.(0);
      } catch {
        /* not ready */
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
        <span className={`pill ${playing ? "pill-gold" : ""}`}>
          {playing ? `♪ playing · ${limit}s` : `heard ${limit}s`}
        </span>
      )}

      {!atEnd && (
        <button className="btn-ghost" onClick={hearMore}>
          Hear more (+{Math.min(STEPS[step + 1], max) - limit}s)
        </button>
      )}

      <button className="btn-ghost" onClick={restart}>
        From the start
      </button>

      <span className="hint">
        {atEnd
          ? "that’s the whole preview — replay as often as you like"
          : "free — listening longer costs you nothing"}
      </span>
    </div>
  );
}
