"""Recipe evaluation utilities for comparing model outputs against reference recipes."""

import json
import logging
from pathlib import Path
from typing import Any

from difflib import SequenceMatcher

from recipe_ingest.models.recipe import Recipe

logger = logging.getLogger(__name__)


def similarity_score(str1: str, str2: str) -> float:
    """Calculate similarity score between two strings (0-1).

    Args:
        str1: First string
        str2: Second string

    Returns:
        Similarity score between 0 and 1
    """
    if not str1 and not str2:
        return 1.0
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower().strip(), str2.lower().strip()).ratio()


def normalize_ingredient(ingredient: str) -> str:
    """Normalize ingredient string for comparison.

    Args:
        ingredient: Ingredient string

    Returns:
        Normalized ingredient string
    """
    # Remove extra whitespace, convert to lowercase
    return " ".join(ingredient.lower().strip().split())


def compare_ingredients(
    predicted: list[str], reference: list[str], threshold: float = 0.8
) -> dict[str, Any]:
    """Compare predicted ingredients against reference.

    Args:
        predicted: Predicted ingredient list
        reference: Reference ingredient list
        threshold: Similarity threshold for matching (0-1)

    Returns:
        Dictionary with accuracy metrics
    """
    if not reference:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "matched_count": 0,
            "total_predicted": len(predicted),
            "total_reference": 0,
        }

    if not predicted:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "matched_count": 0,
            "total_predicted": 0,
            "total_reference": len(reference),
        }

    # Normalize ingredients
    pred_normalized = [normalize_ingredient(ing) for ing in predicted]
    ref_normalized = [normalize_ingredient(ing) for ing in reference]

    # Find matches using similarity
    matched_indices = set()
    matches = []

    for i, pred_ing in enumerate(pred_normalized):
        best_match_idx = -1
        best_score = 0.0

        for j, ref_ing in enumerate(ref_normalized):
            if j in matched_indices:
                continue

            score = similarity_score(pred_ing, ref_ing)
            if score > best_score:
                best_score = score
                best_match_idx = j

        if best_score >= threshold and best_match_idx >= 0:
            matched_indices.add(best_match_idx)
            matches.append((i, best_match_idx, best_score))

    matched_count = len(matches)
    precision = matched_count / len(predicted) if predicted else 0.0
    recall = matched_count / len(reference) if reference else 0.0
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "matched_count": matched_count,
        "total_predicted": len(predicted),
        "total_reference": len(reference),
        "matches": matches,
    }


def compare_instructions(
    predicted: list[str], reference: list[str], threshold: float = 0.7
) -> dict[str, Any]:
    """Compare predicted instructions against reference.

    Args:
        predicted: Predicted instruction list
        reference: Reference instruction list
        threshold: Similarity threshold for matching (0-1)

    Returns:
        Dictionary with accuracy metrics
    """
    if not reference:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "matched_count": 0,
            "total_predicted": len(predicted),
            "total_reference": 0,
            "avg_similarity": 0.0,
        }

    if not predicted:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "matched_count": 0,
            "total_predicted": 0,
            "total_reference": len(reference),
            "avg_similarity": 0.0,
        }

    # For instructions, we compare order-aware (sequence similarity)
    # Calculate similarity for each step
    similarities = []
    max_len = max(len(predicted), len(reference))
    min_len = min(len(predicted), len(reference))

    for i in range(min_len):
        sim = similarity_score(predicted[i], reference[i])
        similarities.append(sim)

    # Penalize for length differences
    length_penalty = min_len / max_len if max_len > 0 else 0.0

    avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
    # Weighted average considering length
    weighted_similarity = avg_similarity * length_penalty

    # Count matches above threshold
    matches = [s for s in similarities if s >= threshold]
    matched_count = len(matches)

    precision = matched_count / len(predicted) if predicted else 0.0
    recall = matched_count / len(reference) if reference else 0.0
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "matched_count": matched_count,
        "total_predicted": len(predicted),
        "total_reference": len(reference),
        "avg_similarity": weighted_similarity,
        "step_similarities": similarities,
    }


def evaluate_recipe(predicted: Recipe, reference: Recipe) -> dict[str, Any]:
    """Evaluate predicted recipe against reference recipe.

    Args:
        predicted: Predicted recipe from model
        reference: Reference (gold standard) recipe

    Returns:
        Dictionary with comprehensive accuracy metrics
    """
    metrics = {}

    # Title similarity
    metrics["title_similarity"] = similarity_score(
        predicted.metadata.title, reference.metadata.title
    )

    # Ingredients comparison
    metrics["ingredients"] = compare_ingredients(
        predicted.ingredients, reference.ingredients
    )

    # Instructions comparison
    metrics["instructions"] = compare_instructions(
        predicted.instructions, reference.instructions
    )

    # Metadata fields
    metadata_metrics = {}
    metadata_metrics["prep_time_match"] = (
        similarity_score(
            predicted.metadata.prep_time or "",
            reference.metadata.prep_time or "",
        )
        if (predicted.metadata.prep_time or reference.metadata.prep_time)
        else None
    )
    metadata_metrics["cook_time_match"] = (
        similarity_score(
            predicted.metadata.cook_time or "",
            reference.metadata.cook_time or "",
        )
        if (predicted.metadata.cook_time or reference.metadata.cook_time)
        else None
    )
    metadata_metrics["cuisine_match"] = (
        similarity_score(
            predicted.metadata.cuisine or "",
            reference.metadata.cuisine or "",
        )
        if (predicted.metadata.cuisine or reference.metadata.cuisine)
        else None
    )
    metadata_metrics["main_ingredient_match"] = (
        similarity_score(
            predicted.metadata.main_ingredient or "",
            reference.metadata.main_ingredient or "",
        )
        if (predicted.metadata.main_ingredient or reference.metadata.main_ingredient)
        else None
    )
    metadata_metrics["servings_match"] = (
        predicted.metadata.servings == reference.metadata.servings
        if (predicted.metadata.servings and reference.metadata.servings)
        else None
    )

    metrics["metadata"] = metadata_metrics

    # Calculate overall score (weighted average)
    weights = {
        "title": 0.15,
        "ingredients": 0.35,
        "instructions": 0.40,
        "metadata": 0.10,
    }

    # Normalize metadata score
    metadata_scores = [
        v for v in metadata_metrics.values() if v is not None and isinstance(v, (float, bool))
    ]
    metadata_score = (
        sum(metadata_scores) / len(metadata_scores) if metadata_scores else 0.0
    )
    # Convert bool to float
    if metadata_metrics.get("servings_match") is not None:
        metadata_scores_bool = [
            float(v) if isinstance(v, bool) else v
            for v in metadata_metrics.values()
            if v is not None
        ]
        metadata_score = (
            sum(metadata_scores_bool) / len(metadata_scores_bool)
            if metadata_scores_bool
            else 0.0
        )

    overall_score = (
        weights["title"] * metrics["title_similarity"]
        + weights["ingredients"] * metrics["ingredients"]["f1"]
        + weights["instructions"] * metrics["instructions"]["f1"]
        + weights["metadata"] * metadata_score
    )

    metrics["overall_score"] = overall_score

    return metrics


def load_reference_recipe(file_path: Path) -> Recipe:
    """Load reference recipe from JSON file.

    Args:
        file_path: Path to JSON file containing reference recipe

    Returns:
        Recipe object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is invalid
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Reference recipe file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    try:
        return Recipe.model_validate(data)
    except Exception as e:
        raise ValueError(f"Invalid reference recipe format: {e}") from e


def save_reference_recipe(recipe: Recipe, file_path: Path) -> None:
    """Save recipe as reference (gold standard).

    Args:
        recipe: Recipe to save
        file_path: Path to save JSON file
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(recipe.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    logger.info(f"Saved reference recipe to {file_path}")

