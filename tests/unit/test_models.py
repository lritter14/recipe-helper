"""Unit tests for recipe models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from recipe_ingest.models import MacroNutrients, Recipe, RecipeMetadata


class TestMacroNutrients:
    """Tests for MacroNutrients model."""

    def test_valid_macros(self) -> None:
        """Test creating valid macronutrient data."""
        macros = MacroNutrients(carbs=50.0, protein=25.0, fat=15.0)
        assert macros.carbs == 50.0
        assert macros.protein == 25.0
        assert macros.fat == 15.0

    def test_negative_values_rejected(self) -> None:
        """Test that negative values are rejected."""
        with pytest.raises(ValidationError):
            MacroNutrients(carbs=-10.0, protein=25.0, fat=15.0)


class TestRecipeMetadata:
    """Tests for RecipeMetadata model."""

    def test_minimal_metadata(self) -> None:
        """Test creating metadata with only required fields."""
        metadata = RecipeMetadata(title="Test Recipe")
        assert metadata.title == "Test Recipe"
        assert isinstance(metadata.created, datetime)

    def test_full_metadata(self) -> None:
        """Test creating metadata with all fields."""
        macros = MacroNutrients(carbs=50.0, protein=25.0, fat=15.0)
        metadata = RecipeMetadata(
            title="Chocolate Chip Cookies",
            prep_time="15 minutes",
            cook_time="10 minutes",
            cuisine="American",
            url="https://example.com/recipe",
            main_ingredient="flour",
            calories_per_serving=150.0,
            macros=macros,
            servings=60,
        )
        assert metadata.title == "Chocolate Chip Cookies"
        assert metadata.servings == 60


class TestRecipe:
    """Tests for Recipe model."""

    def test_valid_recipe(self) -> None:
        """Test creating a valid recipe."""
        metadata = RecipeMetadata(title="Test Recipe")
        recipe = Recipe(
            metadata=metadata,
            ingredients=["1 cup flour", "2 eggs"],
            instructions=["Mix ingredients", "Bake at 350F"],
        )
        assert len(recipe.ingredients) == 2
        assert len(recipe.instructions) == 2

    def test_to_markdown_not_implemented(self) -> None:
        """Test that to_markdown raises NotImplementedError."""
        metadata = RecipeMetadata(title="Test Recipe")
        recipe = Recipe(
            metadata=metadata,
            ingredients=["1 cup flour"],
            instructions=["Mix and bake"],
        )
        with pytest.raises(NotImplementedError):
            recipe.to_markdown()
