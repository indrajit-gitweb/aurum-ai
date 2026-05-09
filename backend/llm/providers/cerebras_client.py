"""
AURUM AI — Cerebras inference client.
Cerebras uses wafer-scale chips delivering 1,000+ tokens/sec — the fastest
free inference available. invoke_deep() cycles through available models so
that if one is rate-limited or unavailable the next is tried automatically.
"""

import logging
from typing import Optional

from openai import OpenAI
from llm.providers.base_provider import RateLimitError, ProviderError

logger = logging.getLogger(__name__)


class CerebrasClient:
    """OpenAI-compatible client for Cerebras Cloud inference."""

    DEFAULT_MODEL = "llama-3.3-70b"

    # Ordered list of models for deep tasks.
    # invoke_deep() tries them in order — if one is rate-limited or unavailable
    # the next is tried automatically before giving up on Cerebras entirely.
    DEEP_MODELS: list[str] = [
        "llama-3.3-70b",    # fastest free inference — primary
        "llama3.1-8b",      # smaller but still very fast — fallback
    ]

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.cerebras.ai/v1",
        )

    def invoke(self, messages: list[dict], model: str = DEFAULT_MODEL) -> str:
        """Run a chat completion and return the response text.

        Raises:
            RateLimitError: If the API returns a 429 / rate-limit response.
            ProviderError:  For all other API errors.
        """
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
            raise ProviderError(f"Cerebras error (model={model}): {exc}") from exc

    def invoke_deep(self, messages: list[dict]) -> str:
        """Invoke the best available Cerebras model for deep reasoning tasks.

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
                logger.debug("Cerebras deep: success via '%s'.", model)
                return result
            except RateLimitError as exc:
                logger.warning("Cerebras deep: '%s' rate-limited, trying next model.", model)
                last_exc = exc
                continue
            except ProviderError as exc:
                all_rate_limited = False
                logger.warning("Cerebras deep: '%s' unavailable (%s), trying next.", model, exc)
                last_exc = exc
                continue

        if all_rate_limited:
            raise RateLimitError(
                f"Cerebras: all {len(self.DEEP_MODELS)} deep models rate-limited. Last: {last_exc}"
            )
        raise ProviderError(
            f"Cerebras: all {len(self.DEEP_MODELS)} deep models exhausted. Last: {last_exc}"
        )
