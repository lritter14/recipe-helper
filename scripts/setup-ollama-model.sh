#!/bin/bash
# Pull the required Ollama model in the container
# Usage: ./scripts/setup-ollama-model.sh [model-name]

set -e

MODEL="${1:-llama3.1:8b}"

echo "📥 Pulling Ollama model: $MODEL"
echo ""

# Check if Ollama container is running
if ! docker ps | grep -q recipe-ingest-ollama; then
    echo "❌ Ollama container is not running"
    echo ""
    echo "Start it with: docker-compose up -d ollama"
    exit 1
fi

echo "Pulling model in container..."
docker exec recipe-ingest-ollama ollama pull "$MODEL"

echo ""
echo "✅ Model pulled successfully!"
echo ""
echo "Verify with:"
echo "  docker exec recipe-ingest-ollama ollama list"
