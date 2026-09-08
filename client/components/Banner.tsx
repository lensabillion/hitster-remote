"use client";

import type { Connection } from "@/lib/room";

/* Says out loud when the game cannot reach its server.
 *
 * The previous version disabled both buttons and explained itself in one line of
 * grey text at the very bottom of the page — below the fold on a phone. A
 * correctly built, correctly deployed client pointed at a server that isn't
 * there looked simply broken, with nothing to act on.
 *
 * So: name the problem, show the address it is actually calling, and say what to
 * check. The URL matters because it is baked in at build time — seeing
 * "localhost:3001" on a deployed site diagnoses the whole thing at a glance. */

export function ConnectionBanner({
  connection,
  serverUrl,
}: {
  connection: Connection;
  serverUrl: string;
}) {
  if (connection === "online") return null;

  if (connection === "connecting") {
    return (
      <div className="banner">
        <span className="pill">connecting</span>
        <span>Reaching the game server…</span>
      </div>
    );
  }

  const isLocal = /localhost|127\.0\.0\.1/.test(serverUrl);
  const deployed =
    typeof window !== "undefined" && !/localhost|127\.0\.0\.1/.test(window.location.host);

  return (
    <div className="banner banner-bad">
      <div className="stack" style={{ gap: 8 }}>
        <div className="row">
          <span className="pill pill-bad">can’t reach the server</span>
        </div>
        <p style={{ margin: 0 }}>
          The game needs its server, and nothing is answering at{" "}
          <code className="mono">{serverUrl}</code>.
        </p>
        {isLocal && deployed ? (
          <p className="hint" style={{ margin: 0 }}>
            That address is <strong>your own computer</strong>, so a deployed site can
            never reach it. Set <code className="mono">NEXT_PUBLIC_SERVER_URL</code> to the
            server’s public address in your hosting settings — then redeploy, because the
            value is compiled in at build time.
          </p>
        ) : (
          <p className="hint" style={{ margin: 0 }}>
            Either the server is asleep or down, or it isn’t allowing this site. On a free
            tier the first request after a quiet spell can take ~30 seconds — this will
            clear on its own if that’s all it is.
          </p>
        )}
      </div>
    </div>
  );
}

export function ErrorBanner({
  message,
  onDismiss,
}: {
  message: string;
  onDismiss: () => void;
}) {
  if (!message) return null;
  return (
    <div className="banner banner-bad">
      <span style={{ flex: 1 }}>{message}</span>
      <button className="btn-ghost" onClick={onDismiss} aria-label="Dismiss">
        Dismiss
      </button>
    </div>
  );
}
