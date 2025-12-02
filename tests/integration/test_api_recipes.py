"""Integration tests for recipe ingestion API endpoint.

All tests use temporary vault paths (temp_vault fixture) to ensure no files
are written outside the test environment. Files are automatically cleaned up
when the temp_vault fixture tears down.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from recipe_ingest.api import create_app

# Sample data for mocking LLM responses
SAMPLE_RECIPE_JSON = {
    "title": "Test Pasta",
    "prep_time": "10 minutes",
    "cook_time": "20 minutes",
    "cuisine": "Italian",
    "main_ingredient": "Pasta",
    "servings": 2,
    "ingredients": ["200g pasta", "1 cup tomato sauce"],
    "instructions": ["Boil water", "Cook pasta", "Add sauce"],
    "notes": "Simple and quick",
}

SAMPLE_NUTRITION_JSON = {
    "calories_per_serving": 400.0,
    "carbs_grams": 60.0,
    "protein_grams": 12.0,
    "fat_grams": 5.0,
}


@pytest.fixture
def client() -> TestClient:
    """Create test client for API testing.

    Returns:
        FastAPI test client
    """
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    with patch("recipe_ingest.core.service.OllamaClient") as MockClient:
        client_instance = MockClient.return_value
        client_instance.health_check.return_value = True
        # Return the same responses for each call (can be called multiple times)
        client_instance.generate.side_effect = [
            SAMPLE_RECIPE_JSON,
            SAMPLE_NUTRITION_JSON,
        ] * 10  # Provide enough responses for multiple test calls
        yield client_instance


@pytest.fixture
def mock_settings(temp_vault: Path):
    """Mock settings with temporary vault.

    Args:
        temp_vault: Temporary vault path
    """
    with patch("recipe_ingest.api.routes.load_settings") as mock_load:
        from recipe_ingest.config import LLMConfig, Settings, VaultConfig

        mock_settings = Settings(
            llm=LLMConfig(endpoint="http://localhost:11434", model="test-model"),
            vault=VaultConfig(path=temp_vault, recipes_dir="personal/recipes"),
        )
        mock_load.return_value = mock_settings
        yield mock_settings


@pytest.mark.integration
class TestRecipeIngestionEndpoint:
    """Tests for recipe ingestion endpoint."""

    def test_successful_recipe_ingestion(
        self, client: TestClient, mock_llm_client, mock_settings, temp_vault: Path
    ) -> None:
        """Test successful recipe ingestion."""
        response = client.post(
            "/api/v1/recipes",
            json={
                "input": "Make some pasta with tomato sauce.",
                "format": "text",
                "preview": False,
                "overwrite": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["recipe_path"] is not None
        assert data["preview"] is not None
        assert "Test Pasta" in data["preview"]
        assert data["processing_time_ms"] > 0
        assert data["error"] is None

        # Verify file was created
        recipe_file = temp_vault / "personal" / "recipes" / "Test Pasta.md"
        assert recipe_file.exists()

        # Explicit cleanup note: temp_vault fixture automatically cleans up all files
        # when test completes, ensuring no files remain outside test environment

    def test_preview_mode(
        self, client: TestClient, mock_llm_client, mock_settings, temp_vault: Path
    ) -> None:
        """Test preview mode doesn't write file."""
        response = client.post(
            "/api/v1/recipes",
            json={
                "input": "Make some pasta with tomato sauce.",
                "format": "text",
                "preview": True,
                "overwrite": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["recipe_path"] is None  # No file written in preview mode
        assert data["preview"] is not None
        assert "Test Pasta" in data["preview"]

        # Verify file was NOT created
        recipe_file = temp_vault / "personal" / "recipes" / "Test Pasta.md"
        assert not recipe_file.exists()

        # Explicit cleanup note: temp_vault fixture automatically cleans up
        # when test completes, ensuring no files remain outside test environment

    def test_duplicate_detection(
        self, client: TestClient, mock_llm_client, mock_settings, temp_vault: Path
    ) -> None:
        """Test duplicate detection returns 409."""
        # Create first recipe
        response1 = client.post(
            "/api/v1/recipes",
            json={
                "input": "Make some pasta with tomato sauce.",
                "format": "text",
                "preview": False,
                "overwrite": False,
            },
        )
        assert response1.status_code == 200

        # Try to create duplicate
        response2 = client.post(
            "/api/v1/recipes",
            json={
                "input": "Make some pasta with tomato sauce.",
                "format": "text",
                "preview": False,
                "overwrite": False,
            },
        )

        assert response2.status_code == 409
        data = response2.json()
        assert "already exists" in data["detail"].lower()

        # Explicit cleanup note: temp_vault fixture automatically cleans up all files
        # when test completes, ensuring no files remain outside test environment

    def test_overwrite_with_matching_ingredients(
        self, client: TestClient, mock_llm_client, mock_settings, temp_vault: Path
    ) -> None:
        """Test overwrite succeeds when ingredients match."""
        # Reset mock to provide fresh responses for second call
        mock_llm_client.generate.side_effect = [
            SAMPLE_RECIPE_JSON,
            SAMPLE_NUTRITION_JSON,
        ] * 5  # Enough for multiple calls

        # Create first recipe
        response1 = client.post(
            "/api/v1/recipes",
            json={
                "input": "Make some pasta with tomato sauce.",
                "format": "text",
                "preview": False,
                "overwrite": False,
            },
        )
        assert response1.status_code == 200

        # Overwrite with same ingredients (mocked to match)
        # The service will read the existing file and compare ingredients
        # Since we're using the same SAMPLE_RECIPE_JSON, ingredients will match
        response2 = client.post(
            "/api/v1/recipes",
            json={
                "input": "Make some pasta with tomato sauce.",
                "format": "text",
                "preview": False,
                "overwrite": True,
            },
        )

        # Should succeed (ingredients match in our mock)
        assert response2.status_code == 200
        data = response2.json()
        assert data["status"] == "success"

        # Explicit cleanup note: temp_vault fixture automatically cleans up all files
        # when test completes, ensuring no files remain outside test environment

    def test_invalid_input_returns_422(self, client: TestClient) -> None:
        """Test invalid input returns 422."""
        response = client.post(
            "/api/v1/recipes",
            json={"input": "", "format": "text"},  # Empty input
        )
        assert response.status_code == 422

    def test_missing_vault_config_returns_503(
        self, client: TestClient, mock_llm_client
    ) -> None:
        """Test missing vault config returns 503."""
        with patch("recipe_ingest.api.routes.load_settings") as mock_load:
            from recipe_ingest.config import LLMConfig, Settings

            mock_settings = Settings(
                llm=LLMConfig(endpoint="http://localhost:11434", model="test-model"),
                vault=None,  # No vault configured
            )
            mock_load.return_value = mock_settings

            response = client.post(
                "/api/v1/recipes",
                json={
                    "input": "Test recipe",
                    "format": "text",
                },
            )

            assert response.status_code == 503
            assert "temporarily unavailable" in response.json()["detail"].lower()

    def test_processing_time_measured(
        self, client: TestClient, mock_llm_client, mock_settings, temp_vault: Path
    ) -> None:
        """Test that processing time is measured and returned."""
        response = client.post(
            "/api/v1/recipes",
            json={
                "input": "Make some pasta with tomato sauce.",
                "format": "text",
                "preview": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "processing_time_ms" in data
        assert isinstance(data["processing_time_ms"], int | float)
        assert data["processing_time_ms"] >= 0

    def test_preview_always_included(
        self, client: TestClient, mock_llm_client, mock_settings, temp_vault: Path
    ) -> None:
        """Test that preview markdown is always included in response."""
        response = client.post(
            "/api/v1/recipes",
            json={
                "input": "Make some pasta with tomato sauce.",
                "format": "text",
                "preview": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["preview"] is not None
        assert isinstance(data["preview"], str)
        assert len(data["preview"]) > 0


@pytest.mark.integration
class TestHealthCheckEndpoint:
    """Tests for health check endpoint."""

    def test_health_check_with_ollama_available(
        self, client: TestClient, temp_vault: Path
    ) -> None:
        """Test health check when Ollama is available."""
        with (
            patch("recipe_ingest.api.routes.load_settings") as mock_load,
            patch("recipe_ingest.api.routes.OllamaClient") as MockClient,
        ):
            from recipe_ingest.config import LLMConfig, Settings, VaultConfig

            mock_settings = Settings(
                llm=LLMConfig(endpoint="http://localhost:11434", model="test-model"),
                vault=VaultConfig(path=temp_vault, recipes_dir="personal/recipes"),
            )
            mock_load.return_value = mock_settings

            client_instance = MockClient.return_value
            client_instance.health_check.return_value = True

            response = client.get("/api/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert data["ollama_connected"] is True
            assert data["vault_accessible"] is True
            assert data["status"] == "healthy"

    def test_health_check_with_ollama_unavailable(
        self, client: TestClient, temp_vault: Path
    ) -> None:
        """Test health check when Ollama is unavailable."""
        with (
            patch("recipe_ingest.api.routes.load_settings") as mock_load,
            patch("recipe_ingest.api.routes.OllamaClient") as MockClient,
        ):
            from recipe_ingest.config import LLMConfig, Settings, VaultConfig

            mock_settings = Settings(
                llm=LLMConfig(endpoint="http://localhost:11434", model="test-model"),
                vault=VaultConfig(path=temp_vault, recipes_dir="personal/recipes"),
            )
            mock_load.return_value = mock_settings

            client_instance = MockClient.return_value
            client_instance.health_check.return_value = False

            response = client.get("/api/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert data["ollama_connected"] is False
            assert data["vault_accessible"] is True
            assert data["status"] == "unhealthy"

    def test_health_check_with_vault_inaccessible(self, client: TestClient) -> None:
        """Test health check when vault is inaccessible."""
        with (
            patch("recipe_ingest.api.routes.load_settings") as mock_load,
            patch("recipe_ingest.api.routes.OllamaClient") as MockClient,
        ):
            from pathlib import Path

            from recipe_ingest.config import LLMConfig, Settings, VaultConfig

            # Use non-existent vault path
            mock_settings = Settings(
                llm=LLMConfig(endpoint="http://localhost:11434", model="test-model"),
                vault=VaultConfig(
                    path=Path("/nonexistent/vault/path"),
                    recipes_dir="personal/recipes",
                ),
            )
            mock_load.return_value = mock_settings

            client_instance = MockClient.return_value
            client_instance.health_check.return_value = True

            response = client.get("/api/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert data["ollama_connected"] is True
            assert data["vault_accessible"] is False
            assert data["status"] == "unhealthy"
