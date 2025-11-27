"""Performance benchmarks for Instagram recipe processing with different Ollama models.

These tests are marked as 'slow' and require:
- Real Instagram access (for the test URL)
- Real Ollama instance running
- Network connectivity

Configuration:
- OLLAMA_MODELS: Comma-separated list of models to test (required)
- OLLAMA_MODELS_LIMIT: Limit to first N models for faster testing (optional, default: all)
- OLLAMA_PRIMARY_MODEL: Test this model first (useful for debugging, optional)
- OLLAMA_ENDPOINT: Ollama API endpoint (optional, default: http://localhost:11434)

Examples:
  # Test all models in OLLAMA_MODELS (only tests models that are available in Ollama)
  pytest tests/performance/test_instagram_benchmark.py -m slow -v

  # Test only first 2 models (faster iteration)
  OLLAMA_MODELS_LIMIT=2 pytest tests/performance/test_instagram_benchmark.py -m slow -v

  # Test a specific model first (good for debugging)
  OLLAMA_PRIMARY_MODEL=llama3.1:8b pytest tests/performance/test_instagram_benchmark.py -m slow -v

  # Run just the smoke test to verify setup
  pytest tests/performance/test_instagram_benchmark.py::TestInstagramBenchmark::test_setup_smoke_test -v

  # Run with verbose logging to see what's sent/received
  pytest tests/performance/test_instagram_benchmark.py::TestInstagramBenchmark::test_setup_smoke_test -v -s --log-cli-level=DEBUG

  # Compare performance (timing) across all models (no reference recipe needed)
  pytest tests/performance/test_instagram_benchmark.py::TestInstagramBenchmark::test_compare_performance -v -s

  # Compare performance AND accuracy (requires reference recipe)
  # First create reference recipe: python tests/performance/create_reference_recipe.py
  pytest tests/performance/test_instagram_benchmark.py::TestInstagramBenchmark::test_compare_all_models -v -s

  # Check what models are available in Ollama
  ./scripts/check-ollama.sh

Resilience:
- Extraction failures are skipped (not failed) to allow other models to be tested
- Connection errors are skipped gracefully
- Better error logging shows what LLM actually returned when extraction fails
"""

import logging
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from recipe_ingest.core import process_recipe
from tests.performance.recipe_evaluator import (
    evaluate_recipe,
    load_reference_recipe,
)

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Test Instagram URL - a real recipe post
TEST_INSTAGRAM_URL = "https://www.instagram.com/reel/DRYdlekE-Yb"

# Path to reference recipe (gold standard)
REFERENCE_RECIPE_PATH = Path(__file__).parent / "reference_recipes" / "DRYdlekE-Yb.json"

# Models to benchmark - loaded from .env file
OLLAMA_MODELS_STR = os.getenv("OLLAMA_MODELS")
if not OLLAMA_MODELS_STR:
    raise ValueError(
        "OLLAMA_MODELS not found in environment. "
        "Please create a .env file from .env.example and set OLLAMA_MODELS."
    )
ALL_MODELS = [model.strip() for model in OLLAMA_MODELS_STR.split(",") if model.strip()]

# Limit models for faster testing (set OLLAMA_MODELS_LIMIT env var to test only first N models)
# Default: test all models, but can be limited for faster iteration
MODELS_LIMIT = int(os.getenv("OLLAMA_MODELS_LIMIT", "0"))  # 0 means no limit
if MODELS_LIMIT > 0:
    OLLAMA_MODELS = ALL_MODELS[:MODELS_LIMIT]
    logger.info(f"Limited to first {MODELS_LIMIT} models: {OLLAMA_MODELS}")
else:
    OLLAMA_MODELS = ALL_MODELS

# Primary model for testing (set OLLAMA_PRIMARY_MODEL to test a specific model first)
# Useful for debugging - test a known-good model before testing others
# If PRIMARY_MODEL is set, it will be used even if not in OLLAMA_MODELS
PRIMARY_MODEL = os.getenv("OLLAMA_PRIMARY_MODEL")
if PRIMARY_MODEL:
    if PRIMARY_MODEL in ALL_MODELS:
        # Move primary model to front if it exists in the list
        OLLAMA_MODELS = [PRIMARY_MODEL] + [m for m in OLLAMA_MODELS if m != PRIMARY_MODEL]
        logger.info(f"Using primary model '{PRIMARY_MODEL}' (found in OLLAMA_MODELS)")
    else:
        # Use primary model even if not in OLLAMA_MODELS (for testing specific models)
        OLLAMA_MODELS = [PRIMARY_MODEL]
        logger.info(
            f"Using primary model '{PRIMARY_MODEL}' (not in OLLAMA_MODELS, testing this model only)"
        )


@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    """Create a temporary vault directory for testing."""
    vault = tmp_path / "test_vault"
    vault.mkdir()
    return vault


@pytest.fixture
def ollama_endpoint() -> str:
    """Get Ollama endpoint from environment or use default."""
    import os

    return os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")


@pytest.fixture
def available_ollama_models(ollama_endpoint: str) -> list[str]:
    """Get list of available models from Ollama.

    Returns:
        List of available model names

    Raises:
        pytest.Skip: If Ollama is not accessible
    """
    from recipe_ingest.llm.client import OllamaClient

    try:
        client = OllamaClient(base_url=ollama_endpoint)
        models = client.list_models()
        logger.info(f"Found {len(models)} available models in Ollama: {models}")
        return models
    except Exception as e:
        logger.warning(f"Could not list Ollama models: {e}")
        pytest.skip(f"Cannot access Ollama to list models: {e}")


@pytest.fixture
def instagram_caption() -> str:
    """Extract Instagram caption once for all tests.

    Returns:
        Extracted caption text

    Raises:
        pytest.Skip: If Instagram extraction fails
    """
    from recipe_ingest.parsers.instagram import InstagramParser

    instagram_parser = InstagramParser()
    try:
        caption = instagram_parser.parse(TEST_INSTAGRAM_URL)
        logger.info(f"Extracted Instagram caption ({len(caption)} characters)")
        return caption
    except Exception as e:
        pytest.skip(f"Failed to extract Instagram caption: {e}")


@pytest.fixture
def reference_recipe():
    """Load reference recipe (gold standard) for accuracy evaluation.

    Returns:
        Reference Recipe object

    Raises:
        pytest.Skip: If reference recipe file doesn't exist
    """
    try:
        recipe = load_reference_recipe(REFERENCE_RECIPE_PATH)
        logger.info(f"Loaded reference recipe: {recipe.metadata.title}")
        return recipe
    except FileNotFoundError:
        pytest.skip(
            f"Reference recipe not found at {REFERENCE_RECIPE_PATH}. "
            "Create a reference recipe first using a trusted model output."
        )
    except Exception as e:
        pytest.skip(f"Failed to load reference recipe: {e}")


@pytest.mark.slow
@pytest.mark.performance
@pytest.mark.integration
class TestInstagramBenchmark:
    """Benchmark Instagram processing with different Ollama models."""

    def test_setup_smoke_test(
        self,
        temp_vault: Path,
        ollama_endpoint: str,
        instagram_caption: str,
    ) -> None:
        """Simple smoke test to verify test setup is working.

        This test uses the first available model (or PRIMARY_MODEL if set) to verify:
        - Ollama is accessible
        - Instagram caption extraction works
        - Basic recipe processing works

        Set OLLAMA_PRIMARY_MODEL env var to test a specific model first.
        The model will be used even if it's not in your OLLAMA_MODELS list.

        Args:
            temp_vault: Temporary vault directory
            ollama_endpoint: Ollama API endpoint
            instagram_caption: Pre-extracted Instagram caption
        """
        if not OLLAMA_MODELS:
            pytest.skip("No models configured for testing")

        # Use first model for smoke test (which will be PRIMARY_MODEL if set)
        model = OLLAMA_MODELS[0]
        logger.info(f"Smoke test with model: {model}")
        logger.info(f"Available models in test: {OLLAMA_MODELS}")
        if PRIMARY_MODEL:
            logger.info(f"PRIMARY_MODEL was set to: {PRIMARY_MODEL}")
        logger.info(f"Input caption length: {len(instagram_caption)} chars")

        # Verify the model matches what was requested
        if PRIMARY_MODEL and model != PRIMARY_MODEL:
            logger.warning(
                f"Requested PRIMARY_MODEL '{PRIMARY_MODEL}' but using '{model}'. "
                f"Check that the model name matches exactly."
            )

        # Optionally check if model is available in Ollama
        try:
            from recipe_ingest.llm.client import OllamaClient

            client = OllamaClient(base_url=ollama_endpoint, model=model)
            available_models = client.list_models()
            if model not in available_models:
                logger.warning(
                    f"Model '{model}' not found in Ollama. Available models: {available_models}"
                )
        except Exception as e:
            logger.debug(f"Could not check available models: {e}")

        try:
            result = process_recipe(
                input_text=instagram_caption,
                vault_path=temp_vault,
                llm_endpoint=ollama_endpoint,
                llm_model=model,
                recipes_dir="personal/recipes",
                overwrite=False,
                preview_only=True,
                source_url=TEST_INSTAGRAM_URL,
            )

            # Basic verification
            assert result.recipe is not None, "Recipe should be extracted"
            assert result.recipe.metadata.title is not None, "Recipe should have a title"
            assert len(result.recipe.ingredients) > 0, "Recipe should have ingredients"
            assert len(result.recipe.instructions) > 0, "Recipe should have instructions"

            logger.info(f"✓ Smoke test passed with {model}: {result.recipe.metadata.title}")

        except ConnectionError as e:
            pytest.fail(f"Setup failed: Cannot connect to Ollama - {e}")
        except ValueError as e:
            # Log the error but don't fail - this helps diagnose LLM issues
            logger.error(f"Setup test failed with {model}: {e}")
            pytest.skip(f"Model '{model}' failed extraction (may be too small/weak): {e}")

    @pytest.mark.parametrize("model", OLLAMA_MODELS)
    def test_instagram_url_with_model(
        self,
        model: str,
        temp_vault: Path,
        ollama_endpoint: str,
        instagram_caption: str,
        available_ollama_models: list[str],
    ) -> None:
        """Test processing Instagram URL with a specific Ollama model.

        This test:
        1. Processes recipe with specified model
        2. Measures processing time
        3. Verifies output quality

        Args:
            model: Ollama model name to test
            temp_vault: Temporary vault directory
            ollama_endpoint: Ollama API endpoint
            instagram_caption: Pre-extracted Instagram caption
            available_ollama_models: List of models available in Ollama
        """
        logger.info(f"Testing Instagram URL with model: {model}")

        # Check if model is available
        if model not in available_ollama_models:
            pytest.skip(
                f"Model '{model}' not found in Ollama. "
                f"Available models: {available_ollama_models}. "
                f"Install with: ollama pull {model}"
            )

        # Process recipe with the specified model
        try:
            result = process_recipe(
                input_text=instagram_caption,
                vault_path=temp_vault,
                llm_endpoint=ollama_endpoint,
                llm_model=model,
                recipes_dir="personal/recipes",
                overwrite=False,
                preview_only=True,  # Don't write files, just measure performance
                source_url=TEST_INSTAGRAM_URL,
            )

            # Verify results
            assert result.recipe is not None
            assert result.recipe.metadata.title is not None
            assert len(result.recipe.ingredients) > 0
            assert len(result.recipe.instructions) > 0

            # Log performance metrics
            total_time = result.timing["total_time"]
            extraction_time = result.timing["extraction_time"]
            formatting_time = result.timing["formatting_time"]

            logger.info(
                f"Model: {model} | "
                f"Total: {total_time:.2f}s | "
                f"Extraction: {extraction_time:.2f}s | "
                f"Formatting: {formatting_time:.2f}s | "
                f"Title: {result.recipe.metadata.title}"
            )

            # Store results for comparison (can be extended to write to file)
            assert total_time > 0, "Processing time should be positive"
            assert extraction_time > 0, "Extraction time should be positive"

        except ConnectionError as e:
            pytest.skip(f"Ollama model '{model}' not available: {e}")
        except ValueError as e:
            # Some models (especially small ones) may fail to extract properly
            # Skip instead of failing to allow other models to be tested
            error_msg = str(e)
            if "failed to extract" in error_msg.lower() or "llm failed" in error_msg.lower():
                logger.warning(
                    f"Model '{model}' failed extraction (may be too small/weak): {error_msg}"
                )
                pytest.skip(f"Model '{model}' extraction failed: {error_msg}")
            else:
                # Re-raise other ValueError exceptions (e.g., validation errors)
                raise

    def test_compare_performance(
        self,
        temp_vault: Path,
        ollama_endpoint: str,
        instagram_caption: str,
        available_ollama_models: list[str],
    ) -> None:
        """Compare performance (timing) across all available models.

        This test runs all models and collects timing data for comparison.
        Does not require a reference recipe - just shows speed differences.

        Args:
            temp_vault: Temporary vault directory
            ollama_endpoint: Ollama API endpoint
            instagram_caption: Pre-extracted Instagram caption
            available_ollama_models: List of models available in Ollama
        """

        # Filter to only models that are available
        models_to_test = [m for m in OLLAMA_MODELS if m in available_ollama_models]
        missing_models = [m for m in OLLAMA_MODELS if m not in available_ollama_models]

        if missing_models:
            logger.warning(
                f"Skipping {len(missing_models)} models not available in Ollama: {missing_models}"
            )
            logger.info("Install missing models with: ollama pull <model_name>")

        if not models_to_test:
            pytest.skip(
                f"None of the configured models are available in Ollama. "
                f"Configured: {OLLAMA_MODELS}, Available: {available_ollama_models}"
            )

        logger.info(f"Testing {len(models_to_test)} available models: {models_to_test}")

        results = []

        for model in models_to_test:
            try:
                result = process_recipe(
                    input_text=instagram_caption,
                    vault_path=temp_vault,
                    llm_endpoint=ollama_endpoint,
                    llm_model=model,
                    recipes_dir="personal/recipes",
                    overwrite=False,
                    preview_only=True,
                    source_url=TEST_INSTAGRAM_URL,
                )

                results.append(
                    {
                        "model": model,
                        "total_time": result.timing["total_time"],
                        "extraction_time": result.timing["extraction_time"],
                        "formatting_time": result.timing["formatting_time"],
                        "title": result.recipe.metadata.title,
                        "ingredients_count": len(result.recipe.ingredients),
                        "instructions_count": len(result.recipe.instructions),
                        "has_nutrition": result.recipe.metadata.calories_per_serving is not None,
                    }
                )

                logger.info(
                    f"✓ {model}: {result.timing['total_time']:.2f}s total "
                    f"({result.timing['extraction_time']:.2f}s extraction) - "
                    f"{result.recipe.metadata.title}"
                )

            except (ConnectionError, Exception) as e:
                logger.warning(f"✗ {model}: Failed - {e}")
                results.append(
                    {
                        "model": model,
                        "error": str(e),
                    }
                )

        # Print comparison table
        print("\n" + "=" * 100)
        print("PERFORMANCE COMPARISON")
        print("=" * 100)
        print(
            f"{'Model':<20} {'Total (s)':<12} {'Extraction (s)':<15} {'Formatting (s)':<15} "
            f"{'Ingredients':<12} {'Instructions':<12} {'Status':<15}"
        )
        print("-" * 100)

        successful_results = [r for r in results if "error" not in r]
        if successful_results:
            # Sort by total time (ascending) - fastest first
            successful_results.sort(key=lambda x: x["total_time"])

            for r in successful_results:
                print(
                    f"{r['model']:<20} {r['total_time']:<12.2f} {r['extraction_time']:<15.2f} "
                    f"{r['formatting_time']:<15.2f} {r['ingredients_count']:<12} "
                    f"{r['instructions_count']:<12} Success"
                )

            # Show failed models
            failed_results = [r for r in results if "error" in r]
            for r in failed_results:
                print(
                    f"{r['model']:<20} {'N/A':<12} {'N/A':<15} {'N/A':<15} "
                    f"{'N/A':<12} {'N/A':<12} Failed: {r['error'][:50]}"
                )

            print("=" * 100)
            fastest = successful_results[0]
            slowest = successful_results[-1]
            print(f"\nFastest: {fastest['model']} ({fastest['total_time']:.2f}s)")
            print(f"Slowest: {slowest['model']} ({slowest['total_time']:.2f}s)")
            if len(successful_results) > 1:
                speedup = slowest["total_time"] / fastest["total_time"]
                print(f"Speed difference: {speedup:.2f}x faster")

        else:
            print("No models succeeded. Check Ollama availability and model names.")

        # At least one model should succeed
        assert len(successful_results) > 0, "At least one model should succeed"

    def test_compare_all_models(
        self,
        temp_vault: Path,
        ollama_endpoint: str,
        instagram_caption: str,
        reference_recipe,
        available_ollama_models: list[str],
    ) -> None:
        """Compare all available models and report performance and accuracy.

        This test runs all models and collects timing and accuracy data for comparison.

        Args:
            temp_vault: Temporary vault directory
            ollama_endpoint: Ollama API endpoint
            instagram_caption: Pre-extracted Instagram caption
            reference_recipe: Reference (gold standard) recipe for comparison
            available_ollama_models: List of models available in Ollama
        """

        # Filter to only models that are available
        models_to_test = [m for m in OLLAMA_MODELS if m in available_ollama_models]
        missing_models = [m for m in OLLAMA_MODELS if m not in available_ollama_models]

        if missing_models:
            logger.warning(
                f"Skipping {len(missing_models)} models not available in Ollama: {missing_models}"
            )
            logger.info("Install missing models with: ollama pull <model_name>")

        if not models_to_test:
            pytest.skip(
                f"None of the configured models are available in Ollama. "
                f"Configured: {OLLAMA_MODELS}, Available: {available_ollama_models}"
            )

        logger.info(f"Testing {len(models_to_test)} available models: {models_to_test}")

        results = []

        for model in models_to_test:
            try:
                result = process_recipe(
                    input_text=instagram_caption,
                    vault_path=temp_vault,
                    llm_endpoint=ollama_endpoint,
                    llm_model=model,
                    recipes_dir="personal/recipes",
                    overwrite=False,
                    preview_only=True,
                    source_url=TEST_INSTAGRAM_URL,
                )

                # Evaluate accuracy
                accuracy_metrics = evaluate_recipe(result.recipe, reference_recipe)

                results.append(
                    {
                        "model": model,
                        "total_time": result.timing["total_time"],
                        "extraction_time": result.timing["extraction_time"],
                        "formatting_time": result.timing["formatting_time"],
                        "title": result.recipe.metadata.title,
                        "ingredients_count": len(result.recipe.ingredients),
                        "instructions_count": len(result.recipe.instructions),
                        "has_nutrition": result.recipe.metadata.calories_per_serving is not None,
                        "overall_accuracy": accuracy_metrics["overall_score"],
                        "title_similarity": accuracy_metrics["title_similarity"],
                        "ingredients_f1": accuracy_metrics["ingredients"]["f1"],
                        "instructions_f1": accuracy_metrics["instructions"]["f1"],
                    }
                )

                logger.info(
                    f"✓ {model}: {result.timing['total_time']:.2f}s | "
                    f"Accuracy: {accuracy_metrics['overall_score']:.2%} "
                    f"({result.recipe.metadata.title})"
                )

            except (ConnectionError, Exception) as e:
                logger.warning(f"✗ {model}: Failed - {e}")
                results.append(
                    {
                        "model": model,
                        "error": str(e),
                    }
                )

        # Print comparison table
        print("\n" + "=" * 100)
        print("PERFORMANCE & ACCURACY COMPARISON")
        print("=" * 100)
        print(
            f"{'Model':<15} {'Total (s)':<12} {'Accuracy':<12} {'Title':<12} "
            f"{'Ing F1':<10} {'Inst F1':<10} {'Status':<15}"
        )
        print("-" * 100)

        successful_results = [r for r in results if "error" not in r]
        if successful_results:
            # Sort by overall accuracy (descending), then by total time (ascending)
            successful_results.sort(key=lambda x: (-x["overall_accuracy"], x["total_time"]))

            for r in successful_results:
                print(
                    f"{r['model']:<15} {r['total_time']:<12.2f} "
                    f"{r['overall_accuracy']:<12.2%} {r['title_similarity']:<12.2%} "
                    f"{r['ingredients_f1']:<10.2%} {r['instructions_f1']:<10.2%} Success"
                )

            # Show failed models
            failed_results = [r for r in results if "error" in r]
            for r in failed_results:
                print(
                    f"{r['model']:<15} {'N/A':<12} {'N/A':<12} {'N/A':<12} {'N/A':<10} {'N/A':<10} Failed: {r['error']}"
                )

            print("=" * 100)
            print(
                f"\nMost Accurate: {successful_results[0]['model']} "
                f"({successful_results[0]['overall_accuracy']:.2%})"
            )
            print(
                f"Fastest: {min(successful_results, key=lambda x: x['total_time'])['model']} "
                f"({min(successful_results, key=lambda x: x['total_time'])['total_time']:.2f}s)"
            )
            print(
                f"Best Balance: {max(successful_results, key=lambda x: x['overall_accuracy'] / x['total_time'])['model']} "
                f"(Accuracy/Time ratio)"
            )

        else:
            print("No models succeeded. Check Ollama availability and model names.")

        # At least one model should succeed
        assert len(successful_results) > 0, "At least one model should succeed"
