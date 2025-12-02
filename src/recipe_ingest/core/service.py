"""Shared recipe processing service for CLI and API."""

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

from recipe_ingest.core.extractor import RecipeExtractor
from recipe_ingest.core.formatter import MarkdownFormatter
from recipe_ingest.core.writer import VaultWriter
from recipe_ingest.llm import OllamaClient
from recipe_ingest.models.recipe import Recipe

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of recipe processing operation."""

    recipe: Recipe
    markdown: str
    file_path: Path | None
    timing: dict[str, float]
    is_duplicate: bool
    duplicate_ingredients_match: bool = False


def _normalize_ingredient(ingredient: str) -> str:
    """Normalize an ingredient string for comparison.

    Args:
        ingredient: Ingredient string (e.g., "2 cups flour")

    Returns:
        Normalized ingredient string (lowercase, trimmed)
    """
    return ingredient.lower().strip()


def _extract_ingredients_from_markdown(markdown_content: str) -> list[str]:
    """Extract ingredients list from markdown recipe file.

    Args:
        markdown_content: Full markdown content of recipe file

    Returns:
        List of ingredient strings extracted from the Ingredients section
    """
    ingredients: list[str] = []

    # Find the Ingredients section
    # Pattern: ## Ingredients followed by bullet points
    ingredients_match = re.search(
        r"##\s+Ingredients\s*\n\n(.*?)(?=\n##|\Z)",
        markdown_content,
        re.DOTALL | re.IGNORECASE,
    )

    if ingredients_match:
        ingredients_text = ingredients_match.group(1)
        # Extract bullet points (lines starting with -)
        for line in ingredients_text.split("\n"):
            line = line.strip()
            if line.startswith("-"):
                # Remove the bullet point marker and clean up
                ingredient = line[1:].strip()
                if ingredient:
                    ingredients.append(ingredient)

    logger.debug(f"Extracted {len(ingredients)} ingredients from markdown")
    return ingredients


def _compare_ingredients(ingredients1: list[str], ingredients2: list[str]) -> bool:
    """Compare two ingredient lists for exact match.

    Args:
        ingredients1: First ingredient list
        ingredients2: Second ingredient list

    Returns:
        True if ingredients match exactly (same ingredients with same quantities)
    """
    normalized1 = sorted(_normalize_ingredient(ing) for ing in ingredients1)
    normalized2 = sorted(_normalize_ingredient(ing) for ing in ingredients2)

    match = normalized1 == normalized2
    logger.debug(
        f"Ingredient comparison: {len(ingredients1)} vs {len(ingredients2)} items, match={match}"
    )
    if not match:
        logger.debug(f"Recipe 1 ingredients: {normalized1}")
        logger.debug(f"Recipe 2 ingredients: {normalized2}")

    return match


def process_recipe(
    input_text: str,
    vault_path: Path,
    llm_endpoint: str,
    llm_model: str,
    recipes_dir: str = "personal/recipes",
    overwrite: bool = False,
    preview_only: bool = False,
    source_url: str | None = None,
) -> ProcessingResult:
    """Process a recipe from input text to formatted markdown.

    This function handles the complete recipe processing pipeline:
    - LLM-based extraction
    - Markdown formatting
    - Duplicate detection with ingredient comparison
    - File writing (unless preview_only=True)

    Args:
        input_text: Unstructured recipe text
        vault_path: Path to Obsidian vault root
        llm_endpoint: Ollama endpoint URL
        llm_model: Ollama model name
        recipes_dir: Relative path to recipes directory within vault
        overwrite: Whether to overwrite existing recipes
        preview_only: If True, don't write file, just return preview
        source_url: Optional source URL (e.g., Instagram post URL)

    Returns:
        ProcessingResult with recipe, markdown, file_path, timing, and duplicate info

    Raises:
        FileExistsError: If duplicate exists and overwrite is False or ingredients don't match
        ValueError: If validation fails
        ConnectionError: If LLM connection fails
        OSError: If file write fails
    """
    start_time = time.time()
    logger.info(f"Starting recipe processing (preview_only={preview_only})")

    # Initialize components
    logger.debug("Initializing LLM client")
    llm_client = OllamaClient(base_url=llm_endpoint, model=llm_model)

    # Health check
    if not llm_client.health_check():
        logger.error(f"Cannot connect to Ollama at {llm_endpoint}")
        raise ConnectionError(f"Cannot connect to Ollama at {llm_endpoint}")

    extractor = RecipeExtractor(llm_client=llm_client)
    formatter = MarkdownFormatter()
    writer = VaultWriter(vault_path=vault_path, recipes_dir=recipes_dir)

    # Extract recipe
    logger.info("Extracting recipe with LLM")
    extraction_start = time.time()
    recipe = extractor.extract(input_text, source_url=source_url)
    extraction_time = time.time() - extraction_start
    logger.info(f"Extraction took {extraction_time:.2f}s")
    logger.info(
        f"Extracted: {recipe.metadata.title} "
        f"({len(recipe.ingredients)} ingredients, {len(recipe.instructions)} steps)"
    )

    # Check for duplicates (always check, but only raise errors in non-preview mode)
    is_duplicate = writer.check_duplicate(recipe.metadata.title)
    duplicate_ingredients_match = False

    if is_duplicate:
        logger.info(f"Duplicate recipe detected: {recipe.metadata.title}")
        # Read existing recipe to compare ingredients
        try:
            existing_file = writer.get_file_path(recipe.metadata.title)
            if existing_file.exists():
                existing_ingredients = _extract_ingredients_from_markdown(
                    existing_file.read_text(encoding="utf-8")
                )
                duplicate_ingredients_match = _compare_ingredients(
                    recipe.ingredients, existing_ingredients
                )
                logger.info(
                    f"Ingredient comparison: match={duplicate_ingredients_match}, "
                    f"new={len(recipe.ingredients)} items, "
                    f"existing={len(existing_ingredients)} items"
                )
        except Exception as e:
            logger.warning(f"Could not read existing recipe for comparison: {e}")
            duplicate_ingredients_match = False

        # Only raise errors in non-preview mode
        if not preview_only:
            # If overwrite not requested, raise error
            if not overwrite:
                logger.error(
                    f"Recipe '{recipe.metadata.title}' already exists and overwrite=False"
                )
                raise FileExistsError(
                    f"Recipe '{recipe.metadata.title}' already exists. "
                    "Use overwrite=True to update directions, calories, or metadata (only if ingredients match exactly)."
                )

            # If overwrite is requested, check if ingredients match
            if overwrite:
                if not duplicate_ingredients_match:
                    logger.error(
                        f"Recipe '{recipe.metadata.title}' already exists but ingredients don't match. "
                        "Cannot overwrite - ingredients must match exactly to update directions, calories, or metadata."
                    )
                    raise FileExistsError(
                        f"Recipe '{recipe.metadata.title}' already exists with different ingredients. "
                        "Cannot overwrite - ingredients must match exactly to allow updating directions, calories, or metadata."
                    )
                else:
                    logger.info(
                        f"Ingredients match - will update directions, calories, and metadata for '{recipe.metadata.title}'"
                    )
        else:
            # Preview mode: log duplicate info but don't fail
            if duplicate_ingredients_match:
                logger.info(
                    "Preview mode: Duplicate exists with matching ingredients. "
                    "Can use overwrite=True to update directions, calories, or metadata."
                )
            else:
                logger.info(
                    "Preview mode: Duplicate exists with different ingredients. "
                    "Cannot overwrite - ingredients must match exactly."
                )

    # Format recipe
    logger.info("Formatting markdown")
    formatting_start = time.time()
    markdown = formatter.format(recipe)
    formatting_time = time.time() - formatting_start
    logger.info(f"Formatting took {formatting_time:.2f}s")

    # Write to vault (unless preview only)
    file_path: Path | None = None
    writing_time = 0.0

    if not preview_only:
        logger.info("Writing recipe to vault")
        write_start = time.time()
        file_path = writer.write(recipe.metadata.title, markdown, overwrite=overwrite)
        writing_time = time.time() - write_start
        logger.info(f"Writing took {writing_time:.2f}s")
        logger.info(f"Recipe saved to: {file_path}")
    else:
        logger.info("Preview mode: skipping file write")

    total_time = time.time() - start_time
    logger.info(f"Total processing time: {total_time:.2f}s")

    return ProcessingResult(
        recipe=recipe,
        markdown=markdown,
        file_path=file_path,
        timing={
            "extraction_time": extraction_time,
            "formatting_time": formatting_time,
            "writing_time": writing_time,
            "total_time": total_time,
        },
        is_duplicate=is_duplicate,
        duplicate_ingredients_match=duplicate_ingredients_match,
    )
