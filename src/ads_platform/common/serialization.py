from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if is_dataclass(obj):
        return {k: to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {str(k): to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_dict(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if hasattr(obj, 'model_dump'):
        return to_dict(obj.model_dump(mode='json'))
    if hasattr(obj, '__dict__'):
        return {k: to_dict(v) for k, v in vars(obj).items()}
    return str(obj)
