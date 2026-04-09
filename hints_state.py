"""Helpers for storing and comparing known appointment hints between checks."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _state_file_path() -> Path:
    configured = os.getenv("HINTS_STATE_FILE", ".appointment_hints.json")
    return Path(configured)


def load_known_hints() -> set[str]:
    path = _state_file_path()
    if not path.exists():
        return set()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set()

    hints = data.get("hints", []) if isinstance(data, dict) else []
    return {str(item) for item in hints if str(item).strip()}


def save_known_hints(hints: set[str]) -> None:
    path = _state_file_path()
    payload = {"hints": sorted(hints)}
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def get_new_hints(current_hints: set[str], known_hints: set[str]) -> set[str]:
    return {hint for hint in current_hints if hint not in known_hints}
