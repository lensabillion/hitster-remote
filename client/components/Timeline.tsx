"use client";

import { useState } from "react";

export type Card = {
  id: string;
  year: number;
  artistAm: string;
  titleAm: string;
  artistLatin: string;
  titleLatin: string;
};

/* The timeline is the centrepiece: it is what every player looks at, and it is
 * where the whole game is played. Two decisions carry it.
 *
 * Placement is by gap, not by drag. A drag target on a phone is a fiddly thing
 * and this is played one-handed on a call; tapping the space between two cards
 * is unambiguous and needs no pointer precision.
 *
 * The year is set in the display face at the largest size on the page, because
 * the year is the answer -- it is what the round is about, and what the reveal
 * lands on. */

function Gap({
  index,
  selected,
  onSelect,
  interactive,
}: {
  index: number;
  selected: boolean;
  onSelect: (i: number) => void;
  interactive: boolean;
}) {
  if (!interactive) return <div style={{ width: 10 }} aria-hidden />;
  return (
    <button
      onClick={() => onSelect(index)}
      aria-label={`Place here, position ${index + 1}`}
      aria-pressed={selected}
      style={{
        width: selected ? 74 : 26,
        alignSelf: "stretch",
        minHeight: 128,
        borderRadius: 2,
        border: selected
          ? "1px solid var(--gold)"
          : "1px dashed var(--rule)",
        background: selected ? "var(--gold-wash)" : "transparent",
        transition: "width 160ms ease, background 160ms ease",
        display: "grid",
        placeItems: "center",
        flexShrink: 0,
      }}
    >
      <span
        className="display"
        style={{
          fontSize: selected ? "var(--t-lg)" : "var(--t-md)",
          color: selected ? "var(--gold)" : "var(--ink-faint)",
          lineHeight: 1,
        }}
      >
        {selected ? "?" : "+"}
      </span>
    </button>
  );
}

function CardFace({ card }: { card: Card }) {
  return (
    <article
      className="surface"
      style={{
        width: 168,
        flexShrink: 0,
        padding: "14px 14px 12px",
        display: "flex",
        flexDirection: "column",
        gap: 10,
        minHeight: 128,
      }}
    >
      <div
        className="display numeral"
        style={{
          fontSize: "var(--t-xl)",
          color: "var(--gold)",
          lineHeight: 1,
        }}
      >
        {card.year}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <div
          className="amharic"
          style={{
            fontSize: "var(--t-base)",
            fontWeight: 600,
            color: "var(--ink)",
          }}
        >
          {card.titleAm || card.titleLatin}
        </div>
        <div
          className="amharic"
          style={{ fontSize: "var(--t-sm)", color: "var(--ink-soft)" }}
        >
          {card.artistAm || card.artistLatin}
        </div>
        <div
          style={{
            fontSize: "var(--t-xs)",
            color: "var(--ink-faint)",
            letterSpacing: "0.02em",
            marginTop: 2,
          }}
        >
          {card.artistLatin}
        </div>
      </div>
    </article>
  );
}

export default function Timeline({
  cards,
  interactive = false,
  onPlace,
}: {
  cards: Card[];
  interactive?: boolean;
  onPlace?: (gap: number) => void;
}) {
  const [selected, setSelected] = useState<number | null>(null);

  function choose(i: number) {
    setSelected(i);
    onPlace?.(i);
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "stretch",
        gap: 6,
        overflowX: "auto",
        padding: "4px 2px 12px",
      }}
    >
      {cards.map((card, i) => (
        <div key={card.id} style={{ display: "contents" }}>
          <Gap
            index={i}
            selected={selected === i}
            onSelect={choose}
            interactive={interactive}
          />
          <CardFace card={card} />
        </div>
      ))}
      <Gap
        index={cards.length}
        selected={selected === cards.length}
        onSelect={choose}
        interactive={interactive}
      />
    </div>
  );
}
