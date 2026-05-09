"""
Groq LLM client for AURUM AI.

Wraps langchain-groq with a simple invoke interface and rate-limit error handling.
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
    DEEP_MODEL = "llama-3.3-70b-versatile"

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
            RateLimitError: If the API returns a 429 error.
            Exception: For other API errors.
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
            raise

    def invoke_deep(self, messages: list) -> str:
        """Invoke the deep-reasoning Groq model (DeepSeek-R1 distil).

        Args:
            messages: List of message dicts or LangChain messages.

        Returns:
            The assistant's response as a plain string.

        Raises:
            RateLimitError: If the API returns a 429 error.
        """
        return self.invoke(messages, model=self.DEEP_MODEL)
