from __future__ import annotations

import math
import random
import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from vehicle.models import PIDValue, VehicleProfile


@dataclass(frozen=True)
class SimulationScenario:
    key: str
    name: str
    vehicle: dict[str, Any]
    dtcs: list[tuple[str, str]]
    base: dict[str, tuple[float, float, str, str]]
    freeze_frame: dict[str, float]
    health_note: str


def _base_engine() -> dict[str, tuple[float, float, str, str]]:
    # pid: (base, noise amplitude, unit, display name)
    return {
        "010C": (780, 45, "rpm", "Engine RPM"),
        "010D": (0, 0, "km/h", "Vehicle Speed"),
        "0105": (90, 1.5, "°C", "Engine Coolant Temperature"),
        "010F": (30, 1.0, "°C", "Intake Air Temperature"),
        "0104": (24, 3.0, "%", "Calculated Engine Load"),
        "0111": (13, 1.5, "%", "Throttle Position"),
        "0110": (3.4, 0.35, "g/s", "MAF Air Flow Rate"),
        "010B": (34, 2.0, "kPa", "Intake Manifold Absolute Pressure"),
        "0106": (1.5, 1.8, "%", "Short-Term Fuel Trim Bank 1"),
        "0107": (2.0, 0.4, "%", "Long-Term Fuel Trim Bank 1"),
        "0114": (0.55, 0.35, "V", "O2 Sensor 1 Voltage"),
        "0142": (14.1, 0.12, "V", "Control Module Voltage"),
        "010E": (10, 2.0, "°", "Ignition Timing Advance"),
        "0146": (24, 0.3, "°C", "Ambient Air Temperature"),
        "012F": (58, 0.05, "%", "Fuel Tank Level Input"),
        "011F": (900, 1, "s", "Run Time Since Engine Start"),
    }


def _scenario(key: str, name: str, dtcs: list[tuple[str, str]], mods: dict[str, tuple[float, float, str, str]], freeze: dict[str, float], note: str) -> SimulationScenario:
    base = _base_engine()
    base.update(mods)
    return SimulationScenario(
        key=key,
        name=name,
        vehicle={"manufacturer": "AutoMind Demo", "model": "Diagnostics Lab", "year": 2024, "engine": "2.0L I4", "fuel_type": "Gasoline", "vin": "SIMULATEDVIN000001"},
        dtcs=dtcs,
        base=base,
        freeze_frame=freeze,
        health_note=note,
    )


SCENARIOS: dict[str, SimulationScenario] = {
    "healthy": _scenario("healthy", "Healthy Vehicle", [], {}, {"010C": 760, "0105": 89, "0142": 14.2}, "No OBD faults are simulated."),
    "misfire": _scenario("misfire", "Cylinder 2 Misfire", [("P0302", "Stored")], {
        "010C": (690, 120, "rpm", "Engine RPM"), "0104": (34, 8, "%", "Calculated Engine Load"), "0106": (8, 5, "%", "Short-Term Fuel Trim Bank 1")
    }, {"010C": 1420, "0105": 88, "0106": 10.2, "0107": 4.1, "0110": 8.8}, "Cylinder-specific misfire demonstration."),
    "rich": _scenario("rich", "Rich Fuel Mixture", [("P0172", "Stored")], {
        "0106": (-18, 4, "%", "Short-Term Fuel Trim Bank 1"), "0107": (-14, 1.0, "%", "Long-Term Fuel Trim Bank 1"), "0114": (0.85, 0.08, "V", "O2 Sensor 1 Voltage")
    }, {"010C": 820, "0106": -20.3, "0107": -13.1, "0110": 4.1}, "Rich-mixture diagnostic demonstration."),
    "lean": _scenario("lean", "Lean Fuel Mixture", [("P0171", "Stored")], {
        "0106": (18, 5, "%", "Short-Term Fuel Trim Bank 1"), "0107": (16, 1.5, "%", "Long-Term Fuel Trim Bank 1"), "0114": (0.2, 0.12, "V", "O2 Sensor 1 Voltage"), "010B": (40, 3, "kPa", "Intake Manifold Absolute Pressure")
    }, {"010C": 790, "0106": 22.7, "0107": 15.4, "0110": 2.6, "010B": 41}, "Lean-mixture diagnostic demonstration."),
    "overheat": _scenario("overheat", "Engine Overheating", [("P0117", "Pending")], {
        "0105": (121, 3, "°C", "Engine Coolant Temperature"), "0104": (38, 5, "%", "Calculated Engine Load")
    }, {"010C": 1050, "0105": 119, "0146": 31}, "High-coolant-temperature demonstration; not real vehicle data."),
    "battery": _scenario("battery", "Weak Battery / Charging Problem", [("P0562", "Stored")], {
        "0142": (11.35, 0.25, "V", "Control Module Voltage"), "010C": (720, 65, "rpm", "Engine RPM")
    }, {"010C": 735, "0142": 11.1, "0105": 82}, "Low-system-voltage demonstration."),
    "oxygen": _scenario("oxygen", "Oxygen Sensor Fault", [("P0130", "Stored")], {
        "0114": (0.45, 0.01, "V", "O2 Sensor 1 Voltage"), "0106": (10, 2.5, "%", "Short-Term Fuel Trim Bank 1")
    }, {"010C": 820, "0114": 0.45, "0106": 11.0}, "Upstream O2 circuit/fueling interaction demonstration."),
    "maf": _scenario("maf", "MAF Sensor Fault", [("P0101", "Stored")], {
        "0110": (0.65, 0.12, "g/s", "MAF Air Flow Rate"), "0106": (14, 4, "%", "Short-Term Fuel Trim Bank 1")
    }, {"010C": 910, "0110": 0.7, "0106": 15.3}, "MAF range/performance demonstration."),
    "catalyst": _scenario("catalyst", "Catalyst Efficiency Fault", [("P0420", "Stored")], {
        "0114": (0.62, 0.25, "V", "O2 Sensor 1 Voltage")
    }, {"010C": 1820, "0105": 92, "0114": 0.7}, "Catalyst-efficiency demonstration."),
    "multi_misfire": _scenario("multi_misfire", "Random Multiple Misfire", [("P0300", "Stored"), ("P0171", "Pending")], {
        "010C": (640, 180, "rpm", "Engine RPM"), "0106": (20, 6, "%", "Short-Term Fuel Trim Bank 1"), "0107": (12, 1.5, "%", "Long-Term Fuel Trim Bank 1"), "0104": (42, 10, "%", "Calculated Engine Load")
    }, {"010C": 1680, "0106": 23.4, "0107": 11.8, "0110": 7.1}, "Combined lean/random-misfire demonstration."),
}


class VehicleSimulator:
    def __init__(self, scenario_key: str = "healthy", seed: int = 42) -> None:
        self._random = random.Random(seed)
        self.started_monotonic = time.monotonic()
        self.set_scenario(scenario_key)

    def set_scenario(self, scenario_key: str) -> None:
        if scenario_key not in SCENARIOS:
            raise KeyError(f"Unknown simulation scenario: {scenario_key}")
        self.scenario = SCENARIOS[scenario_key]
        self.started_monotonic = time.monotonic()

    def vehicle_profile(self) -> VehicleProfile:
        return VehicleProfile(**deepcopy(self.scenario.vehicle))

    def read_dtcs(self) -> list[tuple[str, str]]:
        return list(self.scenario.dtcs)

    def read_freeze_frame(self) -> dict[str, float]:
        return dict(self.scenario.freeze_frame)

    def read_live_data(self) -> dict[str, PIDValue]:
        elapsed = time.monotonic() - self.started_monotonic
        output: dict[str, PIDValue] = {}
        for pid, (base, amplitude, unit, name) in self.scenario.base.items():
            if pid == "011F":
                value = base + elapsed
            elif pid == "0114" and amplitude > 0.05:
                value = base + amplitude * math.sin(elapsed * 2.6)
            else:
                wobble = math.sin(elapsed * (0.55 + (sum(map(ord, pid)) % 7) * 0.07)) * amplitude * 0.55
                jitter = self._random.uniform(-amplitude, amplitude) * 0.18
                value = base + wobble + jitter
            output[pid] = PIDValue(pid=pid, name=name, value=round(max(0, value) if pid in {"010C", "010D", "0104", "0111", "0110", "010B", "012F", "011F"} else value, 2), unit=unit, supported=True)
        return output

    @staticmethod
    def scenario_names() -> list[tuple[str, str]]:
        return [(key, scenario.name) for key, scenario in SCENARIOS.items()]
