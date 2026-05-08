"""
OpenRouter LLM client for AURUM AI.

Uses the openai SDK pointed at the OpenRouter base URL.  Acts as the last-resort
fallback in the multi-provider chain — free-tier models only, no cost incurred.
"""

import logging
from typing import Optional

from openai import OpenAI, RateLimitError as OpenAIRateLimitError

from llm.providers.base_provider import RateLimitError, ProviderError  # BUG-09 fix: use shared class

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterClient:
    """OpenRouter client backed by the openai SDK.

    Args:
        api_key: OpenRouter API key.
    """

    DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct:free"

    # Ordered list of free deep-task models.  invoke_deep() tries them in order,
    # skipping any that return 404 (model no longer hosted on OpenRouter).
    DEEP_MODELS: list[str] = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen3-14b:free",
        "google/gemma-3-27b-it:free",
        "deepseek/deepseek-r1-0528:free",
        "mistralai/mistral-7b-instruct:free",
        "meta-llama/llama-3.1-8b-instruct:free",  # last resort: same as quick
    ]

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("OpenRouter API key must not be empty.")
        self._client = OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
        )

    def _messages_to_dicts(self, messages: list) -> list[dict]:
        """Normalise messages to plain dicts for the openai SDK."""
        result = []
        for msg in messages:
            # Already a plain dict — pass through
            if isinstance(msg, dict):
                result.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
                continue
            # LangChain message objects expose .type and .content
            role_map = {
                "human": "user",
                "ai": "assistant",
                "system": "system",
            }
            role = role_map.get(getattr(msg, "type", "human"), "user")
            result.append({"role": role, "content": msg.content})
        return result

    def invoke(
        self,
        messages: list,
        model: str = DEFAULT_MODEL,
    ) -> str:
        """Invoke an OpenRouter model and return the response text.

        Args:
            messages: List of message dicts (role/content) or LangChain messages.
            model: OpenRouter model path, e.g. ``"meta-llama/llama-3.1-8b-instruct:free"``.

        Returns:
            The assistant's response as a plain string.

        Raises:
            RateLimitError: If the API returns a 429 error.
            Exception: For other API errors.
        """
        normalised = self._messages_to_dicts(messages)
        try:
            completion = self._client.chat.completions.create(
                model=model,
                messages=normalised,
                temperature=0.2,
            )
            return completion.choices[0].message.content or ""
        except OpenAIRateLimitError as exc:
            logger.warning("OpenRouter rate limit hit for model %s: %s", model, exc)
            raise RateLimitError(f"OpenRouter rate limit exceeded: {exc}") from exc
        except Exception as exc:
            exc_str = str(exc)
            exc_lower = exc_str.lower()
            if "429" in exc_str or "rate limit" in exc_lower or "rate_limit" in exc_lower:
                logger.warning("OpenRouter rate limit hit for model %s: %s", model, exc)
                raise RateLimitError(f"OpenRouter rate limit exceeded: {exc}") from exc
            # 404 = model no longer hosted on OpenRouter → provider error (triggers router fallback)
            if "404" in exc_str or "no endpoints found" in exc_lower or "not found" in exc_lower:
                logger.warning("OpenRouter model %s unavailable (404): %s", model, exc)
                raise ProviderError(f"OpenRouter model not found ({model}): {exc}") from exc
            logger.error("OpenRouter invocation error (model=%s): %s", model, exc)
            raise ProviderError(f"OpenRouter error: {exc}") from exc

    def invoke_deep(self, messages: list) -> str:
        """Invoke the best available free deep model with per-model fallback.

        Tries DEEP_MODELS in order.  Both 404 (model gone) AND 429 (model
        rate-limited) cause the next model to be tried — OpenRouter hosts many
        free models and typically at least one is available.  Only when the
        entire list is exhausted is an error raised to the LLMRouter.

        Key distinction from invoke():
          - invoke() propagates RateLimitError immediately (whole-provider limit).
          - invoke_deep() treats a single-model 429 as a per-model limit and
            rotates to the next model before giving up on the provider.

        Raises:
            RateLimitError: Only if ALL models in DEEP_MODELS are rate-limited.
            ProviderError:  If all models return 404 / other errors.
        """
        last_exc: Optional[Exception] = None
        all_rate_limited = True   # assume rate-limited until we see a non-429 error

        for model in self.DEEP_MODELS:
            try:
                result = self.invoke(messages, model=model)
                logger.debug("OpenRouter deep: success via '%s'.", model)
                return result
            except RateLimitError as exc:
                # This model is temporarily rate-limited — try the next one
                logger.warning("OpenRouter deep: '%s' rate-limited, trying next model.", model)
                last_exc = exc
                continue   # ← KEY FIX: was `raise` before, which abandoned all remaining models
            except ProviderError as exc:
                # Model is gone (404) or other non-rate-limit error
                all_rate_limited = False
                logger.warning("OpenRouter deep: '%s' unavailable (%s), trying next.", model, exc)
                last_exc = exc
                continue

        # All models tried — report the appropriate error type
        if all_rate_limited:
            raise RateLimitError(
                f"OpenRouter: all {len(self.DEEP_MODELS)} deep models rate-limited. Last: {last_exc}"
            )
        raise ProviderError(
            f"OpenRouter: all {len(self.DEEP_MODELS)} deep models exhausted. Last: {last_exc}"
        )
