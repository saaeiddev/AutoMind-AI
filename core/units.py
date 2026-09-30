from __future__ import annotations


def convert_value(value: float, unit: str, system: str) -> tuple[float, str]:
    if system != "imperial":
        return value, unit
    if unit == "°C":
        return value * 9 / 5 + 32, "°F"
    if unit == "km/h":
        return value * 0.621371, "mph"
    if unit == "kPa":
        return value * 0.145038, "psi"
    return value, unit


def format_value(value: object, unit: str, system: str = "metric") -> tuple[str, str]:
    if not isinstance(value, (int, float)):
        return ("Unavailable" if value is None else str(value)), unit
    converted, target_unit = convert_value(float(value), unit, system)
    if target_unit in {"rpm", "s"}:
        text = f"{converted:.0f}"
    elif target_unit in {"°C", "°F", "km/h", "mph", "%", "kPa", "psi"}:
        text = f"{converted:.1f}"
    else:
        text = f"{converted:.2f}".rstrip("0").rstrip(".")
    return text, target_unit
