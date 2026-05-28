"""Utilities for logging auction decisions and results to disk."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def append_jsonl(filepath: Path | str, data: dict[str, Any]) -> None:
    """Append a single JSON object as a line to a JSONL file.
    
    Args:
        filepath: Path to the JSONL file (will be created if doesn't exist)
        data: Dictionary to serialize and append
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with filepath.open('a', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False) + '\n')


def get_daily_log_path(base_dir: Path | str, prefix: str, date: str | None = None) -> Path:
    """Get a date-partitioned log file path.
    
    Args:
        base_dir: Base directory for logs
        prefix: Log file prefix (e.g., 'decision_logs', 'auction_results')
        date: Date string (YYYY-MM-DD). If None, uses current date.
    
    Returns:
        Path to the log file: {base_dir}/{prefix}_{date}.jsonl
    """
    if date is None:
        date = datetime.utcnow().strftime('%Y-%m-%d')
    
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    
    return base_dir / f"{prefix}_{date}.jsonl"
