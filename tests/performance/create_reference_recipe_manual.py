"""Manually create a reference recipe (gold standard) for accuracy evaluation.

This script helps you create a reference recipe manually by:
1. Showing you the Instagram caption
2. Providing a template JSON structure
3. Allowing you to manually enter the correct recipe data

Usage:
    python -m tests.performance.create_reference_recipe_manual
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pydantic import HttpUrl, ValidationError  # noqa: E402

from recipe_ingest.models.recipe import MacroNutrients, Recipe, RecipeMetadata  # noqa: E402
from recipe_ingest.parsers.instagram import InstagramParser  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test Instagram URL
TEST_INSTAGRAM_URL = "https://www.instagram.com/reel/DRYdlekE-Yb"

# Path to save reference recipe
REFERENCE_RECIPE_DIR = Path(__file__).parent / "reference_recipes"
REFERENCE_RECIPE_PATH = REFERENCE_RECIPE_DIR / "DRYdlekE-Yb.json"


def get_instagram_caption() -> str:
    """Extract Instagram caption for reference."""
    try:
        instagram_parser = InstagramParser()
        caption = instagram_parser.parse(TEST_INSTAGRAM_URL)
        logger.info(f"Extracted Instagram caption ({len(caption)} characters)")
        return caption
    except Exception as e:
        logger.error(f"Failed to extract Instagram caption: {e}")
        logger.info("You can still create the reference recipe manually")
        return ""


def create_template_json() -> dict:
    """Create a template JSON structure for manual editing."""
    return {
        "metadata": {
            "title": "Super F*ck Protein Brownies",
            "prep_time": None,  # e.g., "15 minutes"
            "cook_time": None,  # e.g., "30 minutes"
            "cuisine": None,  # e.g., "American"
            "url": str(TEST_INSTAGRAM_URL),
            "main_ingredient": None,  # e.g., "chocolate"
            "calories_per_serving": None,  # e.g., 99.0
            "macros": {
                "carbs": 0.0,  # e.g., 8.0
                "protein": 0.0,  # e.g., 11.0
                "fat": 0.0,  # e.g., 2.0
            },
            "servings": None,  # e.g., 9
            "created": datetime.now().isoformat(),
        },
        "ingredients": [
            # Add ingredients here, e.g.:
            # "80g plain flour",
            # "20g cocoa powder",
            # "65g chocolate protein powder",
        ],
        "instructions": [
            # Add instructions here, e.g.:
            # "Preheat the oven to 180 Celsius, 350 Fahrenheit.",
            # "Mix all dry ingredients in a bowl until smooth.",
        ],
        "notes": None,  # Optional notes or tips
    }


def create_reference_interactive() -> Recipe:
    """Interactively create a reference recipe."""
    print("\n" + "=" * 80)
    print("MANUAL REFERENCE RECIPE CREATOR")
    print("=" * 80)
    print("\nThis will help you create a reference (gold standard) recipe")
    print("for accuracy evaluation in benchmark tests.")
    print("\nYou'll be prompted to enter the recipe information manually.")
    print("=" * 80)

    # Show Instagram caption for reference
    caption = get_instagram_caption()
    if caption:
        print("\n📝 Instagram Caption (for reference):")
        print("-" * 80)
        print(caption[:500] + ("..." if len(caption) > 500 else ""))
        print("-" * 80)

    print("\n📋 Enter Recipe Information:")
    print("(Press Enter to skip optional fields)\n")

    # Get required fields
    title = input("Title (required): ").strip()
    if not title:
        print("❌ Title is required!")
        sys.exit(1)

    # Get optional metadata
    prep_time = input("Prep time (e.g., '15 minutes'): ").strip() or None
    cook_time = input("Cook time (e.g., '30 minutes'): ").strip() or None
    cuisine = input("Cuisine (e.g., 'American'): ").strip() or None
    main_ingredient = input("Main ingredient (e.g., 'chocolate'): ").strip() or None

    servings_input = input("Servings (number): ").strip()
    servings = int(servings_input) if servings_input else None

    # Nutrition info
    print("\n📊 Nutrition Information (optional):")
    calories_input = input("Calories per serving: ").strip()
    calories = float(calories_input) if calories_input else None

    carbs_input = input("Carbs (grams per serving): ").strip()
    carbs = float(carbs_input) if carbs_input else 0.0

    protein_input = input("Protein (grams per serving): ").strip()
    protein = float(protein_input) if protein_input else 0.0

    fat_input = input("Fat (grams per serving): ").strip()
    fat = float(fat_input) if fat_input else 0.0

    # Ingredients
    print("\n🥘 Ingredients (enter one per line, empty line to finish):")
    ingredients = []
    while True:
        ingredient = input(f"  Ingredient {len(ingredients) + 1}: ").strip()
        if not ingredient:
            break
        ingredients.append(ingredient)

    if not ingredients:
        print("❌ At least one ingredient is required!")
        sys.exit(1)

    # Instructions
    print("\n📝 Instructions (enter one per line, empty line to finish):")
    instructions = []
    while True:
        instruction = input(f"  Step {len(instructions) + 1}: ").strip()
        if not instruction:
            break
        instructions.append(instruction)

    if not instructions:
        print("❌ At least one instruction is required!")
        sys.exit(1)

    # Notes
    notes = input("\n📌 Notes (optional): ").strip() or None

    # Build recipe
    try:
        url = HttpUrl(TEST_INSTAGRAM_URL) if TEST_INSTAGRAM_URL else None
        macros = (
            MacroNutrients(carbs=carbs, protein=protein, fat=fat)
            if (carbs or protein or fat)
            else None
        )

        metadata = RecipeMetadata(
            title=title,
            prep_time=prep_time,
            cook_time=cook_time,
            cuisine=cuisine,
            url=url,
            main_ingredient=main_ingredient,
            calories_per_serving=calories,
            macros=macros,
            servings=servings,
            created=datetime.now(),
        )

        recipe = Recipe(
            metadata=metadata,
            ingredients=ingredients,
            instructions=instructions,
            notes=notes,
        )

        return recipe

    except ValidationError as e:
        print(f"\n❌ Validation error: {e}")
        sys.exit(1)


def create_reference_from_template() -> None:
    """Create a template JSON file for manual editing."""
    template = create_template_json()
    template_path = REFERENCE_RECIPE_DIR / "DRYdlekE-Yb.template.json"

    REFERENCE_RECIPE_DIR.mkdir(parents=True, exist_ok=True)

    with open(template_path, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Template created at: {template_path}")
    print("\n📝 Next steps:")
    print(f"  1. Edit {template_path} with the correct recipe data")
    print("  2. Fill in all required fields (title, ingredients, instructions)")
    print("  3. Run this script again with --from-template flag to validate and save")


def load_and_validate_template() -> Recipe:
    """Load and validate a template JSON file."""
    template_path = REFERENCE_RECIPE_DIR / "DRYdlekE-Yb.template.json"

    if not template_path.exists():
        print(f"❌ Template file not found: {template_path}")
        print("Run this script without --from-template to create a template first")
        sys.exit(1)

    with open(template_path, encoding="utf-8") as f:
        data = json.load(f)

    try:
        recipe = Recipe.model_validate(data)
        return recipe
    except ValidationError as e:
        print(f"❌ Validation error in template: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Manually create a reference recipe for accuracy evaluation"
    )
    parser.add_argument(
        "--template",
        action="store_true",
        help="Create a template JSON file for manual editing",
    )
    parser.add_argument(
        "--from-template",
        action="store_true",
        help="Load and validate template JSON file, then save as reference",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactively create reference recipe (default)",
    )

    args = parser.parse_args()

    if args.template:
        create_reference_from_template()
        return

    # Default to interactive if not loading from template
    recipe = load_and_validate_template() if args.from_template else create_reference_interactive()

    # Save reference recipe
    REFERENCE_RECIPE_DIR.mkdir(parents=True, exist_ok=True)

    with open(REFERENCE_RECIPE_PATH, "w", encoding="utf-8") as f:
        json.dump(recipe.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("✅ REFERENCE RECIPE CREATED")
    print("=" * 80)
    print(f"Title: {recipe.metadata.title}")
    print(f"Ingredients: {len(recipe.ingredients)}")
    print(f"Instructions: {len(recipe.instructions)}")
    if recipe.metadata.servings:
        print(f"Servings: {recipe.metadata.servings}")
    if recipe.metadata.calories_per_serving:
        print(f"Calories per serving: {recipe.metadata.calories_per_serving}")
    print(f"\nSaved to: {REFERENCE_RECIPE_PATH}")
    print("=" * 80)
    print("\nYou can now run benchmark tests to compare other models against this reference.")


if __name__ == "__main__":
    main()
