from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

from obd.protocol import PID_DEFINITIONS, decode_pid, decode_vin, parse_dtc_response, parse_supported_pids
from obd.transport import OBDTransport, OBDTransportError
from vehicle.models import PIDValue

log = logging.getLogger("automind.obd.elm327")


@dataclass
class AdapterInfo:
    identity: str = ""
    protocol: str = ""
    voltage: str = ""


class ELM327Client:
    """Read-focused ELM327 client. It intentionally exposes no arbitrary CAN write API."""

    INIT_COMMANDS = ("ATZ", "ATE0", "ATL0", "ATS0", "ATH0", "ATSP0")

    def __init__(self, transport: OBDTransport) -> None:
        self.transport = transport
        self.adapter_info = AdapterInfo()
        self.supported_pids: set[str] = set()

    def connect(self) -> AdapterInfo:
        self.transport.open()
        try:
            for cmd in self.INIT_COMMANDS:
                response = self.transport.transact(cmd)
                if "ERROR" in response.upper():
                    raise OBDTransportError(f"Adapter rejected initialization command {cmd}")
            self.adapter_info.identity = self._plain(self.transport.transact("ATI"))
            self.adapter_info.protocol = self._plain(self.transport.transact("ATDP"))
            self.adapter_info.voltage = self._plain(self.transport.transact("ATRV"))
            self.supported_pids = self.read_supported_pids()
            return self.adapter_info
        except Exception:
            self.transport.close()
            raise

    def disconnect(self) -> None:
        self.transport.close()

    @property
    def connected(self) -> bool:
        return self.transport.is_open

    def read_supported_pids(self) -> set[str]:
        supported: set[str] = set()
        for base in (0x00, 0x20, 0x40, 0x60):
            response = self.transport.transact(f"01{base:02X}")
            chunk = parse_supported_pids(response, base)
            supported |= chunk
            # Continuation PID indicates whether the next block is supported.
            if f"{base + 0x20:02X}" not in chunk:
                break
        return supported

    def read_pid(self, pid: str) -> PIDValue:
        pid = pid.upper().replace("01", "", 1) if pid.upper().startswith("01") else pid.upper()
        definition = PID_DEFINITIONS.get(pid)
        if not definition:
            return PIDValue(pid=f"01{pid}", name=f"PID {pid}", value=None, supported=False)
        if self.supported_pids and pid not in self.supported_pids:
            return PIDValue(pid=f"01{pid}", name=definition.name, value=None, unit=definition.unit, supported=False)
        response = self.transport.transact(f"01{pid}")
        if "NO DATA" in response.upper():
            return PIDValue(pid=f"01{pid}", name=definition.name, value=None, unit=definition.unit, supported=False)
        value = decode_pid(pid, response)
        return PIDValue(pid=f"01{pid}", name=definition.name, value=value, unit=definition.unit, supported=value is not None)

    def read_live_data(self, pids: Iterable[str]) -> dict[str, PIDValue]:
        result: dict[str, PIDValue] = {}
        for pid in pids:
            value = self.read_pid(pid)
            result[value.pid] = value
        return result

    def read_stored_dtcs(self) -> list[str]:
        return parse_dtc_response(self.transport.transact("03"), 0x43)

    def read_pending_dtcs(self) -> list[str]:
        return parse_dtc_response(self.transport.transact("07"), 0x47)

    def read_permanent_dtcs(self) -> list[str]:
        return parse_dtc_response(self.transport.transact("0A"), 0x4A)

    def read_vin(self) -> str:
        return decode_vin(self.transport.transact("0902"))

    def read_calibration_id(self) -> str:
        return self._decode_mode09_ascii(self.transport.transact("0904"), 0x04)

    def read_ecu_name(self) -> str:
        return self._decode_mode09_ascii(self.transport.transact("090A"), 0x0A)

    @staticmethod
    def _decode_mode09_ascii(response: str, pid: int) -> str:
        from obd.protocol import clean_response
        data: list[int] = []
        for line in clean_response(response):
            if "NO DATA" in line or "ERROR" in line:
                continue
            values = [int(x, 16) for x in line.split()]
            for i in range(len(values) - 1):
                if values[i] == 0x49 and values[i + 1] == pid:
                    chunk = values[i + 2:]
                    if chunk and chunk[0] <= 0x0F:
                        chunk = chunk[1:]
                    data.extend(chunk)
                    break
        return "".join(chr(b) for b in data if 32 <= b <= 126).strip()[:80]

    def read_freeze_frame(self, pids: Iterable[str]) -> dict[str, PIDValue]:
        # Mode 02 frame 00. Not all ECUs expose all requested PIDs.
        result: dict[str, PIDValue] = {}
        for raw_pid in pids:
            pid = raw_pid.upper().replace("01", "", 1) if raw_pid.upper().startswith("01") else raw_pid.upper()
            definition = PID_DEFINITIONS.get(pid)
            if not definition:
                continue
            response = self.transport.transact(f"02{pid}00")
            # Mode 02 response is 42; reuse the mode-01 decoder by replacing only the service byte in normalized text.
            normalized = response.upper().replace("42 ", "41 ").replace("42", "41", 1)
            try:
                value = decode_pid(pid, normalized)
            except Exception:
                value = None
            result[f"01{pid}"] = PIDValue(
                pid=f"01{pid}", name=definition.name, value=value, unit=definition.unit, supported=value is not None
            )
        return result

    @staticmethod
    def _plain(response: str) -> str:
        lines = [x.strip() for x in response.replace("\r", "\n").split("\n") if x.strip() and x.strip() != ">"]
        return " ".join(lines[-2:])[:120]
