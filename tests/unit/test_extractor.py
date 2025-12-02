"""Unit tests for recipe extractor."""

import pytest
from pytest_mock import MockerFixture

from recipe_ingest.core.extractor import RecipeExtractor
from recipe_ingest.llm.client import OllamaClient
from recipe_ingest.models.recipe import Recipe


class TestRecipeExtractor:
    """Tests for RecipeExtractor class."""

    def test_init_creates_default_client(self) -> None:
        """Test that extractor creates default LLM client if none provided."""
        extractor = RecipeExtractor()
        assert extractor.llm_client is not None
        assert isinstance(extractor.llm_client, OllamaClient)

    def test_init_uses_provided_client(self, mocker: MockerFixture) -> None:
        """Test that extractor uses provided LLM client."""
        mock_client = mocker.Mock(spec=OllamaClient)
        extractor = RecipeExtractor(llm_client=mock_client)
        assert extractor.llm_client is mock_client

    def test_extract_with_empty_text_raises_error(self) -> None:
        """Test that empty text input raises ValueError."""
        extractor = RecipeExtractor()
        with pytest.raises(ValueError, match="Input text cannot be empty"):
            extractor.extract("")

        with pytest.raises(ValueError, match="Input text cannot be empty"):
            extractor.extract("   ")

    def test_extract_with_valid_text_returns_recipe(self, mocker: MockerFixture) -> None:
        """Test successful recipe extraction from valid text."""
        # Mock LLM responses
        mock_client = mocker.Mock(spec=OllamaClient)
        mock_client.generate.side_effect = [
            # First call: recipe extraction
            {
                "title": "Test Recipe",
                "prep_time": "10 minutes",
                "cook_time": "20 minutes",
                "cuisine": "American",
                "main_ingredient": "chicken",
                "servings": 4,
                "ingredients": ["1 cup flour", "2 eggs"],
                "instructions": ["Mix ingredients", "Bake at 350F"],
                "notes": "Delicious!",
            },
            # Second call: nutrition calculation
            {
                "calories_per_serving": 250.0,
                "carbs_grams": 30.0,
                "protein_grams": 15.0,
                "fat_grams": 10.0,
            },
        ]

        extractor = RecipeExtractor(llm_client=mock_client)
        recipe = extractor.extract("Some recipe text")

        # Verify recipe structure
        assert isinstance(recipe, Recipe)
        assert recipe.metadata.title == "Test Recipe"
        assert recipe.metadata.prep_time == "10 minutes"
        assert recipe.metadata.servings == 4
        assert len(recipe.ingredients) == 2
        assert len(recipe.instructions) == 2
        assert recipe.notes == "Delicious!"
        assert recipe.metadata.calories_per_serving == 250.0
        assert recipe.metadata.macros is not None
        assert recipe.metadata.macros.carbs == 30.0

        # Verify LLM was called twice
        assert mock_client.generate.call_count == 2

    def test_extract_missing_required_field_uses_fallback(self, mocker: MockerFixture) -> None:
        """Test that missing required fields use fallback logic instead of raising error."""
        mock_client = mocker.Mock(spec=OllamaClient)
        mock_client.generate.return_value = {
            "title": "Test",
            # Missing ingredients and instructions
        }

        extractor = RecipeExtractor(llm_client=mock_client)
        recipe = extractor.extract("Some text")

        # Should create recipe with empty lists as fallback
        assert isinstance(recipe, Recipe)
        assert recipe.metadata.title == "Test"
        assert recipe.ingredients == []  # Fallback to empty list
        assert recipe.instructions == []  # Fallback to empty list

    def test_calculate_nutrition_returns_defaults_on_error(self, mocker: MockerFixture) -> None:
        """Test that nutrition calculation returns defaults if LLM fails."""
        mock_client = mocker.Mock(spec=OllamaClient)
        mock_client.generate.side_effect = ValueError("LLM error")

        extractor = RecipeExtractor(llm_client=mock_client)
        result = extractor.calculate_nutrition(["1 cup flour"], 4)

        # Should return zeros as defaults
        assert result["calories_per_serving"] == 0.0
        assert result["carbs_grams"] == 0.0
        assert result["protein_grams"] == 0.0
        assert result["fat_grams"] == 0.0

    def test_extract_with_source_url_stores_in_metadata(self, mocker: MockerFixture) -> None:
        """Test that source_url parameter is stored in recipe metadata."""
        mock_client = mocker.Mock(spec=OllamaClient)
        mock_client.generate.side_effect = [
            {
                "title": "Test Recipe",
                "prep_time": "10 minutes",
                "cook_time": "20 minutes",
                "cuisine": "American",
                "main_ingredient": "chicken",
                "servings": 4,
                "ingredients": ["1 cup flour", "2 eggs"],
                "instructions": ["Mix ingredients", "Bake at 350F"],
                "notes": None,
            },
            {
                "calories_per_serving": 250.0,
                "carbs_grams": 30.0,
                "protein_grams": 15.0,
                "fat_grams": 10.0,
            },
        ]

        extractor = RecipeExtractor(llm_client=mock_client)
        source_url = "https://www.instagram.com/p/ABC123/"
        recipe = extractor.extract("Some recipe text", source_url=source_url)

        # Verify source URL is stored in metadata
        assert recipe.metadata.url is not None
        assert str(recipe.metadata.url) == source_url

    def test_extract_without_source_url_has_no_url(self, mocker: MockerFixture) -> None:
        """Test that recipe without source_url has no URL in metadata."""
        mock_client = mocker.Mock(spec=OllamaClient)
        mock_client.generate.side_effect = [
            {
                "title": "Test Recipe",
                "prep_time": "10 minutes",
                "cook_time": "20 minutes",
                "cuisine": "American",
                "main_ingredient": "chicken",
                "servings": 4,
                "ingredients": ["1 cup flour", "2 eggs"],
                "instructions": ["Mix ingredients", "Bake at 350F"],
                "notes": None,
            },
            {
                "calories_per_serving": 250.0,
                "carbs_grams": 30.0,
                "protein_grams": 15.0,
                "fat_grams": 10.0,
            },
        ]

        extractor = RecipeExtractor(llm_client=mock_client)
        recipe = extractor.extract("Some recipe text")

        # Verify URL is None
        assert recipe.metadata.url is None

    def test_extract_with_invalid_source_url_logs_warning(self, mocker: MockerFixture) -> None:
        """Test that invalid source_url format logs warning and continues."""
        mock_client = mocker.Mock(spec=OllamaClient)
        mock_client.generate.side_effect = [
            {
                "title": "Test Recipe",
                "prep_time": "10 minutes",
                "cook_time": "20 minutes",
                "cuisine": "American",
                "main_ingredient": "chicken",
                "servings": 4,
                "ingredients": ["1 cup flour", "2 eggs"],
                "instructions": ["Mix ingredients", "Bake at 350F"],
                "notes": None,
            },
            {
                "calories_per_serving": 250.0,
                "carbs_grams": 30.0,
                "protein_grams": 15.0,
                "fat_grams": 10.0,
            },
        ]

        extractor = RecipeExtractor(llm_client=mock_client)
        invalid_url = "not a valid url"
        recipe = extractor.extract("Some recipe text", source_url=invalid_url)

        # Verify URL is None (invalid URL was rejected)
        assert recipe.metadata.url is None

    def test_extract_with_nutrition_in_source_uses_extracted_values(
        self, mocker: MockerFixture
    ) -> None:
        """Test that nutrition extracted from source text is used instead of calculating."""
        mock_client = mocker.Mock(spec=OllamaClient)
        mock_client.generate.side_effect = [
            # First call: recipe extraction with nutrition included
            {
                "title": "High Protein Smoothie",
                "prep_time": "5 minutes",
                "cook_time": None,
                "cuisine": None,
                "main_ingredient": "protein",
                "servings": 1,
                "ingredients": ["1 cup milk", "1 scoop protein powder", "1 banana"],
                "instructions": ["Blend all ingredients", "Serve immediately"],
                "notes": None,
                "calories_per_serving": 350.0,
                "carbs_grams": 45.0,
                "protein_grams": 30.0,
                "fat_grams": 8.0,
            },
            # Should NOT be called since we have extracted nutrition
        ]

        extractor = RecipeExtractor(llm_client=mock_client)
        recipe = extractor.extract(
            "High Protein Smoothie\n\nIngredients: 1 cup milk, 1 scoop protein, 1 banana\n\n"
            "Nutrition: 350 cal, 45g carbs, 30g protein, 8g fat"
        )

        # Verify extracted nutrition values are used
        assert recipe.metadata.calories_per_serving == 350.0
        assert recipe.metadata.macros is not None
        assert recipe.metadata.macros.carbs == 45.0
        assert recipe.metadata.macros.protein == 30.0
        assert recipe.metadata.macros.fat == 8.0

        # Verify LLM was only called once (no nutrition calculation call)
        assert mock_client.generate.call_count == 1

    def test_extract_with_partial_nutrition_calculates_missing_values(
        self, mocker: MockerFixture
    ) -> None:
        """Test that partial nutrition data triggers calculation for missing values."""
        mock_client = mocker.Mock(spec=OllamaClient)
        mock_client.generate.side_effect = [
            # First call: recipe extraction with partial nutrition
            {
                "title": "Test Recipe",
                "prep_time": "10 minutes",
                "cook_time": "20 minutes",
                "cuisine": "American",
                "main_ingredient": "chicken",
                "servings": 4,
                "ingredients": ["1 cup flour", "2 eggs"],
                "instructions": ["Mix ingredients", "Bake at 350F"],
                "notes": None,
                "calories_per_serving": 300.0,
                "carbs_grams": None,  # Missing carbs
                "protein_grams": 20.0,
                "fat_grams": None,  # Missing fat
            },
            # Second call: nutrition calculation (should be called for missing values)
            {
                "calories_per_serving": 250.0,
                "carbs_grams": 30.0,
                "protein_grams": 15.0,
                "fat_grams": 10.0,
            },
        ]

        extractor = RecipeExtractor(llm_client=mock_client)
        recipe = extractor.extract("Some recipe text with partial nutrition")

        # Verify calculated values are used (not the partial extracted ones)
        assert recipe.metadata.calories_per_serving == 250.0
        assert recipe.metadata.macros is not None
        assert recipe.metadata.macros.carbs == 30.0
        assert recipe.metadata.macros.protein == 15.0
        assert recipe.metadata.macros.fat == 10.0

        # Verify LLM was called twice (extraction + calculation)
        assert mock_client.generate.call_count == 2
