"use client";

/* Songs that exist only in this server's database, not in the committed
 * decks/deck.json.
 *
 * On a deployed server this is the difference between a song that survives and
 * one that silently vanishes: the host throws the database away on every deploy
 * and restart, and on a free tier after a few minutes without visitors. The page
 * used to say nothing about that, so a player could spend an evening fixing
 * years and lose all of it to an idle timeout. */

export type Brief = { id: string; year: number; artistLatin: string; titleLatin: string };
export type Unsaved = { added: Brief[]; removed: Brief[]; changed: Brief[] };
export type Storage = "ephemeral" | "persistent";

export default function UnsavedBanner({
  storage,
  unsaved,
  onDownload,
  downloading,
}: {
  storage: Storage;
  /* null when the server has no committed deck to compare against. */
  unsaved: Unsaved | null;
  onDownload: () => void;
  downloading: boolean;
}) {
  const ephemeral = storage === "ephemeral";
  const total = unsaved
    ? unsaved.added.length + unsaved.removed.length + unsaved.changed.length
    : 0;
  const downloadButton = (className: string) => (
    <button className={className} onClick={onDownload} disabled={downloading}>
      {downloading ? "Preparing…" : "Download deck.json"}
    </button>
  );

  if (!unsaved) {
    return ephemeral ? (
      <div className="banner banner-bad">
        <span>
          Songs added here are temporary: this server discards its database on every
          deploy and restart. Download the deck and commit it to keep changes.
        </span>
        {downloadButton("btn-ghost")}
      </div>
    ) : null;
  }

  if (total === 0) {
    return ephemeral ? (
      <p className="hint" style={{ margin: 0 }}>
        Everything here matches the committed deck. Anything you add on this server is
        temporary until you download deck.json and commit it.
      </p>
    ) : null;
  }

  const one = total === 1;
  const line = (sign: string, c: Brief) => (
    <li key={`${sign}${c.id}`} style={{ listStyle: "none" }}>
      <span className="mono">{sign}</span> {c.artistLatin} — {c.titleLatin}{" "}
      <span className="hint">({c.year})</span>
    </li>
  );

  return (
    <div
      className={`banner${ephemeral ? " banner-bad" : ""}`}
      style={{ alignItems: "flex-start" }}
      role="status"
    >
      <div className="stack" style={{ gap: 10, flex: 1, minWidth: 240 }}>
        <div className="row">
          <span className={`pill ${ephemeral ? "pill-bad" : "pill-gold"}`}>
            {total} unsaved {one ? "change" : "changes"}
          </span>
        </div>
        <p style={{ margin: 0 }}>
          {ephemeral ? (
            <>
              {one ? "This change exists" : "These changes exist"} only on this server,
              and <strong>will be lost</strong>. It throws its database away on every
              deploy and restart — and on a free tier, after a few minutes without
              visitors.
            </>
          ) : (
            <>
              {one ? "This change isn't" : "These changes aren't"} in{" "}
              <span className="mono">deck.json</span> yet, so the deployed game won&apos;t
              have {one ? "it" : "them"}.
            </>
          )}
        </p>
        <ul className="stack" style={{ gap: 2, margin: 0, padding: 0 }}>
          {unsaved.added.map((c) => line("+", c))}
          {unsaved.changed.map((c) => line("~", c))}
          {unsaved.removed.map((c) => line("−", c))}
        </ul>
        <p className="hint" style={{ margin: 0 }}>
          To keep {one ? "it" : "them"}: download, save the file as{" "}
          <span className="mono">server/decks/deck.json</span>, and commit it.
        </p>
      </div>
      {downloadButton("btn")}
    </div>
  );
}
