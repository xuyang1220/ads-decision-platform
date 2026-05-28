"""Tests for logging utilities."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from ads_platform.common.logging_utils import append_jsonl, get_daily_log_path


def test_append_jsonl(tmp_path: Path) -> None:
    """Test appending JSONL data to a file."""
    log_file = tmp_path / "test.jsonl"
    
    # Append first entry
    data1 = {"request_id": "req_1", "value": 100}
    append_jsonl(log_file, data1)
    
    # Append second entry
    data2 = {"request_id": "req_2", "value": 200}
    append_jsonl(log_file, data2)
    
    # Read and verify
    lines = log_file.read_text().strip().split('\n')
    assert len(lines) == 2
    assert json.loads(lines[0]) == data1
    assert json.loads(lines[1]) == data2


def test_append_jsonl_creates_directory(tmp_path: Path) -> None:
    """Test that append_jsonl creates parent directories."""
    nested_dir = tmp_path / "nested" / "path"
    log_file = nested_dir / "test.jsonl"
    
    data = {"key": "value"}
    append_jsonl(log_file, data)
    
    assert log_file.exists()
    assert json.loads(log_file.read_text().strip()) == data


def test_get_daily_log_path_with_date(tmp_path: Path) -> None:
    """Test getting a log path with explicit date."""
    result = get_daily_log_path(tmp_path, "decision_logs", "2024-01-15")
    
    expected = tmp_path / "decision_logs_2024-01-15.jsonl"
    assert result == expected


def test_get_daily_log_path_default_date(tmp_path: Path) -> None:
    """Test getting a log path with current date."""
    result = get_daily_log_path(tmp_path, "auction_results")
    
    today = datetime.utcnow().strftime('%Y-%m-%d')
    expected = tmp_path / f"auction_results_{today}.jsonl"
    assert result == expected


def test_get_daily_log_path_creates_directory(tmp_path: Path) -> None:
    """Test that get_daily_log_path creates the base directory."""
    nested_dir = tmp_path / "logs" / "decisions"
    result = get_daily_log_path(nested_dir, "test", "2024-01-01")
    
    assert nested_dir.exists()
    assert nested_dir.is_dir()
