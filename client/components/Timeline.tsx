"use client";

import { Fragment, useState } from "react";

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

  // One slot before every card, and one after the last.
  const slot = (i: number) =>
    interactive ? (
      <Gap index={i} selected={selected === i} onSelect={choose} />
    ) : (
      <div className="tl-spacer" aria-hidden />
    );

  return (
    <div className="tl">
      {cards.map((card, i) => (
        <Fragment key={card.id}>
          {slot(i)}
          <article className="tl-card">
            <div className="tl-year">{card.year}</div>
            <div className="stack" style={{ gap: 3 }}>
              <div className="tl-title am">{card.titleAm || card.titleLatin}</div>
              <div className="tl-artist am">{card.artistAm || card.artistLatin}</div>
            </div>
          </article>
        </Fragment>
      ))}
      {slot(cards.length)}
    </div>
  );
}
