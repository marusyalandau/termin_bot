"""Helpers for storing and comparing known appointment hints between checks."""

from __future__ import annotations

import json
import os
from datetime import date
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

    if not isinstance(data, dict):
        return set()

    # Preferred format.
    keys = data.get("keys")
    if isinstance(keys, list):
        return {str(item) for item in keys if str(item).strip()}

    # Backward compatibility with older state files.
    hints = data.get("hints", [])
    return {str(item) for item in hints if str(item).strip()}


def save_known_hints(hints: set[str], slots_by_date: dict[str, list[str]] | None = None) -> None:
    path = _state_file_path()
    payload = {
        "keys": sorted(hints),
        # Keep a legacy mirror for tooling expecting the old field.
        "hints": sorted(hints),
    }
    if slots_by_date:
        payload["slots_by_date"] = {
            str(date): [str(slot_time) for slot_time in slot_times]
            for date, slot_times in sorted(slots_by_date.items())
        }
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def get_new_hints(current_hints: set[str], known_hints: set[str]) -> set[str]:
    return {hint for hint in current_hints if hint not in known_hints}


def build_slot_keys(slots_by_date: dict[str, list[str]] | None, fallback_slots: list[str] | None = None) -> set[str]:
    """Build stable unique keys for date/time slots.

    Preferred key format is `DD.MM.YYYY|HH:MM`. If a date has no explicit time,
    `DD.MM.YYYY|` is used so new dates can still be detected.
    """
    if slots_by_date:
        keys: set[str] = set()
        for date, times in slots_by_date.items():
            if times:
                for slot_time in times:
                    keys.add(f"{date}|{slot_time}")
            else:
                keys.add(f"{date}|")
        if keys:
            return keys

    # Backward compatibility path for flat slot lists.
    keys = set()
    for item in (fallback_slots or []):
        value = str(item).strip()
        if value:
            keys.add(value)
    return keys


def parse_ddmmyyyy(value: str) -> date | None:
    """Parse DD.MM.YYYY date values used in slot keys/maps."""
    try:
        day_s, month_s, year_s = value.split(".")
        return date(int(year_s), int(month_s), int(day_s))
    except Exception:
        return None


def filter_slots_by_max_date(
    slots_by_date: dict[str, list[str]] | None,
    max_inclusive: date,
) -> dict[str, list[str]]:
    """Keep only slot entries with date <= max_inclusive."""
    if not slots_by_date:
        return {}

    filtered: dict[str, list[str]] = {}
    for slot_date, times in slots_by_date.items():
        parsed = parse_ddmmyyyy(slot_date)
        if parsed and parsed <= max_inclusive:
            filtered[slot_date] = list(times)
    return filtered
