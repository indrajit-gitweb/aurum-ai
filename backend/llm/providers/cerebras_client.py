"""
AURUM AI — Cerebras inference client.
Cerebras uses wafer-scale chips delivering 1,000+ tokens/sec — the fastest
free inference available. Ideal for the quick-task layer (analyst + persona agents).
"""

import logging
from openai import OpenAI
from llm.providers.base_provider import RateLimitError, ProviderError

logger = logging.getLogger(__name__)

CEREBRAS_QUICK_MODEL = "llama-3.3-70b"
CEREBRAS_FAST_MODEL  = "llama3.1-8b"


class CerebrasClient:
    """OpenAI-compatible client for Cerebras Cloud inference."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.cerebras.ai/v1",
        )

    def invoke(self, messages: list[dict], model: str = CEREBRAS_QUICK_MODEL) -> str:
        """Run a chat completion and return the response text."""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=2048,
                temperature=0.7,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            err = str(exc).lower()
            if "429" in err or "rate limit" in err or "rate_limit" in err:
                raise RateLimitError(f"Cerebras rate limit: {exc}") from exc
            raise ProviderError(f"Cerebras error: {exc}") from exc

    def invoke_deep(self, messages: list[dict]) -> str:
        """Use the larger model for deeper reasoning tasks."""
        return self.invoke(messages, model=CEREBRAS_QUICK_MODEL)
