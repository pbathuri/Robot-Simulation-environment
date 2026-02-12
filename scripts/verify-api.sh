#!/usr/bin/env bash
# Verify LABLAB API endpoints (run after docker compose up or make run)
# Usage: ./scripts/verify-api.sh [PORT]
# Example: ./scripts/verify-api.sh 8001   (when using docker-compose with 8001:8000)

set -e
PORT="${1:-8000}"
BASE="http://127.0.0.1:${PORT}"

echo "=== Verifying API at ${BASE} ==="
echo ""

echo "1. GET /health"
curl -s "${BASE}/health" | head -c 200
echo ""
echo ""

echo "2. GET /api/robodk/status"
curl -s "${BASE}/api/robodk/status" | head -c 300
echo ""
echo ""

echo "3. GET /api/robodk/design/objects"
curl -s "${BASE}/api/robodk/design/objects" | head -c 200
echo ""
echo ""

echo "4. POST /api/robodk/design/objects (create test object)"
curl -s -X POST "${BASE}/api/robodk/design/objects" \
  -H "Content-Type: application/json" \
  -d '{"name":"VerifyTest","object_type":"object"}' | head -c 300
echo ""
echo ""

echo "5. GET /api/robodk/design/objects (list again)"
curl -s "${BASE}/api/robodk/design/objects" | head -c 400
echo ""
echo ""

echo "=== Done. All endpoints responded. ==="
