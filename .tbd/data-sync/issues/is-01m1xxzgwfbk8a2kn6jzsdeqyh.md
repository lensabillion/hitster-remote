---
type: is
id: is-01m1xxzgwfbk8a2kn6jzsdeqyh
title: "Choose and wire the database: SQLite + aiosqlite"
kind: task
status: closed
priority: 1
version: 2
labels:
  - server
  - infra
dependencies: []
created_at: 2026-09-07T12:37:37.295Z
updated_at: 2026-09-07T12:49:02.282Z
closed_at: 2026-09-07T12:49:02.282Z
close_reason: SQLite + aiosqlite wired in server/db.py with WAL; schema covers deck, identities, room seating and timelines.
resolution: null
duplicate_of: null
---
SQLite with WAL, accessed through aiosqlite.

Rationale: the audience is a handful of friends, so a separate database service is pure
operational cost. SQLite is an in-process read at sub-millisecond latency, deploys as a
single file, and needs no connection pooling or network hop. Postgres would add ops
burden for load this will never see.

Split by lifetime:
- DURABLE (SQLite): deck cards, player identities, room records, finished-game history
- EPHEMERAL (memory): live round state, sealed placements, timers

Live round state does not belong in a database — it changes several times per second and
is worthless once the round resolves.
