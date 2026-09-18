#!/bin/sh
set -e

echo "[entrypoint] running database migrations (one-step init)..."
alembic upgrade head

echo "[entrypoint] starting uvicorn on :8000 ..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000