from app.controller import AutoMindController
from core.config import ConfigManager
from database.repository import DatabaseRepository
from vehicle.models import AIAnalysis


def test_simulation_controller_flow(tmp_path):
    c = AutoMindController(ConfigManager(tmp_path / "settings.json"), DatabaseRepository(tmp_path / "db.sqlite"))
    s = c.start_simulation("catalyst")
    assert c.mode == "simulation"
    assert s.dtcs[0].code == "P0420"
    assert c.local_answer("What should I test?")
    report = c.generate_report(tmp_path / "controller-report.pdf")
    assert report.exists()
    c.disconnect()


def test_disconnect_does_not_mutate_historical_session(tmp_path):
    c = AutoMindController(ConfigManager(tmp_path / "settings.json"), DatabaseRepository(tmp_path / "db.sqlite"))
    session = c.start_simulation("healthy")
    c.disconnect()
    original = c.db.get_session(session.id)
    assert original is not None
    ended_at = original.ended_at

    # Mimic the UI opening a saved historical session: no active transport/simulator.
    c.current_session = original
    c.simulator = None
    c.elm = None
    c.connection_state = "Historical Session"
    c.disconnect()

    reloaded = c.db.get_session(session.id)
    assert reloaded is not None
    assert reloaded.ended_at == ended_at


def test_reconnect_requires_saved_port(tmp_path):
    import pytest

    c = AutoMindController(ConfigManager(tmp_path / "settings.json"), DatabaseRepository(tmp_path / "db.sqlite"))
    with pytest.raises(RuntimeError, match="No previous OBD serial port"):
        c.reconnect_real()


def test_ai_result_not_persisted_when_history_storage_disabled(tmp_path):
    config = ConfigManager(tmp_path / "settings.json")
    config.set("privacy", "store_ai_results", False)
    c = AutoMindController(config, DatabaseRepository(tmp_path / "db.sqlite"))
    session = c.start_simulation("lean")
    session.ai_analysis = AIAnalysis(
        summary="Private cloud analysis",
        observed_evidence=["P0171"],
        possible_causes=["Vacuum leak"],
        recommended_steps=["Smoke test"],
        additional_measurements=[],
        confidence="Moderate",
        warnings=[],
        provider="Mock",
    )
    c.save_notes("Local note")
    loaded = c.db.get_session(session.id)
    assert loaded is not None
    assert loaded.user_notes == "Local note"
    assert loaded.ai_analysis is None
