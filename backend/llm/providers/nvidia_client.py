"""
AURUM AI — NVIDIA NIM inference client.

NVIDIA NIM exposes hundreds of hosted models through an OpenAI-compatible
endpoint (https://integrate.api.nvidia.com/v1).  New accounts receive free
credits; the client falls back gracefully if the quota is exhausted.

Key difference from other providers: some NVIDIA models (e.g. reasoning
models) return an extra ``reasoning_content`` field on the message.  The
client captures the final ``content`` answer and ignores the chain-of-thought
so the rest of the pipeline receives clean text.
"""

import logging
from typing import Optional

from openai import OpenAI
from llm.providers.base_provider import RateLimitError, ProviderError

logger = logging.getLogger(__name__)

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NvidiaClient:
    """OpenAI-compatible client for NVIDIA NIM inference."""

    DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"

    # Ordered list of models for deep tasks.
    # invoke_deep() tries them in order — rate-limited or unavailable models
    # are skipped automatically before giving up on NVIDIA entirely.
    #
    # Verified-available models (May 2026) — source: build.nvidia.com/explore/reasoning
    # Free-credit tier: all models below consume credits, newer accounts have quota.
    DEEP_MODELS: list[str] = [
        "nvidia/llama-3.3-nemotron-super-49b-v1",   # NVIDIA-tuned reasoning — best quality
        "meta/llama-3.1-405b-instruct",              # largest Llama — strongest reasoning
        "meta/llama-3.3-70b-instruct",               # solid 70B — reliable fallback
        "stepfun-ai/step-3.5-flash",                 # fast flash model — last resort
    ]

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("NVIDIA API key must not be empty.")
        self._client = OpenAI(
            api_key=api_key,
            base_url=NVIDIA_BASE_URL,
        )

    def invoke(self, messages: list[dict], model: str = DEFAULT_MODEL) -> str:
        """Run a non-streaming chat completion and return the response text.

        Handles both standard models (message.content) and reasoning models
        that additionally populate message.reasoning_content — the final
        answer in ``content`` is always preferred; ``reasoning_content`` is
        used as a fallback only if ``content`` is empty.

        Raises:
            RateLimitError: If the API returns a 429 / rate-limit / quota response.
            ProviderError:  For all other API errors.
        """
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                top_p=0.9,
                max_tokens=4096,
                stream=False,
            )
            msg = response.choices[0].message
            content = msg.content or ""
            # Reasoning models populate reasoning_content with chain-of-thought.
            # We want the final answer only — use content; fall back to reasoning
            # only if content is genuinely empty (rare, but defensive).
            if not content:
                content = getattr(msg, "reasoning_content", None) or ""
            return content
        except Exception as exc:
            err = str(exc).lower()
            if (
                "429" in err
                or "rate limit" in err
                or "rate_limit" in err
                or "quota" in err
                or "insufficient" in err
                or "credits" in err
            ):
                raise RateLimitError(f"NVIDIA rate limit / quota exceeded: {exc}") from exc
            if "404" in err or "not found" in err or "no endpoints" in err:
                raise ProviderError(f"NVIDIA model not found ({model}): {exc}") from exc
            raise ProviderError(f"NVIDIA error (model={model}): {exc}") from exc

    def invoke_deep(self, messages: list[dict]) -> str:
        """Invoke the best available NVIDIA model for deep reasoning tasks.

        Tries DEEP_MODELS in order.  Both rate-limit (429 / quota) and
        provider errors (model deprecated / unavailable) cause the next model
        to be tried.  Only raises when the entire list is exhausted.

        Raises:
            RateLimitError: Only if ALL models are rate-limited / quota-exhausted.
            ProviderError:  If all models return non-rate-limit errors.
        """
        last_exc: Optional[Exception] = None
        all_rate_limited = True

        for model in self.DEEP_MODELS:
            try:
                result = self.invoke(messages, model=model)
                logger.debug("NVIDIA deep: success via '%s'.", model)
                return result
            except RateLimitError as exc:
                logger.warning("NVIDIA deep: '%s' rate-limited/quota, trying next.", model)
                last_exc = exc
                continue
            except ProviderError as exc:
                all_rate_limited = False
                logger.warning("NVIDIA deep: '%s' unavailable (%s), trying next.", model, exc)
                last_exc = exc
                continue

        if all_rate_limited:
            raise RateLimitError(
                f"NVIDIA: all {len(self.DEEP_MODELS)} deep models rate-limited. Last: {last_exc}"
            )
        raise ProviderError(
            f"NVIDIA: all {len(self.DEEP_MODELS)} deep models exhausted. Last: {last_exc}"
        )
