from diagnostics.rules import DiagnosticRuleEngine
from simulator.scenarios import VehicleSimulator


def _finding_for(scenario: str):
    sim = VehicleSimulator(scenario)
    engine = DiagnosticRuleEngine()
    dtcs = engine.enrich_dtcs(sim.read_dtcs())
    live = sim.read_live_data()
    return engine.analyze(dtcs, live)


def test_lean_rule_uses_fuel_trim_evidence():
    findings = _finding_for("lean")
    assert findings
    text = " ".join(findings[0].evidence).lower()
    assert "stft" in text
    assert any("unmetered air" in c["cause"].lower() or "vacuum" in c["cause"].lower() for c in findings[0].possible_causes)


def test_misfire_has_catalyst_warning():
    findings = _finding_for("misfire")
    assert any("catalytic" in w.lower() for w in findings[0].warnings)


def test_health_status_for_weak_voltage():
    sim = VehicleSimulator("battery")
    engine = DiagnosticRuleEngine()
    dtcs = engine.enrich_dtcs(sim.read_dtcs())
    assert engine.health_status(dtcs, sim.read_live_data()) == "Attention Required"
