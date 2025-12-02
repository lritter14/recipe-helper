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
        # Load base settings
        settings = Settings()

        # Manually map flat env vars to nested config objects
        # LLM configuration
        llm_endpoint = os.getenv("RECIPE_INGEST_LLM_ENDPOINT")
        llm_model = os.getenv("RECIPE_INGEST_LLM_MODEL")
        llm_timeout = os.getenv("RECIPE_INGEST_LLM_TIMEOUT")

        if llm_endpoint or llm_model or llm_timeout:
            timeout_value = settings.llm.timeout
            if llm_timeout:
                try:
                    timeout_value = int(llm_timeout)
                except ValueError:
                    logger.warning(f"Invalid LLM timeout value: {llm_timeout}, using default: {settings.llm.timeout}")
            
            settings.llm = LLMConfig(
                endpoint=llm_endpoint if llm_endpoint else settings.llm.endpoint,
                model=llm_model if llm_model else settings.llm.model,
                timeout=timeout_value,
            )

        # Vault configuration
        vault_path = os.getenv("RECIPE_INGEST_VAULT_PATH")
        vault_recipes_dir = os.getenv("RECIPE_INGEST_VAULT_RECIPES_DIR")

        if vault_path:
            settings.vault = VaultConfig(
                path=Path(vault_path),
                recipes_dir=vault_recipes_dir if vault_recipes_dir else (settings.vault.recipes_dir if settings.vault else "personal/recipes"),
            )

        # Log level (handled by Pydantic via env_prefix, but ensure it's set if provided)
        log_level = os.getenv("RECIPE_INGEST_LOG_LEVEL")
        if log_level:
            settings.log_level = log_level

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
