from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class WorkloadCost(BaseModel):
    name: str
    namespace: Optional[str] = None
    kind: str
    replicas: int
    cpu_vcpu_per_replica: float
    memory_gb_per_replica: float
    hourly: float
    monthly: float


class StorageCost(BaseModel):
    name: str
    namespace: Optional[str] = None
    kind: str
    size_gb: float
    replicas: int
    multiply_by_replicas: int
    monthly: float
    hourly: float
    rate_gb_month: float
    volume_type: Optional[str] = None
    note: Optional[str] = None


class LoadBalancerCost(BaseModel):
    name: str
    namespace: Optional[str] = None
    kind: str
    service_type: str
    hourly: float
    monthly: float
    rate_hour: float


class BaselineInfo(BaseModel):
    region: str
    instance_type: str
    price: float
    vcpu: float
    memory_gb: float
    cpu_weight: float
    mem_weight: float


class DerivedRates(BaseModel):
    per_vcpu_hour: float
    per_gb_ram_hour: float
    storage_gb_month: float


class Totals(BaseModel):
    compute_hourly: float
    compute_monthly: float
    storage_hourly: float
    storage_monthly: float
    lb_hourly: float = 0.0
    lb_monthly: float = 0.0

    @property
    def grand_hourly(self) -> float:  # pragma: no cover - convenience
        return self.compute_hourly + self.storage_hourly + self.lb_hourly

    @property
    def grand_monthly(self) -> float:  # pragma: no cover - convenience
        return self.compute_monthly + self.storage_monthly + self.lb_monthly


class EstimationResult(BaseModel):
    baseline: BaselineInfo
    derived_rates: DerivedRates
    workloads: List[WorkloadCost]
    storage: List[StorageCost]
    load_balancers: List[LoadBalancerCost] = []
    totals: Totals
    assumptions: List[str]
    warnings: List[str]
    binpacking: Optional["BinPackingResult"] = None


class NodeBinAllocation(BaseModel):
    workload: str
    namespace: Optional[str] = None
    kind: str
    replicas: int
    cpu_vcpu: float
    memory_gb: float


class NodeBin(BaseModel):
    index: int
    cpu_capacity: float
    mem_capacity_gb: float
    cpu_used: float
    mem_used_gb: float
    allocations: List[NodeBinAllocation]


class BinPackingResult(BaseModel):
    instance_type: str
    node_count: int
    cpu_capacity_per_node: float
    mem_capacity_gb_per_node: float
    overhead_cpu_vcpu: float
    overhead_mem_gb: float
    cpu_utilization: float  # total used / total capacity
    mem_utilization: float
    nodes: List[NodeBin]
