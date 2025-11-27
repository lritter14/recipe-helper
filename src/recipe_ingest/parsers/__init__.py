"""Input parsers for different recipe sources."""

from recipe_ingest.parsers.instagram import InstagramParser
from recipe_ingest.parsers.text import TextParser

__all__ = ["TextParser", "InstagramParser"]
