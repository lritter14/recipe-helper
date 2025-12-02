# Contributing to Recipe Helper

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- Make (optional, for convenience commands)
- Docker and Docker Compose (for containerized testing)

### Getting Started

Clone the repository:

```bash
git clone <repository-url>
cd recipe-helper
```

Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install development dependencies:

```bash
make install-dev
# or
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Write clean, readable code
- Follow the existing code style
- Add docstrings to new functions and classes
- Update type hints as needed

### 3. Write Tests

- Add unit tests for new functionality
- Add integration tests for end-to-end flows
- Ensure tests are focused and descriptive
- Aim for high test coverage

### 4. Run Quality Checks

Run all checks:

```bash
make qa
```

Or run individually:

```bash
make format      # Format code
make lint        # Run linters
make type-check  # Run type checker
make test        # Run tests
```

### 5. Commit Your Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "Add feature: description of what you added"
```

Pre-commit hooks will automatically run formatters and linters.

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Code Style Guidelines

### Python Style

- Follow PEP 8 conventions
- Use type hints for function parameters and return values
- Maximum line length: 100 characters
- Use descriptive variable and function names
- Prefer explicit over implicit

### Docstrings

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """Brief description of function.

    Longer description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: Description of when this is raised
    """
    pass
```

### Testing

- Test files should mirror source structure: `tests/unit/test_<module>.py`
- Use descriptive test names: `test_<function>_<scenario>_<expected_outcome>`
- Use fixtures for common test data
- Mark integration tests with `@pytest.mark.integration`
- Mark performance tests with `@pytest.mark.performance`

Example:

```python
class TestRecipeExtractor:
    """Tests for RecipeExtractor class."""

    def test_extract_with_valid_text_returns_recipe(self) -> None:
        """Test that extract returns a Recipe object for valid input."""
        # Arrange
        extractor = RecipeExtractor()
        text = "..."

        # Act
        result = extractor.extract(text)

        # Assert
        assert isinstance(result, Recipe)
        assert result.metadata.title
```

## Project Structure

```text
src/recipe_ingest/
├── api/              # FastAPI web interface
├── core/             # Core business logic
├── llm/              # LLM client integrations
├── models/           # Data models
├── parsers/          # Input parsers
├── cli.py            # CLI interface
└── config.py         # Configuration
```

## Adding New Features

### Adding a New Parser

Create a new parser in `src/recipe_ingest/parsers/`:

```python
# src/recipe_ingest/parsers/my_parser.py
class MyParser:
    """Parse recipes from custom source."""

    def parse(self, input: str) -> str:
        """Parse input and return cleaned text."""
        # Implementation
        pass
```

Add tests in `tests/unit/test_my_parser.py`.

Update `__init__.py` to export the new parser.

### Adding API Endpoints

Add new endpoints in `src/recipe_ingest/api/routes.py`:

```python
@router.post("/my-endpoint")
async def my_endpoint(request: MyRequest) -> MyResponse:
    """Endpoint description."""
    # Implementation
    pass
```

Add integration tests in `tests/integration/test_api.py`.

## Running Tests

Run all tests:

```bash
pytest
```

Run specific test file:

```bash
pytest tests/unit/test_models.py
```

Run with coverage report:

```bash
pytest --cov=recipe_ingest --cov-report=html
```

View coverage report:

```bash
open htmlcov/index.html
```

## Debugging

### CLI Debugging

Run with verbose logging:

```bash
recipe-ingest --verbose "recipe text..."
```

### API Debugging

Run with auto-reload:

```bash
uvicorn recipe_ingest.api.app:create_app --factory --reload --log-level debug
```

### Docker Debugging

View logs:

```bash
docker-compose logs -f recipe-api
```

Enter container:

```bash
docker-compose exec recipe-api /bin/bash
```

## Common Issues

### Import Errors

If you get import errors, ensure the dependencies are installed:

```bash
pip install -r requirements.txt
```

### Type Checking Errors

Some libraries may not have type stubs. Add them to the `mypy.ini` file:

```ini
[mypy-my_library.*]
ignore_missing_imports = true
```

### Pre-commit Hook Failures

If pre-commit hooks fail, fix the issues and try again:

```bash
make format
git add .
git commit -m "Your message"
```

## Questions?

If you have questions or need help, please:

1. Check the README.md
2. Review the project documentation
3. Open an issue on GitHub

Thank you for contributing!
