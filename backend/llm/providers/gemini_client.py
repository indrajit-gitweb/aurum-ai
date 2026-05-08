"""
Gemini LLM client for AURUM AI.

Wraps langchain-google-genai with a simple invoke interface and rate-limit error handling.
"""

import logging
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from llm.providers.base_provider import RateLimitError  # BUG-09 fix: use shared class

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
    # 1M-context model, useful for long filing documents
    DEEP_MODEL = "gemini-1.5-flash"

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
            if "429" in exc_str or "rate limit" in exc_str or "rate_limit" in exc_str or "quota" in exc_str:
                logger.warning("Gemini rate limit hit for model %s: %s", model, exc)
                raise RateLimitError(f"Gemini rate limit exceeded: {exc}") from exc
            logger.error("Gemini invocation error (model=%s): %s", model, exc)
            raise

    def invoke_deep(self, messages: list) -> str:
        """Invoke the deep / long-context Gemini model (1.5-flash, 1M tokens).

        Ideal for analysing lengthy SEC filings or earnings call transcripts.

        Args:
            messages: List of message dicts or LangChain messages.

        Returns:
            The assistant's response as a plain string.

        Raises:
            RateLimitError: If the API returns a 429 error.
        """
        return self.invoke(messages, model=self.DEEP_MODEL)
