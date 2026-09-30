from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class VehicleProfile:
    id: str = field(default_factory=lambda: str(uuid4()))
    manufacturer: str = ""
    model: str = ""
    year: int | None = None
    engine: str = ""
    fuel_type: str = "Gasoline"
    vin: str = ""
    mileage: float | None = None
    notes: str = ""
    image_path: str = ""
    created_at: str = field(default_factory=utc_now_iso)

    @property
    def display_name(self) -> str:
        pieces = [str(self.year) if self.year else "", self.manufacturer, self.model]
        text = " ".join(p for p in pieces if p).strip()
        return text or "Unidentified Vehicle"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PIDValue:
    pid: str
    name: str
    value: float | int | str | None
    unit: str = ""
    supported: bool = True
    timestamp: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DTCRecord:
    code: str
    status: str = "Stored"
    description: str = "Description unavailable"
    subsystem: str = "Unknown"
    severity: str = "Unknown"
    freeze_frame: dict[str, Any] = field(default_factory=dict)
    possible_causes: list[str] = field(default_factory=list)
    symptoms: list[str] = field(default_factory=list)
    recommended_checks: list[str] = field(default_factory=list)
    related_pids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DiagnosticFinding:
    title: str
    evidence: list[str]
    possible_causes: list[dict[str, Any]]
    recommended_steps: list[str]
    confidence: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AIAnalysis:
    summary: str
    observed_evidence: list[str]
    possible_causes: list[str]
    recommended_steps: list[str]
    additional_measurements: list[str]
    confidence: str
    warnings: list[str]
    provider: str = "local"
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DiagnosticSession:
    id: str = field(default_factory=lambda: str(uuid4()))
    vehicle_id: str = ""
    started_at: str = field(default_factory=utc_now_iso)
    ended_at: str = ""
    adapter: str = ""
    connection_mode: str = "simulation"
    scenario: str = ""
    dtcs: list[DTCRecord] = field(default_factory=list)
    live_data: dict[str, PIDValue] = field(default_factory=dict)
    freeze_frame: dict[str, Any] = field(default_factory=dict)
    findings: list[DiagnosticFinding] = field(default_factory=list)
    ai_analysis: AIAnalysis | None = None
    user_notes: str = ""
    health_status: str = "Unknown"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data
