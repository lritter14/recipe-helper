"""Markdown formatting for recipes."""

import logging

import yaml

from recipe_ingest.models.recipe import Recipe

logger = logging.getLogger(__name__)


class MarkdownFormatter:
    """Format recipes as markdown with YAML frontmatter."""

    def format(self, recipe: Recipe) -> str:
        """Format a recipe as markdown with frontmatter.

        Args:
            recipe: Recipe object to format

        Returns:
            Formatted markdown string with YAML frontmatter
        """
        logger.debug(f"Formatting recipe: {recipe.metadata.title}")

        # Build frontmatter and body
        frontmatter = self._format_frontmatter(recipe)
        body = self._format_body(recipe)

        # Combine with proper markdown structure
        markdown = f"---\n{frontmatter}---\n\n{body}"

        logger.info(f"Formatted recipe: {recipe.metadata.title}")
        return markdown

    def _format_frontmatter(self, recipe: Recipe) -> str:
        """Generate YAML frontmatter from recipe metadata.

        Args:
            recipe: Recipe object

        Returns:
            YAML frontmatter string
        """
        metadata_dict: dict[str, str | int | float | dict[str, float] | None] = {
            "title": recipe.metadata.title,
        }

        # Add optional fields if present
        if recipe.metadata.prep_time:
            metadata_dict["prep_time"] = recipe.metadata.prep_time
        if recipe.metadata.cook_time:
            metadata_dict["cook_time"] = recipe.metadata.cook_time
        if recipe.metadata.cuisine:
            metadata_dict["cuisine"] = recipe.metadata.cuisine
        if recipe.metadata.url:
            metadata_dict["url"] = str(recipe.metadata.url)
        if recipe.metadata.main_ingredient:
            metadata_dict["main_ingredient"] = recipe.metadata.main_ingredient
        if recipe.metadata.servings:
            metadata_dict["servings"] = recipe.metadata.servings

        # Add nutrition info if available
        if recipe.metadata.calories_per_serving:
            metadata_dict["calories_per_serving"] = recipe.metadata.calories_per_serving

        if recipe.metadata.macros:
            metadata_dict["macros"] = {
                "carbs": recipe.metadata.macros.carbs,
                "protein": recipe.metadata.macros.protein,
                "fat": recipe.metadata.macros.fat,
            }

        # Add created timestamp
        metadata_dict["created"] = recipe.metadata.created.isoformat()

        # Convert to YAML
        return yaml.dump(metadata_dict, default_flow_style=False, sort_keys=False)

    def _format_body(self, recipe: Recipe) -> str:
        """Generate markdown body with ingredients and instructions.

        Args:
            recipe: Recipe object

        Returns:
            Markdown body string
        """
        # Title with emoji (optional enhancement)
        title = f"# {recipe.metadata.title}"

        # Ingredients section
        ingredients_section = "## Ingredients\n\n"
        for ingredient in recipe.ingredients:
            ingredients_section += f"- {ingredient}\n"

        # Instructions section
        instructions_section = "\n## Instructions\n\n"
        for i, instruction in enumerate(recipe.instructions, 1):
            instructions_section += f"{i}. {instruction}\n"

        # Optional notes section
        notes_section = ""
        if recipe.notes:
            notes_section = f"\n## Notes\n\n{recipe.notes}\n"

        return f"{title}\n\n{ingredients_section}{instructions_section}{notes_section}"
