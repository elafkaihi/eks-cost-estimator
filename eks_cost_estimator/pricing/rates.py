from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


def get_baseline(
    *, region: str, instance: str, override_price: float | None = None
) -> Dict[str, float]:
    data = _load_baselines()
    try:
        item = data[region][instance]
    except KeyError as e:  # noqa: BLE001
        raise ValueError(
            f"Baseline not found for region '{region}' and instance '{instance}'"
        ) from e
    return {
        "price": float(override_price) if override_price is not None else float(item["price"]),
        "vcpu": float(item["vcpu"]),
        "memory_gb": float(item["memory_gb"]),
    }


def derive_rates(
    *, price: float, vcpu: float, memory_gb: float, cpu_weight: float, mem_weight: float
) -> Dict[str, float]:
    if vcpu <= 0 or memory_gb <= 0:
        raise ValueError("Baseline vCPU and memory must be > 0")
    if not (0 <= cpu_weight <= 1 and 0 <= mem_weight <= 1):
        raise ValueError("Weights must be between 0 and 1")
    if abs((cpu_weight + mem_weight) - 1.0) > 1e-6:
        # not strictly required, but common-sense check
        pass
    per_vcpu_hour = (price * cpu_weight) / vcpu
    per_gb_ram_hour = (price * mem_weight) / memory_gb
    return {"per_vcpu_hour": per_vcpu_hour, "per_gb_ram_hour": per_gb_ram_hour}


def _load_baselines() -> Dict[str, Dict[str, Dict[str, float]]]:
    # Prefer repo-root cache path
    root_path = Path.cwd() / "pricing_cache" / "baselines.json"
    if root_path.exists():
        with root_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    # Fallback to package resource copy
    pkg_path = Path(__file__).with_name("baselines.json")
    if pkg_path.exists():
        with pkg_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    # Final fallback to built-in default
    return {
        "us-east-1": {"m6i.large": {"price": 0.096, "vcpu": 2, "memory_gb": 8}},
        "us-west-2": {"m6i.large": {"price": 0.096, "vcpu": 2, "memory_gb": 8}},
        "eu-west-1": {"m6i.large": {"price": 0.107, "vcpu": 2, "memory_gb": 8}},
        "eu-west-3": {"m6i.large": {"price": 0.119, "vcpu": 2, "memory_gb": 8}},
    }
