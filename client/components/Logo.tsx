/* The mark is a quaver whose flag curls into a question mark: who? when? It is
 * a filled outline with a pen-like thick and thin, drawn in one colour taken
 * from the text around it, so it sits in green beside the name and in ink
 * wherever ink leads. `client/design/mark.py` generates the outline; run it
 * again rather than nudging points, and paste its output here and, in the
 * heavier cut, into `client/app/icon.svg`. */

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
      <path d="M24.88 21.56 L24.74 20.92 L24.67 20.36 L24.66 19.80 L24.69 19.24 L24.78 18.69 L24.91 18.15 L25.08 17.63 L25.30 17.12 L25.55 16.64 L25.84 16.19 L26.15 15.76 L26.49 15.35 L26.85 14.97 L27.23 14.62 L27.63 14.29 L28.04 13.98 L28.47 13.70 L28.91 13.44 L29.37 13.21 L29.85 13.03 L30.33 12.89 L30.83 12.78 L31.34 12.72 L31.84 12.70 L32.35 12.72 L32.85 12.77 L33.34 12.87 L33.82 12.99 L34.29 13.16 L34.75 13.35 L35.19 13.57 L35.61 13.82 L36.01 14.10 L36.40 14.41 L36.76 14.73 L37.11 15.08 L37.43 15.45 L37.74 15.83 L38.03 16.24 L38.29 16.66 L38.53 17.10 L38.74 17.56 L38.92 18.04 L39.07 18.53 L39.18 19.04 L39.25 19.56 L39.28 20.09 L39.26 20.62 L39.20 21.15 L39.08 21.67 L38.92 22.18 L38.71 22.68 L38.46 23.15 L38.17 23.60 L37.84 24.03 L37.48 24.43 L37.09 24.79 L36.67 25.13 L36.23 25.43 L35.66 25.76 L34.75 26.33 L33.83 27.06 L33.04 27.89 L32.38 28.80 L31.88 29.77 L31.51 30.75 L31.28 31.72 L31.14 32.67 L31.08 33.58 L31.08 34.47 L31.10 35.33 L31.15 36.18 L31.20 37.02 L31.25 37.84 L31.29 38.67 L31.30 39.53 L31.30 40.35 L31.30 41.20 L31.30 42.05 L31.30 42.90 L31.30 43.75 L31.30 44.60 L31.30 45.45 L31.30 46.30 L31.30 47.15 L31.30 48.00 L37.50 48.00 L37.50 47.15 L37.50 46.30 L37.50 45.45 L37.50 44.60 L37.50 43.75 L37.50 42.90 L37.50 42.05 L37.50 41.20 L37.50 40.35 L37.50 39.47 L37.48 38.49 L37.44 37.53 L37.39 36.64 L37.34 35.81 L37.30 35.06 L37.28 34.39 L37.28 33.80 L37.31 33.29 L37.37 32.88 L37.45 32.55 L37.54 32.28 L37.66 32.06 L37.81 31.83 L38.03 31.59 L38.36 31.30 L38.94 30.90 L39.65 30.44 L40.42 29.84 L41.16 29.19 L41.84 28.49 L42.47 27.74 L43.04 26.95 L43.56 26.12 L44.02 25.27 L44.43 24.38 L44.77 23.46 L45.06 22.53 L45.29 21.57 L45.45 20.60 L45.55 19.62 L45.58 18.62 L45.53 17.63 L45.41 16.63 L45.22 15.64 L44.95 14.67 L44.60 13.72 L44.17 12.80 L43.67 11.91 L43.10 11.06 L42.45 10.27 L41.74 9.53 L40.98 8.85 L40.16 8.24 L39.30 7.69 L38.39 7.21 L37.46 6.80 L36.50 6.47 L35.51 6.21 L34.51 6.03 L33.51 5.92 L32.50 5.89 L31.49 5.93 L30.49 6.04 L29.50 6.23 L28.53 6.48 L27.58 6.80 L26.65 7.19 L25.76 7.64 L24.90 8.15 L24.08 8.73 L23.32 9.38 L22.62 10.08 L21.98 10.85 L21.41 11.66 L20.90 12.51 L20.47 13.39 L20.10 14.30 L19.81 15.23 L19.59 16.18 L19.43 17.13 L19.35 18.09 L19.32 19.05 L19.36 20.00 L19.46 20.95 L19.62 21.89 L19.81 22.72 Z"/>
      <ellipse cx="28" cy="52" rx="10" ry="7.1" transform="rotate(-25 28 52)"/>
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
