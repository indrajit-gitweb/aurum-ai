"""
AURUM AI — Multi-provider LLM router with automatic fallback.

Priority order for QUICK tasks (speed optimised):
  1. User-supplied key (whichever provider they chose)
  2. Cerebras  — fastest free inference on the planet (1 000 + tok/s)
  3. Groq      — very fast free inference
  4. SambaNova — fast, with 405B model available
  5. Gemini    — large context window (1 M tokens)
  6. OpenRouter — always-on free-model fallback

Priority order for DEEP tasks (quality optimised):
  1. User-supplied key
  2. SambaNova 405B — largest free model available
  3. Groq DeepSeek  — chain-of-thought reasoning
  4. Gemini 1.5     — 1 M context for long documents
  5. Cerebras 70B   — fast fallback
  6. OpenRouter     — free-model fallback

Any provider whose env key is absent/empty is silently skipped.
On RateLimitError the router automatically tries the next provider.
"""

import logging
import os
from typing import Optional

from llm.providers.base_provider import (
    RateLimitError,
    ProviderError,
    AllProvidersExhaustedError,
)
from llm.providers.groq_client import GroqClient
from llm.providers.gemini_client import GeminiClient
from llm.providers.openrouter_client import OpenRouterClient
from llm.providers.cerebras_client import CerebrasClient
from llm.providers.sambanova_client import SambanovaClient

logger = logging.getLogger(__name__)


class LLMRouter:
    """Routes LLM calls across all configured providers with auto-fallback.

    Args:
        user_groq_key:       Optional Groq key supplied by the end user.
        user_gemini_key:     Optional Gemini key supplied by the end user.
        user_openrouter_key: Optional OpenRouter key supplied by the end user.
    """

    def __init__(
        self,
        user_groq_key: Optional[str] = None,
        user_gemini_key: Optional[str] = None,
        user_openrouter_key: Optional[str] = None,
    ) -> None:

        # Build client instances (skip if key is missing)
        def _mk(cls, key: Optional[str]):
            k = (key or "").strip()
            if not k or k in ("add-later", ""):
                return None
            try:
                return cls(k)
            except Exception as exc:
                logger.warning("Failed to init %s: %s", cls.__name__, exc)
                return None

        # ── User-supplied keys (highest priority) ─────────────────────────────
        self._user_groq       = _mk(GroqClient,       user_groq_key)
        self._user_gemini     = _mk(GeminiClient,     user_gemini_key)
        self._user_openrouter = _mk(OpenRouterClient, user_openrouter_key)

        # ── Shared pool keys from environment ─────────────────────────────────
        self._cerebras   = _mk(CerebrasClient,   os.getenv("CEREBRAS_API_KEY"))
        self._groq       = _mk(GroqClient,        os.getenv("GROQ_API_KEY"))
        self._sambanova  = _mk(SambanovaClient,   os.getenv("SAMBANOVA_API_KEY"))
        self._gemini     = _mk(GeminiClient,      os.getenv("GEMINI_API_KEY"))
        self._openrouter = _mk(OpenRouterClient,  os.getenv("OPENROUTER_API_KEY"))

        # ── Priority chains ────────────────────────────────────────────────────
        # QUICK: user keys FIRST (highest priority), then shared pool by speed
        # BUG-10 fix: removed mislabelled "cerebras_user" duplicate of _user_groq;
        # moved gemini_user + openrouter_user to front so user keys are actually
        # tried before the shared pool (not dead-last as before).
        self._quick_chain = [
            ("groq_user",       self._user_groq),
            ("gemini_user",     self._user_gemini),
            ("openrouter_user", self._user_openrouter),
            ("cerebras",        self._cerebras),
            ("groq",            self._groq),
            ("sambanova",       self._sambanova),
            ("gemini",          self._gemini),
            ("openrouter",      self._openrouter),
        ]

        # DEEP: quality first — SambaNova 405B → Groq → Gemini → Cerebras → OpenRouter
        self._deep_chain = [
            ("groq_user",       self._user_groq),
            ("gemini_user",     self._user_gemini),
            ("openrouter_user", self._user_openrouter),
            ("sambanova",       self._sambanova),
            ("groq",            self._groq),
            ("gemini",          self._gemini),
            ("cerebras",        self._cerebras),
            ("openrouter",      self._openrouter),
        ]

        # Strip None entries
        self._quick_chain = [(n, c) for n, c in self._quick_chain if c is not None]
        self._deep_chain  = [(n, c) for n, c in self._deep_chain  if c is not None]

        # Deduplicate while preserving order (same client object may appear twice)
        seen: set = set()
        self._quick_chain = [(n, c) for n, c in self._quick_chain
                             if id(c) not in seen and not seen.add(id(c))]  # type: ignore
        seen = set()
        self._deep_chain  = [(n, c) for n, c in self._deep_chain
                             if id(c) not in seen and not seen.add(id(c))]  # type: ignore

        total = len(set(id(c) for _, c in self._quick_chain + self._deep_chain))
        logger.info("LLMRouter ready — %d unique provider(s) configured.", total)

        if total == 0:
            logger.error(
                "No LLM providers configured! "
                "Set at least one of: GROQ_API_KEY, GEMINI_API_KEY, "
                "OPENROUTER_API_KEY, CEREBRAS_API_KEY, SAMBANOVA_API_KEY"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def invoke(self, messages: list, task_type: str = "quick") -> str:
        """Invoke the LLM with automatic provider fallback.

        Args:
            messages:  List of role/content dicts.
            task_type: ``"quick"`` (speed, for analyst/persona agents) or
                       ``"deep"`` (quality, for debate/PM agents).

        Returns:
            Assistant response text from the first successful provider.

        Raises:
            AllProvidersExhaustedError: When every provider fails.
        """
        chain = self._deep_chain if task_type == "deep" else self._quick_chain

        if not chain:
            raise AllProvidersExhaustedError(
                "No LLM providers are configured. "
                "Please add at least one API key in the sidebar or contact the app owner."
            )

        last_exc: Optional[Exception] = None

        for name, client in chain:
            try:
                if task_type == "deep":
                    response = client.invoke_deep(messages)
                else:
                    response = client.invoke(messages)

                logger.debug("LLMRouter: success via '%s' (%s).", name, task_type)
                return response

            except (RateLimitError, ProviderError) as exc:
                logger.warning(
                    "LLMRouter: '%s' unavailable (%s), trying next provider.",
                    name, exc,
                )
                last_exc = exc
                continue

            except Exception as exc:
                logger.error("LLMRouter: '%s' unexpected error: %s", name, exc)
                last_exc = exc
                continue

        raise AllProvidersExhaustedError(
            f"All {len(chain)} provider(s) exhausted. Last error: {last_exc}"
        )

    def get_status(self) -> dict:
        """Return which providers are active."""
        all_clients = {
            "cerebras":   self._cerebras,
            "groq":       self._groq,
            "sambanova":  self._sambanova,
            "gemini":     self._gemini,
            "openrouter": self._openrouter,
        }
        status = {name: (client is not None) for name, client in all_clients.items()}
        status["total_configured"] = sum(status.values())
        status["any_available"]    = status["total_configured"] > 0
        return status
