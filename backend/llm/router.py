"""
AURUM AI — Multi-provider LLM router with automatic fallback.

Priority order for QUICK tasks (speed optimised):
  1. User-supplied key (whichever provider they chose)
  2. Cerebras  — fastest free inference on the planet (1 000 + tok/s)
  3. Groq      — very fast free inference
  4. SambaNova — fast, with 405B model available
  5. Gemini    — large context window (1 M tokens)
  6. OpenRouter — always-on free-model fallback
  7. NVIDIA NIM — credit-based fallback (405B / Nemotron)

Priority order for DEEP tasks (quality optimised):
  1. User-supplied key
  2. SambaNova 405B — largest free model available
  3. Groq DeepSeek  — chain-of-thought reasoning
  4. Gemini 1.5     — 1 M context for long documents
  5. Cerebras 70B   — fast fallback
  6. OpenRouter     — free-model fallback
  7. NVIDIA NIM     — credit-based last resort (Nemotron-49B / Llama-405B)

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
from llm.providers.nvidia_client import NvidiaClient

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
        user_nvidia_key: Optional[str] = None,
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
        self._user_nvidia     = _mk(NvidiaClient,     user_nvidia_key)

        # ── Shared pool keys from environment ─────────────────────────────────
        self._cerebras   = _mk(CerebrasClient,   os.getenv("CEREBRAS_API_KEY"))
        self._groq       = _mk(GroqClient,        os.getenv("GROQ_API_KEY"))
        self._sambanova  = _mk(SambanovaClient,   os.getenv("SAMBANOVA_API_KEY"))
        self._gemini     = _mk(GeminiClient,      os.getenv("GEMINI_API_KEY"))
        self._openrouter = _mk(OpenRouterClient,  os.getenv("OPENROUTER_API_KEY"))
        self._nvidia     = _mk(NvidiaClient,      os.getenv("NVIDIA_API_KEY"))

        # ── Priority chains ────────────────────────────────────────────────────
        # QUICK: user keys FIRST (highest priority), then shared pool by speed
        # BUG-10 fix: removed mislabelled "cerebras_user" duplicate of _user_groq;
        # moved gemini_user + openrouter_user to front so user keys are actually
        # tried before the shared pool (not dead-last as before).
        self._quick_chain = [
            ("groq_user",       self._user_groq),
            ("gemini_user",     self._user_gemini),
            ("openrouter_user", self._user_openrouter),
            ("nvidia_user",     self._user_nvidia),
            ("cerebras",        self._cerebras),
            ("groq",            self._groq),
            ("sambanova",       self._sambanova),
            ("gemini",          self._gemini),
            ("openrouter",      self._openrouter),
            ("nvidia",          self._nvidia),      # credit-based — last resort
        ]

        # DEEP: quality-optimised — NVIDIA goes last (credit-based, not truly free)
        self._deep_chain = [
            ("groq_user",       self._user_groq),
            ("gemini_user",     self._user_gemini),
            ("openrouter_user", self._user_openrouter),
            ("nvidia_user",     self._user_nvidia),
            ("groq",            self._groq),
            ("openrouter",      self._openrouter),
            ("gemini",          self._gemini),
            ("cerebras",        self._cerebras),
            ("sambanova",       self._sambanova),
            ("nvidia",          self._nvidia),      # credit-based — last resort
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
                "OPENROUTER_API_KEY, CEREBRAS_API_KEY, SAMBANOVA_API_KEY, NVIDIA_API_KEY"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def _try_chain(
        self,
        messages: list,
        chain: list,
        use_deep: bool,
        label: str,
    ) -> Optional[str]:
        """Attempt every provider in *chain* and return the first success.

        Returns None (does NOT raise) if every provider in the chain fails,
        so the caller can try the alternate chain without a try/except.
        """
        for name, client in chain:
            try:
                response = client.invoke_deep(messages) if use_deep else client.invoke(messages)
                logger.debug("LLMRouter: success via '%s' (%s).", name, label)
                return response
            except (RateLimitError, ProviderError) as exc:
                logger.warning(
                    "LLMRouter: '%s' unavailable (%s), trying next.", name, exc
                )
            except Exception as exc:
                logger.error("LLMRouter: '%s' unexpected error: %s", name, exc)
        return None

    def invoke(self, messages: list, task_type: str = "quick") -> str:
        """Invoke the LLM with automatic provider fallback + cross-chain recovery.

        Primary chain is selected by task_type ("deep" or "quick").
        If every provider in the primary chain fails, the router automatically
        retries using the ALTERNATE chain — a different provider ordering that
        starts fresh buckets not hit by the primary chain.

        Example: a persona uses task_type="deep" (Groq-first).  If Groq is
        exhausted, the deep chain falls through OpenRouter → Gemini → Cerebras
        → SambaNova.  If ALL fail, the router switches to the quick chain
        (Cerebras-first) which may find Cerebras still has quota.

        Args:
            messages:  List of role/content dicts.
            task_type: ``"deep"`` (quality, personas/PM) or
                       ``"quick"`` (speed, debate/risk agents).

        Returns:
            Assistant response text from the first successful provider.

        Raises:
            AllProvidersExhaustedError: When both chains are fully exhausted.
        """
        is_deep = task_type == "deep"
        primary_chain   = self._deep_chain  if is_deep else self._quick_chain
        fallback_chain  = self._quick_chain if is_deep else self._deep_chain
        fallback_label  = "quick" if is_deep else "deep"

        if not primary_chain and not fallback_chain:
            raise AllProvidersExhaustedError(
                "No LLM providers are configured. "
                "Please add at least one API key in the sidebar or contact the app owner."
            )

        # ── 1. Try primary chain ──────────────────────────────────────────────
        result = self._try_chain(messages, primary_chain, use_deep=is_deep, label=task_type)
        if result is not None:
            return result

        # ── 2. Primary exhausted — switch to alternate chain ──────────────────
        logger.warning(
            "LLMRouter: %s chain fully exhausted — switching to %s chain as fallback.",
            task_type, fallback_label,
        )
        result = self._try_chain(
            messages, fallback_chain, use_deep=not is_deep, label=fallback_label
        )
        if result is not None:
            return result

        # ── 3. Both chains exhausted ──────────────────────────────────────────
        raise AllProvidersExhaustedError(
            f"All providers exhausted on both '{task_type}' and '{fallback_label}' chains."
        )

    def get_status(self) -> dict:
        """Return which providers are active."""
        all_clients = {
            "cerebras":   self._cerebras,
            "groq":       self._groq,
            "sambanova":  self._sambanova,
            "gemini":     self._gemini,
            "openrouter": self._openrouter,
            "nvidia":     self._nvidia,
        }
        status = {name: (client is not None) for name, client in all_clients.items()}
        status["total_configured"] = sum(status.values())
        status["any_available"]    = status["total_configured"] > 0
        return status
