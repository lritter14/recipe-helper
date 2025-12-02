"""Parser for Instagram recipe links."""

import logging
import re
from urllib.parse import urlparse, urlunparse

import instaloader

logger = logging.getLogger(__name__)


class InstagramParser:
    """Parse Instagram posts to extract recipe content."""

    # Regex patterns for Instagram URLs
    INSTAGRAM_URL_PATTERNS = [
        r"https?://(www\.)?instagram\.com/p/[A-Za-z0-9_-]+/?",
        r"https?://(www\.)?instagram\.com/reel/[A-Za-z0-9_-]+/?",
        r"https?://(www\.)?instagram\.com/tv/[A-Za-z0-9_-]+/?",
        r"https?://(www\.)?instagram\.com/p/[A-Za-z0-9_-]+/.*",
        r"https?://(www\.)?instagram\.com/reel/[A-Za-z0-9_-]+/.*",
        r"https?://(www\.)?instagram\.com/tv/[A-Za-z0-9_-]+/.*",
    ]

    def __init__(self) -> None:
        """Initialize the Instagram parser with instaloader."""
        # Create Instaloader instance without login (for public content)
        # Set quiet=True to suppress retry messages and warnings (like 403 rate limit messages)
        self.loader = instaloader.Instaloader(
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,  # Suppress retry messages and warnings
        )

        # Suppress instaloader's logger output (only show errors, not warnings/info)
        instaloader_logger = logging.getLogger("instaloader")
        instaloader_logger.setLevel(logging.ERROR)

    def is_instagram_url(self, url: str) -> bool:
        """Check if URL is an Instagram link.

        Args:
            url: URL to check

        Returns:
            True if Instagram URL, False otherwise
        """
        if not url or not isinstance(url, str):
            return False

        url = url.strip()
        if not url:
            return False

        # Check against all patterns
        return any(
            re.match(pattern, url, re.IGNORECASE)
            for pattern in self.INSTAGRAM_URL_PATTERNS
        )

    def clean_url(self, url: str) -> str:
        """Remove tracking parameters and fragments from Instagram URL.

        Args:
            url: Instagram URL with potential tracking parameters

        Returns:
            Cleaned URL without query parameters or fragments

        Example:
            Input:  https://www.instagram.com/reel/DRZh6N2EhdO/?igsh=NjZiM2M3MzIxNA==
            Output: https://www.instagram.com/reel/DRZh6N2EhdO
        """
        if not url or not isinstance(url, str):
            return url

        # Parse URL and remove query parameters and fragments
        parsed = urlparse(url.strip())
        # Reconstruct URL without query and fragment
        cleaned = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path.rstrip("/"),  # Remove trailing slash
                parsed.params,
                "",  # Remove query
                "",  # Remove fragment
            )
        )
        return cleaned

    def _extract_shortcode(self, url: str) -> str:
        """Extract shortcode from Instagram URL.

        Args:
            url: Instagram post URL

        Returns:
            Shortcode string

        Raises:
            ValueError: If URL format is invalid
        """
        # Parse URL and extract path
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # Extract shortcode from path (format: /p/SHORTCODE or /reel/SHORTCODE or /tv/SHORTCODE)
        parts = path.split("/")
        if len(parts) >= 2:
            # Get the shortcode (second part after /p/, /reel/, or /tv/)
            shortcode = parts[1]
            if shortcode:
                return shortcode

        raise ValueError(f"Could not extract shortcode from Instagram URL: {url}")

    def parse(self, url: str) -> str:
        """Extract recipe text from Instagram post.

        Args:
            url: Instagram post URL

        Returns:
            Extracted caption text

        Raises:
            ValueError: If URL is invalid or not an Instagram link
            ConnectionError: If unable to fetch Instagram content
        """
        if not self.is_instagram_url(url):
            raise ValueError(f"Invalid Instagram URL: {url}")

        # Clean URL to remove tracking parameters
        url = self.clean_url(url)
        logger.info(f"Extracting caption from Instagram URL: {url}")

        try:
            # Extract shortcode from URL
            shortcode = self._extract_shortcode(url)
            logger.debug(f"Extracted shortcode: {shortcode}")

            # Load post using instaloader
            # Note: instaloader may show 403 warnings during retries (rate limiting),
            # but will automatically retry and eventually succeed
            try:
                post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            except instaloader.exceptions.PostChangedException as e:
                logger.error(f"Post changed or not found: {e}")
                raise ConnectionError(
                    "Instagram post not found or has been changed. "
                    "Please verify the URL is correct and the post is public."
                ) from e
            except instaloader.exceptions.PrivateProfileNotFollowedException as e:
                logger.error(f"Private profile: {e}")
                raise ValueError(
                    "Cannot access Instagram post: The post is from a private account. "
                    "Only public posts can be accessed."
                ) from e
            except instaloader.exceptions.LoginRequiredException as e:
                logger.error(f"Login required: {e}")
                raise ConnectionError(
                    "Instagram requires login to access this content. "
                    "Please ensure the post is public."
                ) from e
            except instaloader.exceptions.ConnectionException as e:
                logger.error(f"Connection error: {e}")
                raise ConnectionError(
                    "Failed to connect to Instagram. "
                    "Please check your internet connection and try again."
                ) from e
            except Exception as e:
                logger.error(f"Unexpected error loading post: {e}")
                raise ConnectionError(
                    f"Failed to load Instagram post: {e}. "
                    f"Please verify the URL is correct and try again."
                ) from e

            # Extract caption
            caption = post.caption
            if not caption:
                logger.warning("No caption found in Instagram post")
                raise ValueError(
                    "Instagram post does not contain a caption. "
                    "Please ensure the post has text content."
                )

            # Ensure caption is a string type
            caption_str = str(caption) if caption else ""
            logger.info(
                f"Successfully extracted caption ({len(caption_str)} characters)"
            )
            return caption_str

        except ValueError:
            # Re-raise ValueError as-is
            raise
        except ConnectionError:
            # Re-raise ConnectionError as-is
            raise
        except Exception as e:
            logger.exception(f"Unexpected error parsing Instagram URL: {e}")
            raise ConnectionError(
                f"Failed to extract content from Instagram URL: {e}. "
                f"Please verify the URL is correct and try again."
            ) from e
