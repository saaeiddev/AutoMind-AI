from diagnostics.rules import DiagnosticRuleEngine
from reports.pdf_report import PDFReportGenerator
from simulator.scenarios import VehicleSimulator
from vehicle.models import DiagnosticSession


def test_pdf_report_generation(tmp_path):
    sim = VehicleSimulator("misfire")
    vehicle = sim.vehicle_profile()
    engine = DiagnosticRuleEngine()
    dtcs = engine.enrich_dtcs(sim.read_dtcs())
    live = sim.read_live_data()
    session = DiagnosticSession(vehicle_id=vehicle.id, connection_mode="simulation", scenario=sim.scenario.name)
    session.dtcs = engine.attach_freeze_frame(dtcs, sim.read_freeze_frame())
    session.live_data = live
    session.freeze_frame = sim.read_freeze_frame()
    session.findings = engine.analyze(session.dtcs, live)
    session.health_status = engine.health_status(session.dtcs, live)
    path = PDFReportGenerator().generate(session, vehicle, tmp_path / "report.pdf")
    assert path.exists()
    assert path.read_bytes().startswith(b"%PDF")
    assert path.stat().st_size > 3000
