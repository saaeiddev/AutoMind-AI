from __future__ import annotations

from typing import Any

from ai.provider import AIProvider
from ai.sanitize import sanitize_diagnostic_payload
from vehicle.models import AIAnalysis, DiagnosticSession, VehicleProfile


class AIService:
    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    def build_context(
        self,
        session: DiagnosticSession,
        vehicle: VehicleProfile | None,
        *,
        include_user_notes: bool = False,
        historical_faults: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        vehicle_context: dict[str, Any] = {}
        if vehicle:
            vehicle_context = {
                "manufacturer": vehicle.manufacturer,
                "model": vehicle.model,
                "year": vehicle.year,
                "engine": vehicle.engine,
                "fuel_type": vehicle.fuel_type,
                "vin": vehicle.vin,
                "mileage": vehicle.mileage,
            }
        session_context: dict[str, Any] = {
            "connection_mode": session.connection_mode,
            "scenario": session.scenario,
            "health_status": session.health_status,
            "dtcs": [d.to_dict() for d in session.dtcs],
            "freeze_frame": session.freeze_frame,
            "live_data": {k: v.to_dict() for k, v in session.live_data.items()},
            "local_findings": [f.to_dict() for f in session.findings],
        }
        if include_user_notes and session.user_notes.strip():
            session_context["user_notes"] = session.user_notes.strip()
        context = {
            "vehicle": vehicle_context,
            "session": session_context,
            "guardrails": {
                "confirmed_vs_possible": "Treat DTCs and measured PID values as observed evidence. Treat mechanical causes as hypotheses until tested.",
                "no_invented_measurements": "Do not invent measurements that are absent or unavailable.",
                "read_only_scope": "Do not provide ECU flashing, immobilizer bypass, odometer modification, safety-system disabling, or arbitrary CAN injection instructions.",
            },
        }
        if historical_faults:
            context["historical_faults"] = historical_faults
        return context

    def analyze(
        self,
        session: DiagnosticSession,
        vehicle: VehicleProfile | None,
        question: str,
        include_vin: bool = False,
        include_user_notes: bool = False,
        historical_faults: list[dict[str, Any]] | None = None,
    ) -> AIAnalysis:
        context = sanitize_diagnostic_payload(
            self.build_context(
                session,
                vehicle,
                include_user_notes=include_user_notes,
                historical_faults=historical_faults,
            ),
            include_vin=include_vin,
        )
        raw = self.provider.analyze(context, question)
        return parse_ai_analysis(raw, provider=self.provider.name)


def parse_ai_analysis(raw: dict[str, Any], provider: str) -> AIAnalysis:
    def strings(key: str) -> list[str]:
        value = raw.get(key, [])
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(x) for x in value if x is not None]
        return []

    summary = str(raw.get("summary", "AI analysis completed."))
    confidence = str(raw.get("confidence", raw.get("uncertainty", "Unspecified")))
    return AIAnalysis(
        summary=summary,
        observed_evidence=strings("observed_evidence") or strings("evidence"),
        possible_causes=strings("possible_causes") or strings("causes"),
        recommended_steps=strings("recommended_steps") or strings("diagnostic_steps"),
        additional_measurements=strings("additional_measurements"),
        confidence=confidence,
        warnings=strings("warnings"),
        provider=provider,
    )
