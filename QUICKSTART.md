# Quick Start Guide

Get up and running with Recipe Helper in 5 minutes.

## Prerequisites Checklist

Before you begin, ensure you have:

- [ ] Python 3.11 or higher installed
- [ ] Git installed
- [ ] llama.cpp installed via `brew install llama.cpp`
- [ ] llama-server running with a model (e.g., `llama-server -m *.gguf -ngl 99`)
- [ ] An Obsidian vault with a `personal/recipes/` directory

## Setup Steps

### 1. Clone and Setup (1 minute)

```bash
# Clone the repository
cd /path/to/your/projects
git clone <repository-url>
cd recipe-helper

# Run automated setup script
./scripts/setup-dev.sh
```

The script will:

- Create a Python virtual environment
- Install all dependencies
- Set up pre-commit hooks

### 2. Configure Environment Variables (1 minute)

Set your Obsidian vault path and LLM settings:

```bash
export RECIPE_INGEST_VAULT_PATH="/Users/your-name/Documents/ObsidianVault"
export RECIPE_INGEST_VAULT_RECIPES_DIR="personal/recipes"
export RECIPE_INGEST_LLM_ENDPOINT="http://localhost:11434"
export RECIPE_INGEST_LLM_MODEL="llama3.1:8b"
```

Or create a `.env` file in the project root (if using python-dotenv):

```bash
RECIPE_INGEST_VAULT_PATH=/Users/your-name/Documents/ObsidianVault
RECIPE_INGEST_VAULT_RECIPES_DIR=personal/recipes
RECIPE_INGEST_LLM_ENDPOINT=http://localhost:11434
RECIPE_INGEST_LLM_MODEL=llama3.1:8b
```

### 3. Verify LLM Server (30 seconds)

```bash
# Check if LLM server is running
./scripts/check-llm.sh
```

If not running:

```bash
# Install llama.cpp if not already installed
brew install llama.cpp

# Download a model (e.g., Qwen in int8 or Mistral Small 3.1 24B in int4)
# Then start the server
llama-server -m *.gguf -ngl 99
```

### 4. Run Tests (1 minute)

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Run tests to verify setup
make test
```

You should see all tests pass (some are stubs for now).

### 5. Try the CLI (30 seconds)

```bash
# Check CLI is working
recipe-ingest --help

# Try a test run
recipe-ingest "Ingredients: 2 cups flour, 1 cup sugar. Instructions: Mix and bake."
```

### 6. Try the Web UI (1 minute)

```bash
# Start the web server
uvicorn recipe_ingest.api.app:create_app --factory --reload

# In your browser, visit:
# http://localhost:8000
```

The web UI provides:

- Simple text input for pasting recipes
- Preview mode to see formatted output before saving
- Overwrite option (only if ingredients match exactly)
- Real-time processing feedback

## Development Workflow

### Daily Development

```bash
# Activate environment
source venv/bin/activate

# Make your changes...

# Run quality checks before committing
make qa

# Or run individually:
make format      # Format code
make lint        # Check linting
make type-check  # Type checking
make test        # Run tests
```

### Working on Features

```bash
# Create a feature branch
git checkout -b feature/my-feature

# Implement your changes

# Run tests
make test

# Check everything passes
make qa

# Commit (pre-commit hooks will run automatically)
git commit -m "Add feature: description"
```

### Running the API Server

```bash
# Start development server
make run-api

# Or directly with uvicorn
uvicorn recipe_ingest.api.app:create_app --factory --reload
```

Visit <http://localhost:8000/docs> for API documentation.

## Docker Deployment (Optional)

For production deployment with Tailscale:

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# - Set TS_AUTHKEY from Tailscale admin
# - Set VAULT_PATH to your vault location

# Start services
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

## What's Next?

Now that your environment is set up, you can:

1. **Implement M1 features** (CLI MVP):
   - Recipe extraction in `src/recipe_ingest/core/extractor.py`
   - Markdown formatting in `src/recipe_ingest/core/formatter.py`
   - Vault writing in `src/recipe_ingest/core/writer.py`

2. **Write tests as you go**:
   - Unit tests in `tests/unit/`
   - Integration tests in `tests/integration/`

3. **Read the documentation**:
   - `README.md` - User documentation
   - `CONTRIBUTING.md` - Development guidelines
   - `SETUP.md` - Detailed setup information

## Troubleshooting

### "Command not found: recipe-ingest"

Make sure the virtual environment is activated:

```bash
source venv/bin/activate
```

### "Cannot connect to LLM server"

Start llama-server:

```bash
# Make sure you have a model file (*.gguf) in the current directory
llama-server -m *.gguf -ngl 99
```

### Import errors

Reinstall the package:

```bash
pip install -e ".[dev]"
```

### Pre-commit hooks failing

Update pre-commit:

```bash
pre-commit autoupdate
pre-commit install
```

## Useful Commands Reference

```bash
# Environment
source venv/bin/activate          # Activate venv
deactivate                        # Deactivate venv

# Development
make format                       # Format code
make lint                         # Run linters
make type-check                   # Type checking
make test                         # Run all tests
make test-unit                    # Unit tests only
make test-integration             # Integration tests only
make qa                           # All quality checks

# Running
make run-api                      # Start API server
make run-cli                      # CLI help

# Docker
make docker-build                 # Build images
make docker-up                    # Start containers
make docker-down                  # Stop containers
make docker-logs                  # View logs

# Cleanup
make clean                        # Remove generated files
```

## Getting Help

- Check `README.md` for detailed documentation
- Read `CONTRIBUTING.md` for development guidelines
- Check `SETUP.md` for architecture overview

---

**Ready to code?** Start with implementing the LLM extraction in `src/recipe_ingest/core/extractor.py`!
