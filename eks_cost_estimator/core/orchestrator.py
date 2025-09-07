from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from eks_cost_estimator.calculators.compute import compute_costs
from eks_cost_estimator.calculators.storage import storage_costs
from eks_cost_estimator.calculators.elb import elb_costs, DEFAULT_ELB_HOURLY
from eks_cost_estimator.calculators.binpack import simulate_binpack
from eks_cost_estimator.models.resources import StorageItem, WorkloadItem
from eks_cost_estimator.models.results import (
    BaselineInfo,
    DerivedRates,
    EstimationResult,
    Totals,
)
from eks_cost_estimator.parsers.yaml_parser import ParseOutput, parse_files
from eks_cost_estimator.pricing.rates import derive_rates, get_baseline
from eks_cost_estimator.pricing.aws_pricing import get_live_baseline, LivePricingError


@dataclass(slots=True)
class EstimationConfig:
    region: str
    baseline_instance: str
    baseline_price_override: float | None
    cpu_weight: float
    mem_weight: float
    detailed: bool = False
    elb_hourly_price: float = DEFAULT_ELB_HOURLY
    binpack: bool = False
    node_overhead_cpu: float = 0.2
    node_overhead_mem_gb: float = 0.5
    live_pricing: bool = False
    aws_profile: str | None = None


def orchestrate(paths: List[str], cfg: EstimationConfig) -> EstimationResult:
    parsed: ParseOutput = parse_files(paths)

    if cfg.live_pricing:
        try:
            baseline = get_live_baseline(
                region=cfg.region, instance=cfg.baseline_instance, profile=cfg.aws_profile
            )
            if cfg.baseline_price_override is not None:
                baseline["price"] = float(cfg.baseline_price_override)
        except LivePricingError as e:
            # Fallback to static cache if live pricing fails
            baseline = get_baseline(
                region=cfg.region,
                instance=cfg.baseline_instance,
                override_price=cfg.baseline_price_override,
            )
    else:
        baseline = get_baseline(
            region=cfg.region,
            instance=cfg.baseline_instance,
            override_price=cfg.baseline_price_override,
        )
    rates = derive_rates(
        price=baseline["price"],
        vcpu=baseline["vcpu"],
        memory_gb=baseline["memory_gb"],
        cpu_weight=cfg.cpu_weight,
        mem_weight=cfg.mem_weight,
    )

    workload_costs, compute_totals = compute_costs(parsed.workloads, rates)
    storage_items = parsed.storage
    storage_cost_items, storage_totals = storage_costs(storage_items)
    lb_cost_items, lb_totals = elb_costs(parsed.services, cfg.elb_hourly_price)

    totals = Totals(
        compute_hourly=compute_totals["hourly"],
        compute_monthly=compute_totals["monthly"],
        storage_monthly=storage_totals["monthly"],
        storage_hourly=storage_totals["hourly"],
        lb_hourly=lb_totals["hourly"],
        lb_monthly=lb_totals["monthly"],
    )

    base_info = BaselineInfo(
        region=cfg.region,
        instance_type=cfg.baseline_instance,
        price=baseline["price"],
        vcpu=baseline["vcpu"],
        memory_gb=baseline["memory_gb"],
        cpu_weight=cfg.cpu_weight,
        mem_weight=cfg.mem_weight,
    )
    derived = DerivedRates(
        per_vcpu_hour=rates["per_vcpu_hour"],
        per_gb_ram_hour=rates["per_gb_ram_hour"],
        storage_gb_month=storage_cost_items[0].rate_gb_month if storage_cost_items else 0.08,
    )

    assumptions = sorted({*parsed.assumptions})
    warnings = sorted({*parsed.warnings})

    binpacking = None
    if cfg.binpack:
        binpacking = simulate_binpack(
            parsed.workloads,
            instance_type=cfg.baseline_instance,
            node_cpu_vcpu=baseline["vcpu"],
            node_mem_gb=baseline["memory_gb"],
            overhead_cpu_vcpu=cfg.node_overhead_cpu,
            overhead_mem_gb=cfg.node_overhead_mem_gb,
        )
        assumptions.append(
            f"Bin-packing: reserved {cfg.node_overhead_cpu} vCPU and {cfg.node_overhead_mem_gb} GB per node for system/kube"
        )

    return EstimationResult(
        baseline=base_info,
        derived_rates=derived,
        workloads=workload_costs,
        storage=storage_cost_items,
        load_balancers=lb_cost_items,
        totals=totals,
        assumptions=assumptions,
        warnings=warnings,
        binpacking=binpacking,
    )
