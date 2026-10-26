/* The mark is a record. Its grooves stand in for the years a song can land on,
 * and the one raised point on a groove is the moment you are placing. It is drawn
 * in one colour, taken from the text around it, so it sits in green in the
 * topbar and in ink wherever ink leads. `client/app/icon.svg` carries the same
 * drawing for the favicon; change both together. */

type MarkProps = { size?: number; title?: string; className?: string };

export function Mark({ size = 28, title, className }: MarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      className={className}
      role={title ? "img" : "presentation"}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      focusable="false"
    >
      <circle cx="32" cy="32" r="28" fill="none" stroke="currentColor" strokeWidth="5" />
      <circle cx="32" cy="32" r="19" fill="none" stroke="currentColor" strokeWidth="2.5" />
      <circle cx="32" cy="32" r="11" fill="none" stroke="currentColor" strokeWidth="2.5" />
      <circle cx="32" cy="32" r="3.5" fill="currentColor" />
      <circle
        cx="45.4"
        cy="18.6"
        r="4.6"
        fill="currentColor"
        stroke="var(--ground)"
        strokeWidth="2.5"
      />
    </svg>
  );
}

/* The name. ሸክላ (shekla) is the Amharic word for a record -- the one you put on --
 * which is what every round does. The Ge'ez sits on the display face, the Latin
 * beside it on the text face. `compact` is the topbar form. */
export default function Logo({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return (
      <span className="logo">
        <Mark size={22} className="accent" title="Shekla" />
        <span className="display am" style={{ fontSize: "var(--t-xl)" }}>
          ሸክላ
        </span>
      </span>
    );
  }
  return (
    <div className="logo logo-lg">
      <Mark size={56} className="accent" title="Shekla" />
      <h1 className="display am" style={{ fontSize: "var(--t-3xl)" }}>
        ሸክላ
      </h1>
      <span className="h accent" style={{ fontSize: "var(--t-xl)" }}>
        Shekla
      </span>
    </div>
  );
}
