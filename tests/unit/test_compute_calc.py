from __future__ import annotations

import math

from eks_cost_estimator.calculators.compute import compute_costs
from eks_cost_estimator.models.resources import WorkloadItem


def test_compute_costs_deterministic():
    w = WorkloadItem(
        name="web",
        namespace="default",
        kind="Deployment",
        replicas=3,
        cpu_vcpu_per_replica=1.0,
        memory_gb_per_replica=2.0,
    )
    rates = {"per_vcpu_hour": 0.0288, "per_gb_ram_hour": 0.0048}
    items, totals = compute_costs([w], rates)
    assert len(items) == 1
    hourly = items[0].hourly
    monthly = items[0].monthly
    assert math.isclose(hourly, 0.1152, rel_tol=1e-9)
    assert math.isclose(monthly, 0.1152 * 720, rel_tol=1e-9)
    assert math.isclose(totals["hourly"], hourly, rel_tol=1e-9)
    assert math.isclose(totals["monthly"], monthly, rel_tol=1e-9)

