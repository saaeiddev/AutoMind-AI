from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

from knowledge.service import get_knowledge_base
from vehicle.models import DTCRecord, DiagnosticFinding, PIDValue


class DiagnosticRuleEngine:
    """Deterministic local diagnostic interpretation.

    Findings deliberately use "possible" language. A DTC or measured PID is evidence;
    a proposed mechanical cause is never promoted to confirmed diagnosis by this layer.
    """

    def __init__(self) -> None:
        self.kb = get_knowledge_base()

    def enrich_dtcs(self, codes: Iterable[tuple[str, str] | str]) -> list[DTCRecord]:
        records: list[DTCRecord] = []
        for item in codes:
            if isinstance(item, tuple):
                code, status = item
            else:
                code, status = item, "Stored"
            info = self.kb.dtc_info(code)
            records.append(DTCRecord(
                code=code.upper(),
                status=status,
                description=info.get("description", "Description unavailable"),
                subsystem=info.get("subsystem", "Unknown"),
                severity=info.get("severity", "Unknown"),
                possible_causes=list(info.get("causes", [])),
                symptoms=list(info.get("symptoms", [])),
                recommended_checks=list(info.get("checks", [])),
                related_pids=list(info.get("related_pids", [])),
            ))
        return records

    def attach_freeze_frame(self, records: list[DTCRecord], freeze_frame: dict[str, Any]) -> list[DTCRecord]:
        return [replace(r, freeze_frame=freeze_frame) for r in records]

    def analyze(self, dtcs: list[DTCRecord], live_data: dict[str, PIDValue]) -> list[DiagnosticFinding]:
        findings: list[DiagnosticFinding] = []
        by_code = {d.code: d for d in dtcs}
        values = {pid: v.value for pid, v in live_data.items() if v.supported and isinstance(v.value, (int, float))}

        if not dtcs:
            evidence = self._health_evidence(values)
            findings.append(DiagnosticFinding(
                title="No stored OBD-II faults detected",
                evidence=evidence or ["No stored DTCs are present in the current scan."],
                possible_causes=[],
                recommended_steps=[
                    "Continue monitoring live data if the vehicle has a symptom without a stored code.",
                    "Check pending codes and freeze-frame availability when appropriate.",
                ],
                confidence="High for code status; mechanical health cannot be confirmed from this alone.",
            ))
            return findings

        for dtc in dtcs:
            evidence = [f"{dtc.code} is reported as {dtc.status}: {dtc.description}."]
            ranked = [{"cause": c, "priority": "Possible", "reason": "Common cause for this DTC"} for c in dtc.possible_causes]
            steps = list(dtc.recommended_checks)
            warnings: list[str] = []

            if dtc.code.startswith("P030"):
                self._apply_misfire_context(ranked, evidence, steps, warnings, values, by_code)
            elif dtc.code == "P0171":
                self._apply_lean_context(ranked, evidence, steps, values)
            elif dtc.code == "P0172":
                self._apply_rich_context(ranked, evidence, steps, values)
            elif dtc.code == "P0562":
                self._apply_voltage_context(ranked, evidence, steps, warnings, values)
            elif dtc.code == "P0420":
                self._apply_catalyst_context(ranked, evidence, steps, by_code, values)
            elif dtc.code == "P0101":
                self._apply_maf_context(ranked, evidence, steps, values)
            elif dtc.code in ("P0117", "P0128"):
                self._apply_coolant_context(ranked, evidence, steps, values)

            findings.append(DiagnosticFinding(
                title=f"{dtc.code} - {dtc.description}",
                evidence=evidence,
                possible_causes=self._dedupe_causes(ranked),
                recommended_steps=self._dedupe(steps),
                confidence="Moderate: based on the reported DTC and available OBD-II measurements; confirm with vehicle-specific testing.",
                warnings=warnings,
            ))
        return findings

    @staticmethod
    def health_status(dtcs: list[DTCRecord], live_data: dict[str, PIDValue]) -> str:
        severities = {d.severity.lower() for d in dtcs}
        voltage = _num(live_data, "0142")
        coolant = _num(live_data, "0105")
        if "high" in severities or (voltage is not None and voltage < 11.8) or (coolant is not None and coolant > 115):
            return "Attention Required"
        if dtcs:
            return "Check Recommended"
        return "No OBD Faults Detected"

    def _apply_misfire_context(self, ranked, evidence, steps, warnings, values, by_code) -> None:
        stft, ltft = values.get("0106"), values.get("0107")
        if stft is not None and ltft is not None:
            evidence.append(f"Fuel trims: STFT {stft:.1f}%, LTFT {ltft:.1f}%.")
            if stft + ltft > 18:
                ranked.insert(0, {"cause": "Lean mixture / intake leak affecting combustion", "priority": "Higher", "reason": "Combined fuel trim is strongly positive."})
                steps.insert(0, "Check for intake/vacuum leaks and verify fuel delivery before replacing ignition parts at random.")
        if "P0171" in by_code:
            ranked.insert(0, {"cause": "Lean-condition related misfire", "priority": "Higher", "reason": "P0171 is present with the misfire code."})
        warnings.append("A severe active misfire can overheat and damage the catalytic converter. Avoid prolonged driving if the MIL is flashing or the engine runs very poorly.")

    def _apply_lean_context(self, ranked, evidence, steps, values) -> None:
        stft, ltft, maf, rpm, load = values.get("0106"), values.get("0107"), values.get("0110"), values.get("010C"), values.get("0104")
        if stft is not None: evidence.append(f"STFT is {stft:.1f}%.")
        if ltft is not None: evidence.append(f"LTFT is {ltft:.1f}%.")
        if stft is not None and ltft is not None and stft + ltft > 20:
            ranked.insert(0, {"cause": "Unmetered air or insufficient fuel delivery", "priority": "Higher", "reason": "Combined fuel trim is strongly positive."})
            steps.insert(0, "Compare fuel trims at idle versus 2500 RPM: a large improvement off-idle can support an intake/vacuum leak hypothesis.")
        if maf is not None and rpm is not None:
            evidence.append(f"MAF is {maf:.2f} g/s at {rpm:.0f} rpm.")
        if load is not None:
            evidence.append(f"Calculated engine load is {load:.1f}%.")

    def _apply_rich_context(self, ranked, evidence, steps, values) -> None:
        stft, ltft = values.get("0106"), values.get("0107")
        if stft is not None: evidence.append(f"STFT is {stft:.1f}%.")
        if ltft is not None: evidence.append(f"LTFT is {ltft:.1f}%.")
        if stft is not None and ltft is not None and stft + ltft < -18:
            ranked.insert(0, {"cause": "Excess fuel or over-reported airflow", "priority": "Higher", "reason": "Combined fuel trim is strongly negative."})
            steps.insert(0, "Check for injector leakage, excessive fuel pressure, and implausible MAF readings before replacing oxygen sensors.")

    def _apply_voltage_context(self, ranked, evidence, steps, warnings, values) -> None:
        voltage = values.get("0142")
        if voltage is not None:
            evidence.append(f"Control module voltage is {voltage:.2f} V.")
            if voltage < 12.0:
                ranked.insert(0, {"cause": "Low system voltage presently measured", "priority": "Higher", "reason": "The ECU-reported voltage is below 12.0 V."})
                steps.insert(0, "Measure battery voltage directly with a suitable meter and verify charging voltage with the engine running.")
        warnings.append("Low voltage can create multiple secondary fault codes. Diagnose the power/ground system before interpreting unrelated module faults.")

    def _apply_catalyst_context(self, ranked, evidence, steps, by_code, values) -> None:
        upstream = [c for c in by_code if c.startswith("P03") or c in {"P0171", "P0172", "P0130", "P0101"}]
        if upstream:
            evidence.append("Other engine/fueling codes are present: " + ", ".join(sorted(upstream)) + ".")
            ranked.insert(0, {"cause": "Upstream engine/fueling fault contributing to catalyst efficiency code", "priority": "Higher", "reason": "Related engine/fuel DTCs are present."})
            steps.insert(0, "Resolve active misfire/fueling faults first, then reassess P0420 after appropriate drive cycles.")
        coolant = values.get("0105")
        if coolant is not None:
            evidence.append(f"Coolant temperature is {coolant:.1f} °C at this snapshot.")

    def _apply_maf_context(self, ranked, evidence, steps, values) -> None:
        maf, rpm, throttle = values.get("0110"), values.get("010C"), values.get("0111")
        if maf is not None: evidence.append(f"MAF reports {maf:.2f} g/s.")
        if rpm is not None: evidence.append(f"Engine speed is {rpm:.0f} rpm.")
        if throttle is not None: evidence.append(f"Throttle position is {throttle:.1f}%.")
        if maf is not None and rpm is not None and rpm > 600 and maf < 1.0:
            ranked.insert(0, {"cause": "MAF signal implausibly low for a running engine", "priority": "Higher", "reason": "Measured airflow is below 1 g/s while RPM indicates the engine is running."})

    def _apply_coolant_context(self, ranked, evidence, steps, values) -> None:
        coolant, ambient, runtime = values.get("0105"), values.get("0146"), values.get("011F")
        if coolant is not None: evidence.append(f"Coolant temperature is {coolant:.1f} °C.")
        if ambient is not None: evidence.append(f"Ambient temperature is {ambient:.1f} °C.")
        if runtime is not None: evidence.append(f"Engine runtime is {runtime:.0f} s.")
        if coolant is not None and coolant > 115:
            steps.insert(0, "If the engine is actually overheating, stop operation safely and inspect the cooling system before continuing diagnosis.")

    @staticmethod
    def _health_evidence(values: dict[str, float]) -> list[str]:
        evidence: list[str] = []
        if "0142" in values: evidence.append(f"Control module voltage: {values['0142']:.2f} V.")
        if "0105" in values: evidence.append(f"Coolant temperature: {values['0105']:.1f} °C.")
        if "010C" in values: evidence.append(f"Engine speed: {values['010C']:.0f} rpm.")
        return evidence

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        out: list[str] = []
        for item in items:
            if item not in out:
                out.append(item)
        return out

    @staticmethod
    def _dedupe_causes(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in items:
            key = item.get("cause", "")
            if key and key not in seen:
                seen.add(key)
                out.append(item)
        return out


def _num(live_data: dict[str, PIDValue], pid: str) -> float | None:
    value = live_data.get(pid)
    if value and value.supported and isinstance(value.value, (int, float)):
        return float(value.value)
    return None
