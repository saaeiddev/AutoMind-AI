# Supported OBD-II Functionality - AutoMind AI 0.1.0

## Services

| Function | OBD service | Status |
|---|---:|---|
| Current powertrain data | Mode 01 | Implemented |
| Freeze frame | Mode 02 | Implemented, ECU-dependent |
| Stored DTCs | Mode 03 | Implemented |
| Pending DTCs | Mode 07 | Implemented |
| Vehicle VIN | Mode 09 PID 02 | Implemented, ECU-dependent |
| Permanent DTCs | Mode 0A | Implemented, ECU-dependent |
| Supported PID bitfields | Mode 01 PIDs 00/20/40/60 | Implemented |
| Clear DTCs | Mode 04 | Intentionally not implemented in V1 |
| ECU reprogramming | - | Not implemented |
| Arbitrary CAN transmit | - | Not implemented |

## Mode 01 PID decoders

The application currently contains decoders for 46 standard/common PID measurements where supported by the ECU:

- 0104 Calculated Engine Load
- 0105 Engine Coolant Temperature
- 0106 Short-Term Fuel Trim Bank 1
- 0107 Long-Term Fuel Trim Bank 1
- 0108 Short-Term Fuel Trim Bank 2
- 0109 Long-Term Fuel Trim Bank 2
- 010A Fuel Pressure
- 010B Intake Manifold Absolute Pressure
- 010C Engine RPM
- 010D Vehicle Speed
- 010E Ignition Timing Advance
- 010F Intake Air Temperature
- 0110 MAF Air Flow Rate
- 0111 Throttle Position
- 0114-011B O2 Sensor 1-8 Voltage representations
- 011F Run Time Since Engine Start
- 0121 Distance Traveled With MIL On
- 012C Commanded EGR
- 012E Commanded Evaporative Purge
- 012F Fuel Tank Level Input
- 0130 Warm-ups Since Codes Cleared
- 0131 Distance Since Codes Cleared
- 0133 Barometric Pressure
- 013C-013F Catalyst Temperature sensors
- 0142 Control Module Voltage
- 0145 Relative Throttle Position
- 0146 Ambient Air Temperature
- 0149-014B Accelerator Pedal Positions D/E/F
- 014C Commanded Throttle Actuator
- 0152 Ethanol Fuel Percentage
- 015A Relative Accelerator Pedal Position
- 015B Hybrid Battery Pack Remaining Life
- 015C Engine Oil Temperature
- 015E Engine Fuel Rate

A decoder being present does not mean a specific vehicle supports that PID. ECU-supported PID discovery is performed at connection time and unavailable measurements remain unavailable.
