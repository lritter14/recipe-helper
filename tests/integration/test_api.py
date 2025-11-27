"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from recipe_ingest.api import create_app


@pytest.fixture
def client() -> TestClient:
    """Create test client for API testing.

    Returns:
        FastAPI test client
    """
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check_returns_200(self, client: TestClient) -> None:
        """Test that health check endpoint returns 200."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_check_structure(self, client: TestClient) -> None:
        """Test health check response structure."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "status" in data
        assert "ollama_connected" in data
        assert "vault_accessible" in data
        assert data["status"] in ["healthy", "unhealthy"]
        assert isinstance(data["ollama_connected"], bool)
        assert isinstance(data["vault_accessible"], bool)


@pytest.mark.integration
class TestRecipeIngestionEndpoint:
    """Tests for recipe ingestion endpoint (basic validation)."""

    def test_ingest_recipe_validation(self, client: TestClient) -> None:
        """Test request validation."""
        response = client.post(
            "/api/v1/recipes",
            json={"input": "", "format": "text"},  # Empty input should fail
        )
        assert response.status_code == 422  # Validation error

    def test_root_route_returns_html(self, client: TestClient) -> None:
        """Test that root route returns HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Recipe Ingestion Pipeline" in response.text
