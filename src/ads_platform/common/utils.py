from __future__ import annotations

from typing import Any


def clip(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
