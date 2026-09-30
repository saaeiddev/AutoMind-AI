from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from core.paths import resource_path


class KnowledgeBase:
    def __init__(self) -> None:
        self._dtc = self._load_json("knowledge/dtc_database.json")
        self._pids = self._load_json("knowledge/pid_metadata.json")

    @staticmethod
    def _load_json(path: str) -> dict[str, Any]:
        return json.loads(resource_path(path).read_text(encoding="utf-8"))

    def dtc_info(self, code: str) -> dict[str, Any]:
        code = code.upper().strip()
        return dict(self._dtc.get(code, {
            "description": "Generic OBD-II code; not yet documented in the local AutoMind knowledge base.",
            "subsystem": _subsystem_for_code(code),
            "severity": "Unknown",
            "symptoms": [],
            "causes": [],
            "checks": ["Consult an appropriately licensed repair reference for this specific vehicle and code."],
            "related_pids": [],
        }))

    def pid_info(self, pid: str) -> dict[str, Any]:
        return dict(self._pids.get(pid.upper(), {}))

    @property
    def pids(self) -> dict[str, Any]:
        return dict(self._pids)


@lru_cache(maxsize=1)
def get_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase()


def _subsystem_for_code(code: str) -> str:
    if not code:
        return "Unknown"
    return {
        "P": "Powertrain",
        "C": "Chassis",
        "B": "Body",
        "U": "Network",
    }.get(code[0], "Unknown")
