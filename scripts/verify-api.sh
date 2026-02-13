#!/bin/bash
# Verify API endpoints for LABLAB
# Usage: ./verify-api.sh [PORT] (default: 8000)

PORT=${1:-8000}
HOST="http://localhost:$PORT"

echo "Verifying API at $HOST..."

# 1. Health Check
echo "1. Checking health..."
curl -s "$HOST/api/health" | grep "ok" || echo "❌ Health check failed"

# 2. RoboDK Status
echo "2. Checking RoboDK status..."
STATUS=$(curl -s "$HOST/api/robodk/status")
echo "   Response: $STATUS"

# 3. Design Objects (Empty initially)
echo "3. Listing design objects..."
OBJECTS=$(curl -s "$HOST/api/robodk/design/objects")
echo "   Response: $OBJECTS"

# 4. Create Object
echo "4. Creating test object..."
CREATE_RES=$(curl -s -X POST "$HOST/api/robodk/design/objects" \
  -H "Content-Type: application/json" \
  -d '{"name": "TestBox", "object_type": "object", "pose": [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]}')
echo "   Response: $CREATE_RES"

# 5. List Objects Again
echo "5. Listing design objects (should have 1)..."
OBJECTS_AGAIN=$(curl -s "$HOST/api/robodk/design/objects")
echo "   Response: $OBJECTS_AGAIN"

echo "Done."
