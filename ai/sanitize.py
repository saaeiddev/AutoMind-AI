from __future__ import annotations

from copy import deepcopy
from typing import Any


SENSITIVE_KEYS = {"owner", "registration", "license_plate", "email", "phone", "address", "gps", "location"}


def sanitize_diagnostic_payload(payload: dict[str, Any], include_vin: bool = False) -> dict[str, Any]:
    cleaned = deepcopy(payload)
    _strip_sensitive(cleaned)
    vehicle = cleaned.get("vehicle")
    if isinstance(vehicle, dict) and not include_vin:
        vehicle.pop("vin", None)
    return cleaned


def _strip_sensitive(value: Any) -> None:
    if isinstance(value, dict):
        for key in list(value.keys()):
            if key.lower() in SENSITIVE_KEYS:
                value.pop(key, None)
            else:
                _strip_sensitive(value[key])
    elif isinstance(value, list):
        for item in value:
            _strip_sensitive(item)
