"""Integration tests for full recipe ingestion pipeline.

All tests use temporary vault paths (temp_vault fixture) to ensure no files
are written outside the test environment. Files are automatically cleaned up
when the temp_vault fixture tears down.
"""

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from recipe_ingest.core import MarkdownFormatter, RecipeExtractor, VaultWriter
from recipe_ingest.llm import OllamaClient


@pytest.mark.integration
class TestFullPipeline:
    """Integration tests for complete recipe ingestion flow."""

    def test_full_pipeline_with_mocked_llm(
        self, temp_vault: Path, sample_recipe_text: str, mocker: MockerFixture
    ) -> None:
        """Test complete pipeline from text input to vault file."""
        # Mock LLM responses
        mock_client = mocker.Mock(spec=OllamaClient)
        mock_client.generate.side_effect = [
            # Recipe extraction response
            {
                "title": "Chocolate Chip Cookies",
                "prep_time": "15 minutes",
                "cook_time": "10 minutes",
                "cuisine": "American",
                "main_ingredient": "flour",
                "servings": 60,
                "ingredients": [
                    "2 1/4 cups all-purpose flour",
                    "1 tsp baking soda",
                    "1 tsp salt",
                    "1 cup butter, softened",
                    "3/4 cup granulated sugar",
                    "3/4 cup packed brown sugar",
                    "2 large eggs",
                    "2 tsp vanilla extract",
                    "2 cups chocolate chips",
                ],
                "instructions": [
                    "Preheat oven to 375°F.",
                    "Mix flour, baking soda, and salt in a bowl.",
                    "Beat butter and sugars until creamy.",
                    "Add eggs and vanilla, beat well.",
                    "Gradually mix in flour mixture.",
                    "Stir in chocolate chips.",
                    "Drop by rounded tablespoon onto baking sheets.",
                    "Bake 9-11 minutes until golden brown.",
                    "Cool on baking sheet for 2 minutes.",
                    "Transfer to wire rack.",
                ],
                "notes": None,
            },
            # Nutrition calculation response
            {
                "calories_per_serving": 120.0,
                "carbs_grams": 15.0,
                "protein_grams": 2.0,
                "fat_grams": 6.0,
            },
        ]

        # Initialize components
        extractor = RecipeExtractor(llm_client=mock_client)
        formatter = MarkdownFormatter()
        writer = VaultWriter(vault_path=temp_vault)

        # Step 1: Extract
        recipe = extractor.extract(sample_recipe_text)
        assert recipe.metadata.title == "Chocolate Chip Cookies"
        assert len(recipe.ingredients) == 9
        assert len(recipe.instructions) == 10

        # Step 2: Format
        markdown = formatter.format(recipe)
        assert "---\n" in markdown
        assert "title: Chocolate Chip Cookies" in markdown
        assert "## Ingredients" in markdown
        assert "## Instructions" in markdown

        # Step 3: Write
        file_path = writer.write(recipe.metadata.title, markdown)
        assert file_path.exists()
        assert file_path.name == "Chocolate Chip Cookies.md"

        # Verify file contents
        content = file_path.read_text()
        assert "title: Chocolate Chip Cookies" in content
        assert "servings: 60" in content
        assert "calories_per_serving: 120.0" in content
        assert "2 1/4 cups all-purpose flour" in content

        # Verify LLM was called correct number of times
        assert mock_client.generate.call_count == 2

        # Explicit cleanup - temp_vault auto-cleans, but being explicit makes intent clear
        # All files created in temp_vault will be automatically removed when fixture tears down

    def test_duplicate_detection_in_pipeline(self, temp_vault: Path, mocker: MockerFixture) -> None:
        """Test that duplicate detection works in full pipeline."""
        # Mock LLM responses
        mock_client = mocker.Mock(spec=OllamaClient)
        mock_client.generate.side_effect = [
            # First recipe extraction
            {
                "title": "Duplicate Recipe",
                "ingredients": ["ingredient"],
                "instructions": ["instruction"],
                "servings": 1,
            },
            # First nutrition
            {
                "calories_per_serving": 100.0,
                "carbs_grams": 10.0,
                "protein_grams": 5.0,
                "fat_grams": 3.0,
            },
            # Second recipe extraction (same title)
            {
                "title": "Duplicate Recipe",
                "ingredients": ["different ingredient"],
                "instructions": ["different instruction"],
                "servings": 1,
            },
            # Second nutrition
            {
                "calories_per_serving": 100.0,
                "carbs_grams": 10.0,
                "protein_grams": 5.0,
                "fat_grams": 3.0,
            },
        ]

        extractor = RecipeExtractor(llm_client=mock_client)
        formatter = MarkdownFormatter()
        writer = VaultWriter(vault_path=temp_vault)

        # First recipe - should succeed
        recipe1 = extractor.extract("First recipe text")
        markdown1 = formatter.format(recipe1)
        file_path = writer.write(recipe1.metadata.title, markdown1)
        assert file_path.exists()

        # Second recipe with same title - should fail without overwrite
        recipe2 = extractor.extract("Second recipe text")
        markdown2 = formatter.format(recipe2)

        with pytest.raises(FileExistsError):
            writer.write(recipe2.metadata.title, markdown2, overwrite=False)

        # With overwrite flag - should succeed
        file_path = writer.write(recipe2.metadata.title, markdown2, overwrite=True)
        assert file_path.exists()
        content = file_path.read_text()
        assert "different ingredient" in content

        # Explicit cleanup - temp_vault auto-cleans, but being explicit makes intent clear
        # All files created in temp_vault will be automatically removed when fixture tears down
