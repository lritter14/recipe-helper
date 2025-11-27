# Project Setup Summary

This document provides an overview of the Recipe Helper project structure and setup.

## Project Overview

A Python-based system for automated recipe extraction and formatting from multiple sources (text, Instagram, URLs) into an Obsidian vault.

## Technology Stack

- **Language**: Python 3.11+
- **Web Framework**: FastAPI
- **LLM Integration**: llama.cpp (OpenAI-compatible local LLM)
- **Data Validation**: Pydantic v2
- **Testing**: pytest with coverage
- **Linting**: Ruff, Black, mypy
- **Containerization**: Docker with Tailscale sidecar
- **Dependency Management**: pyproject.toml (PEP 621)

## Project Structure

```text
recipe-helper/
├── src/recipe_ingest/           # Main application package
│   ├── api/                     # FastAPI web interface
│   │   ├── app.py              # Application factory
│   │   └── routes.py           # API endpoints
│   ├── core/                    # Core business logic
│   │   ├── extractor.py        # LLM-based recipe extraction
│   │   ├── formatter.py        # Markdown formatting
│   │   └── writer.py           # Vault file operations
│   ├── llm/                     # LLM client integrations
│   │   └── client.py           # OpenAI-compatible LLM client wrapper
│   ├── models/                  # Pydantic data models
│   │   └── recipe.py           # Recipe and metadata models
│   ├── parsers/                 # Input format parsers
│   │   ├── text.py             # Unstructured text parser
│   │   └── instagram.py        # Instagram link parser
│   ├── cli.py                   # Command-line interface
│   └── config.py                # Configuration management
├── tests/                       # Test suite
│   ├── conftest.py             # Pytest fixtures
│   ├── unit/                    # Unit tests
│   │   └── test_models.py
│   └── integration/             # Integration tests
│       └── test_api.py
├── config/                      # Configuration files (deprecated - use env vars)
├── scripts/                     # Utility scripts
│   ├── setup-dev.sh            # Development setup
│   └── check-llm.sh             # LLM server connectivity check
├── pyproject.toml              # Project metadata and dependencies
├── Dockerfile                   # Container image definition
├── docker-compose.yml          # Multi-container orchestration
├── Makefile                    # Common development tasks
├── README.md                   # User documentation
├── CONTRIBUTING.md             # Developer guidelines
└── LICENSE                     # MIT License
```

## Core Components

### 1. Data Models (`models/recipe.py`)

- `MacroNutrients`: Nutritional information (carbs, protein, fat)
- `RecipeMetadata`: Frontmatter fields (title, times, cuisine, etc.)
- `Recipe`: Complete recipe with metadata and content

### 2. Core Processing (`core/`)

- `RecipeExtractor`: Extract structured data from unstructured text using LLM
- `MarkdownFormatter`: Format recipes as markdown with YAML frontmatter
- `VaultWriter`: Write recipes to Obsidian vault with atomic operations

### 3. Input Parsers (`parsers/`)

- `TextParser`: Handle unstructured text input
- `InstagramParser`: Extract captions from Instagram posts

### 4. LLM Integration (`llm/client.py`)

- `LLMClient`: Wrapper for OpenAI-compatible LLM API (llama.cpp) with structured output support

### 5. Interfaces

- **CLI** (`cli.py`): Command-line tool using Click
- **Web API** (`api/`): FastAPI server with REST endpoints

## Configuration

### pyproject.toml

Main configuration file containing:

- **Dependencies**: Core runtime dependencies
- **Dev dependencies**: Testing, linting, type checking tools
- **Tool configuration**: Ruff, mypy, pytest, black, coverage settings
- **Package metadata**: Name, version, authors, entry points

### Linting and Type Checking

- **Ruff**: Fast Python linter (replaces flake8, isort)
  - Line length: 100
  - Enabled rules: pycodestyle, pyflakes, bugbear, comprehensions, pyupgrade
- **Black**: Code formatter (line length: 100)
- **mypy**: Static type checker with strict settings
- **pre-commit**: Automated checks on git commit

### Testing

- **pytest**: Test runner with markers for unit/integration/slow tests
- **pytest-cov**: Coverage reporting (HTML and terminal)
- **pytest-asyncio**: Async test support for FastAPI
- **pytest-mock**: Mocking utilities

Test configuration:

- Source: `src/`
- Tests: `tests/unit/` and `tests/integration/`
- Coverage target: Configured in `pyproject.toml`

## Docker Setup

### Dockerfile

Multi-stage build:

1. **Builder stage**: Install dependencies
2. **Final stage**: Minimal runtime image with non-root user

Features:

- Python 3.11-slim base image
- Non-root user for security
- Health check endpoint
- Optimized for size

### docker-compose.yml

Services:

1. **recipe-api**: Main application service
2. **tailscale**: Network sidecar for remote access

Configuration:

- Shared network mode for Tailscale integration
- Volume mounts for vault and config
- Environment variable configuration
- Health checks for monitoring

## Development Workflow

### Quick Start

```bash
# Run automated setup
./scripts/setup-dev.sh

# Or manual setup
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

### Common Commands

```bash
# Quality checks
make format      # Format code
make lint        # Run linters
make type-check  # Type checking
make test        # Run tests with coverage
make qa          # Run all quality checks

# Development
make run-api     # Start API server
make run-cli     # Show CLI help

# Docker
make docker-build    # Build image
make docker-up       # Start services
make docker-logs     # View logs
make docker-down     # Stop services

# Cleanup
make clean       # Remove generated files
```

## Implementation Status

### ✅ Completed

- [x] Project structure and organization
- [x] Dependency management (pyproject.toml)
- [x] Data models (Pydantic)
- [x] Core stub modules (extractor, formatter, writer)
- [x] Parser stubs (text, Instagram)
- [x] LLM client stub (llama.cpp)
- [x] CLI interface stub (Click)
- [x] Web API stub (FastAPI)
- [x] Configuration management
- [x] Testing infrastructure
- [x] Linting and formatting setup
- [x] Docker and Docker Compose files
- [x] Pre-commit hooks
- [x] Documentation (README, CONTRIBUTING)
- [x] Utility scripts

### 🚧 To Be Implemented

Milestones:

- [ ] **M1**: CLI MVP with LLM extraction
- [ ] **M2**: Web UI implementation
- [ ] **M3**: Instagram link support
- [ ] **M4**: Comprehensive test coverage
- [ ] **M5**: Production containerization
- [ ] **M6**: Mobile integration (Taildrop/tsnet)
- [ ] **M7**: Performance monitoring

## Next Steps

1. **Set up development environment**:
   - Run `./scripts/setup-dev.sh`
   - Set environment variables (RECIPE_INGEST_VAULT_PATH, etc.)
   - Set up `.env` for Docker deployment

2. **Verify dependencies**:
   - Check LLM server: `./scripts/check-llm.sh`
   - Run tests: `make test`

3. **Start implementation**:
   - Begin with M1: CLI MVP
   - Implement LLM extraction in `core/extractor.py`
   - Build markdown formatter in `core/formatter.py`
   - Implement vault writer in `core/writer.py`

4. **Follow development practices**:
   - Write tests first (TDD)
   - Run quality checks before commits
   - Update documentation as you go
   - Follow CONTRIBUTING.md guidelines

## Key Design Decisions

1. **Python over Go**: Faster MVP development with better LLM ecosystem
2. **llama.cpp for LLM**: Local execution, no API costs, privacy, better performance
3. **Pydantic v2**: Modern validation and serialization
4. **FastAPI**: Fast, modern, automatic API docs
5. **Ruff over flake8**: Significantly faster linting
6. **Atomic writes**: Temp file + rename for vault safety
7. **Structured output**: JSON schema for reliable LLM extraction
8. **Tailscale sidecar**: Zero-trust network access
9. **Multi-stage Docker**: Smaller production images

## References

- User documentation: `README.md`
- Developer guide: `CONTRIBUTING.md`
- Dependencies: `pyproject.toml`

---

**Note**: This is a greenfield project with a solid foundation. All core modules have stub implementations ready for development.
