/* Durable player identity.
 *
 * The server keys players by this id, never by socket id, so a refresh, a
 * tunnel, or a dropped connection re-binds the same seat with its timeline and
 * tokens intact. This is the single thing that makes the game survive an
 * unreliable connection, which is the connection it is designed for. */

const ID_KEY = "zema.playerId";
const NAME_KEY = "zema.playerName";

function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `p-${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
}

/* Storage throws in some contexts (private windows, blocked site data), and a
 * game that cannot start because of that is worse than one that forgets a seat
 * on reload -- so fall back to a per-tab id rather than failing. */
let fallbackId: string | null = null;

export function getPlayerId(): string {
  try {
    const existing = localStorage.getItem(ID_KEY);
    if (existing) return existing;
    const fresh = uuid();
    localStorage.setItem(ID_KEY, fresh);
    return fresh;
  } catch {
    return (fallbackId ??= uuid());
  }
}

export function getPlayerName(): string {
  try {
    return localStorage.getItem(NAME_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setPlayerName(name: string): void {
  try {
    localStorage.setItem(NAME_KEY, name);
  } catch {
    /* A remembered name is a convenience, not state the game depends on. */
  }
}
