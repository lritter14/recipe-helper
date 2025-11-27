"""Input parsers for different recipe sources."""

from recipe_ingest.parsers.text import TextParser

# Lazy import InstagramParser to avoid lzma dependency issues in test environments
try:
    from recipe_ingest.parsers.instagram import InstagramParser
except ImportError:
    # If instaloader/lzma is not available, create a stub
    InstagramParser = None  # type: ignore[assignment, misc]

__all__ = ["TextParser", "InstagramParser"]
