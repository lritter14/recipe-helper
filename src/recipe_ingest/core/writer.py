"""Write recipes to Obsidian vault."""

import contextlib
import logging
import os
import re
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class VaultWriter:
    """Write formatted recipes to Obsidian vault with atomic operations."""

    def __init__(self, vault_path: Path, recipes_dir: str = "personal/recipes") -> None:
        """Initialize the vault writer.

        Args:
            vault_path: Path to the Obsidian vault root
            recipes_dir: Relative path to recipes directory within vault

        Raises:
            ValueError: If vault path doesn't exist or is not accessible
        """
        self.vault_path = Path(vault_path)
        self.recipes_dir = self.vault_path / recipes_dir

        # Validate vault path
        if not self.vault_path.exists():
            raise ValueError(f"Vault path does not exist: {vault_path}")
        if not self.vault_path.is_dir():
            raise ValueError(f"Vault path is not a directory: {vault_path}")

        # Create recipes directory if it doesn't exist
        self.recipes_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Vault writer initialized: {self.recipes_dir}")

    def write(self, title: str, content: str, overwrite: bool = False) -> Path:
        """Write a recipe to the vault using atomic operations.

        Args:
            title: Recipe title (used for filename)
            content: Formatted markdown content
            overwrite: Whether to overwrite existing files

        Returns:
            Path to the written file

        Raises:
            FileExistsError: If file exists and overwrite is False
            IOError: If write operation fails
        """
        # Sanitize filename
        filename = self._sanitize_filename(title)
        file_path = self.recipes_dir / f"{filename}.md"

        # Check for duplicates
        if not overwrite and file_path.exists():
            logger.warning(f"Recipe already exists: {file_path}")
            raise FileExistsError(
                f"Recipe '{title}' already exists at {file_path}. Use overwrite=True to replace it."
            )

        logger.info(f"Writing recipe to: {file_path}")

        try:
            # Write to temporary file first (atomic operation)
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.recipes_dir, prefix=".tmp_", suffix=".md"
            )

            try:
                # Write content to temp file
                with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())

                # Atomically rename temp file to final destination
                os.replace(temp_path, file_path)
                logger.info(f"Successfully wrote recipe: {file_path}")

            except Exception:
                # Clean up temp file on failure
                with contextlib.suppress(Exception):
                    os.unlink(temp_path)
                raise

        except Exception as e:
            logger.error(f"Failed to write recipe: {e}")
            raise OSError(f"Failed to write recipe to {file_path}: {e}") from e

        return file_path

    def get_file_path(self, title: str) -> Path:
        """Get the file path for a recipe title.

        Args:
            title: Recipe title

        Returns:
            Path to the recipe file
        """
        filename = self._sanitize_filename(title)
        return self.recipes_dir / f"{filename}.md"

    def check_duplicate(self, title: str) -> bool:
        """Check if a recipe with the same title already exists.

        Args:
            title: Recipe title to check

        Returns:
            True if duplicate exists, False otherwise
        """
        file_path = self.get_file_path(title)
        exists = file_path.exists()

        if exists:
            logger.debug(f"Duplicate found: {file_path}")
        return exists

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize recipe title for use as filename.

        Args:
            title: Recipe title

        Returns:
            Sanitized filename (without extension)
        """
        # Remove or replace invalid filename characters
        # Keep alphanumeric, spaces, hyphens, and underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', "", title)

        # Replace multiple spaces with single space
        sanitized = re.sub(r"\s+", " ", sanitized)

        # Trim whitespace
        sanitized = sanitized.strip()

        # Limit length (filesystem limit is typically 255, be conservative)
        max_length = 200
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].strip()

        # Fallback if title becomes empty after sanitization
        if not sanitized:
            sanitized = "untitled_recipe"

        logger.debug(f"Sanitized '{title}' to '{sanitized}'")
        return sanitized
