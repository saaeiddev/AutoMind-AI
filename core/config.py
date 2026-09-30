from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any

from core.paths import ensure_directories


DEFAULT_SETTINGS: dict[str, Any] = {
    "general": {
        "first_run_complete": False,
        "units": "metric",
        "theme": "dark",
        "simulation_mode": True,
    },
    "obd": {
        "serial_port": "",
        "baud_rate": 38400,
        "timeout_seconds": 2.0,
        "auto_detect": True,
    },
    "ai": {
        "enabled": False,
        "cloud_analysis_allowed": False,
        "backend_url": "",
        "client_token_env": "AUTOMIND_CLIENT_TOKEN",
        "send_vin": False,
        "send_session_notes": False,
        "timeout_seconds": 30,
    },
    "privacy": {
        "store_ai_results": True,
        "include_vin_in_reports": True,
    },
    "diagnostics": {
        "sample_interval_ms": 750,
        "auto_save_sessions": True,
    },
}


class ConfigManager:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or ensure_directories().config
        self._lock = RLock()
        self._data = deepcopy(DEFAULT_SETTINGS)
        self.load()

    @property
    def data(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._data)

    def load(self) -> None:
        with self._lock:
            if not self.path.exists():
                self.save()
                return
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                self._data = _deep_merge(deepcopy(DEFAULT_SETTINGS), loaded)
            except (OSError, json.JSONDecodeError, TypeError):
                self._data = deepcopy(DEFAULT_SETTINGS)

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
            tmp.replace(self.path)

    def get(self, section: str, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any, save: bool = True) -> None:
        with self._lock:
            self._data.setdefault(section, {})[key] = value
            if save:
                self.save()


def _deep_merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base
