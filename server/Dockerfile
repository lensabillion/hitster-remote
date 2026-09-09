# The game server: FastAPI + Socket.IO over a long-lived WebSocket.
#
# This CANNOT run on Vercel. Socket.IO needs a connection that stays open, and
# serverless functions are torn down between requests. Anywhere that runs a
# normal long-lived process is fine — Fly.io, Railway, Render.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so code edits do not invalidate the layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Load the RESOLVED deck. No network calls: the track ids were verified once,
# during curation, and are committed as data.
#
# The previous version re-probed Deezer here. That made the build depend on
# Deezer's search being healthy, and it is not always — under throttling Deezer
# answers with an empty result set rather than an error, so the import silently
# produced a near-empty deck and the server then refused to start a game.
RUN python tools/build_deck.py seed decks/deck.json \
    && python tools/build_deck.py list

# Render and Railway inject PORT; Fly sets it in fly.toml. 3001 is the local default.
ENV PORT=3001
EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request,os,sys; \
sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\",\"3001\")}/health').status==200 else 1)"

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-3001}"]
