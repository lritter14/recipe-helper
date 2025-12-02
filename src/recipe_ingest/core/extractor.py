"""Recipe extraction logic using LLM."""

import logging
import re
from datetime import datetime
from typing import Any

from pydantic import HttpUrl

from recipe_ingest.llm.client import OllamaClient
from recipe_ingest.models.recipe import MacroNutrients, Recipe, RecipeMetadata

logger = logging.getLogger(__name__)


# JSON schema for recipe extraction
RECIPE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "prep_time": {"type": ["string", "null"]},
        "cook_time": {"type": ["string", "null"]},
        "cuisine": {"type": ["string", "null"]},
        "main_ingredient": {"type": ["string", "null"]},
        "servings": {"type": ["integer", "null"]},
        "ingredients": {
            "type": "array",
            "items": {"type": "string"},
        },
        "instructions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "notes": {"type": ["string", "null"]},
        "calories_per_serving": {"type": ["number", "null"]},
        "carbs_grams": {"type": ["number", "null"]},
        "protein_grams": {"type": ["number", "null"]},
        "fat_grams": {"type": ["number", "null"]},
    },
    "required": ["title", "ingredients", "instructions"],
}

# JSON schema for nutrition calculation
NUTRITION_SCHEMA = {
    "type": "object",
    "properties": {
        "calories_per_serving": {"type": "number"},
        "carbs_grams": {"type": "number"},
        "protein_grams": {"type": "number"},
        "fat_grams": {"type": "number"},
    },
    "required": ["calories_per_serving", "carbs_grams", "protein_grams", "fat_grams"],
}


class RecipeExtractor:
    """Extract structured recipe data from unstructured text using LLM."""

    # Maximum input text length to send to LLM (characters)
    # This helps reduce tokens for very long inputs
    MAX_INPUT_LENGTH = 5000

    def __init__(self, llm_client: OllamaClient | None = None) -> None:
        """Initialize the recipe extractor.

        Args:
            llm_client: LLM client instance (e.g., Ollama client)
        """
        self.llm_client = llm_client or OllamaClient()

    def extract(self, text: str, source_url: str | None = None) -> Recipe:
        """Extract recipe information from unstructured text.

        Args:
            text: Raw recipe text from any source
            source_url: Optional source URL (e.g., Instagram post URL)

        Returns:
            Structured Recipe object with metadata and content

        Raises:
            ValueError: If extraction fails or required fields are missing
            ConnectionError: If LLM service is unavailable
        """
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

        logger.info(f"Extracting recipe from text (length: {len(text)} chars)")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Full input text:\n{text}")
        else:
            logger.debug(f"Input text preview: {text[:300]}...")

        # Preprocess and optimize input text
        processed_text = self._preprocess_text(text)
        original_length = len(text)
        processed_length = len(processed_text)
        if original_length != processed_length:
            logger.info(
                f"Text preprocessing: {original_length} -> {processed_length} chars "
                f"({(1 - processed_length / original_length) * 100:.1f}% reduction)"
            )

        # Create extraction prompt
        prompt = self._create_extraction_prompt(processed_text)
        logger.debug(f"Created extraction prompt (length: {len(prompt)} chars)")

        try:
            # Get structured output from LLM
            logger.info("Calling LLM for recipe extraction...")
            result = self.llm_client.generate(prompt, schema=RECIPE_SCHEMA)
            logger.info(f"Received LLM response with keys: {list(result.keys())}")

            # Check if LLM returned a schema instead of actual data
            if result.get("type") == "object" and "properties" in result:
                logger.warning(
                    "LLM returned JSON schema instead of recipe data. "
                    "Attempting to extract from input text as fallback."
                )
                # Try to extract from input text
                result = self._extract_fallback(processed_text, result)

            # Validate required fields with fallbacks
            if not result.get("title"):
                logger.warning(
                    f"LLM response missing 'title' field. "
                    f"Response keys: {list(result.keys())}. "
                    f"Attempting fallback extraction from input text."
                )
                fallback_title = self._extract_title_fallback(processed_text)
                if fallback_title:
                    result["title"] = fallback_title
                    logger.info(f"Using fallback title: {fallback_title}")
                else:
                    result["title"] = "Untitled Recipe"
                    logger.warning("Using default title: 'Untitled Recipe'")

            if not result.get("ingredients"):
                logger.warning(
                    f"LLM response missing 'ingredients' field. "
                    f"Response keys: {list(result.keys())}. "
                    f"Attempting fallback extraction from input text."
                )
                fallback_ingredients = self._extract_ingredients_fallback(processed_text)
                if fallback_ingredients:
                    result["ingredients"] = fallback_ingredients
                    logger.info(f"Using fallback ingredients ({len(fallback_ingredients)} items)")
                else:
                    result["ingredients"] = []
                    logger.warning("Using empty ingredients list as fallback")

            if not result.get("instructions"):
                logger.warning(
                    f"LLM response missing 'instructions' field. "
                    f"Response keys: {list(result.keys())}. "
                    f"Attempting fallback extraction from input text."
                )
                fallback_instructions = self._extract_instructions_fallback(processed_text)
                if fallback_instructions:
                    result["instructions"] = fallback_instructions
                    logger.info(f"Using fallback instructions ({len(fallback_instructions)} steps)")
                else:
                    result["instructions"] = []
                    logger.warning("Using empty instructions list as fallback")

            logger.debug(f"Extracted recipe: {result.get('title')}")

            # Check if nutrition info was extracted from source text
            servings = result.get("servings") or 1
            extracted_nutrition = {
                "calories_per_serving": result.get("calories_per_serving"),
                "carbs_grams": result.get("carbs_grams"),
                "protein_grams": result.get("protein_grams"),
                "fat_grams": result.get("fat_grams"),
            }

            # Use extracted nutrition if all values are present, otherwise calculate
            has_extracted_nutrition = all(
                v is not None
                for v in [
                    extracted_nutrition["calories_per_serving"],
                    extracted_nutrition["carbs_grams"],
                    extracted_nutrition["protein_grams"],
                    extracted_nutrition["fat_grams"],
                ]
            )

            if has_extracted_nutrition:
                # Type narrowing: we know all values are not None at this point
                calories = extracted_nutrition["calories_per_serving"]
                carbs = extracted_nutrition["carbs_grams"]
                protein = extracted_nutrition["protein_grams"]
                fat = extracted_nutrition["fat_grams"]
                assert calories is not None
                assert carbs is not None
                assert protein is not None
                assert fat is not None
                logger.info(
                    "Using nutrition information extracted from source text: "
                    f"{calories:.0f} cal, "
                    f"{carbs:.1f}g carbs, "
                    f"{protein:.1f}g protein, "
                    f"{fat:.1f}g fat"
                )
                nutrition = {
                    "calories_per_serving": float(calories),
                    "carbs_grams": float(carbs),
                    "protein_grams": float(protein),
                    "fat_grams": float(fat),
                }
            else:
                # Check if we have partial nutrition data
                has_partial = any(
                    v is not None
                    for v in [
                        extracted_nutrition["calories_per_serving"],
                        extracted_nutrition["carbs_grams"],
                        extracted_nutrition["protein_grams"],
                        extracted_nutrition["fat_grams"],
                    ]
                )
                if has_partial:
                    logger.warning(
                        "Partial nutrition data found in source but not all values present. "
                        "Calculating complete nutrition from ingredients."
                    )
                else:
                    logger.info(
                        "No nutrition info found in source text, calculating from ingredients"
                    )
                calculated_nutrition = self.calculate_nutrition(
                    result["ingredients"], servings, text
                )
                nutrition = calculated_nutrition

                # Log comparison if we had partial extracted data
                if has_partial:
                    logger.info(
                        "Nutrition comparison - Extracted (partial) vs Calculated: "
                        f"Calories: {extracted_nutrition['calories_per_serving']} vs {calculated_nutrition['calories_per_serving']:.0f}, "
                        f"Carbs: {extracted_nutrition['carbs_grams']} vs {calculated_nutrition['carbs_grams']:.1f}g, "
                        f"Protein: {extracted_nutrition['protein_grams']} vs {calculated_nutrition['protein_grams']:.1f}g, "
                        f"Fat: {extracted_nutrition['fat_grams']} vs {calculated_nutrition['fat_grams']:.1f}g"
                    )

            # Convert source_url to HttpUrl if provided
            url: HttpUrl | None = None
            if source_url:
                try:
                    url = HttpUrl(source_url)
                    logger.debug(f"Set source URL in metadata: {source_url}")
                except Exception as e:
                    logger.warning(f"Invalid source URL format: {source_url}, error: {e}")

            # Build metadata
            metadata = RecipeMetadata(
                title=result["title"],
                prep_time=result.get("prep_time"),
                cook_time=result.get("cook_time"),
                cuisine=result.get("cuisine"),
                url=url,
                main_ingredient=result.get("main_ingredient"),
                servings=servings,
                calories_per_serving=nutrition.get("calories_per_serving"),
                macros=MacroNutrients(
                    carbs=nutrition["carbs_grams"],
                    protein=nutrition["protein_grams"],
                    fat=nutrition["fat_grams"],
                ),
                created=datetime.now(),
            )

            # Build recipe
            recipe = Recipe(
                metadata=metadata,
                ingredients=result["ingredients"],
                instructions=result["instructions"],
                notes=result.get("notes"),
            )

            logger.info(f"Successfully extracted recipe: {recipe.metadata.title}")
            return recipe

        except ConnectionError:
            logger.error("Failed to connect to LLM service")
            raise
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise ValueError(f"Failed to extract recipe: {e}") from e

    def calculate_nutrition(
        self, ingredients: list[str], servings: int, source_text: str | None = None
    ) -> dict[str, float]:
        """Calculate estimated nutritional information using LLM.

        Args:
            ingredients: List of ingredients with quantities
            servings: Number of servings
            source_text: Optional source text that may contain nutrition information

        Returns:
            Dictionary with calories_per_serving and macro grams

        Raises:
            ValueError: If calculation fails
            ConnectionError: If LLM service is unavailable
        """
        logger.info(
            f"Calculating nutrition for {len(ingredients)} ingredients, {servings} servings"
        )

        # Create nutrition prompt
        prompt = self._create_nutrition_prompt(ingredients, servings, source_text)

        try:
            result = self.llm_client.generate(prompt, schema=NUTRITION_SCHEMA)

            # Validate and return
            nutrition = {
                "calories_per_serving": float(result["calories_per_serving"]),
                "carbs_grams": float(result["carbs_grams"]),
                "protein_grams": float(result["protein_grams"]),
                "fat_grams": float(result["fat_grams"]),
            }

            logger.debug(f"Calculated nutrition: {nutrition['calories_per_serving']} cal/serving")
            return nutrition

        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Nutrition calculation failed, using defaults: {e}")
            # Return conservative defaults if calculation fails
            return {
                "calories_per_serving": 0.0,
                "carbs_grams": 0.0,
                "protein_grams": 0.0,
                "fat_grams": 0.0,
            }

    def _preprocess_text(self, text: str) -> str:
        """Preprocess and optimize input text to reduce tokens.

        Args:
            text: Raw recipe text

        Returns:
            Cleaned and optimized text
        """
        if not text:
            return text

        # Normalize whitespace: collapse multiple spaces/newlines
        text = re.sub(r"[ \t]+", " ", text)  # Multiple spaces to single
        text = re.sub(r"\n{3,}", "\n\n", text)  # Multiple newlines to double
        text = re.sub(r" *\n *", "\n", text)  # Remove spaces around newlines

        # Remove common social media artifacts
        text = re.sub(r"#\w+", "", text)  # Remove hashtags (but keep content)
        text = re.sub(r"@\w+", "", text)  # Remove @mentions

        # Remove excessive punctuation
        text = re.sub(r"\.{3,}", "...", text)  # Multiple dots to ellipsis
        text = re.sub(r"!{2,}", "!", text)  # Multiple exclamations to single

        # Trim and normalize
        text = text.strip()

        # Truncate if too long (preserve structure by truncating at sentence boundary)
        original_length = len(text)
        if original_length > self.MAX_INPUT_LENGTH:
            truncated = text[: self.MAX_INPUT_LENGTH]
            # Try to truncate at sentence boundary
            last_period = truncated.rfind(".")
            last_newline = truncated.rfind("\n")
            cutoff = max(last_period, last_newline)
            if cutoff > self.MAX_INPUT_LENGTH * 0.8:  # Only if we don't lose too much
                text = truncated[: cutoff + 1]
                logger.warning(
                    f"Input text truncated from {original_length} to {len(text)} chars "
                    f"at sentence boundary"
                )
            else:
                text = truncated
                logger.warning(
                    f"Input text truncated from {original_length} to {len(text)} chars "
                    f"(no good sentence boundary found)"
                )

        return text

    def _create_extraction_prompt(self, text: str) -> str:
        """Create optimized prompt for recipe extraction.

        Args:
            text: Preprocessed recipe text

        Returns:
            Compact formatted prompt string
        """
        # Compact prompt - reduced verbosity while maintaining clarity
        return f"""Extract recipe as JSON:
- title, prep_time, cook_time, cuisine, main_ingredient, servings (int)
- ingredients: array of strings with quantities
- instructions: array of step strings
- notes (optional)
- calories_per_serving, carbs_grams, protein_grams, fat_grams (numbers, optional if in text)

Extract nutrition values if explicitly stated (e.g., "X cal", "Xg protein").

Text:
{text}

Return JSON only."""

    def _extract_fallback(self, text: str, schema_response: dict[str, Any]) -> dict[str, Any]:
        """Extract recipe data from text when LLM returns schema instead of data.

        Args:
            text: Input recipe text
            schema_response: The schema response from LLM

        Returns:
            Dictionary with extracted recipe fields
        """
        result: dict[str, Any] = {}

        # Try to extract title
        title = self._extract_title_fallback(text)
        if title:
            result["title"] = title

        # Try to extract ingredients
        ingredients = self._extract_ingredients_fallback(text)
        if ingredients:
            result["ingredients"] = ingredients

        # Try to extract instructions
        instructions = self._extract_instructions_fallback(text)
        if instructions:
            result["instructions"] = instructions

        # Preserve any other fields that might be in the response
        for key in [
            "notes",
            "calories_per_serving",
            "carbs_grams",
            "protein_grams",
            "fat_grams",
            "prep_time",
            "cook_time",
            "cuisine",
            "main_ingredient",
            "servings",
        ]:
            if key in schema_response and schema_response[key] is not None:
                result[key] = schema_response[key]

        return result

    def _extract_title_fallback(self, text: str) -> str | None:
        """Extract recipe title from text as fallback.

        Args:
            text: Input recipe text

        Returns:
            Extracted title or None if not found
        """
        if not text:
            return None

        # Look for title patterns:
        # 1. First line if it's short and looks like a title
        lines = text.split("\n")
        first_line = lines[0].strip()

        # If first line is short (less than 100 chars) and doesn't start with common recipe words
        if (
            len(first_line) < 100
            and first_line
            and not first_line.lower().startswith(
                (
                    "ingredients",
                    "instructions",
                    "directions",
                    "prep",
                    "cook",
                    "serves",
                    "makes",
                    "-",
                    "*",
                    "1.",
                    "2.",
                )
            )
        ):
            return first_line

        # 2. Look for patterns like "Recipe: Title" or "Title Recipe"
        title_patterns = [
            r"^([^:\n]{5,80})\s*recipe",
            r"recipe:\s*([^:\n]{5,80})",
            r"^([A-Z][^:\n]{4,80})(?:\n|$)",
        ]

        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                title = match.group(1).strip()
                if title and len(title) < 100:
                    return title

        return None

    def _extract_ingredients_fallback(self, text: str) -> list[str] | None:
        """Extract ingredients list from text as fallback.

        Args:
            text: Input recipe text

        Returns:
            List of ingredients or None if not found
        """
        if not text:
            return None

        ingredients = []

        # Look for ingredients section
        ingredients_patterns = [
            r"ingredients?[:\s]*\n((?:[-•*]\s*.+\n?)+)",
            r"ingredients?[:\s]*\n((?:\d+[.)]?\s*.+\n?)+)",
        ]

        for pattern in ingredients_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                ingredients_text = match.group(1)
                # Split by lines and clean
                for line in ingredients_text.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    # Remove bullet points and numbering
                    line = re.sub(r"^[-•*]\s*", "", line)
                    line = re.sub(r"^\d+[.)]\s*", "", line)
                    if line:
                        ingredients.append(line)
                if ingredients:
                    return ingredients

        # Fallback: look for lines that look like ingredients (short lines with common ingredient words)
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line or len(line) > 100:  # Skip very long lines
                continue
            # Check if line looks like an ingredient (has quantity words or common patterns)
            if re.search(
                r"\d+\s*(cup|tbsp|tsp|oz|lb|g|kg|ml|l|gram|pound|ounce)",
                line,
                re.IGNORECASE,
            ):
                # Remove bullet points
                line = re.sub(r"^[-•*]\s*", "", line)
                if line:
                    ingredients.append(line)

        return ingredients if ingredients else None

    def _extract_instructions_fallback(self, text: str) -> list[str] | None:
        """Extract instructions from text as fallback.

        Args:
            text: Input recipe text

        Returns:
            List of instruction steps or None if not found
        """
        if not text:
            return None

        instructions = []

        # Look for instructions section
        instructions_patterns = [
            r"(?:instructions?|directions?|steps?|method)[:\s]*\n((?:[-•*]\s*.+\n?)+)",
            r"(?:instructions?|directions?|steps?|method)[:\s]*\n((?:\d+[.)]?\s*.+\n?)+)",
        ]

        for pattern in instructions_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                instructions_text = match.group(1)
                # Split by lines and clean
                for line in instructions_text.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    # Remove bullet points and numbering
                    line = re.sub(r"^[-•*]\s*", "", line)
                    line = re.sub(r"^\d+[.)]\s*", "", line)
                    if line:
                        instructions.append(line)
                if instructions:
                    return instructions

        # Fallback: look for numbered steps
        numbered_steps = re.findall(r"^\d+[.)]\s*(.+)$", text, re.MULTILINE)
        if numbered_steps:
            return [step.strip() for step in numbered_steps if step.strip()]

        return instructions if instructions else None

    def _create_nutrition_prompt(
        self, ingredients: list[str], servings: int, source_text: str | None = None
    ) -> str:
        """Create optimized prompt for nutrition calculation.

        Args:
            ingredients: List of ingredients with quantities
            servings: Number of servings
            source_text: Optional source text that may contain nutrition information

        Returns:
            Compact formatted prompt string
        """
        # Compact ingredients list (no bullet points to save tokens)
        ingredients_text = "\n".join(ingredients)

        source_context = ""
        if source_text:
            # Preprocess and limit source text
            processed_source = self._preprocess_text(source_text)
            # Limit to first 300 chars (reduced from 500)
            truncated_text = processed_source[:300]
            source_context = f"\n\nSource: {truncated_text}"

        # Compact prompt
        return f"""Estimate nutrition (JSON):
- calories_per_serving, carbs_grams, protein_grams, fat_grams (numbers)

Ingredients:
{ingredients_text}

Servings: {servings}{source_context}

Use source values if reasonable, else estimate from ingredients."""
