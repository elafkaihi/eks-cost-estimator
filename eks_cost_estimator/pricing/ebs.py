from __future__ import annotations

from typing import Dict, Optional


# Region-agnostic defaults (USD per GB-month). IOPS/throughput costs excluded (MVP).
DEFAULT_EBS_RATES: Dict[str, float] = {
    "gp3": 0.08,
    "gp2": 0.10,
    "io1": 0.125,
    "io2": 0.125,
    "st1": 0.045,
    "sc1": 0.015,
    "standard": 0.05,  # magnetic
}


def detect_volume_type(storage_class_name: Optional[str]) -> Optional[str]:
    if not storage_class_name:
        return None
    name = str(storage_class_name).strip().lower()
    for vt in DEFAULT_EBS_RATES.keys():
        if name == vt or vt in name:
            return vt
    return None


def get_rate_for_type(
    volume_type: Optional[str],
    *,
    default_rate: float,
    rates: Dict[str, float] | None = None,
) -> float:
    mapping = rates or DEFAULT_EBS_RATES
    if not volume_type:
        return default_rate
    vt = str(volume_type).lower()
    return mapping.get(vt, default_rate)

