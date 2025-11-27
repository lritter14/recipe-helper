"""Pytest configuration and shared fixtures."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_vault() -> Generator[Path, None, None]:
    """Create a temporary Obsidian vault for testing.

    Yields:
        Path to temporary vault directory
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        recipes_dir = vault_path / "personal" / "recipes"
        recipes_dir.mkdir(parents=True, exist_ok=True)
        yield vault_path


@pytest.fixture
def sample_recipe_text() -> str:
    """Sample unstructured recipe text for testing.

    Returns:
        Raw recipe text
    """
    return """
    Chocolate Chip Cookies

    Ingredients:
    - 2 1/4 cups all-purpose flour
    - 1 tsp baking soda
    - 1 tsp salt
    - 1 cup butter, softened
    - 3/4 cup granulated sugar
    - 3/4 cup packed brown sugar
    - 2 large eggs
    - 2 tsp vanilla extract
    - 2 cups chocolate chips

    Instructions:
    1. Preheat oven to 375°F.
    2. Mix flour, baking soda, and salt in a bowl.
    3. Beat butter and sugars until creamy.
    4. Add eggs and vanilla, beat well.
    5. Gradually mix in flour mixture.
    6. Stir in chocolate chips.
    7. Drop by rounded tablespoon onto baking sheets.
    8. Bake 9-11 minutes until golden brown.
    9. Cool on baking sheet for 2 minutes.
    10. Transfer to wire rack.

    Prep time: 15 minutes
    Cook time: 10 minutes
    Servings: 60 cookies
    """


@pytest.fixture
def sample_instagram_url() -> str:
    """Sample Instagram URL for testing.

    Returns:
        Instagram post URL
    """
    return "https://www.instagram.com/p/ABC123/"
