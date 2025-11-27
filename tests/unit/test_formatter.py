"""Unit tests for markdown formatter."""

from datetime import datetime

from recipe_ingest.core.formatter import MarkdownFormatter
from recipe_ingest.models.recipe import MacroNutrients, Recipe, RecipeMetadata


class TestMarkdownFormatter:
    """Tests for MarkdownFormatter class."""

    def test_format_minimal_recipe(self) -> None:
        """Test formatting a recipe with only required fields."""
        metadata = RecipeMetadata(title="Simple Recipe")
        recipe = Recipe(
            metadata=metadata,
            ingredients=["1 cup flour", "2 eggs"],
            instructions=["Mix", "Bake"],
        )

        formatter = MarkdownFormatter()
        result = formatter.format(recipe)

        # Check structure
        assert result.startswith("---\n")
        assert "---\n\n# Simple Recipe" in result
        assert "## Ingredients" in result
        assert "- 1 cup flour" in result
        assert "- 2 eggs" in result
        assert "## Instructions" in result
        assert "1. Mix" in result
        assert "2. Bake" in result

    def test_format_full_recipe_with_all_fields(self) -> None:
        """Test formatting a recipe with all optional fields."""
        macros = MacroNutrients(carbs=30.0, protein=15.0, fat=10.0)
        metadata = RecipeMetadata(
            title="Complete Recipe",
            prep_time="15 minutes",
            cook_time="30 minutes",
            cuisine="Italian",
            main_ingredient="pasta",
            servings=4,
            calories_per_serving=350.0,
            macros=macros,
            created=datetime(2025, 1, 1, 12, 0, 0),
        )
        recipe = Recipe(
            metadata=metadata,
            ingredients=["1 lb pasta", "2 cups sauce"],
            instructions=["Boil pasta", "Add sauce", "Serve"],
            notes="Best served hot!",
        )

        formatter = MarkdownFormatter()
        result = formatter.format(recipe)

        # Check frontmatter contains all fields
        assert "title: Complete Recipe" in result
        assert "prep_time: 15 minutes" in result
        assert "cook_time: 30 minutes" in result
        assert "cuisine: Italian" in result
        assert "main_ingredient: pasta" in result
        assert "servings: 4" in result
        assert "calories_per_serving: 350.0" in result
        assert "carbs: 30.0" in result
        assert "protein: 15.0" in result
        assert "fat: 10.0" in result

        # Check body sections
        assert "# Complete Recipe" in result
        assert "## Ingredients" in result
        assert "- 1 lb pasta" in result
        assert "## Instructions" in result
        assert "1. Boil pasta" in result
        assert "2. Add sauce" in result
        assert "3. Serve" in result
        assert "## Notes" in result
        assert "Best served hot!" in result

    def test_format_creates_valid_yaml_frontmatter(self) -> None:
        """Test that frontmatter is valid YAML."""
        import yaml

        metadata = RecipeMetadata(title="Test Recipe", servings=2)
        recipe = Recipe(
            metadata=metadata,
            ingredients=["ingredient"],
            instructions=["instruction"],
        )

        formatter = MarkdownFormatter()
        result = formatter.format(recipe)

        # Extract frontmatter
        parts = result.split("---\n")
        assert len(parts) >= 3  # Empty, frontmatter, body
        frontmatter_text = parts[1]

        # Should parse as valid YAML
        frontmatter_data = yaml.safe_load(frontmatter_text)
        assert frontmatter_data["title"] == "Test Recipe"
        assert frontmatter_data["servings"] == 2
