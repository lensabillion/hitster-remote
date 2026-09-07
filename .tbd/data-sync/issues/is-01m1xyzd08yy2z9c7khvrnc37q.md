---
type: is
id: is-01m1xyzd08yy2z9c7khvrnc37q
title: "Design pass: user does not like the current look"
kind: task
status: closed
priority: 2
version: 2
labels:
  - design
  - ui
dependencies: []
created_at: 2026-09-07T12:55:01.895Z
updated_at: 2026-09-07T18:54:03.364Z
closed_at: 2026-09-07T18:54:03.363Z
close_reason: "UI pass shipped: one leading element per screen, numbered answer card with visible point values, cleaner higher-contrast palette, class system replacing inline styles. Typography pairing kept deliberately."
resolution: null
duplicate_of: null
---
User reviewed the first build and said the design is not right yet, but explicitly
chose to defer: get the game working first, then improve the look.

Do NOT redesign before the game loop is playable. Revisit once rounds run end to end,
when there is real content on screen to design around rather than a static sample.

Current state, for reference when revisiting:
- Two families, Abyssinica SIL (display) + Noto Sans Ethiopic (text), both covering
  Ethiopic and Latin. The two-family constraint and bilingual coverage should survive
  any redesign; the palette and layout need not.
- Palette is Ethiopian Orthodox manuscript illumination on a committed dark theme.

Worth asking at that point: which part is off — the palette, the density, the card
shape, or the overall mood?
