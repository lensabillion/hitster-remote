/* The mark is a quaver whose flag curls into a question mark: who? when?
 * Engraving proportions: a heavy oval head, a thin stem, and a flag that swells
 * over the top of its loop and tapers to a point. One colour, taken from the
 * text around it, so it sits in green beside the name and in ink wherever ink
 * leads. `client/design/mark.py` generates the outline; run it again rather
 * than nudging points, and paste its output here and, in the heavier cut,
 * into `client/app/icon.svg`. */

type MarkProps = { size?: number; title?: string; className?: string };

export function Mark({ size = 28, title, className }: MarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="currentColor"
      className={className}
      role={title ? "img" : "presentation"}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      focusable="false"
    >
      <path d="M34.50 29.58 L34.52 29.02 L34.56 28.86 L34.32 29.93 L34.81 30.19 L35.38 30.47 L36.03 30.74 L36.76 30.98 L37.58 31.13 L38.47 31.17 L39.41 31.04 L40.37 30.72 L41.23 30.23 L41.85 29.80 L42.40 29.40 L42.95 28.97 L43.48 28.52 L43.99 28.05 L44.50 27.56 L44.98 27.04 L45.45 26.50 L45.89 25.93 L46.31 25.33 L46.70 24.71 L47.05 24.06 L47.37 23.39 L47.64 22.70 L47.87 21.98 L48.05 21.25 L48.18 20.51 L48.26 19.75 L48.28 18.99 L48.24 18.24 L48.16 17.48 L48.05 16.73 L47.90 15.98 L47.72 15.24 L47.51 14.51 L47.26 13.79 L46.98 13.07 L46.67 12.37 L46.32 11.68 L45.93 11.01 L45.51 10.35 L45.05 9.72 L44.56 9.11 L44.02 8.54 L43.46 7.99 L42.86 7.48 L42.23 7.00 L41.57 6.56 L40.89 6.17 L40.18 5.82 L39.45 5.51 L38.70 5.26 L37.94 5.05 L37.17 4.89 L36.40 4.78 L35.62 4.72 L34.83 4.70 L34.06 4.73 L33.29 4.80 L32.52 4.91 L31.77 5.07 L31.03 5.26 L30.30 5.48 L29.59 5.74 L28.90 6.03 L28.21 6.34 L27.55 6.69 L26.90 7.06 L26.27 7.45 L25.65 7.87 L25.06 8.31 L24.50 8.80 L23.99 9.34 L23.51 9.91 L23.09 10.51 L22.71 11.14 L22.38 11.80 L22.10 12.47 L21.86 13.15 L21.66 13.84 L21.51 14.53 L21.38 15.22 L21.29 15.91 L21.23 16.60 L21.19 17.28 L21.17 17.95 L21.17 18.62 L21.18 19.28 L21.21 19.94 L21.26 20.60 L21.38 21.25 L21.59 21.87 L21.86 22.48 L22.18 23.05 L22.55 23.60 L22.93 24.11 L23.32 24.61 L23.70 25.10 L24.07 25.58 L24.42 26.06 L24.83 25.79 L24.54 25.29 L24.31 24.76 L24.15 24.21 L24.05 23.64 L24.01 23.06 L23.99 22.50 L24.01 21.94 L24.02 21.40 L24.03 20.87 L24.03 20.35 L24.01 19.84 L24.02 19.33 L24.09 18.82 L24.20 18.32 L24.35 17.83 L24.55 17.36 L24.78 16.91 L25.04 16.48 L25.32 16.08 L25.63 15.69 L25.96 15.33 L26.30 14.99 L26.65 14.68 L27.00 14.37 L27.35 14.09 L27.70 13.82 L28.05 13.55 L28.40 13.29 L28.75 13.04 L29.10 12.78 L29.46 12.55 L29.84 12.35 L30.23 12.18 L30.63 12.04 L31.04 11.92 L31.46 11.84 L31.88 11.78 L32.29 11.75 L32.71 11.75 L33.12 11.77 L33.53 11.81 L33.93 11.87 L34.33 11.95 L34.71 12.05 L35.09 12.16 L35.47 12.28 L35.83 12.42 L36.19 12.56 L36.54 12.72 L36.89 12.88 L37.23 13.05 L37.56 13.24 L37.89 13.43 L38.22 13.64 L38.54 13.85 L38.85 14.08 L39.16 14.33 L39.46 14.58 L39.74 14.86 L40.02 15.15 L40.28 15.45 L40.52 15.77 L40.75 16.11 L40.96 16.46 L41.14 16.83 L41.30 17.21 L41.44 17.60 L41.54 17.99 L41.62 18.40 L41.67 18.81 L41.71 19.22 L41.74 19.64 L41.77 20.06 L41.78 20.48 L41.79 20.91 L41.78 21.34 L41.76 21.78 L41.73 22.23 L41.67 22.68 L41.59 23.13 L41.48 23.59 L41.35 24.04 L41.19 24.48 L40.99 24.92 L40.77 25.35 L40.51 25.75 L40.22 26.14 L39.89 26.51 L39.54 26.85 L39.22 27.12 L38.83 27.35 L38.54 27.45 L38.26 27.50 L37.96 27.49 L37.61 27.44 L37.22 27.34 L36.79 27.18 L36.34 26.99 L35.88 26.78 L35.40 26.55 L34.89 26.34 L34.29 26.15 L33.52 26.07 L32.54 26.31 L31.71 27.01 L31.30 27.83 L31.14 28.64 L31.10 29.42 Z"/>
      <rect x="31.10" y="28.90" width="3.40" height="21.10" rx="1.70"/>
      <ellipse cx="24.8" cy="51.0" rx="10.2" ry="7.0" transform="rotate(-22 24.8 51.0)"/>
    </svg>
  );
}

/* The name. እስቲ (isti) is "go on, then": the word that opens a dare, as in
 * እስቲ ማን ዘፈነው? -- go on, who sang it? The wordmark is the Ge'ez alone on the
 * display face; the Latin lives only in the mark's accessible name and the
 * page title. `compact` is the topbar form. */
export default function Logo({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return (
      <span className="logo">
        <Mark size={22} className="accent" title="Isti" />
        <span className="display am" style={{ fontSize: "var(--t-xl)" }}>
          እስቲ
        </span>
      </span>
    );
  }
  return (
    <div className="logo logo-lg">
      <Mark size={56} className="accent" title="Isti" />
      <h1 className="display am" style={{ fontSize: "var(--t-3xl)" }}>
        እስቲ
      </h1>
    </div>
  );
}
