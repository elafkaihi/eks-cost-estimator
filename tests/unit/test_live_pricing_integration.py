from __future__ import annotations

import types

from eks_cost_estimator.core.orchestrator import EstimationConfig, orchestrate


class DummySession:
    def __init__(self):
        pass

    def client(self, service, region_name=None):  # noqa: D401
        if service == "pricing":
            return DummyPricing()
        if service == "ec2":
            return DummyEC2()
        raise AssertionError("unexpected service")


class DummyPricing:
    def get_products(self, ServiceCode, Filters, MaxResults):  # noqa: N803, D401
        # Return a minimal shape with an OnDemand term and pricePerUnit
        product = {
            "terms": {
                "OnDemand": {
                    "A": {
                        "priceDimensions": {
                            "B": {"pricePerUnit": {"USD": "0.123"}}
                        }
                    }
                }
            }
        }
        return {"PriceList": [__import__("json").dumps(product)]}


class DummyEC2:
    def describe_instance_types(self, InstanceTypes):  # noqa: N803, D401
        return {
            "InstanceTypes": [
                {
                    "VCpuInfo": {"DefaultVCpus": 4},
                    "MemoryInfo": {"SizeInMiB": 16384},
                }
            ]
        }


def test_orchestrate_uses_live_pricing_when_enabled(monkeypatch):
    # Patch session builder inside aws_pricing to return our dummy session
    import eks_cost_estimator.pricing.aws_pricing as ap

    monkeypatch.setattr(ap, "_session", lambda profile=None: DummySession())

    cfg = EstimationConfig(
        region="eu-west-3",
        baseline_instance="m6i.large",
        baseline_price_override=None,
        cpu_weight=0.6,
        mem_weight=0.4,
        live_pricing=True,
    )
    # Use a very small file set: just reuse existing fixtures
    res = orchestrate(
        [
            "tests/fixtures/deployment.yaml",
        ],
        cfg,
    )
    # Baseline price should be our dummy 0.123
    assert abs(res.baseline.price - 0.123) < 1e-9
    assert res.baseline.vcpu == 4
    assert res.baseline.memory_gb == 16

