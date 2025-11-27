"""Unit tests for Instagram parser."""

import pytest
from pytest_mock import MockerFixture

from recipe_ingest.parsers.instagram import InstagramParser


class TestInstagramParser:
    """Tests for InstagramParser class."""

    def test_is_instagram_url_with_post_url(self) -> None:
        """Test URL detection for standard post URLs."""
        parser = InstagramParser()
        assert parser.is_instagram_url("https://www.instagram.com/p/ABC123/")
        assert parser.is_instagram_url("https://instagram.com/p/ABC123/")
        assert parser.is_instagram_url("http://www.instagram.com/p/ABC123/")
        assert parser.is_instagram_url("https://www.instagram.com/p/ABC123/?utm_source=test")

    def test_is_instagram_url_with_reel_url(self) -> None:
        """Test URL detection for reel URLs."""
        parser = InstagramParser()
        assert parser.is_instagram_url("https://www.instagram.com/reel/ABC123/")
        assert parser.is_instagram_url("https://instagram.com/reel/ABC123/")
        assert parser.is_instagram_url("https://www.instagram.com/reel/ABC123/?utm_source=test")

    def test_is_instagram_url_with_tv_url(self) -> None:
        """Test URL detection for IGTV URLs."""
        parser = InstagramParser()
        assert parser.is_instagram_url("https://www.instagram.com/tv/ABC123/")
        assert parser.is_instagram_url("https://instagram.com/tv/ABC123/")
        assert parser.is_instagram_url("https://www.instagram.com/tv/ABC123/?utm_source=test")

    def test_is_instagram_url_with_invalid_urls(self) -> None:
        """Test URL detection rejects non-Instagram URLs."""
        parser = InstagramParser()
        assert not parser.is_instagram_url("https://www.example.com/p/ABC123/")
        assert not parser.is_instagram_url("not a url")
        assert not parser.is_instagram_url("")
        assert not parser.is_instagram_url("https://www.facebook.com/p/ABC123/")

    def test_extract_shortcode_from_post_url(self) -> None:
        """Test shortcode extraction from post URL."""
        parser = InstagramParser()
        assert parser._extract_shortcode("https://www.instagram.com/p/ABC123/") == "ABC123"
        assert parser._extract_shortcode("https://instagram.com/p/XYZ789/") == "XYZ789"
        assert (
            parser._extract_shortcode("https://www.instagram.com/p/ABC123/?utm_source=test")
            == "ABC123"
        )

    def test_extract_shortcode_from_reel_url(self) -> None:
        """Test shortcode extraction from reel URL."""
        parser = InstagramParser()
        assert parser._extract_shortcode("https://www.instagram.com/reel/ABC123/") == "ABC123"
        assert parser._extract_shortcode("https://instagram.com/reel/XYZ789/") == "XYZ789"

    def test_extract_shortcode_from_tv_url(self) -> None:
        """Test shortcode extraction from IGTV URL."""
        parser = InstagramParser()
        assert parser._extract_shortcode("https://www.instagram.com/tv/ABC123/") == "ABC123"
        assert parser._extract_shortcode("https://instagram.com/tv/XYZ789/") == "XYZ789"

    def test_extract_shortcode_with_invalid_url_raises_error(self) -> None:
        """Test that invalid URL format raises ValueError."""
        parser = InstagramParser()
        with pytest.raises(ValueError, match="Could not extract shortcode"):
            parser._extract_shortcode("https://www.instagram.com/invalid/")

    def test_parse_with_valid_url_returns_caption(self, mocker: MockerFixture) -> None:
        """Test successful caption extraction from Instagram URL."""
        parser = InstagramParser()

        # Mock instaloader Post
        mock_post = mocker.Mock()
        mock_post.caption = (
            "Delicious chocolate cake recipe! Ingredients: 2 cups flour, 1 cup sugar..."
        )

        # Mock Post.from_shortcode
        mocker.patch("instaloader.Post.from_shortcode", return_value=mock_post)

        url = "https://www.instagram.com/p/ABC123/"
        result = parser.parse(url)

        assert (
            result == "Delicious chocolate cake recipe! Ingredients: 2 cups flour, 1 cup sugar..."
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_parse_with_invalid_url_raises_error(self) -> None:
        """Test that invalid URL raises ValueError."""
        parser = InstagramParser()
        with pytest.raises(ValueError, match="Invalid Instagram URL"):
            parser.parse("https://www.example.com/p/ABC123/")

    def test_parse_with_no_caption_raises_error(self, mocker: MockerFixture) -> None:
        """Test that post without caption raises ValueError."""
        parser = InstagramParser()

        # Mock instaloader Post with no caption
        mock_post = mocker.Mock()
        mock_post.caption = None

        # Mock Post.from_shortcode
        mocker.patch("instaloader.Post.from_shortcode", return_value=mock_post)

        url = "https://www.instagram.com/p/ABC123/"
        with pytest.raises(ValueError, match="does not contain a caption"):
            parser.parse(url)

    def test_parse_with_empty_caption_raises_error(self, mocker: MockerFixture) -> None:
        """Test that post with empty caption raises ValueError."""
        parser = InstagramParser()

        # Mock instaloader Post with empty caption
        mock_post = mocker.Mock()
        mock_post.caption = ""

        # Mock Post.from_shortcode
        mocker.patch("instaloader.Post.from_shortcode", return_value=mock_post)

        url = "https://www.instagram.com/p/ABC123/"
        with pytest.raises(ValueError, match="does not contain a caption"):
            parser.parse(url)

    def test_parse_with_post_not_found_raises_connection_error(self, mocker: MockerFixture) -> None:
        """Test that post not found raises ConnectionError."""
        parser = InstagramParser()

        # Mock Post.from_shortcode to raise PostChangedException
        import instaloader.exceptions

        mocker.patch(
            "instaloader.Post.from_shortcode",
            side_effect=instaloader.exceptions.PostChangedException("Post not found"),
        )

        url = "https://www.instagram.com/p/ABC123/"
        with pytest.raises(ConnectionError, match="not found or has been changed"):
            parser.parse(url)

    def test_parse_with_private_profile_raises_value_error(self, mocker: MockerFixture) -> None:
        """Test that private profile raises ValueError."""
        parser = InstagramParser()

        # Mock Post.from_shortcode to raise PrivateProfileNotFollowedException
        import instaloader.exceptions

        mocker.patch(
            "instaloader.Post.from_shortcode",
            side_effect=instaloader.exceptions.PrivateProfileNotFollowedException(
                "Private profile"
            ),
        )

        url = "https://www.instagram.com/p/ABC123/"
        with pytest.raises(ValueError, match="private account"):
            parser.parse(url)

    def test_parse_with_connection_error_raises_connection_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test that connection errors raise ConnectionError."""
        parser = InstagramParser()

        # Mock Post.from_shortcode to raise ConnectionException
        import instaloader.exceptions

        mocker.patch(
            "instaloader.Post.from_shortcode",
            side_effect=instaloader.exceptions.ConnectionException("Connection failed"),
        )

        url = "https://www.instagram.com/p/ABC123/"
        with pytest.raises(ConnectionError, match="Failed to connect to Instagram"):
            parser.parse(url)

    def test_parse_with_login_required_raises_connection_error(self, mocker: MockerFixture) -> None:
        """Test that login required raises ConnectionError."""
        parser = InstagramParser()

        # Mock Post.from_shortcode to raise LoginRequiredException
        import instaloader.exceptions

        mocker.patch(
            "instaloader.Post.from_shortcode",
            side_effect=instaloader.exceptions.LoginRequiredException("Login required"),
        )

        url = "https://www.instagram.com/p/ABC123/"
        with pytest.raises(ConnectionError, match="requires login"):
            parser.parse(url)

    def test_parse_with_unexpected_error_raises_connection_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test that unexpected errors raise ConnectionError."""
        parser = InstagramParser()

        # Mock Post.from_shortcode to raise generic exception
        mocker.patch("instaloader.Post.from_shortcode", side_effect=Exception("Unexpected error"))

        url = "https://www.instagram.com/p/ABC123/"
        with pytest.raises(ConnectionError, match="Failed to load Instagram post"):
            parser.parse(url)
