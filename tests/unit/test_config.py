"""Unit tests for configuration management."""

from pathlib import Path

import yaml

from recipe_ingest.config import Settings, load_settings


class TestSettings:
    """Tests for Settings class."""

    def test_settings_with_defaults(self) -> None:
        """Test that settings can be created with all defaults."""
        settings = Settings()
        assert settings.llm.endpoint == "http://localhost:11434"
        assert settings.llm.model == "llama2"
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

    def test_load_settings_without_config_file(self, tmp_path: Path) -> None:
        """Test loading settings when no config file exists."""
        # Change to a directory with no config
        import os

        orig_dir = Path.cwd()
        os.chdir(tmp_path)

        try:
            settings = load_settings()
            assert settings.llm.model == "llama2"  # Default
            assert settings.vault is None
        finally:
            os.chdir(orig_dir)

    def test_load_settings_from_config_file(self, tmp_path: Path) -> None:
        """Test loading settings from a config file."""
        # Create config file
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        config_data = {
            "llm": {"endpoint": "http://test:11434", "model": "test-model", "timeout": 90},
            "vault": {"path": str(tmp_path / "vault"), "recipes_dir": "recipes"},
            "log_level": "DEBUG",
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Load settings
        settings = load_settings(config_file)

        # Verify settings loaded from file
        assert settings.llm.endpoint == "http://test:11434"
        assert settings.llm.model == "test-model"
        assert settings.llm.timeout == 90
        assert settings.vault is not None
        assert str(settings.vault.path) == str(tmp_path / "vault")
        assert settings.vault.recipes_dir == "recipes"
        assert settings.log_level == "DEBUG"

    def test_load_settings_with_empty_config_file(self, tmp_path: Path) -> None:
        """Test loading settings when config file is empty."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        settings = load_settings(config_file)

        # Should use defaults
        assert settings.llm.model == "llama2"
        assert settings.vault is None

    def test_load_settings_with_invalid_yaml(self, tmp_path: Path) -> None:
        """Test loading settings when config file has invalid YAML."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content: [")

        # Should not crash, just use defaults
        settings = load_settings(config_file)
        assert settings.llm.model == "llama2"

    def test_load_settings_with_partial_config(self, tmp_path: Path) -> None:
        """Test loading settings with only some fields in config file."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "llm": {"model": "custom-model"},
            # Vault not specified
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        settings = load_settings(config_file)

        # Model from config, endpoint from default
        assert settings.llm.model == "custom-model"
        assert settings.llm.endpoint == "http://localhost:11434"
        assert settings.vault is None

    def test_load_settings_searches_standard_locations(self, tmp_path: Path) -> None:
        """Test that load_settings checks standard config locations."""
        import os

        # Create config in current directory
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        config_data = {"llm": {"model": "found-model"}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Change to tmp_path so it finds config/config.yaml
        orig_dir = Path.cwd()
        os.chdir(tmp_path)

        try:
            settings = load_settings()
            assert settings.llm.model == "found-model"
        finally:
            os.chdir(orig_dir)
