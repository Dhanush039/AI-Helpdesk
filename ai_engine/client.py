"""
ai_engine.client
================

Thin, provider-agnostic wrapper around the OpenAI Chat Completions API.

Design goals
------------
* The rest of the application never touches the OpenAI SDK directly.
  It only calls functions in this module, so the underlying provider
  could be swapped out later without touching Django views/models.
* The API key is NEVER hardcoded. It is read from the environment
  (via Django settings, which itself loads a local .env file).
* Every possible failure mode (missing key, invalid key, timeout,
  rate limit, network failure, malformed response) is caught and
  turned into a predictable AIServiceError so calling code can show
  a friendly message instead of crashing.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger("ai_engine")


class AIServiceError(Exception):
    """Raised for any AI-related failure that the UI should handle gracefully."""


class AINotConfiguredError(AIServiceError):
    """Raised when no OPENAI_API_KEY is configured."""


@dataclass
class AIResponse:
    """Normalized result returned to callers."""
    ok: bool
    text: str = ""
    data: dict | None = None
    error: str | None = None


def is_configured() -> bool:
    """Return True if an OpenAI API key has been supplied via environment."""
    return bool(getattr(settings, "OPENAI_API_KEY", ""))


def _get_client():
    """Lazily build an OpenAI client using the key from settings/env."""
    if not is_configured():
        raise AINotConfiguredError(
            "AI service is not configured. Please configure OPENAI_API_KEY."
        )
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency always installed
        raise AIServiceError("The 'openai' package is not installed.") from exc

    return OpenAI(api_key=settings.OPENAI_API_KEY)


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    *,
    json_mode: bool = False,
    temperature: float = 0.2,
    timeout: float = 30.0,
) -> AIResponse:
    """
    Call the chat completion endpoint and return a normalized AIResponse.

    This function never raises for "expected" failure modes (missing key,
    timeout, rate limiting, bad response, etc). Instead it returns an
    AIResponse with ok=False and a human-readable error message.
    """
    try:
        client = _get_client()
    except AINotConfiguredError as exc:
        return AIResponse(ok=False, error=str(exc))
    except AIServiceError as exc:
        logger.error("AI client init failed: %s", exc)
        return AIResponse(ok=False, error="AI service is currently unavailable.")

    try:
        # Import errors lazily so the module still loads if the SDK's
        # internal error module ever moves.
        from openai import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            RateLimitError,
            APIStatusError,
        )
    except ImportError:  # pragma: no cover
        APIConnectionError = APITimeoutError = AuthenticationError = RateLimitError = APIStatusError = Exception

    try:
        kwargs = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        completion = client.chat.completions.create(
            model=getattr(settings, "AI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            timeout=timeout,
            **kwargs,
        )
        content = completion.choices[0].message.content or ""

        if json_mode:
            try:
                data = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                logger.warning("AI returned invalid JSON, falling back to raw text.")
                return AIResponse(
                    ok=False,
                    error="The AI returned an unexpected response. Please try again.",
                )
            return AIResponse(ok=True, text=content, data=data)

        return AIResponse(ok=True, text=content)

    except AuthenticationError:
        logger.error("OpenAI authentication failed - invalid API key.")
        return AIResponse(ok=False, error="AI service rejected the configured API key.")
    except RateLimitError:
        logger.warning("OpenAI rate limit hit.")
        return AIResponse(ok=False, error="AI service is busy right now (rate limited). Please try again shortly.")
    except APITimeoutError:
        logger.warning("OpenAI request timed out.")
        return AIResponse(ok=False, error="AI service timed out. Please try again.")
    except APIConnectionError:
        logger.warning("OpenAI connection failure.")
        return AIResponse(ok=False, error="Could not reach the AI service. Check your network connection.")
    except APIStatusError as exc:
        logger.error("OpenAI API status error: %s", exc)
        return AIResponse(ok=False, error="AI service is currently unavailable.")
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        logger.exception("Unexpected AI error: %s", exc)
        return AIResponse(ok=False, error="An unexpected error occurred while contacting the AI service.")
