#!/usr/bin/env bash
# Entrypoint for backend API container. Ensures PORT is set, then runs uvicorn.
set -e
export PORT="${PORT:-8000}"
exec uvicorn apps.api.main:app --host 0.0.0.0 --port "${PORT}"
