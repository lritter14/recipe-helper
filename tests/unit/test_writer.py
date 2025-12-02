"""Unit tests for vault writer."""

from pathlib import Path

import pytest

from recipe_ingest.core.writer import VaultWriter


class TestVaultWriter:
    """Tests for VaultWriter class."""

    def test_init_with_nonexistent_vault_raises_error(self, tmp_path: Path) -> None:
        """Test that initializing with nonexistent vault raises ValueError."""
        fake_path = tmp_path / "nonexistent"
        with pytest.raises(ValueError, match="Vault path does not exist"):
            VaultWriter(fake_path)

    def test_init_with_file_instead_of_directory_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Test that initializing with a file raises ValueError."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        with pytest.raises(ValueError, match="not a directory"):
            VaultWriter(file_path)

    def test_init_creates_recipes_directory(self, temp_vault: Path) -> None:
        """Test that writer creates recipes directory if it doesn't exist."""
        # Remove recipes dir if it exists
        recipes_dir = temp_vault / "personal" / "recipes"
        if recipes_dir.exists():
            recipes_dir.rmdir()

        writer = VaultWriter(temp_vault, "personal/recipes")
        assert writer.recipes_dir.exists()
        assert writer.recipes_dir.is_dir()

    def test_init_with_custom_recipes_dir(self, temp_vault: Path) -> None:
        """Test that writer uses custom recipes directory."""
        custom_dir = "custom/recipes/path"
        writer = VaultWriter(temp_vault, custom_dir)
        assert writer.recipes_dir == temp_vault / custom_dir
        assert writer.recipes_dir.exists()

    def test_write_creates_new_file(self, temp_vault: Path) -> None:
        """Test writing a new recipe file."""
        writer = VaultWriter(temp_vault)
        content = "# Test Recipe\n\nSome content"

        file_path = writer.write("Test Recipe", content)

        assert file_path.exists()
        assert file_path.is_file()
        assert file_path.read_text() == content
        assert file_path.name == "Test Recipe.md"

    def test_write_sanitizes_filename(self, temp_vault: Path) -> None:
        """Test that filenames are properly sanitized."""
        writer = VaultWriter(temp_vault)
        content = "test content"

        # Test various problematic characters
        file_path = writer.write('Test: Recipe / With * "Invalid" Chars', content)

        # Should have removed invalid characters
        assert file_path.exists()
        assert "/" not in file_path.name
        assert "*" not in file_path.name
        assert '"' not in file_path.name
        assert ":" not in file_path.name

    def test_write_without_overwrite_raises_on_duplicate(
        self, temp_vault: Path
    ) -> None:
        """Test that writing duplicate without overwrite raises error."""
        writer = VaultWriter(temp_vault)
        content = "test content"

        # Write first time
        writer.write("Duplicate Test", content)

        # Second write should fail
        with pytest.raises(FileExistsError, match="already exists"):
            writer.write("Duplicate Test", content, overwrite=False)

    def test_write_with_overwrite_replaces_file(self, temp_vault: Path) -> None:
        """Test that overwrite flag allows replacing existing files."""
        writer = VaultWriter(temp_vault)

        # Write first version
        file_path = writer.write("Overwrite Test", "original content")
        assert file_path.read_text() == "original content"

        # Overwrite with new content
        file_path = writer.write("Overwrite Test", "new content", overwrite=True)
        assert file_path.read_text() == "new content"

    def test_check_duplicate_returns_true_for_existing(self, temp_vault: Path) -> None:
        """Test that check_duplicate detects existing recipes."""
        writer = VaultWriter(temp_vault)

        # No duplicate initially
        assert not writer.check_duplicate("New Recipe")

        # Write recipe
        writer.write("New Recipe", "content")

        # Now should be duplicate
        assert writer.check_duplicate("New Recipe")

    def test_sanitize_filename_handles_long_names(self, temp_vault: Path) -> None:
        """Test that very long filenames are truncated."""
        writer = VaultWriter(temp_vault)
        long_title = "A" * 300  # Longer than max length

        sanitized = writer._sanitize_filename(long_title)

        assert len(sanitized) <= 200
        assert sanitized.startswith("A")

    def test_sanitize_filename_handles_empty_result(self, temp_vault: Path) -> None:
        """Test that empty titles get a fallback name."""
        writer = VaultWriter(temp_vault)

        sanitized = writer._sanitize_filename("***")
        assert sanitized == "untitled_recipe"

        sanitized = writer._sanitize_filename("")
        assert sanitized == "untitled_recipe"
