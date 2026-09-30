from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

log = logging.getLogger("automind.obd")

try:
    import serial  # type: ignore
    from serial.tools import list_ports  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    serial = None
    list_ports = None


class OBDTransportError(RuntimeError):
    pass


class OBDTransport(ABC):
    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def transact(self, command: str) -> str: ...

    @property
    @abstractmethod
    def is_open(self) -> bool: ...


@dataclass(frozen=True)
class PortInfo:
    device: str
    description: str
    hwid: str = ""


def available_serial_ports() -> list[PortInfo]:
    if list_ports is None:
        return []
    ports: list[PortInfo] = []
    for p in list_ports.comports():
        ports.append(PortInfo(p.device, p.description or "Serial Port", p.hwid or ""))
    return ports


class SerialELM327Transport(OBDTransport):
    def __init__(self, port: str, baud_rate: int = 38400, timeout: float = 2.0) -> None:
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self._serial = None
        self._lock = threading.Lock()

    def open(self) -> None:
        if serial is None:
            raise OBDTransportError("pyserial is not installed. Install production dependencies before using a real adapter.")
        try:
            self._serial = serial.Serial(
                self.port,
                self.baud_rate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
            time.sleep(0.25)
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
        except Exception as exc:
            raise OBDTransportError(f"Could not open {self.port}: {exc}") from exc

    @property
    def is_open(self) -> bool:
        return bool(self._serial and self._serial.is_open)

    def close(self) -> None:
        if self._serial:
            try:
                self._serial.close()
            finally:
                self._serial = None

    def transact(self, command: str) -> str:
        if not self.is_open:
            raise OBDTransportError("Serial adapter is not open")
        assert self._serial is not None
        with self._lock:
            try:
                self._serial.reset_input_buffer()
                payload = (command.strip() + "\r").encode("ascii")
                self._serial.write(payload)
                self._serial.flush()
                deadline = time.monotonic() + self.timeout
                data = bytearray()
                while time.monotonic() < deadline:
                    chunk = self._serial.read(self._serial.in_waiting or 1)
                    if chunk:
                        data.extend(chunk)
                        if b">" in data:
                            break
                response = data.decode("ascii", errors="replace")
                log.debug("ELM command %s -> %s", command, response.replace("\r", " ").replace("\n", " "))
                return response
            except Exception as exc:
                raise OBDTransportError(f"ELM327 communication failed: {exc}") from exc
