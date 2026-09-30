from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    user_root: Path
    logs: Path
    database: Path
    reports: Path
    config: Path


def resource_path(relative: str) -> Path:
    """Return an absolute path for bundled or source-tree resources."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / relative


def get_paths() -> AppPaths:
    if os.name == "nt":
        local_app_data = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        documents = Path(os.getenv("USERPROFILE", str(Path.home()))) / "Documents"
    else:
        local_app_data = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        documents = Path.home() / "Documents"

    user_root = local_app_data / "AutoMindAI"
    reports = documents / "AutoMind AI" / "Reports"
    return AppPaths(
        user_root=user_root,
        logs=user_root / "Logs",
        database=user_root / "automind.db",
        reports=reports,
        config=user_root / "settings.json",
    )


def ensure_directories() -> AppPaths:
    paths = get_paths()
    paths.user_root.mkdir(parents=True, exist_ok=True)
    paths.logs.mkdir(parents=True, exist_ok=True)
    paths.reports.mkdir(parents=True, exist_ok=True)
    return paths
