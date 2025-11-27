#!/bin/sh

# start-tailscale.sh - Start Tailscale service for recipe-ingest API
# Usage: start-tailscale.sh <service_name> <port>
# Example: start-tailscale.sh recipe-ingest 8000

set -eux

# Check if required arguments are provided
if [ $# -ne 2 ]; then
    echo "Usage: $0 <service_name> <port>"
    echo "Example: $0 recipe-ingest 8000"
    exit 1
fi

SERVICE_NAME="$1"
PORT="$2"

# Check if TS_AUTH_KEY is set
if [ -z "${TS_AUTH_KEY:-}" ]; then
    echo "Error: TS_AUTH_KEY environment variable is not set"
    exit 1
fi

echo "Starting Tailscale for service: $SERVICE_NAME on port: $PORT"

# Start tailscaled in userspace networking mode
tailscaled --tun=userspace-networking &

# Wait for tailscaled to be ready and connect to Tailscale
echo "Connecting to Tailscale network..."

until tailscale up --authkey="$TS_AUTH_KEY" --hostname="$SERVICE_NAME" --accept-dns=false; do
    echo "Retrying connection in 2 seconds..."
    sleep 2
done

echo "Successfully connected to Tailscale network as $SERVICE_NAME"

# Start serving the local port
echo "Starting Tailscale serve for http://127.0.0.1:$PORT"
tailscale serve --bg "http://127.0.0.1:$PORT"

echo "Tailscale service started successfully for $SERVICE_NAME"
echo "Service is now accessible via Tailscale network"

# Keep the container running
tail -f /dev/null
