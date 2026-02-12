#!/usr/bin/env bash
# Entrypoint for UI container (Next.js standalone). Usually not needed; image CMD is used.
set -e
export PORT="${PORT:-3000}"
exec node server.js
