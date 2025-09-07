from __future__ import annotations

import re


_CPU_M_PATTERN = re.compile(r"^(?P<val>\d+(?:\.\d+)?)m$")
_NUM_PATTERN = re.compile(r"^(?P<val>\d+(?:\.\d+)?)$")

_MEM_PATTERN = re.compile(r"^(?P<val>\d+(?:\.\d+)?)(?P<unit>Ki|Mi|Gi|Ti|KB|MB|GB|TB)$", re.IGNORECASE)


def parse_cpu(value: str | int | float) -> float:
    """Parse Kubernetes CPU quantity to vCPU (cores).

    - 500m => 0.5
    - 1 => 1.0
    - 0.5 => 0.5
    """
    s = str(value).strip()
    m = _CPU_M_PATTERN.match(s)
    if m:
        return float(m.group("val")) / 1000.0
    m = _NUM_PATTERN.match(s)
    if m:
        return float(m.group("val"))
    raise ValueError(f"Unknown CPU unit: {value}")


def parse_mem_gb(value: str | int | float) -> float:
    """Parse Kubernetes memory quantity to GB (decimal, 1 GB = 1e9 bytes).

    Supports binary units (Ki, Mi, Gi, Ti) and decimal (KB, MB, GB, TB).
    """
    s = str(value).strip()
    m = _MEM_PATTERN.match(s)
    if not m:
        raise ValueError(f"Unknown memory unit: {value}")
    val = float(m.group("val"))
    unit = m.group("unit").upper()

    # Convert to bytes first
    if unit == "KI":
        bytes_val = val * 1024.0
    elif unit == "MI":
        bytes_val = val * 1024.0 ** 2
    elif unit == "GI":
        bytes_val = val * 1024.0 ** 3
    elif unit == "TI":
        bytes_val = val * 1024.0 ** 4
    elif unit == "KB":
        bytes_val = val * 1_000.0
    elif unit == "MB":
        bytes_val = val * 1_000_000.0
    elif unit == "GB":
        bytes_val = val * 1_000_000_000.0
    elif unit == "TB":
        bytes_val = val * 1_000_000_000_000.0
    else:  # pragma: no cover - redundant due to regex
        raise ValueError(f"Unknown memory unit: {value}")

    gb = bytes_val / 1_000_000_000.0
    return gb

