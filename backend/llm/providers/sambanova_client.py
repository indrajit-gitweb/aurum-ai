"""
AURUM AI — SambaNova inference client.
SambaNova offers the Llama 3.1 405B model — the largest free model available
anywhere. Perfect for deep-reasoning tasks: debate, risk analysis, and the
Portfolio Manager's final BUY/HOLD/SELL verdict.
"""

import logging
from openai import OpenAI
from llm.providers.base_provider import RateLimitError, ProviderError

logger = logging.getLogger(__name__)

SAMBANOVA_DEEP_MODEL  = "Meta-Llama-3.1-405B-Instruct"
SAMBANOVA_QUICK_MODEL = "Meta-Llama-3.3-70B-Instruct"
SAMBANOVA_REASON_MODEL = "DeepSeek-R1"          # chain-of-thought reasoning


class SambanovaClient:
    """OpenAI-compatible client for SambaNova Cloud inference."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.sambanova.ai/v1",
        )

    def invoke(self, messages: list[dict], model: str = SAMBANOVA_QUICK_MODEL) -> str:
        """Run a chat completion and return the response text."""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=4096,
                temperature=0.7,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            err = str(exc).lower()
            if "429" in err or "rate limit" in err or "rate_limit" in err:
                raise RateLimitError(f"SambaNova rate limit: {exc}") from exc
            raise ProviderError(f"SambaNova error: {exc}") from exc

    def invoke_deep(self, messages: list[dict]) -> str:
        """Use the 405B model for the most complex reasoning tasks."""
        return self.invoke(messages, model=SAMBANOVA_DEEP_MODEL)
