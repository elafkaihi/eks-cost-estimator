from __future__ import annotations

import math

from eks_cost_estimator.calculators.storage import storage_costs
from eks_cost_estimator.models.resources import StorageItem
from eks_cost_estimator.pricing.ebs import DEFAULT_EBS_RATES


def test_storage_uses_volume_type_rate_when_present():
    pvc_gp2 = StorageItem(
        name="cache",
        namespace="default",
        kind="PersistentVolumeClaim",
        size_gb=100.0,
        replicas=1,
        multiply_by_replicas=1,
        volume_type="gp2",
    )
    # default rate 0.08 (gp3), but gp2 should use 0.10 from mapping
    items, totals = storage_costs([pvc_gp2], rate_gb_month=0.08)
    assert len(items) == 1
    item = items[0]
    assert math.isclose(item.rate_gb_month, DEFAULT_EBS_RATES["gp2"], rel_tol=1e-9)
    assert math.isclose(item.monthly, 100.0 * DEFAULT_EBS_RATES["gp2"], rel_tol=1e-9)
    assert math.isclose(totals["monthly"], item.monthly, rel_tol=1e-9)

