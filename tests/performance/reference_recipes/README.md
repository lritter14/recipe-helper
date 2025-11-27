# Reference Recipes

This directory contains reference (gold standard) recipes used for accuracy evaluation in benchmark tests.

## Creating a Reference Recipe

You can create a reference recipe in two ways:

### Option 1: Manual Creation (Recommended)

Manually create a reference recipe to ensure accuracy:

```bash
# Interactive mode (prompts you for all fields)
python -m tests.performance.create_reference_recipe_manual

# Or create a template JSON file to edit
python -m tests.performance.create_reference_recipe_manual --template
# Then edit the template and validate it:
python -m tests.performance.create_reference_recipe_manual --from-template
```

This allows you to:
- Manually verify and correct all recipe data
- Ensure the reference is truly a "gold standard"
- See the Instagram caption for reference while entering data

### Option 2: LLM-Generated (Then Manually Review)

Generate using an LLM, then manually review and correct:

```bash
python -m tests.performance.create_reference_recipe
```

This will:
1. Extract the recipe from the Instagram URL
2. Process it using a trusted model (default: `llama3.1:8b`, configurable via `REFERENCE_MODEL` env var)
3. Save it as a JSON file in this directory

**Important**: Always manually review and correct LLM-generated reference recipes to ensure accuracy.

## File Naming

Reference recipes are named based on the Instagram post ID:
- `DRYdlekE-Yb.json` for URL `https://www.instagram.com/reel/DRYdlekE-Yb`

## Manual Creation

You can also manually create a reference recipe by:
1. Processing the recipe with a trusted/high-quality model
2. Manually reviewing and correcting the output
3. Saving it as JSON using the Recipe model's `model_dump()` method

## Using Reference Recipes

The benchmark tests automatically load reference recipes and compare model outputs against them, calculating:
- Title similarity
- Ingredients precision/recall/F1
- Instructions precision/recall/F1
- Metadata field matches
- Overall accuracy score

