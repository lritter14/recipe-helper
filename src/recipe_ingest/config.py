"""Configuration management."""

import logging
import os
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class LLMConfig(BaseModel):
    """LLM configuration."""

    endpoint: str = Field(default="http://localhost:11434", description="Ollama endpoint URL")
    model: str = Field(default="llama3.1:8b", description="Model name")
    timeout: int = Field(default=120, description="Request timeout in seconds")


class VaultConfig(BaseModel):
    """Obsidian vault configuration."""

    path: Path = Field(..., description="Path to Obsidian vault root")
    recipes_dir: str = Field(
        default="personal/recipes", description="Relative path to recipes directory"
    )


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="RECIPE_INGEST_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM configuration")
    vault: VaultConfig | None = Field(default=None, description="Vault configuration")
    log_level: str = Field(default="INFO", description="Logging level")


def load_settings() -> Settings:
    """Load application settings from environment variables.

    Returns:
        Application settings instance
    """
    try:
        # Map single-underscore env vars to double-underscore format for Pydantic
        # This allows using RECIPE_INGEST_LLM_ENDPOINT (single underscore) instead of RECIPE_INGEST_LLM__ENDPOINT (double underscore)
        # Pydantic requires double underscores for nested config (e.g., RECIPE_INGEST_VAULT__RECIPES_DIR)
        env_mapping = {
            "RECIPE_INGEST_LLM_ENDPOINT": "RECIPE_INGEST_LLM__ENDPOINT",
            "RECIPE_INGEST_LLM_MODEL": "RECIPE_INGEST_LLM__MODEL",
            "RECIPE_INGEST_LLM_TIMEOUT": "RECIPE_INGEST_LLM__TIMEOUT",
            "RECIPE_INGEST_VAULT_PATH": "RECIPE_INGEST_VAULT__PATH",
            "RECIPE_INGEST_VAULT_RECIPES_DIR": "RECIPE_INGEST_VAULT__RECIPES_DIR",
        }

        # Track which env vars we set so we can clean them up
        env_vars_set = []

        # Temporarily set double-underscore vars from single-underscore vars
        # Only map if the double-underscore version doesn't already exist
        for single_underscore_key, double_underscore_key in env_mapping.items():
            if single_underscore_key in os.environ and double_underscore_key not in os.environ:
                os.environ[double_underscore_key] = os.environ[single_underscore_key]
                env_vars_set.append(double_underscore_key)

        try:
            settings = Settings()
        finally:
            # Clean up the environment variables we set
            for key in env_vars_set:
                os.environ.pop(key, None)

        # Support LLM_BASE_URL as a simpler alternative to RECIPE_INGEST_LLM_ENDPOINT
        # This allows using the service name pattern: LLM_BASE_URL=http://ollama:11434
        llm_base_url = os.getenv("LLM_BASE_URL")
        if llm_base_url:
            logger.info(f"Using LLM_BASE_URL environment variable: {llm_base_url}")
            settings.llm.endpoint = llm_base_url

        # Normalize LLM endpoint: remove any path components, keep only base URL
        # The endpoint should be just the base URL (e.g., http://ollama:11434)
        # The client code will append paths like /api/tags as needed
        if settings.llm.endpoint:
            from urllib.parse import urlparse, urlunparse

            parsed = urlparse(settings.llm.endpoint)
            # Reconstruct URL with only scheme, netloc (host:port), no path
            normalized_endpoint = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
            if normalized_endpoint != settings.llm.endpoint:
                logger.warning(
                    f"LLM endpoint had path components, normalizing: "
                    f"{settings.llm.endpoint} -> {normalized_endpoint}"
                )
                settings.llm.endpoint = normalized_endpoint

        logger.info(
            f"Settings loaded - LLM endpoint: {settings.llm.endpoint}, "
            f"LLM model: {settings.llm.model}, "
            f"Vault: {settings.vault.path if settings.vault else 'not configured'}"
        )
        return settings

    except ValidationError as e:
        logger.error(f"Configuration validation error: {e}")
        # Return defaults if validation fails
        return Settings()
