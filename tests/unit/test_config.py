"""Unit tests for configuration management."""

import pytest

from recipe_ingest.config import Settings, load_settings


class TestSettings:
    """Tests for Settings class."""

    def test_settings_with_defaults(self) -> None:
        """Test that settings can be created with all defaults."""
        settings = Settings()
        assert settings.llm.endpoint == "http://localhost:11434"
        assert settings.llm.model == "llama3.1:8b"
        assert settings.llm.timeout == 120
        assert settings.vault is None
        assert settings.log_level == "INFO"

    def test_settings_with_custom_llm(self) -> None:
        """Test settings with custom LLM configuration."""
        settings = Settings(
            llm={"endpoint": "http://custom:11434", "model": "llama3", "timeout": 60}
        )
        assert settings.llm.endpoint == "http://custom:11434"
        assert settings.llm.model == "llama3"
        assert settings.llm.timeout == 60


class TestLoadSettings:
    """Tests for load_settings function."""

    def test_load_settings_with_defaults(self) -> None:
        """Test loading settings with all defaults."""
        settings = load_settings()
        assert settings.llm.model == "llama3.1:8b"  # Default
        assert settings.llm.endpoint == "http://localhost:11434"
        assert settings.llm.timeout == 120
        assert settings.vault is None
        assert settings.log_level == "INFO"

    def test_load_settings_from_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading settings from environment variables."""
        monkeypatch.setenv("RECIPE_INGEST_LLM_ENDPOINT", "http://test:11434")
        monkeypatch.setenv("RECIPE_INGEST_LLM_MODEL", "test-model")
        monkeypatch.setenv("RECIPE_INGEST_LLM_TIMEOUT", "90")
        monkeypatch.setenv("RECIPE_INGEST_VAULT_PATH", "/test/vault")
        monkeypatch.setenv("RECIPE_INGEST_VAULT_RECIPES_DIR", "recipes")
        monkeypatch.setenv("RECIPE_INGEST_LOG_LEVEL", "DEBUG")

        settings = load_settings()

        assert settings.llm.endpoint == "http://test:11434"
        assert settings.llm.model == "test-model"
        assert settings.llm.timeout == 90
        assert settings.vault is not None
        assert str(settings.vault.path) == "/test/vault"
        assert settings.vault.recipes_dir == "recipes"
        assert settings.log_level == "DEBUG"

    def test_load_settings_with_llm_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that LLM_BASE_URL environment variable is supported."""
        monkeypatch.setenv("LLM_BASE_URL", "http://ollama:11434")
        monkeypatch.setenv("RECIPE_INGEST_LLM_MODEL", "test-model")

        settings = load_settings()

        assert settings.llm.endpoint == "http://ollama:11434"
        assert settings.llm.model == "test-model"

    def test_load_settings_with_partial_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading settings with only some environment variables set."""
        monkeypatch.setenv("RECIPE_INGEST_LLM_MODEL", "custom-model")

        settings = load_settings()

        # Model from env, endpoint from default
        assert settings.llm.model == "custom-model"
        assert settings.llm.endpoint == "http://localhost:11434"
        assert settings.vault is None

    def test_load_settings_env_vars_override_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that environment variables properly override defaults."""
        monkeypatch.setenv("RECIPE_INGEST_LLM_ENDPOINT", "http://custom:11434")
        monkeypatch.setenv("RECIPE_INGEST_LLM_TIMEOUT", "60")

        settings = load_settings()

        assert settings.llm.endpoint == "http://custom:11434"
        assert settings.llm.timeout == 60
        assert settings.llm.model == "llama3.1:8b"  # Still default
