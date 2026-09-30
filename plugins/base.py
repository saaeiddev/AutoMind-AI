from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PluginManifest:
    plugin_id: str
    name: str
    version: str
    vendor: str
    capabilities: tuple[str, ...]
    read_only: bool = True


class DiagnosticPlugin(ABC):
    """Future extension point for licensed/documented diagnostic integrations.

    V1 intentionally does not dynamically load third-party code. This interface
    establishes the contract for a future signed/permissioned plugin manager.
    """

    manifest: PluginManifest

    @abstractmethod
    def probe(self) -> dict[str, Any]: ...

    @abstractmethod
    def read_data(self, request: dict[str, Any]) -> dict[str, Any]: ...
