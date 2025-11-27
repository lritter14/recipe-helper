"""Ollama LLM client wrapper."""

import json
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama local LLM."""

    def __init__(
        self, base_url: str = "http://localhost:11434", model: str = "llama3.1:8b"
    ) -> None:
        """Initialize the Ollama client.

        Args:
            base_url: Ollama API base URL
            model: Model name to use
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._timeout = 120

    def generate(
        self, prompt: str, schema: dict[str, Any] | None = None, format_json: bool = True
    ) -> dict[str, Any]:
        """Generate structured output from a prompt.

        Args:
            prompt: Input prompt text
            schema: Optional JSON schema for structured output
            format_json: Whether to request JSON format output

        Returns:
            Parsed response as dictionary

        Raises:
            ConnectionError: If unable to connect to Ollama
            ValueError: If response parsing fails
        """
        url = f"{self.base_url}/api/generate"

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        # Request JSON format if specified
        if format_json:
            payload["format"] = "json"

        # Add schema to prompt if provided
        # Use compact JSON (no indentation) to reduce tokens
        if schema:
            schema_str = json.dumps(schema, separators=(",", ":"))
            payload["prompt"] = f"{prompt}\n\nSchema: {schema_str}"

        # Log what we're sending
        logger.info(
            f"Sending request to Ollama model '{self.model}' "
            f"(prompt length: {len(payload['prompt'])} chars, format_json: {format_json})"
        )
        # Show full prompt in DEBUG, preview in INFO
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Full prompt:\n{payload['prompt']}")
        else:
            prompt_preview = (
                payload["prompt"][:500] + "..."
                if len(payload["prompt"]) > 500
                else payload["prompt"]
            )
            logger.debug(f"Prompt preview: {prompt_preview}")

        try:
            response = requests.post(url, json=payload, timeout=self._timeout)
            response.raise_for_status()

            result = response.json()
            response_text = result.get("response", "")

            if not response_text:
                logger.error("Empty response from Ollama")
                raise ValueError("Empty response from Ollama")

            # Log raw response
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"Raw response from Ollama (length: {len(response_text)}):\n{response_text}"
                )
            else:
                response_preview = (
                    response_text[:500] + "..." if len(response_text) > 500 else response_text
                )
                logger.debug(f"Raw response preview: {response_preview}")

            # Parse JSON response
            if format_json:
                try:
                    parsed: dict[str, Any] = json.loads(response_text)
                    logger.info(f"Successfully parsed JSON response. Keys: {list(parsed.keys())}")
                    logger.debug(f"Parsed response: {json.dumps(parsed, indent=2)[:1000]}")
                    return parsed
                except json.JSONDecodeError as e:
                    logger.error(
                        f"Failed to parse JSON response. "
                        f"Error: {e}. "
                        f"Response text (first 1000 chars): {response_text[:1000]}"
                    )
                    raise ValueError(f"Invalid JSON response from LLM: {e}") from e
            else:
                return {"response": response_text}

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to Ollama at {self.base_url}")
            raise ConnectionError(
                f"Failed to connect to Ollama at {self.base_url}. "
                f"Ensure Ollama is running (try: ollama serve)"
            ) from e
        except requests.exceptions.Timeout as e:
            logger.error(f"Ollama request timed out after {self._timeout}s")
            raise ConnectionError(f"Ollama request timed out after {self._timeout}s") from e
        except requests.exceptions.HTTPError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise ConnectionError(f"Ollama HTTP error: {e}") from e

    def health_check(self, retries: int = 3, delay: float = 2.0) -> bool:
        """Check if Ollama service is available.

        Args:
            retries: Number of retry attempts
            delay: Delay between retries in seconds

        Returns:
            True if service is healthy, False otherwise
        """
        for attempt in range(retries):
            try:
                url = f"{self.base_url}/api/tags"
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                return True
            except Exception as e:
                if attempt < retries - 1:
                    logger.debug(
                        f"Ollama health check attempt {attempt + 1}/{retries} failed: {e}, retrying in {delay}s..."
                    )
                    import time

                    time.sleep(delay)
                else:
                    logger.warning(f"Ollama health check failed after {retries} attempts: {e}")
        return False

    def list_models(self) -> list[str]:
        """List available models.

        Returns:
            List of model names

        Raises:
            ConnectionError: If unable to connect to Ollama
        """
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise ConnectionError(f"Failed to list Ollama models: {e}") from e
