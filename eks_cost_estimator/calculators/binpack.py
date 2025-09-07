from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from eks_cost_estimator.models.resources import WorkloadItem
from eks_cost_estimator.models.results import (
    BinPackingResult,
    NodeBin,
    NodeBinAllocation,
)


@dataclass(slots=True)
class _Item:
    name: str
    namespace: Optional[str]
    kind: str
    cpu: float
    mem: float
    replicas: int


def _flatten_items(workloads: List[WorkloadItem]) -> List[_Item]:
    items: List[_Item] = []
    for w in workloads:
        if w.cpu_vcpu_per_replica <= 0 or w.memory_gb_per_replica <= 0 or w.replicas <= 0:
            continue
        items.append(
            _Item(
                name=w.name,
                namespace=w.namespace,
                kind=w.kind,
                cpu=w.cpu_vcpu_per_replica,
                mem=w.memory_gb_per_replica,
                replicas=w.replicas,
            )
        )
    return items


def simulate_binpack(
    workloads: List[WorkloadItem],
    *,
    instance_type: str,
    node_cpu_vcpu: float,
    node_mem_gb: float,
    overhead_cpu_vcpu: float = 0.2,
    overhead_mem_gb: float = 0.5,
) -> BinPackingResult:
    # Effective capacities
    cpu_cap = max(0.0, float(node_cpu_vcpu) - float(overhead_cpu_vcpu))
    mem_cap = max(0.0, float(node_mem_gb) - float(overhead_mem_gb))

    items = _flatten_items(workloads)

    # Sort items by max utilization fraction descending
    def key(i: _Item) -> Tuple[float, float]:
        frac_cpu = i.cpu / cpu_cap if cpu_cap > 0 else 1.0
        frac_mem = i.mem / mem_cap if mem_cap > 0 else 1.0
        return (max(frac_cpu, frac_mem), i.cpu + i.mem)

    items.sort(key=key, reverse=True)

    # Nodes state
    nodes_cpu_used: List[float] = []
    nodes_mem_used: List[float] = []
    nodes_allocs: List[dict[Tuple[str, Optional[str], str], int]] = []

    for it in items:
        for _ in range(it.replicas):
            # Find best fit node
            best_idx: Optional[int] = None
            best_score: float = 1e9
            for idx in range(len(nodes_cpu_used)):
                new_cpu = nodes_cpu_used[idx] + it.cpu
                new_mem = nodes_mem_used[idx] + it.mem
                if new_cpu <= cpu_cap + 1e-9 and new_mem <= mem_cap + 1e-9:
                    # score: leftover sum (lower is better)
                    score = (cpu_cap - new_cpu) + (mem_cap - new_mem)
                    if score < best_score:
                        best_score = score
                        best_idx = idx
            if best_idx is None:
                # create new node
                nodes_cpu_used.append(it.cpu)
                nodes_mem_used.append(it.mem)
                nodes_allocs.append({})
                best_idx = len(nodes_cpu_used) - 1
            else:
                nodes_cpu_used[best_idx] += it.cpu
                nodes_mem_used[best_idx] += it.mem

            key_alloc = (it.name, it.namespace, it.kind)
            nodes_allocs[best_idx][key_alloc] = nodes_allocs[best_idx].get(key_alloc, 0) + 1

    # Build result structure
    total_cpu_used = sum(nodes_cpu_used)
    total_mem_used = sum(nodes_mem_used)
    total_cpu_cap = cpu_cap * len(nodes_cpu_used)
    total_mem_cap = mem_cap * len(nodes_cpu_used)

    nodes: List[NodeBin] = []
    for idx, (cpu_used, mem_used, alloc_map) in enumerate(
        zip(nodes_cpu_used, nodes_mem_used, nodes_allocs)
    ):
        allocs: List[NodeBinAllocation] = []
        for (name, ns, kind), reps in alloc_map.items():
            # find the item spec for cpu/mem per replica
            itm = next((x for x in items if x.name == name and x.namespace == ns and x.kind == kind), None)
            cpu_total = (itm.cpu if itm else 0.0) * reps
            mem_total = (itm.mem if itm else 0.0) * reps
            allocs.append(
                NodeBinAllocation(
                    workload=name,
                    namespace=ns,
                    kind=kind,
                    replicas=reps,
                    cpu_vcpu=cpu_total,
                    memory_gb=mem_total,
                )
            )
        nodes.append(
            NodeBin(
                index=idx + 1,
                cpu_capacity=cpu_cap,
                mem_capacity_gb=mem_cap,
                cpu_used=cpu_used,
                mem_used_gb=mem_used,
                allocations=sorted(allocs, key=lambda a: (a.workload, a.namespace or "")),
            )
        )

    return BinPackingResult(
        instance_type=instance_type,
        node_count=len(nodes),
        cpu_capacity_per_node=cpu_cap,
        mem_capacity_gb_per_node=mem_cap,
        overhead_cpu_vcpu=float(overhead_cpu_vcpu),
        overhead_mem_gb=float(overhead_mem_gb),
        cpu_utilization=(total_cpu_used / total_cpu_cap) if total_cpu_cap > 0 else 0.0,
        mem_utilization=(total_mem_used / total_mem_cap) if total_mem_cap > 0 else 0.0,
        nodes=nodes,
    )

