from __future__ import annotations

import math

from eks_cost_estimator.utils.units import parse_cpu, parse_mem_gb


def test_parse_cpu_units():
    assert math.isclose(parse_cpu("500m"), 0.5)
    assert math.isclose(parse_cpu("1"), 1.0)
    assert math.isclose(parse_cpu(2), 2.0)
    assert math.isclose(parse_cpu(0.25), 0.25)


def test_parse_mem_units():
    assert math.isclose(parse_mem_gb("256Mi"), 0.268435456, rel_tol=1e-9)
    assert math.isclose(parse_mem_gb("1Gi"), 1.073741824, rel_tol=1e-9)
    assert math.isclose(parse_mem_gb("100MB"), 0.1, rel_tol=1e-9)
    assert math.isclose(parse_mem_gb("1GB"), 1.0, rel_tol=1e-9)

