import shutil
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from recipe_ingest.cli import main

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
def mock_llm_client():
    with patch("recipe_ingest.core.service.OllamaClient") as MockClient:
        client_instance = MockClient.return_value
        # Mock health check to return True
        client_instance.health_check.return_value = True

        # Mock generate to return recipe then nutrition
        # The extractor calls generate twice: once for recipe, once for nutrition
        client_instance.generate.side_effect = [
            SAMPLE_RECIPE_JSON,
            SAMPLE_NUTRITION_JSON,
        ]
        yield client_instance


def test_m1_verification_end_to_end(mock_llm_client, tmp_path):
    """
    Verify M1 requirements:
    1. CLI accepts unstructured text input
    2. LLM integration (mocked)
    3. Extraction of fields
    4. Nutrition calculation
    5. Markdown formatting with frontmatter
    6. Write to vault

    Uses temporary directory internal to test environment, not relying on config.
    """
    runner = CliRunner()

    # Input text
    input_text = "Make some pasta with tomato sauce."

    # Output directory (simulated vault) - use tmp_path which is automatically cleaned up
    # This ensures we don't write to any external config-specified paths
    output_dir = tmp_path / "test_vault"
    output_dir.mkdir()

    try:
        # Patch config to ensure we use default recipes_dir and don't rely on external config
        with patch("recipe_ingest.cli.load_settings") as mock_load_settings:
            from recipe_ingest.config import LLMConfig, Settings

            # Create settings with default recipes_dir, no vault path (CLI arg will provide it)
            mock_settings = Settings(
                llm=LLMConfig(endpoint="http://test-endpoint", model="test-model"),
                vault=None,  # No vault in config, forcing use of --output-dir
            )
            mock_load_settings.return_value = mock_settings

            # Run CLI command with explicit output directory to override any config
            result = runner.invoke(
                main,
                [
                    input_text,
                    "--output-dir",
                    str(output_dir),
                    "--llm-model",
                    "test-model",
                    "--llm-endpoint",
                    "http://test-endpoint",
                ],
            )

            # Verify CLI execution success
            assert result.exit_code == 0, f"CLI failed with output: {result.output}"
            assert "✅ Recipe saved" in result.output

            # Verify file creation
            # Note: When vault is None in config, CLI uses default "personal/recipes" subdirectory
            expected_file = output_dir / "personal/recipes/Test Pasta.md"

            if not expected_file.exists():
                print(f"\nCLI Output:\n{result.output}")
                print(f"\nDirectory contents of {output_dir}:")
                for p in output_dir.rglob("*"):
                    print(f"  {p.relative_to(output_dir)}")

            assert expected_file.exists()

            # Verify file content
            content = expected_file.read_text()

            # Check Frontmatter
            assert "title: Test Pasta" in content
            assert "cuisine: Italian" in content
            assert "calories_per_serving: 400" in content
            assert "carbs: 60.0" in content

            # Check Body
            assert "# Test Pasta" in content
            assert "## Ingredients" in content
            assert "- 200g pasta" in content
            assert "## Instructions" in content
            assert "1. Boil water" in content

            # Verify LLM interaction
            # Should be called twice: extraction and nutrition
            assert mock_llm_client.generate.call_count == 2

    finally:
        # Explicit cleanup - remove all created files and directories
        # (tmp_path auto-cleans, but being explicit makes intent clear)
        if output_dir.exists():
            shutil.rmtree(output_dir, ignore_errors=True)
