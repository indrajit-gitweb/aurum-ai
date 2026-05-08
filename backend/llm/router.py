"""
Multi-provider LLM router for AURUM AI.

Priority order (left to right):
  1. User-supplied key (whichever provider they chose)
  2. Groq  (env GROQ_API_KEY)
  3. Gemini (env GEMINI_API_KEY)
  4. OpenRouter (env OPENROUTER_API_KEY)

Any provider whose key is absent/empty is silently skipped.
On RateLimitError the router tries the next provider automatically.
"""

import logging
import os
from typing import Callable, Optional

from llm.providers.groq_client import GroqClient
from llm.providers.groq_client import RateLimitError as GroqRateLimitError
from llm.providers.gemini_client import GeminiClient
from llm.providers.gemini_client import RateLimitError as GeminiRateLimitError
from llm.providers.openrouter_client import OpenRouterClient
from llm.providers.openrouter_client import RateLimitError as OpenRouterRateLimitError

logger = logging.getLogger(__name__)

# Unified alias used by callers
RateLimitError = (GroqRateLimitError, GeminiRateLimitError, OpenRouterRateLimitError)


class AllProvidersExhaustedError(Exception):
    """Raised when every configured LLM provider has failed or rate-limited."""
    pass


class LLMRouter:
    """Routes LLM calls across Groq → Gemini → OpenRouter with auto-fallback.

    Args:
        user_key: Optional API key supplied by the end user.
        user_provider: Which provider the user key belongs to
            (``"groq"``, ``"gemini"``, or ``"openrouter"``).
    """

    def __init__(
        self,
        user_key: Optional[str] = None,
        user_provider: str = "groq",
    ) -> None:
        self._providers: list[tuple[str, object]] = []

        # ── User-supplied key goes first ──────────────────────────────────────
        if user_key and user_key.strip():
            provider = user_provider.lower().strip()
            try:
                if provider == "groq":
                    self._providers.append(("groq_user", GroqClient(user_key)))
                elif provider == "gemini":
                    self._providers.append(("gemini_user", GeminiClient(user_key)))
                elif provider == "openrouter":
                    self._providers.append(("openrouter_user", OpenRouterClient(user_key)))
                else:
                    logger.warning("Unknown user provider '%s' — ignoring user key.", provider)
            except Exception as exc:
                logger.warning("Failed to initialise user-supplied %s client: %s", provider, exc)

        # ── Shared pool keys from environment ─────────────────────────────────
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        if groq_key:
            try:
                self._providers.append(("groq", GroqClient(groq_key)))
            except Exception as exc:
                logger.warning("Failed to initialise Groq client: %s", exc)

        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        if gemini_key:
            try:
                self._providers.append(("gemini", GeminiClient(gemini_key)))
            except Exception as exc:
                logger.warning("Failed to initialise Gemini client: %s", exc)

        openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if openrouter_key:
            try:
                self._providers.append(("openrouter", OpenRouterClient(openrouter_key)))
            except Exception as exc:
                logger.warning("Failed to initialise OpenRouter client: %s", exc)

        if not self._providers:
            logger.error(
                "LLMRouter initialised with zero providers.  "
                "Set at least one of GROQ_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY."
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def invoke(self, messages: list, task_type: str = "quick") -> str:
        """Invoke the LLM with automatic provider fallback.

        Args:
            messages: Conversation history as a list of role/content dicts
                (or LangChain message objects).
            task_type: ``"quick"`` (default, fast model) or ``"deep"``
                (larger / long-context model).

        Returns:
            The first successful assistant response text.

        Raises:
            AllProvidersExhaustedError: When every provider is rate-limited
                or unavailable.
        """
        if not self._providers:
            raise AllProvidersExhaustedError("No LLM providers are configured.")

        last_exc: Optional[Exception] = None
        for name, client in self._providers:
            try:
                if task_type == "deep":
                    response = client.invoke_deep(messages)
                else:
                    response = client.invoke(messages)
                logger.debug("LLMRouter: success via provider '%s'.", name)
                return response
            except RateLimitError as exc:  # type: ignore[misc]
                logger.warning(
                    "LLMRouter: provider '%s' rate-limited, trying next. (%s)",
                    name,
                    exc,
                )
                last_exc = exc
                continue
            except Exception as exc:
                logger.error(
                    "LLMRouter: provider '%s' raised unexpected error: %s",
                    name,
                    exc,
                )
                last_exc = exc
                continue

        raise AllProvidersExhaustedError(
            f"All {len(self._providers)} provider(s) exhausted.  "
            f"Last error: {last_exc}"
        )

    def get_status(self) -> dict:
        """Return which providers are configured and available.

        Returns:
            Dictionary mapping provider names to booleans.
            User-supplied providers show up as ``"<provider>_user": True``.
        """
        status = {
            "groq": False,
            "gemini": False,
            "openrouter": False,
            "groq_user": False,
            "gemini_user": False,
            "openrouter_user": False,
            "any_available": bool(self._providers),
            "provider_count": len(self._providers),
        }
        for name, _ in self._providers:
            if name in status:
                status[name] = True
        return status
