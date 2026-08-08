"""Plugin settings: env vars and optional JSON settings file.

Resolution order (first non-empty wins for API base):
1. ``PCB_COPILOT_API_BASE`` environment variable
2. ``PCB_AI_API_BASE`` environment variable
3. ``api_base`` in settings JSON
4. Default ``http://127.0.0.1:8000``
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_API_BASE = "http://127.0.0.1:8000"
SETTINGS_FILENAMES = (
    "pcb_copilot_settings.json",
    "settings.json",
)


def _user_settings_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "pcb-copilot"
    return Path.home() / ".pcb-copilot"


def settings_search_paths(plugin_dir: Path | None = None) -> list[Path]:
    """Candidate settings file locations (plugin dir, user config)."""
    paths: list[Path] = []
    if plugin_dir is not None:
        for name in SETTINGS_FILENAMES:
            paths.append(plugin_dir / name)
    user_dir = _user_settings_dir()
    for name in SETTINGS_FILENAMES:
        paths.append(user_dir / name)
    return paths


def load_settings_file(plugin_dir: Path | None = None) -> dict[str, Any]:
    for path in settings_search_paths(plugin_dir):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return {}


def get_api_base(plugin_dir: Path | None = None) -> str:
    for key in ("PCB_COPILOT_API_BASE", "PCB_AI_API_BASE"):
        value = (os.environ.get(key) or "").strip()
        if value:
            return value.rstrip("/")
    settings = load_settings_file(plugin_dir)
    raw = settings.get("api_base") or settings.get("api_url")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().rstrip("/")
    return DEFAULT_API_BASE


def get_timeout_s(plugin_dir: Path | None = None, default: float = 120.0) -> float:
    env = (os.environ.get("PCB_COPILOT_TIMEOUT_S") or "").strip()
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    settings = load_settings_file(plugin_dir)
    raw = settings.get("timeout_s")
    if isinstance(raw, (int, float)) and raw > 0:
        return float(raw)
    return default
