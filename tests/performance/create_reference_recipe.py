"""Script to create a reference recipe (gold standard) from a model output.

This script processes a recipe using a trusted model and saves it as the reference
for accuracy evaluation in benchmark tests.

Usage:
    python -m tests.performance.create_reference_recipe
    # OR
    python tests/performance/create_reference_recipe.py
"""

import logging
import os
import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv  # noqa: E402

from recipe_ingest.core import process_recipe  # noqa: E402
from recipe_ingest.parsers.instagram import InstagramParser  # noqa: E402
from tests.performance.recipe_evaluator import save_reference_recipe  # noqa: E402

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test Instagram URL
TEST_INSTAGRAM_URL = "https://www.instagram.com/reel/DRYdlekE-Yb"

# Path to save reference recipe
REFERENCE_RECIPE_DIR = Path(__file__).parent / "reference_recipes"
REFERENCE_RECIPE_PATH = REFERENCE_RECIPE_DIR / "DRYdlekE-Yb.json"

# Trusted model to use for generating reference (use your best/most accurate model)
TRUSTED_MODEL = os.getenv("REFERENCE_MODEL", "llama3.1:8b")
OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")


def main() -> None:
    """Create reference recipe from Instagram URL."""
    logger.info(f"Creating reference recipe from: {TEST_INSTAGRAM_URL}")
    logger.info(f"Using model: {TRUSTED_MODEL}")

    # Extract Instagram caption
    try:
        instagram_parser = InstagramParser()
        caption = instagram_parser.parse(TEST_INSTAGRAM_URL)
        logger.info(f"Extracted Instagram caption ({len(caption)} characters)")
    except Exception as e:
        logger.error(f"Failed to extract Instagram caption: {e}")
        sys.exit(1)

    # Process recipe with trusted model
    try:
        # Use a temporary directory
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = process_recipe(
                input_text=caption,
                vault_path=Path(tmpdir),
                llm_endpoint=OLLAMA_ENDPOINT,
                llm_model=TRUSTED_MODEL,
                recipes_dir="personal/recipes",
                overwrite=False,
                preview_only=True,
                source_url=TEST_INSTAGRAM_URL,
            )

            if not result.recipe:
                logger.error("Failed to extract recipe")
                sys.exit(1)

            # Save as reference
            save_reference_recipe(result.recipe, REFERENCE_RECIPE_PATH)
            logger.info(f"✓ Reference recipe saved to {REFERENCE_RECIPE_PATH}")

            # Print recipe summary
            print("\n" + "=" * 80)
            print("REFERENCE RECIPE CREATED")
            print("=" * 80)
            print(f"Title: {result.recipe.metadata.title}")
            print(f"Ingredients: {len(result.recipe.ingredients)}")
            print(f"Instructions: {len(result.recipe.instructions)}")
            if result.recipe.metadata.servings:
                print(f"Servings: {result.recipe.metadata.servings}")
            if result.recipe.metadata.prep_time:
                print(f"Prep Time: {result.recipe.metadata.prep_time}")
            if result.recipe.metadata.cook_time:
                print(f"Cook Time: {result.recipe.metadata.cook_time}")
            print("=" * 80)
            print(
                "\nYou can now run benchmark tests to compare other models against this reference."
            )

    except Exception as e:
        logger.error(f"Failed to create reference recipe: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
