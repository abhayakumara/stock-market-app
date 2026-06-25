"""AI layer (Claude). Market commentary and natural-language strategy authoring.

The Anthropic SDK is an optional dependency and is imported lazily, so the rest of the app
runs without it. All entry points raise :class:`AIUnavailable` when the SDK or API key is
missing; callers translate that to a 503.
"""

from .client import AIClient, AIUnavailable

__all__ = ["AIClient", "AIUnavailable"]
