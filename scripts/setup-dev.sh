#!/bin/bash
# Development environment setup script

set -e

echo "🚀 Setting up Recipe Ingestion Pipeline development environment..."

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python $required_version or higher is required (found $python_version)"
    exit 1
fi
echo "✅ Python $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --quiet --upgrade pip

# Install package with dev dependencies
echo "📥 Installing package with development dependencies..."
pip install --quiet -e ".[dev]"

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install

# Create config directory if it doesn't exist
if [ ! -d "config" ]; then
    mkdir -p config
fi

# Copy example config if config doesn't exist
if [ ! -f "config/config.yaml" ] && [ -f "config/config.yaml.example" ]; then
    echo "⚙️  Creating config from example..."
    cp config/config.yaml.example config/config.yaml
    echo "⚠️  Please edit config/config.yaml with your settings"
fi

# Create .env from example if it doesn't exist
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "🔐 Creating .env from example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your settings"
fi

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Edit config/config.yaml with your Obsidian vault path"
echo "  3. Edit .env with your Tailscale auth key (for Docker deployment)"
echo "  4. Run tests: make test"
echo "  5. Start the API server: make run-api"
echo ""
echo "For more information, see README.md and CONTRIBUTING.md"

