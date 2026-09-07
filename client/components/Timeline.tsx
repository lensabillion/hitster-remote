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

/* The timeline: a scrolling rail of cards with tappable slots between them.
 *
 * Placement is by tapping a gap, never by dragging. A drag target is fiddly on a
 * phone and this is played one-handed while on a call.
 *
 * The year is the largest thing on a card because the year is what the round is
 * about. Amharic title next, Latin artist last and small — enough to recognise a
 * card at a glance without turning it into a paragraph. */

function Gap({
  index,
  selected,
  onSelect,
}: {
  index: number;
  selected: boolean;
  onSelect: (i: number) => void;
}) {
  return (
    <button
      className={`tl-gap${selected ? " tl-gap-on" : ""}`}
      onClick={() => onSelect(index)}
      aria-label={`Place the song in position ${index + 1}`}
      aria-pressed={selected}
    >
      {selected ? "?" : "+"}
    </button>
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

  if (!cards.length && !interactive) {
    return <p className="tl-empty">No cards yet.</p>;
  }

  return (
    <div className="tl">
      {cards.map((card, i) => (
        <div key={card.id} style={{ display: "contents" }}>
          {interactive ? (
            <Gap index={i} selected={selected === i} onSelect={choose} />
          ) : (
            <div className="tl-spacer" aria-hidden />
          )}
          <article className="tl-card">
            <div className="tl-year">{card.year}</div>
            <div className="stack" style={{ gap: 3 }}>
              <div className="tl-title am">{card.titleAm || card.titleLatin}</div>
              <div className="tl-artist am">{card.artistAm || card.artistLatin}</div>
            </div>
          </article>
        </div>
      ))}
      {interactive ? (
        <Gap
          index={cards.length}
          selected={selected === cards.length}
          onSelect={choose}
        />
      ) : (
        <div className="tl-spacer" aria-hidden />
      )}
    </div>
  );
}
