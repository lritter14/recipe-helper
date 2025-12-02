"""Recipe data models using Pydantic."""

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class MacroNutrients(BaseModel):
    """Macronutrient information."""

    carbs: float = Field(..., description="Carbohydrates in grams", ge=0)
    protein: float = Field(..., description="Protein in grams", ge=0)
    fat: float = Field(..., description="Fat in grams", ge=0)


class RecipeMetadata(BaseModel):
    """Recipe metadata for frontmatter."""

    title: str = Field(..., description="Recipe title")
    prep_time: str | None = Field(
        None, description="Preparation time (e.g., '15 minutes')"
    )
    cook_time: str | None = Field(None, description="Cooking time (e.g., '30 minutes')")
    cuisine: str | None = Field(None, description="Cuisine type (e.g., 'Italian')")
    url: HttpUrl | None = Field(None, description="Source URL if applicable")
    main_ingredient: str | None = Field(None, description="Primary ingredient")
    calories_per_serving: float | None = Field(
        None, description="Estimated calories", ge=0
    )
    macros: MacroNutrients | None = Field(None, description="Macronutrient breakdown")
    servings: int | None = Field(None, description="Number of servings", ge=1)
    created: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )


class Recipe(BaseModel):
    """Complete recipe with metadata and content."""

    metadata: RecipeMetadata = Field(..., description="Recipe metadata")
    ingredients: list[str] = Field(
        ..., description="List of ingredients with quantities"
    )
    instructions: list[str] = Field(..., description="Cooking instructions as steps")
    notes: str | None = Field(None, description="Additional notes or comments")

    def to_markdown(self) -> str:
        """Convert recipe to markdown format with frontmatter.

        Returns:
            Formatted markdown string with YAML frontmatter
        """
        # TODO: Implement markdown conversion
        raise NotImplementedError("Markdown conversion not yet implemented")
