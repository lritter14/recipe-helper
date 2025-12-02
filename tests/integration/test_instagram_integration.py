"""Integration tests for Instagram URL processing.

All tests use temporary vault paths (temp_vault fixture) to ensure no files
are written outside the test environment. Files are automatically cleaned up
when the temp_vault fixture tears down.
"""

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from recipe_ingest.core import process_recipe


@pytest.mark.integration
class TestInstagramIntegration:
    """Integration tests for Instagram URL processing flow."""

    def test_process_recipe_with_source_url_stores_in_metadata(
        self, temp_vault: Path, mocker: MockerFixture
    ) -> None:
        """Test that source_url parameter is stored in recipe metadata."""
        instagram_url = "https://www.instagram.com/p/ABC123xyz/"
        recipe_text = """Chocolate Cake Recipe

Ingredients:
- 2 cups all-purpose flour
- 1 cup granulated sugar
- 1/2 cup cocoa powder
- 1 tsp baking soda
- 1/2 tsp salt
- 1 cup buttermilk
- 1/2 cup vegetable oil
- 2 large eggs
- 1 tsp vanilla extract

Instructions:
1. Preheat oven to 350°F.
2. Mix dry ingredients in a bowl.
3. Mix wet ingredients in another bowl.
4. Combine wet and dry ingredients.
5. Pour into greased 9x13 pan.
6. Bake for 30-35 minutes until toothpick comes out clean.
"""

        # Mock LLM responses
        mock_client = mocker.Mock()
        mock_client.generate.side_effect = [
            # Recipe extraction response
            {
                "title": "Chocolate Cake",
                "prep_time": "15 minutes",
                "cook_time": "30 minutes",
                "cuisine": "American",
                "main_ingredient": "chocolate",
                "servings": 12,
                "ingredients": [
                    "2 cups all-purpose flour",
                    "1 cup granulated sugar",
                    "1/2 cup cocoa powder",
                    "1 tsp baking soda",
                    "1/2 tsp salt",
                    "1 cup buttermilk",
                    "1/2 cup vegetable oil",
                    "2 large eggs",
                    "1 tsp vanilla extract",
                ],
                "instructions": [
                    "Preheat oven to 350°F.",
                    "Mix dry ingredients in a bowl.",
                    "Mix wet ingredients in another bowl.",
                    "Combine wet and dry ingredients.",
                    "Pour into greased 9x13 pan.",
                    "Bake for 30-35 minutes until toothpick comes out clean.",
                ],
                "notes": None,
            },
            # Nutrition calculation response
            {
                "calories_per_serving": 280.0,
                "carbs_grams": 38.0,
                "protein_grams": 5.0,
                "fat_grams": 12.0,
            },
        ]
        mock_client.health_check.return_value = True

        # Mock OllamaClient
        mocker.patch(
            "recipe_ingest.core.service.OllamaClient", return_value=mock_client
        )

        # Process recipe with source URL
        result = process_recipe(
            input_text=recipe_text,
            vault_path=temp_vault,
            llm_endpoint="http://localhost:11434",
            llm_model="llama2",
            recipes_dir="personal/recipes",
            overwrite=False,
            preview_only=False,
            source_url=instagram_url,
        )

        # Verify recipe was extracted
        assert result.recipe.metadata.title == "Chocolate Cake"
        assert result.recipe.metadata.url is not None
        assert str(result.recipe.metadata.url) == instagram_url
        assert len(result.recipe.ingredients) == 9
        assert len(result.recipe.instructions) == 6

        # Verify file was written
        assert result.file_path is not None
        assert result.file_path.exists()

        # Verify frontmatter contains source URL
        markdown_content = result.file_path.read_text(encoding="utf-8")
        assert "url:" in markdown_content
        assert instagram_url in markdown_content

    def test_process_recipe_without_source_url_has_no_url(
        self, temp_vault: Path, mocker: MockerFixture
    ) -> None:
        """Test that recipe without source_url has no URL in metadata."""
        recipe_text = (
            "Quick pasta recipe: 1 lb pasta, 2 cups marinara, 1/2 cup parmesan."
        )

        # Mock LLM responses
        mock_client = mocker.Mock()
        mock_client.generate.side_effect = [
            {
                "title": "Quick Pasta",
                "prep_time": "5 minutes",
                "cook_time": "15 minutes",
                "cuisine": "Italian",
                "main_ingredient": "pasta",
                "servings": 4,
                "ingredients": [
                    "1 lb pasta",
                    "2 cups marinara sauce",
                    "1/2 cup parmesan cheese",
                ],
                "instructions": [
                    "Cook pasta according to package directions.",
                    "Mix pasta with marinara sauce.",
                    "Top with parmesan cheese.",
                ],
                "notes": None,
            },
            {
                "calories_per_serving": 350.0,
                "carbs_grams": 55.0,
                "protein_grams": 12.0,
                "fat_grams": 8.0,
            },
        ]
        mock_client.health_check.return_value = True

        # Mock OllamaClient
        mocker.patch(
            "recipe_ingest.core.service.OllamaClient", return_value=mock_client
        )

        # Process recipe without source URL
        result = process_recipe(
            input_text=recipe_text,
            vault_path=temp_vault,
            llm_endpoint="http://localhost:11434",
            llm_model="llama2",
            recipes_dir="personal/recipes",
            overwrite=False,
            preview_only=False,
            source_url=None,
        )

        # Verify source URL is None
        assert result.recipe.metadata.url is None
        assert result.file_path is not None
