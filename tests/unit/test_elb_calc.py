from __future__ import annotations

import math

from eks_cost_estimator.calculators.elb import elb_costs
from eks_cost_estimator.models.resources import ServiceItem


def test_elb_costs_simple():
    services = [
        ServiceItem(
            name="a",
            namespace="default",
            kind="Service",
            service_type="LoadBalancer",
            annotations=None,
        ),
        ServiceItem(
            name="b",
            namespace="default",
            kind="Service",
            service_type="ClusterIP",
            annotations=None,
        ),
    ]
    items, totals = elb_costs(services, hourly_rate=0.02)
    assert len(items) == 1
    assert math.isclose(items[0].hourly, 0.02, rel_tol=1e-9)
    assert math.isclose(items[0].monthly, 0.02 * 720, rel_tol=1e-9)
    assert math.isclose(totals["hourly"], 0.02, rel_tol=1e-9)
    assert math.isclose(totals["monthly"], 0.02 * 720, rel_tol=1e-9)

