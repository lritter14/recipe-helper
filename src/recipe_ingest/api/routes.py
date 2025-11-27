"""API routes for recipe ingestion."""

import logging
import time
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from recipe_ingest.config import load_settings
from recipe_ingest.core import process_recipe
from recipe_ingest.llm import OllamaClient
from recipe_ingest.parsers.instagram import InstagramParser

logger = logging.getLogger(__name__)

# Configure templates
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/api/v1", tags=["recipes"])
root_router = APIRouter()


class RecipeRequest(BaseModel):
    """Request model for recipe ingestion."""

    input: str = Field(..., description="Recipe text or URL", min_length=1)
    format: Literal["text", "instagram"] = Field(default="text", description="Input format type")
    preview: bool = Field(default=False, description="Preview only, don't save recipe")
    overwrite: bool = Field(
        default=False, description="Overwrite existing recipe if ingredients match"
    )


class RecipeResponse(BaseModel):
    """Response model for recipe ingestion."""

    status: Literal["success", "error"] = Field(..., description="Processing status")
    recipe_path: str | None = Field(None, description="Path to saved recipe file")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    preview: str | None = Field(None, description="Formatted markdown preview")
    error: str | None = Field(None, description="Error message if status is error")
    is_duplicate: bool = Field(
        default=False, description="Whether a recipe with this title already exists"
    )
    duplicate_ingredients_match: bool = Field(
        default=False,
        description="Whether the duplicate recipe has matching ingredients (allows overwrite)",
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "unhealthy"] = Field(..., description="Service health status")
    ollama_connected: bool = Field(..., description="Ollama connectivity status")
    vault_accessible: bool = Field(..., description="Vault path accessibility")


@router.post("/recipes", response_model=RecipeResponse)
async def ingest_recipe(request: RecipeRequest) -> RecipeResponse:
    """Ingest a recipe from text or URL.

    Args:
        request: Recipe ingestion request

    Returns:
        Processing result with recipe path or error

    Raises:
        HTTPException: If processing fails
    """
    start_time = time.time()

    # Log request body
    logger.info(f"Received recipe request: {request.model_dump_json()}")

    try:
        # Load configuration
        settings = load_settings()

        # Validate vault path
        vault_path = settings.vault.path if settings.vault else None
        if not vault_path:
            logger.error("Vault path not configured")
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable. Vault path not configured.",
            )

        vault_path = Path(vault_path)
        if not vault_path.exists() or not vault_path.is_dir():
            logger.error(f"Vault path does not exist or is not a directory: {vault_path}")
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable. Vault path is not accessible.",
            )

        # Get LLM settings
        llm_endpoint = settings.llm.endpoint
        llm_model = settings.llm.model
        recipes_dir = settings.vault.recipes_dir if settings.vault else "personal/recipes"

        logger.info(
            f"Processing recipe request: preview={request.preview}, "
            f"overwrite={request.overwrite}, format={request.format}"
        )

        # Check if input is an Instagram URL
        instagram_parser = InstagramParser()
        source_url: str | None = None
        input_text = request.input

        # Auto-detect Instagram URLs if format is "text" or explicitly handle "instagram" format
        if request.format == "instagram" or (
            request.format == "text" and instagram_parser.is_instagram_url(request.input)
        ):
            logger.info("Detected Instagram URL, extracting caption...")
            try:
                # Clean URL to remove tracking parameters
                source_url = instagram_parser.clean_url(request.input.strip())
                input_text = instagram_parser.parse(source_url)
                logger.info(f"Successfully extracted caption ({len(input_text)} characters)")
            except ValueError as e:
                logger.error(f"Instagram parsing error: {e}")
                raise HTTPException(
                    status_code=422,
                    detail=f"Failed to extract Instagram content: {e}",
                ) from None
            except ConnectionError as e:
                logger.error(f"Instagram connection error: {e}")
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to connect to Instagram: {e}",
                ) from None
            except Exception as e:
                logger.exception("Unexpected error extracting Instagram content")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to extract Instagram content: {e}",
                ) from None

        # Process recipe using shared service
        result = process_recipe(
            input_text=input_text,
            vault_path=vault_path,
            llm_endpoint=llm_endpoint,
            llm_model=llm_model,
            recipes_dir=recipes_dir,
            overwrite=request.overwrite,
            preview_only=request.preview,
            source_url=source_url,
        )

        processing_time_ms = result.timing["total_time"] * 1000

        return RecipeResponse(
            status="success",
            recipe_path=str(result.file_path) if result.file_path else None,
            processing_time_ms=processing_time_ms,
            preview=result.markdown,
            error=None,
            is_duplicate=result.is_duplicate,
            duplicate_ingredients_match=result.duplicate_ingredients_match,
        )

    except FileExistsError as e:
        # Duplicate recipe error
        logger.error(f"Duplicate recipe error: {e}", exc_info=True)
        processing_time_ms = (time.time() - start_time) * 1000
        raise HTTPException(
            status_code=409,
            detail="Recipe already exists. Use overwrite=true to replace it (only if ingredients match exactly).",
        ) from None

    except ValueError as e:
        # Validation error
        logger.error(f"Validation error: {e}", exc_info=True)
        processing_time_ms = (time.time() - start_time) * 1000
        raise HTTPException(
            status_code=422,
            detail="Invalid recipe input provided. Please check your input and try again.",
        ) from None

    except ConnectionError as e:
        # LLM connection error
        logger.error(f"Connection error: {e}", exc_info=True)
        processing_time_ms = (time.time() - start_time) * 1000
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again later.",
        ) from None

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error during recipe ingestion: {e}")
        processing_time_ms = (time.time() - start_time) * 1000
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later.",
        ) from None


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check service health and dependencies.

    Returns:
        Health status of service and dependencies
    """
    # Load configuration
    settings = load_settings()

    # Check Ollama connectivity
    ollama_connected = False
    try:
        llm_endpoint = settings.llm.endpoint
        llm_model = settings.llm.model
        llm_client = OllamaClient(base_url=llm_endpoint, model=llm_model)
        ollama_connected = llm_client.health_check()
        logger.debug(f"Ollama health check: {ollama_connected}")
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        ollama_connected = False

    # Check vault accessibility
    vault_accessible = False
    try:
        vault_path = settings.vault.path if settings.vault else None
        if vault_path:
            vault_path = Path(vault_path)
            vault_accessible = vault_path.exists() and vault_path.is_dir()
            # Check if we can write (test by checking if directory is writable)
            if vault_accessible:
                try:
                    # Try to create a test file to verify write access
                    test_file = vault_path / ".health_check"
                    test_file.touch()
                    test_file.unlink()
                except Exception:
                    vault_accessible = False
        logger.debug(f"Vault accessibility check: {vault_accessible}")
    except Exception as e:
        logger.warning(f"Vault accessibility check failed: {e}")
        vault_accessible = False

    # Determine overall status
    status: Literal["healthy", "unhealthy"] = (
        "healthy" if (ollama_connected and vault_accessible) else "unhealthy"
    )

    return HealthResponse(
        status=status,
        ollama_connected=ollama_connected,
        vault_accessible=vault_accessible,
    )


@root_router.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    """Serve the web UI homepage.

    Args:
        request: FastAPI request object

    Returns:
        HTML response with recipe ingestion form
    """
    return templates.TemplateResponse(request, "index.html")
