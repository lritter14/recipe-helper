"""Configuration management."""

import logging
import os
from pathlib import Path

import yaml
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
    """Application settings loaded from environment and config files."""

    model_config = SettingsConfigDict(
        env_prefix="RECIPE_INGEST_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM configuration")
    vault: VaultConfig | None = Field(default=None, description="Vault configuration")
    log_level: str = Field(default="INFO", description="Logging level")


def load_settings(config_path: Path | None = None) -> Settings:
    """Load application settings from environment and config files.

    Args:
        config_path: Optional path to config file. If not provided, checks standard locations.

    Returns:
        Application settings instance
    """
    config_data: dict = {}

    # Try to load from config file
    if config_path and config_path.exists():
        config_data = _load_config_file(config_path)
    else:
        # Try standard locations
        standard_paths = [
            Path.cwd() / "config" / "config.yaml",
            Path.home() / ".config" / "recipe-ingest" / "config.yaml",
        ]

        for path in standard_paths:
            if path.exists():
                logger.debug(f"Loading config from: {path}")
                config_data = _load_config_file(path)
                break

    # Create settings from config data and environment variables
    # Environment variables will override config file values
    try:
        settings = Settings(**config_data) if config_data else Settings()

        # Support LLM_BASE_URL as a simpler alternative to RECIPE_INGEST_LLM__ENDPOINT
        # This allows using the service name pattern: LLM_BASE_URL=http://ollama:11434
        llm_base_url = os.getenv("LLM_BASE_URL")
        if llm_base_url:
            logger.info(f"Using LLM_BASE_URL environment variable: {llm_base_url}")
            settings.llm.endpoint = llm_base_url

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


def _load_config_file(path: Path) -> dict:
    """Load configuration from YAML file.

    Args:
        path: Path to YAML config file

    Returns:
        Configuration dictionary
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data is None:
                logger.warning(f"Config file is empty: {path}")
                return {}
            if not isinstance(data, dict):
                logger.warning(f"Config file is not a dictionary: {path}")
                return {}
            logger.info(f"Loaded configuration from: {path}")
            return data
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML config: {e}")
        return {}
    except Exception as e:
        logger.error(f"Failed to load config file: {e}")
        return {}
