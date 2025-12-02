"""Command-line interface for recipe ingestion."""

import logging
import sys
from pathlib import Path

import click

from recipe_ingest.config import load_settings
from recipe_ingest.core import process_recipe

# Lazy import InstagramParser to avoid lzma dependency issues
try:
    from recipe_ingest.parsers.instagram import InstagramParser
except ImportError:
    InstagramParser = None  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the CLI.

    Args:
        verbose: Enable verbose (DEBUG) logging
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(level=log_level, format=log_format, stream=sys.stderr)

    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


@click.command()
@click.argument("input_text", required=False)
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True, path_type=Path),
    help="Read input from file instead of argument",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Obsidian vault path (default: from env RECIPE_INGEST_VAULT_PATH)",
)
@click.option(
    "--llm-endpoint",
    "-l",
    default=None,
    help="Ollama endpoint URL (default: from env RECIPE_INGEST_LLM_ENDPOINT)",
)
@click.option(
    "--llm-model",
    "-m",
    default=None,
    help="Ollama model name (default: from env RECIPE_INGEST_LLM_MODEL)",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing recipe files",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def main(
    input_text: str | None,
    file: Path | None,
    output_dir: Path | None,
    llm_endpoint: str | None,
    llm_model: str | None,
    overwrite: bool,
    verbose: bool,
) -> None:
    """Recipe ingestion CLI tool.

    Process recipes from text, files, or URLs and save to Obsidian vault.

    Examples:

        recipe-ingest "Ingredients: flour, sugar..."

        recipe-ingest --file recipe.txt

        recipe-ingest "https://instagram.com/p/..." (future)

        cat recipe.txt | recipe-ingest
    """
    # Setup logging
    setup_logging(verbose)

    logger.info("Starting recipe ingestion")

    try:
        # Get input text
        if file:
            logger.info(f"Reading from file: {file}")
            input_text = file.read_text(encoding="utf-8")
        elif not input_text:
            # Read from stdin if no input provided
            if sys.stdin.isatty():
                click.echo("Error: No input provided. Use --help for usage.", err=True)
                sys.exit(1)
            logger.info("Reading from stdin")
            input_text = sys.stdin.read()

        if not input_text or not input_text.strip():
            click.echo("Error: Input text is empty", err=True)
            sys.exit(1)

        logger.debug(f"Input text length: {len(input_text)} characters")

        # Check if input is an Instagram URL
        source_url: str | None = None
        # Instagram parser not available, skip Instagram URL detection
        instagram_parser = None if InstagramParser is None else InstagramParser()

        if instagram_parser and instagram_parser.is_instagram_url(input_text):
            logger.info("Detected Instagram URL, extracting caption...")
            click.echo("📸 Detected Instagram link, extracting caption...")
            try:
                # Clean URL to remove tracking parameters
                source_url = instagram_parser.clean_url(input_text.strip())
                input_text = instagram_parser.parse(source_url)
                logger.info(
                    f"Successfully extracted caption ({len(input_text)} characters)"
                )
                click.echo(f"✅ Extracted caption ({len(input_text)} characters)")
            except ValueError as e:
                logger.error(f"Instagram parsing error: {e}")
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)
            except ConnectionError as e:
                logger.error(f"Instagram connection error: {e}")
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)
            except Exception as e:
                logger.exception("Unexpected error extracting Instagram content")
                click.echo(f"Error: Failed to extract Instagram content: {e}", err=True)
                sys.exit(1)

        # Load configuration
        settings = load_settings()

        # Determine vault path (CLI arg > env var > error)
        vault_path = output_dir or (settings.vault.path if settings.vault else None)
        if not vault_path:
            click.echo(
                "Error: No vault path specified. Use --output-dir or set "
                "RECIPE_INGEST_VAULT_PATH environment variable",
                err=True,
            )
            sys.exit(1)

        vault_path = Path(vault_path)
        logger.info(f"Using vault path: {vault_path}")

        # Determine LLM settings (CLI args > env vars > defaults)
        llm_endpoint_final = llm_endpoint or settings.llm.endpoint
        llm_model_final = llm_model or settings.llm.model

        logger.info(f"Using LLM endpoint: {llm_endpoint_final}")
        logger.info(f"Using LLM model: {llm_model_final}")

        # Determine recipes directory (from env var or default)
        recipes_dir = (
            settings.vault.recipes_dir if settings.vault else "personal/recipes"
        )
        logger.info(f"Using recipes directory: {recipes_dir}")

        # Process recipe using shared service
        click.echo("🔧 Initializing components...")
        click.echo("🤖 Extracting recipe with LLM...")

        result = process_recipe(
            input_text=input_text,
            vault_path=vault_path,
            llm_endpoint=llm_endpoint_final,
            llm_model=llm_model_final,
            recipes_dir=recipes_dir,
            overwrite=overwrite,
            preview_only=False,
            source_url=source_url,
        )

        # Display results
        click.echo(f"✅ Extracted: {result.recipe.metadata.title}")
        click.echo(f"   Ingredients: {len(result.recipe.ingredients)}")
        click.echo(f"   Instructions: {len(result.recipe.instructions)} steps")
        if result.recipe.metadata.servings:
            click.echo(f"   Servings: {result.recipe.metadata.servings}")
        if result.recipe.metadata.calories_per_serving:
            click.echo(
                f"   Calories: {result.recipe.metadata.calories_per_serving:.0f} per serving"
            )

        if result.file_path:
            click.echo(f"\n✅ Recipe saved: {result.file_path}")
        click.echo(f"⏱️  Total time: {result.timing['total_time']:.2f}s")

        # Show breakdown if verbose
        if verbose:
            click.echo("\nTiming breakdown:")
            click.echo(f"  Extraction: {result.timing['extraction_time']:.2f}s")
            click.echo(f"  Formatting: {result.timing['formatting_time']:.2f}s")
            click.echo(f"  Writing: {result.timing['writing_time']:.2f}s")

    except FileExistsError as e:
        logger.error(f"Duplicate recipe: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during recipe ingestion")
        click.echo(f"Error: An unexpected error occurred: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
