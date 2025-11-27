#!/bin/bash
# Quick test script to verify llama-server is working with the recipe pipeline

echo "Testing LLM server connection..."
echo ""

# Check if server is running
if curl -f -s "http://localhost:8080/v1/models" > /dev/null 2>&1; then
    echo "✅ Server is running"
    echo ""
    echo "Available models:"
    curl -s "http://localhost:8080/v1/models" | python3 -m json.tool | grep '"id"' | cut -d'"' -f4
    echo ""
    echo "Testing a simple request..."
    
    # Test a simple completion
    curl -s -X POST "http://localhost:8080/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d '{
            "model": "meta-llama-3.1-8b-instruct-q4_0",
            "messages": [{"role": "user", "content": "Say hello"}],
            "max_tokens": 10
        }' | python3 -m json.tool
    
    echo ""
    echo "✅ Connection test complete!"
else
    echo "❌ Server is not running at http://localhost:8080"
    echo "Start it with: llama-server --hf-repo ... -ngl 99 --port 8080"
fi

