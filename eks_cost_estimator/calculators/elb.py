from __future__ import annotations

from typing import Dict, List, Tuple

from eks_cost_estimator.models.resources import ServiceItem
from eks_cost_estimator.models.results import LoadBalancerCost


DEFAULT_ELB_HOURLY = 0.0225  # Approx ALB/NLB hourly, LCUs excluded (MVP)


def elb_costs(
    services: List[ServiceItem], hourly_rate: float = DEFAULT_ELB_HOURLY
) -> Tuple[List[LoadBalancerCost], Dict[str, float]]:
    items: List[LoadBalancerCost] = []
    total_hourly = 0.0
    for s in services:
        if s.service_type.lower() != "loadbalancer":
            continue
        hourly = hourly_rate
        monthly = hourly * 720.0
        total_hourly += hourly
        items.append(
            LoadBalancerCost(
                name=s.name,
                namespace=s.namespace,
                kind=s.kind,
                service_type=s.service_type,
                hourly=hourly,
                monthly=monthly,
                rate_hour=hourly_rate,
            )
        )
    totals = {"hourly": total_hourly, "monthly": total_hourly * 720.0}
    return items, totals

