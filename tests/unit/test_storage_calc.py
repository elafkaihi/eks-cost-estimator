from __future__ import annotations

import math

from eks_cost_estimator.calculators.storage import storage_costs
from eks_cost_estimator.models.resources import StorageItem


def test_storage_cost_rules():
    # StatefulSet VCT: multiply by replicas
    vct = StorageItem(
        name="db-data",
        namespace="default",
        kind="StatefulSetVolumeClaimTemplate",
        size_gb=20.0,
        replicas=3,
        multiply_by_replicas=3,
    )
    # Deployment shared PVC: not multiplied by replicas (factor 1)
    pvc = StorageItem(
        name="shared-cache",
        namespace="default",
        kind="PersistentVolumeClaim",
        size_gb=50.0,
        replicas=5,
        multiply_by_replicas=1,
    )

    items, totals = storage_costs([vct, pvc], rate_gb_month=0.08)
    assert len(items) == 2
    vct_cost = next(i for i in items if i.kind == "StatefulSetVolumeClaimTemplate")
    pvc_cost = next(i for i in items if i.kind == "PersistentVolumeClaim")

    assert math.isclose(vct_cost.monthly, 20.0 * 0.08 * 3, rel_tol=1e-9)
    assert math.isclose(pvc_cost.monthly, 50.0 * 0.08 * 1, rel_tol=1e-9)
    assert math.isclose(totals["monthly"], vct_cost.monthly + pvc_cost.monthly, rel_tol=1e-9)

