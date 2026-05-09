"""
Gemini LLM client for AURUM AI.

Wraps langchain-google-genai with a simple invoke interface and rate-limit error handling.
invoke_deep() cycles through a ranked list of free-tier models so that if one
model is rate-limited or deprecated the next is tried automatically.
"""

import logging
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from llm.providers.base_provider import RateLimitError, ProviderError

logger = logging.getLogger(__name__)


def _to_langchain_messages(messages: list) -> list:
    """Convert plain dicts to LangChain message objects if needed."""
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


class GeminiClient:
    """Thin wrapper around ``langchain_google_genai.ChatGoogleGenerativeAI``.

    Args:
        api_key: Google Gemini API key.
    """

    DEFAULT_MODEL = "gemini-2.0-flash"

    # Ordered list of free-tier deep models.
    # invoke_deep() tries them in order — if one is rate-limited or unavailable
    # the next is tried automatically before giving up on Gemini entirely.
    DEEP_MODELS: list[str] = [
        "gemini-2.0-flash",          # fast, capable, generous free tier — primary
        "gemini-1.5-flash",          # 1M context window — great for long filings
        "gemini-2.0-flash-lite",     # lightweight fallback
        "gemini-1.5-flash-8b",       # smallest / last resort
    ]

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Gemini API key must not be empty.")
        self._api_key = api_key

    def _build_client(self, model: str) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            google_api_key=self._api_key,
            model=model,
            temperature=0.2,
            convert_system_message_to_human=True,
        )

    def invoke(
        self,
        messages: list,
        model: str = DEFAULT_MODEL,
    ) -> str:
        """Invoke the Gemini model and return the response text.

        Args:
            messages: List of message dicts (role/content) or LangChain messages.
            model: Model identifier string.

        Returns:
            The assistant's response as a plain string.

        Raises:
            RateLimitError: If the API returns a 429 / quota-exceeded response.
            ProviderError:  For all other API errors.
        """
        lc_messages = _to_langchain_messages(messages)
        client = self._build_client(model)
        try:
            response = client.invoke(lc_messages)
            return response.content
        except Exception as exc:
            exc_str = str(exc).lower()
            if "429" in exc_str or "rate limit" in exc_str or "rate_limit" in exc_str or "quota" in exc_str:
                logger.warning("Gemini rate limit hit for model %s: %s", model, exc)
                raise RateLimitError(f"Gemini rate limit exceeded: {exc}") from exc
            logger.error("Gemini invocation error (model=%s): %s", model, exc)
            raise ProviderError(f"Gemini error (model={model}): {exc}") from exc

    def invoke_deep(self, messages: list) -> str:
        """Invoke the best available Gemini model for deep reasoning tasks.

        Tries DEEP_MODELS in order.  Both rate-limit (429/quota) and provider
        errors (model deprecated / unavailable) cause the next model to be tried.
        Only raises an error when the entire model list is exhausted.

        Raises:
            RateLimitError: Only if ALL models are rate-limited / quota-exceeded.
            ProviderError:  If all models return non-rate-limit errors.
        """
        last_exc: Optional[Exception] = None
        all_rate_limited = True

        for model in self.DEEP_MODELS:
            try:
                result = self.invoke(messages, model=model)
                logger.debug("Gemini deep: success via '%s'.", model)
                return result
            except RateLimitError as exc:
                logger.warning("Gemini deep: '%s' rate-limited, trying next model.", model)
                last_exc = exc
                continue
            except ProviderError as exc:
                all_rate_limited = False
                logger.warning("Gemini deep: '%s' unavailable (%s), trying next.", model, exc)
                last_exc = exc
                continue

        if all_rate_limited:
            raise RateLimitError(
                f"Gemini: all {len(self.DEEP_MODELS)} deep models rate-limited. Last: {last_exc}"
            )
        raise ProviderError(
            f"Gemini: all {len(self.DEEP_MODELS)} deep models exhausted. Last: {last_exc}"
        )
