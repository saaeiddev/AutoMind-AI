from simulator.scenarios import SCENARIOS, VehicleSimulator


def test_all_scenarios_emit_live_data():
    for key in SCENARIOS:
        sim = VehicleSimulator(key)
        values = sim.read_live_data()
        assert "010C" in values
        assert "0105" in values
        assert values["010C"].supported


def test_simulation_vehicle_is_labeled():
    sim = VehicleSimulator("healthy")
    profile = sim.vehicle_profile()
    assert profile.vin.startswith("SIMULATED")


def test_lean_scenario_has_expected_dtc():
    assert ("P0171", "Stored") in VehicleSimulator("lean").read_dtcs()
