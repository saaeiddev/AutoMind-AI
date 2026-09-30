from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable


HEX_RE = re.compile(r"[^0-9A-Fa-f]")


@dataclass(frozen=True)
class PIDDefinition:
    pid: str
    name: str
    unit: str
    bytes_required: int
    decoder: Callable[[list[int]], float]


def _a(b: list[int]) -> int:
    return b[0]


def _ab(b: list[int]) -> int:
    return (b[0] << 8) | b[1]


PID_DEFINITIONS: dict[str, PIDDefinition] = {
    "04": PIDDefinition("04", "Calculated Engine Load", "%", 1, lambda b: _a(b) * 100 / 255),
    "05": PIDDefinition("05", "Engine Coolant Temperature", "°C", 1, lambda b: _a(b) - 40),
    "06": PIDDefinition("06", "Short-Term Fuel Trim Bank 1", "%", 1, lambda b: (_a(b) - 128) * 100 / 128),
    "07": PIDDefinition("07", "Long-Term Fuel Trim Bank 1", "%", 1, lambda b: (_a(b) - 128) * 100 / 128),
    "08": PIDDefinition("08", "Short-Term Fuel Trim Bank 2", "%", 1, lambda b: (_a(b) - 128) * 100 / 128),
    "09": PIDDefinition("09", "Long-Term Fuel Trim Bank 2", "%", 1, lambda b: (_a(b) - 128) * 100 / 128),
    "0A": PIDDefinition("0A", "Fuel Pressure", "kPa", 1, lambda b: _a(b) * 3),
    "0B": PIDDefinition("0B", "Intake Manifold Absolute Pressure", "kPa", 1, lambda b: _a(b)),
    "0C": PIDDefinition("0C", "Engine RPM", "rpm", 2, lambda b: _ab(b) / 4),
    "0D": PIDDefinition("0D", "Vehicle Speed", "km/h", 1, lambda b: _a(b)),
    "0E": PIDDefinition("0E", "Ignition Timing Advance", "°", 1, lambda b: _a(b) / 2 - 64),
    "0F": PIDDefinition("0F", "Intake Air Temperature", "°C", 1, lambda b: _a(b) - 40),
    "10": PIDDefinition("10", "MAF Air Flow Rate", "g/s", 2, lambda b: _ab(b) / 100),
    "11": PIDDefinition("11", "Throttle Position", "%", 1, lambda b: _a(b) * 100 / 255),
    "14": PIDDefinition("14", "O2 Sensor 1 Voltage", "V", 2, lambda b: b[0] / 200),
    "15": PIDDefinition("15", "O2 Sensor 2 Voltage", "V", 2, lambda b: b[0] / 200),
    "16": PIDDefinition("16", "O2 Sensor 3 Voltage", "V", 2, lambda b: b[0] / 200),
    "17": PIDDefinition("17", "O2 Sensor 4 Voltage", "V", 2, lambda b: b[0] / 200),
    "18": PIDDefinition("18", "O2 Sensor 5 Voltage", "V", 2, lambda b: b[0] / 200),
    "19": PIDDefinition("19", "O2 Sensor 6 Voltage", "V", 2, lambda b: b[0] / 200),
    "1A": PIDDefinition("1A", "O2 Sensor 7 Voltage", "V", 2, lambda b: b[0] / 200),
    "1B": PIDDefinition("1B", "O2 Sensor 8 Voltage", "V", 2, lambda b: b[0] / 200),
    "1F": PIDDefinition("1F", "Run Time Since Engine Start", "s", 2, lambda b: _ab(b)),
    "21": PIDDefinition("21", "Distance Traveled With MIL On", "km", 2, lambda b: _ab(b)),
    "2C": PIDDefinition("2C", "Commanded EGR", "%", 1, lambda b: _a(b) * 100 / 255),
    "2E": PIDDefinition("2E", "Commanded Evaporative Purge", "%", 1, lambda b: _a(b) * 100 / 255),
    "30": PIDDefinition("30", "Warm-ups Since Codes Cleared", "count", 1, lambda b: _a(b)),
    "31": PIDDefinition("31", "Distance Since Codes Cleared", "km", 2, lambda b: _ab(b)),
    "33": PIDDefinition("33", "Barometric Pressure", "kPa", 1, lambda b: _a(b)),
    "3C": PIDDefinition("3C", "Catalyst Temperature Bank 1 Sensor 1", "°C", 2, lambda b: _ab(b) / 10 - 40),
    "3D": PIDDefinition("3D", "Catalyst Temperature Bank 2 Sensor 1", "°C", 2, lambda b: _ab(b) / 10 - 40),
    "3E": PIDDefinition("3E", "Catalyst Temperature Bank 1 Sensor 2", "°C", 2, lambda b: _ab(b) / 10 - 40),
    "3F": PIDDefinition("3F", "Catalyst Temperature Bank 2 Sensor 2", "°C", 2, lambda b: _ab(b) / 10 - 40),
    "2F": PIDDefinition("2F", "Fuel Tank Level Input", "%", 1, lambda b: _a(b) * 100 / 255),
    "42": PIDDefinition("42", "Control Module Voltage", "V", 2, lambda b: _ab(b) / 1000),
    "46": PIDDefinition("46", "Ambient Air Temperature", "°C", 1, lambda b: _a(b) - 40),
    "45": PIDDefinition("45", "Relative Throttle Position", "%", 1, lambda b: _a(b) * 100 / 255),
    "49": PIDDefinition("49", "Accelerator Pedal Position D", "%", 1, lambda b: _a(b) * 100 / 255),
    "4A": PIDDefinition("4A", "Accelerator Pedal Position E", "%", 1, lambda b: _a(b) * 100 / 255),
    "4B": PIDDefinition("4B", "Accelerator Pedal Position F", "%", 1, lambda b: _a(b) * 100 / 255),
    "4C": PIDDefinition("4C", "Commanded Throttle Actuator", "%", 1, lambda b: _a(b) * 100 / 255),
    "52": PIDDefinition("52", "Ethanol Fuel Percentage", "%", 1, lambda b: _a(b) * 100 / 255),
    "5A": PIDDefinition("5A", "Relative Accelerator Pedal Position", "%", 1, lambda b: _a(b) * 100 / 255),
    "5B": PIDDefinition("5B", "Hybrid Battery Pack Remaining Life", "%", 1, lambda b: _a(b) * 100 / 255),
    "5C": PIDDefinition("5C", "Engine Oil Temperature", "°C", 1, lambda b: _a(b) - 40),
    "5E": PIDDefinition("5E", "Engine Fuel Rate", "L/h", 2, lambda b: _ab(b) / 20),
}


def clean_response(response: str) -> list[str]:
    """Normalize an ELM327 response into uppercase hex-only data lines."""
    lines: list[str] = []
    for raw in response.replace("\r", "\n").split("\n"):
        line = raw.strip().upper()
        if not line or line == ">" or line.startswith("SEARCHING"):
            continue
        if any(token in line for token in ("NO DATA", "STOPPED", "UNABLE TO CONNECT", "ERROR")):
            lines.append(line)
            continue
        # Drop CAN headers when ELM headers accidentally remain enabled by retaining only byte-like tokens.
        tokens = re.findall(r"\b[0-9A-F]{2}\b", line)
        if not tokens:
            compact = HEX_RE.sub("", line)
            if len(compact) >= 4 and len(compact) % 2 == 0:
                tokens = [compact[i:i+2] for i in range(0, len(compact), 2)]
        if tokens:
            lines.append(" ".join(tokens))
    return lines


def extract_mode_payload(response: str, response_mode: int, pid: int | None = None) -> list[int]:
    target_mode = f"{response_mode:02X}"
    target_pid = f"{pid:02X}" if pid is not None else None
    for line in clean_response(response):
        if any(x in line for x in ("NO DATA", "ERROR", "STOPPED")):
            continue
        values = [int(x, 16) for x in line.split()]
        for i, value in enumerate(values):
            if value == response_mode:
                if target_pid is None:
                    return values[i + 1 :]
                if i + 1 < len(values) and values[i + 1] == pid:
                    return values[i + 2 :]
    return []


def decode_pid(pid: str, response: str) -> float | None:
    pid = pid.upper().replace("0X", "")
    definition = PID_DEFINITIONS.get(pid)
    if not definition:
        raise KeyError(f"Unsupported decoder for PID {pid}")
    payload = extract_mode_payload(response, 0x41, int(pid, 16))
    if len(payload) < definition.bytes_required:
        return None
    return round(definition.decoder(payload[: definition.bytes_required]), 3)


def parse_dtc_response(response: str, service_response: int = 0x43) -> list[str]:
    """Parse Mode 03/07/0A responses into standard five-character DTCs."""
    payload = extract_mode_payload(response, service_response)
    if not payload:
        return []
    # Some adapters include a byte count at the start. Drop an odd leading byte when plausible.
    if len(payload) % 2 == 1 and payload[0] <= len(payload) - 1:
        payload = payload[1:]
    codes: list[str] = []
    for i in range(0, len(payload) - 1, 2):
        a, b = payload[i], payload[i + 1]
        if a == 0 and b == 0:
            continue
        family = "PCBU"[(a & 0xC0) >> 6]
        d1 = str((a & 0x30) >> 4)
        code = f"{family}{d1}{a & 0x0F:X}{(b & 0xF0) >> 4:X}{b & 0x0F:X}"
        codes.append(code)
    return codes


def parse_supported_pids(response: str, base_pid: int = 0x00) -> set[str]:
    payload = extract_mode_payload(response, 0x41, base_pid)
    if len(payload) < 4:
        return set()
    bitfield = int.from_bytes(bytes(payload[:4]), "big")
    supported: set[str] = set()
    for offset in range(1, 33):
        mask = 1 << (32 - offset)
        if bitfield & mask:
            supported.add(f"{base_pid + offset:02X}")
    return supported


def decode_vin(response: str) -> str:
    """Best-effort decode of Mode 09 PID 02 VIN across common ELM formats."""
    raw_lines = clean_response(response)
    bytes_out: list[int] = []
    for line in raw_lines:
        if any(x in line for x in ("NO DATA", "ERROR")):
            continue
        vals = [int(x, 16) for x in line.split()]
        # Find 49 02 marker; byte after may be frame index.
        for i in range(len(vals) - 2):
            if vals[i] == 0x49 and vals[i + 1] == 0x02:
                chunk = vals[i + 2 :]
                if chunk and chunk[0] <= 0x05:
                    chunk = chunk[1:]
                bytes_out.extend(chunk)
                break
    vin = "".join(chr(b) for b in bytes_out if 32 <= b <= 126).strip()
    return vin[:17]
