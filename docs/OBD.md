# OBD-II and ELM327 Notes

## Scope

AutoMind AI 0.1.0 focuses on generic, standards-based OBD-II diagnostics through ELM327-compatible serial adapters.

## Connection flow

1. Open selected Windows COM port.
2. Reset adapter with `ATZ`.
3. Disable command echo, linefeeds, spaces and headers for predictable parsing.
4. Use automatic protocol selection (`ATSP0`).
5. Read adapter identity (`ATI`), active protocol (`ATDP`) and adapter-reported voltage (`ATRV`).
6. Query supported PID bitfields.
7. Read vehicle data only after initialization succeeds.

## OBD services used

- Mode 01: current powertrain data
- Mode 02: freeze-frame data
- Mode 03: stored DTCs
- Mode 07: pending DTCs
- Mode 09 PID 02: VIN when supported
- Mode 0A: permanent DTCs when supported

## Read-only design

No public method exists for arbitrary CAN frame transmission. There is no ECU-flashing path. DTC clearing is intentionally not implemented in the MVP.

## Unsupported data

A vehicle may support only a subset of standard PIDs. The client queries supported-PID bitfields and represents unavailable values with `supported=False` or `value=None` rather than fabricating readings.

## Adapter caveats

ELM327-compatible products vary significantly. Some clones:

- falsely report firmware versions,
- omit commands,
- time out on certain CAN protocols,
- behave differently at 38400 vs 115200 baud,
- expose Bluetooth as a serial COM port only after Windows pairing.

The software therefore exposes serial-port and baud-rate selection and treats normal connection failures as recoverable errors.

## Future OBD work

- More Mode 01 decoders
- richer multi-frame parsing
- protocol-specific optimizations
- J2534 transport
- better BLE transport abstraction
- enhanced readiness-monitor reporting
- manufacturer-specific modules only through documented/licensed integrations
