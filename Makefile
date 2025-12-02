.PHONY: help install install-dev test lint format type-check clean docker-build docker-up docker-down docker-clean docker-clean-all git-init git-status build build-no-cache run-container

help:  ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install:  ## Install package
	pip install -e .

install-dev:  ## Install package with development dependencies
	pip install -e ".[dev]"

git-init:  ## Initialize git repository (if not already initialized)
	@if [ ! -d .git ]; then \
		git init; \
		git branch -m main; \
		echo "Git repository initialized. Don't forget to add a remote!"; \
	else \
		echo "Git repository already initialized."; \
	fi

git-status:  ## Show git status
	git status

test:  ## Run tests with coverage
	pytest --cov=recipe_ingest --cov-report=term-missing --cov-report=html --ignore=tests/performance

test-unit:  ## Run unit tests only
	pytest tests/unit -v

test-integration:  ## Run integration tests only
	pytest tests/integration -v

lint:  ## Run linters (ruff)
	ruff check src/ tests/

format:  ## Format code with black and ruff
	black src/ tests/
	ruff check --fix src/ tests/

type-check:  ## Run type checker (mypy)
	mypy src/

qa: format lint type-check test  ## Run all quality checks

all: qa test

clean:  ## Clean up generated files
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:  ## Build Docker image locally
	docker build -t recipe-ingest:local .

build-no-cache:  ## Build Docker image without using cache (fixes apt hash mismatches)
	docker build --no-cache --pull -t recipe-ingest:local .

run-container:  ## Run container using docker compose (requires build first, starts recipe-api and dependencies)
	@if ! docker image inspect recipe-ingest:local >/dev/null 2>&1; then \
		echo "Error: Image recipe-ingest:local not found. Run 'make build' first."; \
		exit 1; \
	fi
	@echo "Starting recipe-api container and dependencies..."
	DOCKER_IMAGE=recipe-ingest:local docker compose up -d recipe-api ollama
	@echo "Container started! API available at http://10.0.0.122:8100"
	@echo "View logs with: docker compose logs -f recipe-api"

docker-build: build  ## Build Docker image (alias for build)

docker-clean:  ## Clean Docker build cache and unused resources
	docker builder prune -f
	docker system prune -f --volumes

docker-clean-all:  ## Remove all Docker images and containers (use with caution)
	docker system prune -a -f --volumes

docker-up:  ## Start services with Docker Compose
	docker compose up -d

docker-restart:  ## Restart services
	docker compose restart

docker-down:  ## Stop services
	docker compose down

docker-logs:  ## View service logs
	docker compose logs -f

run-api:  ## Run API server locally
	uvicorn recipe_ingest.api.app:create_app --factory --reload --host 0.0.0.0 --port 8100

run-cli:  ## Run CLI (example)
	recipe-ingest --help

download-models:  ## Download all LLM models configured in .env file
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Please copy .env.example to .env first."; \
		exit 1; \
	fi
	@echo "Downloading Ollama models from .env..."
	@. .env && \
	for model in $$(echo $$OLLAMA_MODELS | tr ',' ' '); do \
		echo "Pulling model: $$model"; \
		ollama pull $$model || echo "Failed to pull $$model"; \
	done
