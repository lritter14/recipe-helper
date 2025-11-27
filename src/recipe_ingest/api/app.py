"""FastAPI application factory."""

import contextlib
import logging
import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from recipe_ingest.api.routes import root_router, router

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging for the API application."""
    log_level = os.getenv("RECIPE_INGEST_LOG_LEVEL", "INFO").upper()
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format,
        stream=sys.stdout,
        force=True,  # Override any existing configuration
    )
    
    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

# Configure templates
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifespan events.

    Args:
        _app: FastAPI application instance (required by lifespan signature)

    Yields:
        None: Control is yielded to the application
    """
    # Startup
    logger.info("Starting Recipe Ingestion API")
    # TODO: Initialize LLM client, validate configuration
    yield
    # Shutdown
    logger.info("Shutting down Recipe Ingestion API")
    # TODO: Cleanup resources if needed


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    # Configure logging before creating the app
    setup_logging()
    
    app = FastAPI(
        title="Recipe Ingestion API",
        description="Automated recipe extraction and formatting service",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure based on environment
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(root_router)
    app.include_router(router)

    return app
