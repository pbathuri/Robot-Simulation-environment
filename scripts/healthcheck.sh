#!/usr/bin/env bash
# Healthcheck for backend API. Exit 0 if /api/health returns OK.
set -e
url="${1:-http://127.0.0.1:8000/api/health}"
curl -sf "$url" >/dev/null || exit 1
