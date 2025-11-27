#!/bin/bash
# Test API accessibility from remote device (e.g., iPhone via Tailscale)
# Usage: ./scripts/test-api-remote.sh [hostname]

set -e

HOSTNAME="${1:-recipe-ingest}"
PORT="${2:-8000}"
BASE_URL="http://${HOSTNAME}:${PORT}"

echo "🧪 Testing Recipe Pipeline API accessibility"
echo "Hostname: $HOSTNAME"
echo "Port: $PORT"
echo "Base URL: $BASE_URL"
echo ""

# Test 1: Health check
echo "1️⃣ Testing health endpoint..."
if curl -f -s "${BASE_URL}/api/v1/health" > /dev/null 2>&1; then
    echo "✅ Health check passed"
    echo ""
    echo "Health status:"
    curl -s "${BASE_URL}/api/v1/health" | python3 -m json.tool 2>/dev/null || curl -s "${BASE_URL}/api/v1/health"
else
    echo "❌ Health check failed"
    echo ""
    echo "Troubleshooting:"
    echo "  - Is the API server running? (docker ps)"
    echo "  - Is Tailscale connected on this device?"
    echo "  - Is the hostname correct? Try: docker exec recipe-ingest-tailscale tailscale status"
    exit 1
fi

echo ""

# Test 2: Test recipe endpoint (with preview)
echo "2️⃣ Testing recipe endpoint (preview mode)..."
TEST_URL="https://www.instagram.com/p/EXAMPLE"
TEST_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/recipes" \
    -H "Content-Type: application/json" \
    -d "{\"input\": \"${TEST_URL}\", \"format\": \"instagram\", \"preview\": true}" 2>&1)

if echo "$TEST_RESPONSE" | grep -q '"status"'; then
    echo "✅ Recipe endpoint is accessible"
    echo ""
    echo "Response preview:"
    echo "$TEST_RESPONSE" | python3 -m json.tool 2>/dev/null | head -20 || echo "$TEST_RESPONSE" | head -20
else
    echo "⚠️  Recipe endpoint returned unexpected response:"
    echo "$TEST_RESPONSE"
fi

echo ""
echo "✅ API is ready for iOS Shortcuts integration!"
echo ""
echo "Use this URL in your Shortcut:"
echo "  ${BASE_URL}/api/v1/recipes"
echo ""
echo "Example request body:"
echo '  {"input": "https://www.instagram.com/p/...", "format": "instagram"}'

