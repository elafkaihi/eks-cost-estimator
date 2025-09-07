from __future__ import annotations

from typing import Dict, List, Tuple

from eks_cost_estimator.models.resources import WorkloadItem
from eks_cost_estimator.models.results import WorkloadCost


def compute_costs(
    workloads: List[WorkloadItem],
    rates: Dict[str, float],
) -> Tuple[List[WorkloadCost], Dict[str, float]]:
    per_vcpu_hour = float(rates["per_vcpu_hour"])
    per_gb_ram_hour = float(rates["per_gb_ram_hour"])

    items: List[WorkloadCost] = []
    total_hourly = 0.0
    total_monthly = 0.0

    for w in workloads:
        per_replica_hourly = (
            w.cpu_vcpu_per_replica * per_vcpu_hour
            + w.memory_gb_per_replica * per_gb_ram_hour
        )
        hourly = per_replica_hourly * w.replicas
        monthly = hourly * 720.0
        total_hourly += hourly
        total_monthly += monthly
        items.append(
            WorkloadCost(
                name=w.name,
                namespace=w.namespace,
                kind=w.kind,
                replicas=w.replicas,
                cpu_vcpu_per_replica=w.cpu_vcpu_per_replica,
                memory_gb_per_replica=w.memory_gb_per_replica,
                hourly=hourly,
                monthly=monthly,
            )
        )

    totals = {"hourly": total_hourly, "monthly": total_monthly}
    return items, totals

