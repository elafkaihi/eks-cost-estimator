from __future__ import annotations

from typing import Dict, List, Tuple, Optional

from eks_cost_estimator.models.resources import StorageItem
from eks_cost_estimator.models.results import StorageCost
from eks_cost_estimator.pricing.ebs import DEFAULT_EBS_RATES, get_rate_for_type


DEFAULT_STORAGE_RATE_GB_MONTH = 0.08


def storage_costs(
    items: List[StorageItem],
    rate_gb_month: float = DEFAULT_STORAGE_RATE_GB_MONTH,
    *,
    rates_by_type: Optional[Dict[str, float]] = None,
) -> Tuple[List[StorageCost], Dict[str, float]]:
    costs: List[StorageCost] = []
    total_monthly = 0.0
    for s in items:
        # StatefulSet vct multiplies by replicas; standalone PVC referenced by Deployment is shared (factor 1)
        multiplier = s.multiply_by_replicas if s.multiply_by_replicas else 1
        # choose rate by detected volume type if available
        vt_rate = get_rate_for_type(s.volume_type, default_rate=rate_gb_month, rates=rates_by_type or DEFAULT_EBS_RATES)
        monthly = s.size_gb * vt_rate * float(multiplier)
        total_monthly += monthly
        costs.append(
            StorageCost(
                name=s.name,
                namespace=s.namespace,
                kind=s.kind,
                size_gb=s.size_gb,
                replicas=s.replicas,
                multiply_by_replicas=multiplier,
                monthly=monthly,
                hourly=monthly / 720.0,
                rate_gb_month=vt_rate,
                volume_type=s.volume_type,
                note=s.note,
            )
        )
    totals = {"monthly": total_monthly, "hourly": total_monthly / 720.0}
    return costs, totals
