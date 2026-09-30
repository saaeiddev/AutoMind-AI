from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Iterator

from core.paths import ensure_directories
from vehicle.models import AIAnalysis, DTCRecord, DiagnosticFinding, DiagnosticSession, PIDValue, VehicleProfile


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS vehicle_profiles (
    id TEXT PRIMARY KEY,
    manufacturer TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER,
    engine TEXT,
    fuel_type TEXT,
    vin TEXT,
    mileage REAL,
    notes TEXT,
    image_path TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS diagnostic_sessions (
    id TEXT PRIMARY KEY,
    vehicle_id TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    adapter TEXT,
    connection_mode TEXT NOT NULL,
    scenario TEXT,
    dtcs_json TEXT NOT NULL,
    live_data_json TEXT NOT NULL,
    freeze_frame_json TEXT NOT NULL,
    findings_json TEXT NOT NULL,
    ai_analysis_json TEXT,
    user_notes TEXT,
    health_status TEXT,
    FOREIGN KEY(vehicle_id) REFERENCES vehicle_profiles(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON diagnostic_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_vehicle ON diagnostic_sessions(vehicle_id);
CREATE TABLE IF NOT EXISTS live_data_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_json TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES diagnostic_sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_live_snapshots_session ON live_data_snapshots(session_id, captured_at);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES diagnostic_sessions(id) ON DELETE CASCADE
);
"""


class DatabaseRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or ensure_directories().database
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self.initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._lock, self._connect() as con:
            con.executescript(SCHEMA)

    def save_vehicle(self, vehicle: VehicleProfile) -> None:
        with self._lock, self._connect() as con:
            con.execute(
                """INSERT INTO vehicle_profiles
                (id, manufacturer, model, year, engine, fuel_type, vin, mileage, notes, image_path, created_at)
                VALUES (:id,:manufacturer,:model,:year,:engine,:fuel_type,:vin,:mileage,:notes,:image_path,:created_at)
                ON CONFLICT(id) DO UPDATE SET
                    manufacturer=excluded.manufacturer,
                    model=excluded.model,
                    year=excluded.year,
                    engine=excluded.engine,
                    fuel_type=excluded.fuel_type,
                    vin=excluded.vin,
                    mileage=excluded.mileage,
                    notes=excluded.notes,
                    image_path=excluded.image_path""",
                vehicle.to_dict(),
            )

    def delete_vehicle(self, vehicle_id: str) -> None:
        with self._lock, self._connect() as con:
            con.execute("DELETE FROM vehicle_profiles WHERE id=?", (vehicle_id,))

    def list_vehicles(self) -> list[VehicleProfile]:
        with self._lock, self._connect() as con:
            rows = con.execute("SELECT * FROM vehicle_profiles ORDER BY created_at DESC").fetchall()
        return [VehicleProfile(**dict(row)) for row in rows]

    def get_vehicle(self, vehicle_id: str) -> VehicleProfile | None:
        with self._lock, self._connect() as con:
            row = con.execute("SELECT * FROM vehicle_profiles WHERE id=?", (vehicle_id,)).fetchone()
        return VehicleProfile(**dict(row)) if row else None

    def get_vehicle_by_vin(self, vin: str) -> VehicleProfile | None:
        vin = vin.strip()
        if not vin:
            return None
        with self._lock, self._connect() as con:
            row = con.execute(
                "SELECT * FROM vehicle_profiles WHERE UPPER(vin)=UPPER(?) ORDER BY created_at DESC LIMIT 1",
                (vin,),
            ).fetchone()
        return VehicleProfile(**dict(row)) if row else None

    def save_session(self, session: DiagnosticSession) -> None:
        payload = session.to_dict()
        with self._lock, self._connect() as con:
            con.execute(
                """INSERT INTO diagnostic_sessions
                (id, vehicle_id, started_at, ended_at, adapter, connection_mode, scenario,
                 dtcs_json, live_data_json, freeze_frame_json, findings_json, ai_analysis_json,
                 user_notes, health_status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                  ended_at=excluded.ended_at,
                  adapter=excluded.adapter,
                  connection_mode=excluded.connection_mode,
                  scenario=excluded.scenario,
                  dtcs_json=excluded.dtcs_json,
                  live_data_json=excluded.live_data_json,
                  freeze_frame_json=excluded.freeze_frame_json,
                  findings_json=excluded.findings_json,
                  ai_analysis_json=excluded.ai_analysis_json,
                  user_notes=excluded.user_notes,
                  health_status=excluded.health_status""",
                (
                    session.id,
                    session.vehicle_id or None,
                    session.started_at,
                    session.ended_at,
                    session.adapter,
                    session.connection_mode,
                    session.scenario,
                    json.dumps(payload["dtcs"]),
                    json.dumps(payload["live_data"]),
                    json.dumps(payload["freeze_frame"]),
                    json.dumps(payload["findings"]),
                    json.dumps(payload["ai_analysis"]) if payload["ai_analysis"] else None,
                    session.user_notes,
                    session.health_status,
                ),
            )

    def list_sessions(self, limit: int = 100) -> list[DiagnosticSession]:
        with self._lock, self._connect() as con:
            rows = con.execute(
                "SELECT * FROM diagnostic_sessions ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._session_from_row(row) for row in rows]

    def get_session(self, session_id: str) -> DiagnosticSession | None:
        with self._lock, self._connect() as con:
            row = con.execute("SELECT * FROM diagnostic_sessions WHERE id=?", (session_id,)).fetchone()
        return self._session_from_row(row) if row else None

    def list_sessions_for_vehicle(self, vehicle_id: str, limit: int = 20) -> list[DiagnosticSession]:
        if not vehicle_id:
            return []
        with self._lock, self._connect() as con:
            rows = con.execute(
                "SELECT * FROM diagnostic_sessions WHERE vehicle_id=? ORDER BY started_at DESC LIMIT ?",
                (vehicle_id, limit),
            ).fetchall()
        return [self._session_from_row(row) for row in rows]

    def add_live_snapshot(self, session_id: str, values: dict[str, PIDValue]) -> None:
        if not values:
            return
        payload = {k: v.to_dict() for k, v in values.items()}
        with self._lock, self._connect() as con:
            con.execute(
                "INSERT INTO live_data_snapshots (session_id, data_json) VALUES (?,?)",
                (session_id, json.dumps(payload)),
            )

    def list_live_snapshots(self, session_id: str, limit: int = 500) -> list[dict[str, object]]:
        with self._lock, self._connect() as con:
            rows = con.execute(
                "SELECT captured_at, data_json FROM live_data_snapshots WHERE session_id=? "
                "ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [
            {
                "captured_at": row["captured_at"],
                "values": {k: PIDValue(**v) for k, v in json.loads(row["data_json"]).items()},
            }
            for row in reversed(rows)
        ]

    def register_report(self, session_id: str, path: str) -> None:
        with self._lock, self._connect() as con:
            con.execute("INSERT INTO reports (session_id, path) VALUES (?,?)", (session_id, path))

    def list_reports(self, session_id: str | None = None, limit: int = 100) -> list[dict[str, object]]:
        with self._lock, self._connect() as con:
            if session_id:
                rows = con.execute(
                    "SELECT id, session_id, path, created_at FROM reports WHERE session_id=? "
                    "ORDER BY id DESC LIMIT ?",
                    (session_id, limit),
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT id, session_id, path, created_at FROM reports ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _session_from_row(row: sqlite3.Row) -> DiagnosticSession:
        dtcs = [DTCRecord(**d) for d in json.loads(row["dtcs_json"])]
        live_data = {k: PIDValue(**v) for k, v in json.loads(row["live_data_json"]).items()}
        findings = [DiagnosticFinding(**f) for f in json.loads(row["findings_json"])]
        ai_raw = json.loads(row["ai_analysis_json"]) if row["ai_analysis_json"] else None
        ai_analysis = AIAnalysis(**ai_raw) if ai_raw else None
        return DiagnosticSession(
            id=row["id"],
            vehicle_id=row["vehicle_id"] or "",
            started_at=row["started_at"],
            ended_at=row["ended_at"] or "",
            adapter=row["adapter"] or "",
            connection_mode=row["connection_mode"],
            scenario=row["scenario"] or "",
            dtcs=dtcs,
            live_data=live_data,
            freeze_frame=json.loads(row["freeze_frame_json"]),
            findings=findings,
            ai_analysis=ai_analysis,
            user_notes=row["user_notes"] or "",
            health_status=row["health_status"] or "Unknown",
        )
