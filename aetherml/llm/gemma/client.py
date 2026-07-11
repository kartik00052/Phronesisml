"""Gemma LLM client — thin API wrapper with timeout and retry.

This is the only module that makes external HTTP/SDK calls to the
language model.  It contains no business logic beyond request
construction, timeout enforcement, retry on transient failures, and
response parsing.

Design:
- Adapter pattern: wraps the raw API call, making the LLM backend
  swappable (e.g., swap Gemma for another model by changing the
  client implementation).
- Resource-bounded: every call enforces ``timeout_seconds`` from config.
  If the call exceeds the timeout, an ``LLMTimeoutError`` is raised
  immediately — the pipeline never hangs on an LLM call.
- Retry with exponential backoff: transient failures (5xx, network
  errors) are retried up to ``max_retries`` times.
- Credentials via config/env: API key is read from ``LLMConfig.api_key``
  or the ``AETHERML_LLM_API_KEY`` environment variable.  Never hardcoded.

Security:
- The client does NOT interpret, evaluate, or execute any part of the
  prompt or response.  Prompts are constructed by ``llm/prompts/``;
  responses are parsed by ``llm/parser/``.  This module is a pure
  transport layer.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from aetherml.configs.settings import LLMConfig
from aetherml.exceptions import LLMAuthenticationError, LLMTimeoutError

logger = logging.getLogger(__name__)

# Environment variable for API key fallback.
_API_KEY_ENV_VAR = "AETHERML_LLM_API_KEY"


class GemmaClient:
    """Thin client for the Gemma LLM API.

    Args:
        config: LLM configuration with API key, model ID, timeout, etc.
    """

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._api_key = config.api_key or os.environ.get(_API_KEY_ENV_VAR)
        self._model_id = config.model_id
        self._timeout = config.timeout_seconds
        self._max_retries = config.max_retries

    async def close(self) -> None:
        """Release any resources held by the client.

        Currently a no-op since the HTTP backend is a placeholder.
        When a real httpx/aiohttp client is added, this method should
        call ``client.aclose()``.
        """
        # Placeholder for future httpx.AsyncClient cleanup.

    async def __aenter__(self) -> GemmaClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def generate(self, prompt: str, *, system_instruction: str | None = None) -> str:
        """Send a prompt to the LLM and return the response text.

        Args:
            prompt: The user prompt (already constructed with delimiters).
            system_instruction: Optional system-level instruction prepended
                to the prompt.

        Returns:
            The LLM response as a plain string.

        Raises:
            LLMTimeoutError: If the API call exceeds ``timeout_seconds``.
            LLMAuthenticationError: If no API key is configured.
            LLMError: On other API failures after retries exhausted.
        """
        if not self._api_key:
            raise LLMAuthenticationError(
                "No LLM API key configured. Set llm.api_key in config "
                f"or export {_API_KEY_ENV_VAR}."
            )

        full_prompt = (
            f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        )

        last_error: Exception | None = None
        for attempt in range(1 + self._max_retries):
            try:
                response = await self._call_api(full_prompt)
                return response
            except LLMTimeoutError:
                raise
            except LLMAuthenticationError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt < self._max_retries:
                    delay = 2**attempt
                    logger.warning(
                        "LLM call failed (attempt %d/%d): %s. Retrying in %ds.",
                        attempt + 1,
                        1 + self._max_retries,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "LLM call failed after %d attempts: %s",
                        1 + self._max_retries,
                        exc,
                    )

        from aetherml.exceptions import LLMError
        raise LLMError(f"LLM API call failed after {1 + self._max_retries} attempts: {last_error}")

    async def _call_api(self, prompt: str) -> str:
        """Make the actual API call with timeout enforcement.

        This method uses ``asyncio.wait_for`` to enforce the timeout.
        The actual HTTP call is a placeholder that can be replaced with
        a real SDK implementation.
        """
        try:
            return await asyncio.wait_for(
                self._do_request(prompt),
                timeout=self._timeout,
            )
        except TimeoutError as exc:
            raise LLMTimeoutError(
                f"LLM API call exceeded timeout of {self._timeout}s."
            ) from exc

    async def _do_request(self, prompt: str) -> str:
        """Execute the HTTP request to the LLM API.

        This is a placeholder implementation.  In production, this would
        call the Gemma API via the appropriate SDK or HTTP client.
        """
        # Placeholder: real implementation would use httpx/aiohttp
        # to call the Gemma API endpoint.
        raise NotImplementedError(
            "Gemma API backend not configured. "
            "Set up a real LLM backend in llm/gemma/client.py."
        )
