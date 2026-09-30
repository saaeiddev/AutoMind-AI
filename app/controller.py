from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from ai.provider import BackendAIProvider, AIProviderError
from ai.service import AIService
from core.config import ConfigManager
from core.events import EventBus
from core.paths import ensure_directories
from database.repository import DatabaseRepository
from diagnostics.rules import DiagnosticRuleEngine
from knowledge.service import get_knowledge_base
from obd.elm327 import ELM327Client
from obd.protocol import PID_DEFINITIONS
from obd.transport import PortInfo, SerialELM327Transport, available_serial_ports
from reports.pdf_report import PDFReportGenerator
from simulator.scenarios import VehicleSimulator
from vehicle.models import AIAnalysis, DTCRecord, DiagnosticSession, PIDValue, VehicleProfile

log = logging.getLogger("automind.controller")


DEFAULT_LIVE_PIDS = ["04", "05", "06", "07", "0B", "0C", "0D", "0F", "10", "11", "14", "1F", "2F", "42", "46"]


class AutoMindController:
    def __init__(self, config: ConfigManager | None = None, db: DatabaseRepository | None = None) -> None:
        self.config = config or ConfigManager()
        self.db = db or DatabaseRepository()
        self.events = EventBus()
        self.rules = DiagnosticRuleEngine()
        self.kb = get_knowledge_base()
        self.reporter = PDFReportGenerator()
        self.simulator: VehicleSimulator | None = None
        self.elm: ELM327Client | None = None
        self.current_vehicle: VehicleProfile | None = None
        self.current_session: DiagnosticSession | None = None
        self.connection_state = "Vehicle Disconnected"
        self.adapter_state = "Adapter Disconnected"
        self.ai_state = "AI Offline"

    @property
    def mode(self) -> str:
        if self.simulator:
            return "simulation"
        if self.elm and self.elm.connected:
            return "real"
        return "disconnected"

    def list_ports(self) -> list[PortInfo]:
        ports = available_serial_ports()
        log.info("Hardware detection: %d serial ports found", len(ports))
        return ports

    def start_simulation(self, scenario_key: str) -> DiagnosticSession:
        self.disconnect()
        self.simulator = VehicleSimulator(scenario_key)
        self.current_vehicle = self.simulator.vehicle_profile()
        self.db.save_vehicle(self.current_vehicle)
        self.current_session = DiagnosticSession(
            vehicle_id=self.current_vehicle.id,
            adapter="Built-in Vehicle Simulator",
            connection_mode="simulation",
            scenario=self.simulator.scenario.name,
        )
        self.connection_state = "SIMULATION MODE"
        self.adapter_state = "Simulator Active"
        self.config.set("general", "simulation_mode", True)
        self._persist_session(self.current_session)
        self.refresh_live_data()
        self.scan_diagnostics()
        self.events.publish("connection_changed", self.status_snapshot())
        log.info("Simulation started: %s", self.simulator.scenario.name)
        return self.current_session

    def connect_real(self, port: str, baud_rate: int | None = None) -> dict[str, str]:
        self.disconnect()
        baud = int(baud_rate or self.config.get("obd", "baud_rate", 38400))
        timeout = float(self.config.get("obd", "timeout_seconds", 2.0))
        transport = SerialELM327Transport(port, baud, timeout)
        elm = ELM327Client(transport)
        self.adapter_state = "Connecting..."
        self.connection_state = "Vehicle Disconnected"
        try:
            info = elm.connect()
            vin = elm.read_vin()
            try:
                calibration_id = elm.read_calibration_id()
            except Exception:
                calibration_id = ""
            try:
                ecu_name = elm.read_ecu_name()
            except Exception:
                ecu_name = ""
        except Exception:
            self.adapter_state = "Adapter Disconnected"
            self.connection_state = "ECU Communication Error"
            self.events.publish("connection_changed", self.status_snapshot())
            raise
        self.elm = elm
        self.current_vehicle = self.db.get_vehicle_by_vin(vin) if vin else None
        if self.current_vehicle is None:
            self.current_vehicle = VehicleProfile(vin=vin)
        self.db.save_vehicle(self.current_vehicle)
        self.current_session = DiagnosticSession(
            vehicle_id=self.current_vehicle.id,
            adapter=f"{info.identity} on {port}".strip(),
            connection_mode="real",
            scenario="",
        )
        self.adapter_state = "Adapter Connected"
        self.connection_state = "Vehicle Connected"
        self.config.set("general", "simulation_mode", False)
        self.config.set("obd", "serial_port", port)
        self._persist_session(self.current_session)
        self.events.publish("connection_changed", self.status_snapshot())
        log.info("ELM327 connected on %s; protocol=%s", port, info.protocol)
        return {
            "identity": info.identity,
            "protocol": info.protocol,
            "voltage": info.voltage,
            "vin": vin,
            "calibration_id": calibration_id,
            "ecu_name": ecu_name,
            "supported_pid_count": str(len(elm.supported_pids)),
        }

    def reconnect_real(self) -> dict[str, str]:
        port = str(self.config.get("obd", "serial_port", "")).strip()
        if not port:
            raise RuntimeError("No previous OBD serial port is saved. Select an adapter and connect once first.")
        baud = int(self.config.get("obd", "baud_rate", 38400))
        return self.connect_real(port, baud)

    def disconnect(self) -> None:
        if self.elm:
            try:
                self.elm.disconnect()
            except Exception as exc:
                log.warning("Error while disconnecting ELM327: %s", exc)
        # Only active simulator/ELM sessions receive a new end timestamp.
        # Viewing a historical session must never mutate its original record.
        if self.current_session and (self.simulator is not None or self.elm is not None):
            self.current_session.ended_at = datetime.now(timezone.utc).isoformat()
            try:
                self._persist_session(self.current_session)
            except Exception as exc:
                log.error("Could not save session during disconnect: %s", exc)
        self.elm = None
        self.simulator = None
        self.connection_state = "Vehicle Disconnected"
        self.adapter_state = "Adapter Disconnected"
        self.events.publish("connection_changed", self.status_snapshot())

    def refresh_live_data(self, pids: Iterable[str] | None = None) -> dict[str, PIDValue]:
        if not self.current_session:
            return {}
        if self.simulator:
            values = self.simulator.read_live_data()
            if pids:
                normalized = {p.upper() if p.upper().startswith("01") else "01" + p.upper() for p in pids}
                values = {k: v for k, v in values.items() if k in normalized}
        elif self.elm and self.elm.connected:
            requested = list(pids or DEFAULT_LIVE_PIDS)
            try:
                values = self.elm.read_live_data(requested)
            except Exception:
                self.connection_state = "ECU Communication Error"
                self.events.publish("connection_changed", self.status_snapshot())
                raise
        else:
            return {}
        self.current_session.live_data.update(values)
        self.current_session.health_status = self.rules.health_status(self.current_session.dtcs, self.current_session.live_data)
        if self.config.get("diagnostics", "auto_save_sessions", True):
            try:
                self.db.add_live_snapshot(self.current_session.id, values)
            except Exception as exc:
                log.warning("Could not persist live-data snapshot: %s", exc)
        self.events.publish("live_data", self.current_session.live_data)
        return values

    def scan_diagnostics(self) -> list[DTCRecord]:
        if not self.current_session:
            raise RuntimeError("No active diagnostic session.")
        code_status: list[tuple[str, str]] = []
        freeze_frame: dict[str, object] = {}
        if self.simulator:
            code_status = self.simulator.read_dtcs()
            freeze_frame = self.simulator.read_freeze_frame()
        elif self.elm and self.elm.connected:
            for code in self.elm.read_stored_dtcs():
                code_status.append((code, "Stored"))
            for code in self.elm.read_pending_dtcs():
                code_status.append((code, "Pending"))
            try:
                for code in self.elm.read_permanent_dtcs():
                    code_status.append((code, "Permanent"))
            except Exception as exc:
                log.info("Permanent DTC query not supported: %s", exc)
            related = set(DEFAULT_LIVE_PIDS)
            try:
                freeze_values = self.elm.read_freeze_frame(related)
                freeze_frame = {
                    pid: {"value": p.value, "unit": p.unit, "name": p.name}
                    for pid, p in freeze_values.items() if p.supported and p.value is not None
                }
            except Exception as exc:
                log.info("Freeze-frame read unavailable: %s", exc)
        else:
            raise RuntimeError("Vehicle is not connected and Simulation Mode is not active.")

        unique: list[tuple[str, str]] = []
        seen = set()
        for code, status in code_status:
            key = (code, status)
            if key not in seen:
                seen.add(key)
                unique.append(key)
        records = self.rules.enrich_dtcs(unique)
        self.current_session.freeze_frame = freeze_frame
        self.current_session.dtcs = self.rules.attach_freeze_frame(records, freeze_frame)
        self.refresh_live_data()
        self.current_session.findings = self.rules.analyze(self.current_session.dtcs, self.current_session.live_data)
        self.current_session.health_status = self.rules.health_status(self.current_session.dtcs, self.current_session.live_data)
        self._persist_session(self.current_session)
        self.events.publish("diagnostics", self.current_session)
        log.info("Diagnostic scan complete: %d DTC(s)", len(records))
        return records

    def ai_analysis(self, question: str) -> AIAnalysis:
        if not self.current_session:
            raise RuntimeError("No active diagnostic session.")
        enabled = bool(self.config.get("ai", "enabled", False))
        allowed = bool(self.config.get("ai", "cloud_analysis_allowed", False))
        if not (enabled and allowed):
            self.ai_state = "AI Offline"
            raise AIProviderError("Cloud AI analysis is disabled in Settings. Local diagnostic analysis remains available.")
        endpoint = str(self.config.get("ai", "backend_url", "")).strip()
        provider = BackendAIProvider(
            endpoint=endpoint,
            token_env=str(self.config.get("ai", "client_token_env", "AUTOMIND_CLIENT_TOKEN")),
            timeout_seconds=int(self.config.get("ai", "timeout_seconds", 30)),
        )
        service = AIService(provider)
        include_vin = bool(self.config.get("ai", "send_vin", False))
        include_user_notes = bool(self.config.get("ai", "send_session_notes", False))
        historical_faults: list[dict[str, object]] = []
        if self.current_session.vehicle_id:
            try:
                history = self.db.list_sessions_for_vehicle(self.current_session.vehicle_id, limit=6)
                for previous in history:
                    if previous.id == self.current_session.id:
                        continue
                    historical_faults.append({
                        "started_at": previous.started_at,
                        "health_status": previous.health_status,
                        "connection_mode": previous.connection_mode,
                        "dtcs": [{"code": d.code, "status": d.status} for d in previous.dtcs],
                    })
            except Exception as exc:
                log.warning("Could not load historical fault context for AI: %s", exc)
        self.ai_state = "AI Connecting"
        self.events.publish("connection_changed", self.status_snapshot())
        log.info(
            "AI analysis request: session=%s provider=%s question_chars=%d vin_included=%s",
            self.current_session.id,
            provider.name,
            len(question),
            include_vin,
        )
        try:
            analysis = service.analyze(
                self.current_session,
                self.current_vehicle,
                question,
                include_vin=include_vin,
                include_user_notes=include_user_notes,
                historical_faults=historical_faults,
            )
        except Exception as exc:
            self.ai_state = "AI Offline"
            self.events.publish("connection_changed", self.status_snapshot())
            log.warning("AI analysis failed: session=%s error=%s", self.current_session.id, type(exc).__name__)
            raise
        self.ai_state = "AI Online"
        self.events.publish("connection_changed", self.status_snapshot())
        self.current_session.ai_analysis = analysis
        self._persist_session(self.current_session)
        self.events.publish("ai_analysis", analysis)
        return analysis

    def local_answer(self, question: str) -> str:
        if not self.current_session:
            return "No active diagnostic session. Connect a vehicle or start Simulation Mode first."
        if not self.current_session.findings:
            self.scan_diagnostics()
        lines = ["LOCAL DIAGNOSTIC ANALYSIS", "", "Confirmed / observed data:"]
        if self.current_session.dtcs:
            for d in self.current_session.dtcs:
                lines.append(f"- {d.code} ({d.status}): {d.description}")
        else:
            lines.append("- No stored OBD-II DTCs detected in the current scan.")
        for pid in ("010C", "0105", "0142", "0106", "0107", "0110"):
            v = self.current_session.live_data.get(pid)
            if v and v.supported and v.value is not None:
                lines.append(f"- {v.name}: {v.value} {v.unit}".rstrip())
        lines += ["", "Possible diagnostic causes (not confirmed):"]
        causes: list[str] = []
        for finding in self.current_session.findings:
            for cause in finding.possible_causes[:3]:
                text = cause.get("cause", "")
                if text and text not in causes:
                    causes.append(text)
        if causes:
            lines.extend(f"- {c}" for c in causes[:8])
        else:
            lines.append("- No specific cause is inferred from the current data.")
        lines += ["", "Recommended diagnostic sequence:"]
        steps: list[str] = []
        for finding in self.current_session.findings:
            for step in finding.recommended_steps:
                if step not in steps:
                    steps.append(step)
        lines.extend(f"{i}. {s}" for i, s in enumerate(steps[:8], 1))
        if question.strip():
            lines += ["", f"Question context: {question.strip()}", "Cloud AI is optional; this answer comes from AutoMind's deterministic local rules and current session data."]
        return "\n".join(lines)

    def generate_report(self, output_path: Path | None = None) -> Path:
        if not self.current_session:
            raise RuntimeError("No active diagnostic session.")
        self._persist_session(self.current_session)
        path = self.reporter.generate(
            self.current_session, self.current_vehicle, output_path,
            units=str(self.config.get("general", "units", "metric")),
            include_vin=bool(self.config.get("privacy", "include_vin_in_reports", True)),
        )
        self.db.register_report(self.current_session.id, str(path))
        self.events.publish("report_generated", str(path))
        log.info("PDF report generated: %s", path)
        return path

    def save_notes(self, notes: str) -> None:
        if not self.current_session:
            return
        self.current_session.user_notes = notes
        self._persist_session(self.current_session)

    def _persist_session(self, session: DiagnosticSession) -> None:
        """Persist session state while enforcing local AI-history privacy settings."""
        store_ai = bool(self.config.get("privacy", "store_ai_results", True))
        if session.ai_analysis is not None and not store_ai:
            self.db.save_session(replace(session, ai_analysis=None))
        else:
            self.db.save_session(session)

    def status_snapshot(self) -> dict[str, str]:
        return {
            "vehicle": self.connection_state,
            "adapter": self.adapter_state,
            "ai": self.ai_state,
            "mode": self.mode,
        }

    def supported_pid_rows(self) -> list[tuple[str, str, str]]:
        rows = []
        for pid, definition in PID_DEFINITIONS.items():
            rows.append((f"01{pid}", definition.name, definition.unit))
        return rows

    def open_logs_folder(self) -> None:
        self._open_path(ensure_directories().logs)

    def open_reports_folder(self) -> None:
        self._open_path(ensure_directories().reports)

    def open_report_file(self, path: str | Path) -> None:
        target = Path(path)
        if not target.exists():
            raise FileNotFoundError(f"Report file no longer exists: {target}")
        self._open_path(target)

    @staticmethod
    def _open_path(path: Path) -> None:
        if path.suffix == "":
            path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif os.name == "posix":
            try:
                subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                pass
