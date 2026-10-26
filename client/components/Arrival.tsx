/* The landing page's arrival, played once as the page opens.
 *
 * A crowd of ears is listening to nothing in particular. As the song starts, each
 * one turns toward the place the mark is about to appear; the mark arrives where
 * they are listening, the crowd clears for the name, and "Listen." gives way to the
 * question. It says the table rule out loud: everyone hears every song.
 *
 * All CSS (`.arrival` in globals.css), so it runs from the first paint and needs no
 * script. Every element's resting style is its final frame and the animations fill
 * backwards, so with reduced motion the header is simply there. The crowd is laid
 * out in px from the header's top-left corner, where the mark is: ears that would
 * fall past the right edge are clipped, so one deterministic layout serves every
 * width and the server and client render the same markup. */

import type { CSSProperties } from "react";
import Logo from "@/components/Logo";

// The mark's centre, from the header's top-left corner. The logo row is one line of
// the wordmark (3.5rem at line-height 1.7; 2.5rem on a phone) with the 56px mark
// centred in it.
const MARK_X = 28;
const MARK_Y_WIDE = 47.6;
const MARK_Y_NARROW = 34;

// Ear centres inside these boxes would sit on the logo or the question. On a phone
// the bottom row would also reach the rules underneath, hence the floor.
const CLEAR_WIDE = { right: 272, top: -8, bottom: 188 };
const CLEAR_NARROW = { right: 219, top: -8, bottom: 150, floor: 132 };

const ROWS = [-20, 40, 100, 160];
const COLS = 14;
const MAX_TILT = 0.55; // radians: an ear leans toward the sound, it does not spin

type Ear = { key: string; className: string; style: CSSProperties };

/* Unmirrored, the glyph is an ear facing left; mirrored, one facing right. Turn it
 * to face (MARK_X, my), leaning no further than MAX_TILT. */
function aim(x: number, y: number, my: number) {
  const dx = MARK_X - x;
  const dy = my - y;
  const face = dx >= 0 ? -1 : 1;
  let tilt = face === 1 ? Math.atan2(dy, dx) - Math.PI : Math.atan2(dy, dx);
  tilt = Math.atan2(Math.sin(tilt), Math.cos(tilt));
  tilt = Math.max(-MAX_TILT, Math.min(MAX_TILT, tilt));
  return { face, deg: (tilt * 180) / Math.PI, d: Math.hypot(dx, dy), dx, dy };
}

function crowd(): Ear[] {
  let seed = 7;
  const rnd = () => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };
  const ears: Ear[] = [];
  ROWS.forEach((rowY, row) => {
    for (let col = 0; col < COLS; col++) {
      const jitter = row === 0 ? 4 : 8;
      const x = 32 + col * 64 + (rnd() - 0.5) * 2 * jitter;
      const y = rowY + (rnd() - 0.5) * 2 * jitter;
      const s0 = rnd() < 0.5 ? -1 : 1;
      const r0 = (rnd() - 0.5) * 40;

      const offWide = x < CLEAR_WIDE.right && y > CLEAR_WIDE.top && y < CLEAR_WIDE.bottom;
      const offNarrow =
        y > CLEAR_NARROW.floor ||
        (x < CLEAR_NARROW.right && y > CLEAR_NARROW.top && y < CLEAR_NARROW.bottom);
      if (offWide && offNarrow) continue;

      const wide = aim(x, y, MARK_Y_WIDE);
      const narrow = aim(x, y, MARK_Y_NARROW);
      // Nearer ears hear it first.
      const at = Math.round(450 + 450 * Math.min(1, wide.d / 700));
      const drift = 6 / (wide.d || 1); // they lean back a little as they leave
      ears.push({
        key: `${row}-${col}`,
        className: ["ear", offWide && "ear-off-wide", offNarrow && "ear-off-narrow"]
          .filter(Boolean)
          .join(" "),
        style: {
          "--x": `${x.toFixed(1)}px`,
          "--y": `${y.toFixed(1)}px`,
          "--r0": `${r0.toFixed(1)}deg`,
          "--s0": String(s0),
          "--s1": String(wide.face),
          "--r1-wide": `${wide.deg.toFixed(1)}deg`,
          "--r1-narrow": `${narrow.deg.toFixed(1)}deg`,
          "--ux": `${(-wide.dx * drift).toFixed(1)}px`,
          "--uy": `${(-wide.dy * drift).toFixed(1)}px`,
          "--at": `${at}ms`,
        } as CSSProperties,
      });
    }
  });
  return ears;
}

const EARS = crowd();

/* An ear in profile, facing left: the rim, then the fold inside it. The same
 * pictogram as Lucide's "ear" (ISC licence), redrawn on a 24-unit grid. */
function EarGlyph() {
  return (
    <svg viewBox="0 0 24 24" focusable="false">
      <path d="M6 9a6 6 0 1 1 12 0c0 5.5-5 5.5-5 9.5a3.5 3.5 0 1 1-7 0" />
      <path d="M15 9a3 3 0 0 0-6 0v1a2.5 2.5 0 1 1 0 5" />
    </svg>
  );
}

export default function Arrival() {
  return (
    <div className="stack arrival" style={{ gap: 20 }}>
      <div className="ears" aria-hidden="true">
        {EARS.map((ear) => (
          <span key={ear.key} className={ear.className} style={ear.style}>
            <EarGlyph />
          </span>
        ))}
      </div>
      <Logo />
      <h2 className="h arrival-line" style={{ fontSize: "var(--t-2xl)" }}>
        <span className="arrival-listen" aria-hidden="true">
          Listen.
        </span>
        <span className="arrival-who">Who? When?</span>
      </h2>
    </div>
  );
}
