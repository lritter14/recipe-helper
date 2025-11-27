# Recipe Ingestion Pipeline

Automated recipe extraction and formatting for Obsidian vault. Extract recipes from unstructured text, Instagram posts, or URLs and automatically format them into your Obsidian vault.

## Features

- **Multiple input formats**: Unstructured text, Instagram URLs, or copied content
- **LLM-powered extraction**: Uses llama.cpp for intelligent recipe parsing
- **Structured output**: Consistent markdown format with YAML frontmatter
- **Nutritional estimates**: Automatic calorie and macro calculations
- **CLI and Web UI**: Use via command line or web interface
- **Remote access**: Tailscale integration for access from any device
- **Atomic writes**: Safe file operations with duplicate detection

## Quick Start

### Prerequisites

- Python 3.11+
- [llama.cpp](https://github.com/ggerganov/llama.cpp) installed via `brew install llama.cpp`
- llama-server running (e.g., `llama-server -m *.gguf -ngl 99`)
- Docker and Docker Compose (for containerized deployment)
- Obsidian vault with `personal/recipes/` directory

### Installation

Clone the repository and install dependencies:

```bash
git clone <repository-url>
cd recipe-pipeline
pip install -e ".[dev]"
```

### Usage

#### CLI

Process a recipe from text:

```bash
recipe-ingest "Ingredients: flour, sugar, eggs..."
```

Process from file:

```bash
recipe-ingest --file recipe.txt
```

Process Instagram post:

```bash
recipe-ingest "https://www.instagram.com/p/..."
```

#### Web UI

Start the development server:

```bash
uvicorn recipe_ingest.api.app:create_app --factory --reload
```

Visit `http://localhost:8000` to access the web interface.

The web UI provides:
- Text input area for pasting recipes
- Preview mode to see formatted output without saving
- Overwrite option (only if ingredients match exactly)
- Real-time processing with progress indicators
- Formatted markdown preview

#### Docker Deployment

Build and run with Docker Compose:

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Set TS_AUTHKEY, VAULT_PATH, etc.

# Start services
docker-compose up -d
```

## Development

### Setup Development Environment

Install with development dependencies:

```bash
pip install -e ".[dev]"
```

Install pre-commit hooks:

```bash
pre-commit install
```

### Running Tests

Run all tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=recipe_ingest --cov-report=html
```

Run only unit tests:

```bash
pytest -m unit
```

### Code Quality

Format code:

```bash
black src/ tests/
```

Lint code:

```bash
ruff check src/ tests/
```

Type check:

```bash
mypy src/
```

## Configuration

### Config File

Create `~/.config/recipe-ingest/config.yaml`:

```yaml
llm:
  endpoint: "http://localhost:8080"
  model: "qwen"
  timeout: 120

vault:
  path: "/path/to/obsidian/vault"
  recipes_dir: "personal/recipes"

log_level: "INFO"
```

### Environment Variables

Configuration can also be set via environment variables:

- `RECIPE_INGEST_LLM__ENDPOINT`: LLM server endpoint URL
- `RECIPE_INGEST_LLM__MODEL`: Model name
- `RECIPE_INGEST_VAULT__PATH`: Vault path
- `RECIPE_INGEST_LOG_LEVEL`: Logging level

## Project Structure

```text
recipe-pipeline/
├── src/recipe_ingest/       # Main application package
│   ├── api/                 # FastAPI web interface
│   ├── core/                # Core processing logic
│   ├── llm/                 # LLM client integrations
│   ├── models/              # Pydantic data models
│   ├── parsers/             # Input parsers (text, Instagram)
│   ├── cli.py               # CLI interface
│   └── config.py            # Configuration management
├── tests/                   # Test suite
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
├── config/                  # Configuration files
├── pyproject.toml           # Project metadata and dependencies
├── Dockerfile               # Container image definition
└── docker-compose.yml       # Multi-container orchestration
```

## Roadmap

See `intro.md` for detailed project plan and milestones.

- [x] Project setup and structure
- [ ] M1: CLI MVP with unstructured text
- [ ] M2: Web UI (chatbot-like interface)
- [ ] M3: Instagram link support
- [ ] M4: Testing infrastructure
- [ ] M5: Containerization and Tailscale
- [ ] M6: Mobile integration
- [ ] M7: Performance monitoring

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linters
4. Submit a pull request

## License

MIT License - see LICENSE file for details
