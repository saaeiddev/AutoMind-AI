from database.repository import DatabaseRepository
from vehicle.models import DiagnosticSession, VehicleProfile


def test_vehicle_and_session_roundtrip(tmp_path):
    db = DatabaseRepository(tmp_path / "test.db")
    vehicle = VehicleProfile(manufacturer="Test", model="Car", year=2025, vin="TESTVIN123")
    db.save_vehicle(vehicle)
    loaded = db.get_vehicle(vehicle.id)
    assert loaded and loaded.vin == "TESTVIN123"
    session = DiagnosticSession(vehicle_id=vehicle.id, connection_mode="simulation", scenario="Healthy")
    db.save_session(session)
    loaded_session = db.get_session(session.id)
    assert loaded_session and loaded_session.vehicle_id == vehicle.id


def test_delete_vehicle_keeps_session(tmp_path):
    db = DatabaseRepository(tmp_path / "test.db")
    v = VehicleProfile(manufacturer="A", model="B")
    db.save_vehicle(v)
    s = DiagnosticSession(vehicle_id=v.id)
    db.save_session(s)
    db.delete_vehicle(v.id)
    loaded = db.get_session(s.id)
    assert loaded and loaded.vehicle_id == ""


def test_live_snapshot_roundtrip(tmp_path):
    from vehicle.models import PIDValue

    db = DatabaseRepository(tmp_path / "test.db")
    vehicle = VehicleProfile(manufacturer="Test", model="Car")
    db.save_vehicle(vehicle)
    session = DiagnosticSession(vehicle_id=vehicle.id, connection_mode="simulation")
    db.save_session(session)
    db.add_live_snapshot(session.id, {"010C": PIDValue(pid="010C", name="Engine RPM", value=812, unit="rpm")})
    rows = db.list_live_snapshots(session.id)
    assert len(rows) == 1
    assert rows[0]["values"]["010C"].value == 812


def test_vehicle_lookup_by_vin_is_case_insensitive(tmp_path):
    db = DatabaseRepository(tmp_path / "test.db")
    vehicle = VehicleProfile(manufacturer="Test", model="Car", vin="abc123vin")
    db.save_vehicle(vehicle)
    loaded = db.get_vehicle_by_vin("ABC123VIN")
    assert loaded and loaded.id == vehicle.id


def test_report_registry_roundtrip(tmp_path):
    db = DatabaseRepository(tmp_path / "test.db")
    vehicle = VehicleProfile(manufacturer="Test", model="Car")
    db.save_vehicle(vehicle)
    session = DiagnosticSession(vehicle_id=vehicle.id)
    db.save_session(session)
    db.register_report(session.id, "C:/Reports/report.pdf")
    reports = db.list_reports(session.id)
    assert len(reports) == 1
    assert reports[0]["session_id"] == session.id
    assert reports[0]["path"] == "C:/Reports/report.pdf"


def test_list_sessions_for_vehicle_filters_other_vehicles(tmp_path):
    db = DatabaseRepository(tmp_path / "test.db")
    first = VehicleProfile(manufacturer="A", model="One")
    second = VehicleProfile(manufacturer="B", model="Two")
    db.save_vehicle(first); db.save_vehicle(second)
    s1 = DiagnosticSession(vehicle_id=first.id, scenario="First")
    s2 = DiagnosticSession(vehicle_id=second.id, scenario="Second")
    db.save_session(s1); db.save_session(s2)
    rows = db.list_sessions_for_vehicle(first.id)
    assert [s.id for s in rows] == [s1.id]
