"""
AURUM AI — Shared provider exceptions.
All LLM provider clients raise these so the router can handle them uniformly.
"""


class RateLimitError(Exception):
    """Raised when a provider returns a 429 / rate-limit response."""
    pass


class ProviderError(Exception):
    """Raised for non-rate-limit provider errors."""
    pass


class AllProvidersExhaustedError(Exception):
    """Raised by LLMRouter when every configured provider has been tried."""
    pass
