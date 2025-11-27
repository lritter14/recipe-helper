#!/bin/bash
# Get Tailscale hostname and IP for API access
# Usage: ./scripts/get-tailscale-info.sh

set -e

echo "🔍 Getting Tailscale connection info..."
echo ""

# Check if container is running
if ! docker ps | grep -q recipe-ingest-tailscale; then
    echo "❌ Tailscale container is not running"
    echo ""
    echo "Start it with: docker-compose up -d"
    exit 1
fi

echo "📡 Tailscale Status:"
echo ""

# Get status from Tailscale container
docker exec recipe-ingest-tailscale tailscale status 2>/dev/null || {
    echo "⚠️  Could not get Tailscale status"
    echo "Container might still be starting up..."
    echo ""
    echo "Check logs with: docker logs recipe-ingest-tailscale"
    exit 1
}

echo ""
echo "📝 API Access Information:"
echo ""

# Try to extract hostname/IP from status
STATUS=$(docker exec recipe-ingest-tailscale tailscale status 2>/dev/null)

# Look for the hostname (usually the first line shows the machine name)
HOSTNAME=$(echo "$STATUS" | head -1 | awk '{print $1}' | sed 's/\.$//' || echo "recipe-ingest")

# Look for IP address (100.x.x.x format)
IP=$(echo "$STATUS" | grep -oE '100\.[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "")

echo "Hostname: $HOSTNAME"
if [ -n "$IP" ]; then
    echo "IP Address: $IP"
fi
echo ""
echo "API URLs:"
echo "  http://${HOSTNAME}:8000/api/v1/recipes"
if [ -n "$IP" ]; then
    echo "  http://${IP}:8000/api/v1/recipes"
fi
echo ""
echo "Health Check:"
echo "  http://${HOSTNAME}:8000/api/v1/health"
if [ -n "$IP" ]; then
    echo "  http://${IP}:8000/api/v1/health"
fi
echo ""
echo "💡 Use one of these URLs in your iOS Shortcut"
echo "   (Hostname is preferred, but IP works if hostname doesn't resolve)"
