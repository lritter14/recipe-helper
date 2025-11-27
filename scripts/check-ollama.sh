#!/bin/bash
# Check if Ollama is running and accessible

set -e

OLLAMA_ENDPOINT="${OLLAMA_ENDPOINT:-http://localhost:11434}"

echo "🔍 Checking Ollama connectivity..."
echo "Endpoint: $OLLAMA_ENDPOINT"

if curl -f -s "$OLLAMA_ENDPOINT/api/tags" > /dev/null 2>&1; then
    echo "✅ Ollama is running and accessible"
    echo ""
    echo "Available models:"
    curl -s "$OLLAMA_ENDPOINT/api/tags" | python3 -m json.tool | grep '"name"' | cut -d'"' -f4
    exit 0
else
    echo "❌ Cannot connect to Ollama at $OLLAMA_ENDPOINT"
    echo ""
    echo "Please ensure Ollama is installed and running:"
    echo "  1. Install: https://ollama.ai"
    echo "  2. Start: ollama serve"
    echo "  3. Pull a model: ollama pull llama2"
    exit 1
fi
