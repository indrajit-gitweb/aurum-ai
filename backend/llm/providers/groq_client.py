"""
Groq LLM client for AURUM AI.

Wraps langchain-groq with a simple invoke interface and rate-limit error handling.
invoke_deep() cycles through a ranked list of free-tier models so that if one
model is rate-limited or deprecated the next is tried automatically.
"""

import logging
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_groq import ChatGroq
from llm.providers.base_provider import RateLimitError, ProviderError

logger = logging.getLogger(__name__)


def _to_langchain_messages(messages: list) -> list:
    """Convert plain dicts to LangChain message objects if needed.

    Accepts:
        - Already-constructed LangChain message objects (passed through)
        - Dicts with keys ``role`` and ``content``
    """
    result = []
    for msg in messages:
        if isinstance(msg, (HumanMessage, SystemMessage, AIMessage)):
            result.append(msg)
            continue
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            result.append(SystemMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))
        else:
            result.append(HumanMessage(content=content))
    return result


class GroqClient:
    """Thin wrapper around ``langchain_groq.ChatGroq``.

    Args:
        api_key: Groq API key.
    """

    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    # Ordered list of verified-active free-tier models (confirmed May 2026).
    # invoke_deep() tries them in order — rate-limited or unavailable models
    # are skipped automatically before giving up on Groq entirely.
    #
    # Removed (decommissioned — return "model not found" immediately):
    #   llama-3.1-70b-versatile, mixtral-8x7b-32768, gemma2-9b-it
    #
    # Free-tier limits:
    #   llama-3.3-70b-versatile                  12K TPM  30 RPM   1K RPD
    #   meta-llama/llama-4-scout-17b-16e-instruct 30K TPM  30 RPM   1K RPD  ← highest TPM
    #   llama-3.1-8b-instant                      6K TPM   30 RPM  14.4K RPD ← highest RPD
    #   qwen/qwen3-32b                             6K TPM   60 RPM   1K RPD  ← highest RPM
    DEEP_MODELS: list[str] = [
        "llama-3.3-70b-versatile",                     # best quality — primary (production)
        "openai/gpt-oss-120b",                         # 120B production model — stable fallback
        "meta-llama/llama-4-scout-17b-16e-instruct",   # highest TPM (30K) — preview
        "llama-3.1-8b-instant",                        # highest RPD (14.4K) — production
        "qwen/qwen3-32b",                              # highest RPM (60) — preview
    ]

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Groq API key must not be empty.")
        self._api_key = api_key

    def _build_client(self, model: str) -> ChatGroq:
        return ChatGroq(
            api_key=self._api_key,
            model_name=model,
            temperature=0.2,
        )

    def invoke(
        self,
        messages: list,
        model: str = DEFAULT_MODEL,
    ) -> str:
        """Invoke the Groq model and return the response text.

        Args:
            messages: List of message dicts (role/content) or LangChain messages.
            model: Model identifier string.

        Returns:
            The assistant's response as a plain string.

        Raises:
            RateLimitError: If the API returns a 429 / rate-limit response.
            ProviderError:  For all other API errors.
        """
        lc_messages = _to_langchain_messages(messages)
        client = self._build_client(model)
        try:
            response = client.invoke(lc_messages)
            return response.content
        except Exception as exc:
            exc_str = str(exc).lower()
            if "429" in exc_str or "rate limit" in exc_str or "rate_limit" in exc_str:
                logger.warning("Groq rate limit hit for model %s: %s", model, exc)
                raise RateLimitError(f"Groq rate limit exceeded: {exc}") from exc
            logger.error("Groq invocation error (model=%s): %s", model, exc)
            raise ProviderError(f"Groq error (model={model}): {exc}") from exc

    def invoke_deep(self, messages: list) -> str:
        """Invoke the best available Groq model for deep reasoning tasks.

        Tries DEEP_MODELS in order.  Both rate-limit (429) and provider errors
        (model deprecated / unavailable) cause the next model to be tried.
        Only raises an error when the entire model list is exhausted.

        Raises:
            RateLimitError: Only if ALL models are rate-limited.
            ProviderError:  If all models return non-rate-limit errors.
        """
        last_exc: Optional[Exception] = None
        all_rate_limited = True

        for model in self.DEEP_MODELS:
            try:
                result = self.invoke(messages, model=model)
                logger.debug("Groq deep: success via '%s'.", model)
                return result
            except RateLimitError as exc:
                logger.warning("Groq deep: '%s' rate-limited, trying next model.", model)
                last_exc = exc
                continue
            except ProviderError as exc:
                all_rate_limited = False
                logger.warning("Groq deep: '%s' unavailable (%s), trying next.", model, exc)
                last_exc = exc
                continue

        if all_rate_limited:
            raise RateLimitError(
                f"Groq: all {len(self.DEEP_MODELS)} deep models rate-limited. Last: {last_exc}"
            )
        raise ProviderError(
            f"Groq: all {len(self.DEEP_MODELS)} deep models exhausted. Last: {last_exc}"
        )
