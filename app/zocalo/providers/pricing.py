"""Starting prices per million tokens (input, output), matched by model-name prefix, longest first.

These are list prices as published by the providers when this table was written. They change: every model's
price can be edited in Settings → Models, and costs use whatever is stored there. Unknown models start at 0 and
are flagged so the user sets a price before trusting cost estimates.
"""
from __future__ import annotations

PRICES: dict[str, tuple[float, float]] = {
    # Google
    "gemini-2.0-flash-lite": (0.075, 0.30),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-3-flash": (0.50, 3.00),
    "gemini-3-pro": (2.00, 12.00),
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.1-pro": (2.00, 12.00),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.6-flash": (0.75, 3.75),
    "gemini-3.8-flash": (0.75, 3.75),
    "gemma": (0.0, 0.0),
    # Anthropic
    "claude-haiku-4": (1.00, 5.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-opus-4-1": (15.00, 75.00),
    "claude-opus-4-5": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-opus-4": (15.00, 75.00),
    # OpenAI
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-5-nano": (0.05, 0.40),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5": (1.25, 10.00),
}


def default_price(model_id: str) -> tuple[float | None, float | None]:
    mid = model_id.lower().split("/")[-1]
    for prefix in sorted(PRICES, key=len, reverse=True):
        if mid.startswith(prefix):
            return PRICES[prefix]
    return None, None
