"""
AURUM AI — SambaNova inference client.
SambaNova offers the Llama 3.1 405B model — the largest free model available
anywhere. invoke_deep() cycles through a ranked list of models so that if one
is rate-limited or unavailable the next is tried automatically.
"""

import logging
from typing import Optional

from openai import OpenAI
from llm.providers.base_provider import RateLimitError, ProviderError

logger = logging.getLogger(__name__)

SAMBANOVA_QUICK_MODEL = "Meta-Llama-3.3-70B-Instruct"


class SambanovaClient:
    """OpenAI-compatible client for SambaNova Cloud inference."""

    # Ordered list of free-tier deep models.
    # invoke_deep() tries them in order — if one is rate-limited or unavailable
    # the next is tried automatically before giving up on SambaNova entirely.
    #
    # Verified-active models (May 2026) — source: api.sambanova.ai/v1/models
    # Removed (no longer available):
    #   Meta-Llama-3.1-405B-Instruct, Meta-Llama-3.1-70B-Instruct
    DEEP_MODELS: list[str] = [
        "DeepSeek-V3.2",                       # latest DeepSeek — strong reasoning
        "Meta-Llama-3.3-70B-Instruct",         # verified active — strong fallback
        "Llama-4-Maverick-17B-128E-Instruct",  # Llama 4 — new
        "gemma-3-12b-it",                      # lightweight last resort
    ]

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.sambanova.ai/v1",
        )

    def invoke(self, messages: list[dict], model: str = SAMBANOVA_QUICK_MODEL) -> str:
        """Run a chat completion and return the response text.

        Raises:
            RateLimitError: If the API returns a 429 / rate-limit response.
            ProviderError:  For all other API errors.
        """
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
            raise ProviderError(f"SambaNova error (model={model}): {exc}") from exc

    def invoke_deep(self, messages: list[dict]) -> str:
        """Invoke the best available SambaNova model for deep reasoning tasks.

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
                logger.debug("SambaNova deep: success via '%s'.", model)
                return result
            except RateLimitError as exc:
                logger.warning("SambaNova deep: '%s' rate-limited, trying next model.", model)
                last_exc = exc
                continue
            except ProviderError as exc:
                all_rate_limited = False
                logger.warning("SambaNova deep: '%s' unavailable (%s), trying next.", model, exc)
                last_exc = exc
                continue

        if all_rate_limited:
            raise RateLimitError(
                f"SambaNova: all {len(self.DEEP_MODELS)} deep models rate-limited. Last: {last_exc}"
            )
        raise ProviderError(
            f"SambaNova: all {len(self.DEEP_MODELS)} deep models exhausted. Last: {last_exc}"
        )
