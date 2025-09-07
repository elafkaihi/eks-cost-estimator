from __future__ import annotations

from eks_cost_estimator.calculators.binpack import simulate_binpack
from eks_cost_estimator.models.resources import WorkloadItem


def test_binpacking_simple_two_nodes():
    # Baseline m6i.large example: 2 vCPU, 8 GB; reserve 0.2 vCPU and 0.5 GB
    workloads = [
        WorkloadItem(
            name="app-a",
            namespace="default",
            kind="Deployment",
            replicas=2,
            cpu_vcpu_per_replica=1.0,
            memory_gb_per_replica=4.0,
        ),
        WorkloadItem(
            name="app-b",
            namespace="default",
            kind="Deployment",
            replicas=1,
            cpu_vcpu_per_replica=0.8,
            memory_gb_per_replica=3.5,
        ),
    ]

    res = simulate_binpack(
        workloads,
        instance_type="m6i.large",
        node_cpu_vcpu=2.0,
        node_mem_gb=8.0,
        overhead_cpu_vcpu=0.2,
        overhead_mem_gb=0.5,
    )

    assert res.node_count == 2
    # Ensure one node nearly full and the other has 1 replica
    assert any(abs(n.cpu_used - n.cpu_capacity) < 1e-6 and abs(n.mem_used_gb - n.mem_capacity_gb) < 1e-6 for n in res.nodes)
