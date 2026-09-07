import { useEffect, useRef } from "react";
import { loadYouTubeAPI } from "../lib/youtube.js";

/**
 * Hidden YouTube player. Plays seconds 0-10 of a video, then fires onEnded.
 * The user never sees the iframe — we just want the audio.
 */
export default function YouTubePlayer({ videoId, onEnded }) {
  const containerRef = useRef(null);
  const playerRef = useRef(null);
  const endedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    endedRef.current = false;

    loadYouTubeAPI().then((YT) => {
      if (cancelled || !containerRef.current) return;
      playerRef.current = new YT.Player(containerRef.current, {
        height: "1",
        width: "1",
        videoId,
        playerVars: {
          autoplay: 1,
          controls: 0,
          disablekb: 1,
          fs: 0,
          modestbranding: 1,
          playsinline: 1,
          rel: 0,
          start: 0,
          end: 10,
        },
        events: {
          onReady: (e) => {
            try {
              e.target.setVolume(80);
              e.target.playVideo();
            } catch (_) {}
          },
          onStateChange: (e) => {
            // 0 = ended
            if (e.data === 0 && !endedRef.current) {
              endedRef.current = true;
              onEnded?.();
            }
          },
        },
      });
    });

    // Hard backstop: end after 10.5s even if YT doesn't fire ended.
    const t = setTimeout(() => {
      if (!endedRef.current) {
        endedRef.current = true;
        try {
          playerRef.current?.stopVideo?.();
        } catch (_) {}
        onEnded?.();
      }
    }, 10500);

    return () => {
      cancelled = true;
      clearTimeout(t);
      try {
        playerRef.current?.destroy?.();
      } catch (_) {}
    };
  }, [videoId]);

  return (
    <div className="absolute -left-[9999px] -top-[9999px] pointer-events-none opacity-0">
      <div ref={containerRef} />
    </div>
  );
}
