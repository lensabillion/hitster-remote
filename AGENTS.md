# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

<!-- BEGIN TBD INTEGRATION format=f08 surface=agents-md -->
## tbd

This repository uses **tbd** for git-native issue tracking (beads), spec-driven
planning, and on-demand engineering guidelines.
As the agent, you operate tbd on the user’s behalf: translate their requests into tbd
actions rather than telling them to run commands.

- Run `tbd prime` to load current project state and the full tbd workflow.
- Run `tbd skill` for the complete reusable tbd skill instructions.
- Run `tbd shortcut --list` and `tbd guidelines --list` for on-demand resources.
- Track all work as beads: `tbd create`, `tbd ready`, `tbd close`, and `tbd sync`.

<!-- END TBD INTEGRATION -->

## Build & Test

```bash
# Server (FastAPI + Socket.IO)
cd server
python3 -m venv .venv && ./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/uvicorn main:app --reload --port 3001
./.venv/bin/python -m pytest tests/ -q
./.venv/bin/ruff check .

# Client (Next.js)
cd client
npm install
npm run dev
npm run typecheck && npm run lint && npm run build
```

## Architecture Overview

See [CLAUDE.md](CLAUDE.md) for the working notes and the rules that are easy to get
wrong, and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full picture: round
lifecycle, socket protocol, state split, scoring and matching.

## Conventions & Patterns

- `server/game.py` is pure rules with no I/O; keep it that way and keep it unit tested.
- Never send an unrevealed card to any client. Room state is serialised per viewer.
- The deck is data: `server/decks/deck.json` is exported by the tool and committed,
  never edited by hand.
- Python is linted with ruff (`server/ruff.toml`); the formatter is deliberately not
  enforced. The client is typechecked with `tsc` and linted with `next lint`.
