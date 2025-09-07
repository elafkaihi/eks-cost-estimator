from __future__ import annotations

import csv
import io
import json
from typing import Any

from rich.console import Console
from rich.table import Table

from eks_cost_estimator.models.results import EstimationResult


def render_table(result: EstimationResult) -> None:
    console = Console()

    table = Table(title="Compute Cost Estimates")
    table.add_column("Resource")
    table.add_column("Kind")
    table.add_column("Namespace")
    table.add_column("Replicas", justify="right")
    table.add_column("CPU/rep (vCPU)", justify="right")
    table.add_column("Mem/rep (GB)", justify="right")
    table.add_column("Hourly ($)", justify="right")
    table.add_column("Monthly ($)", justify="right")

    for w in result.workloads:
        table.add_row(
            w.name,
            w.kind,
            w.namespace or "",
            str(w.replicas),
            f"{w.cpu_vcpu_per_replica:.3f}",
            f"{w.memory_gb_per_replica:.3f}",
            f"{w.hourly:.4f}",
            f"{w.monthly:.2f}",
        )

    console.print(table)

    st_table = Table(title="Storage Cost Estimates")
    st_table.add_column("Resource")
    st_table.add_column("Kind")
    st_table.add_column("Namespace")
    st_table.add_column("Type")
    st_table.add_column("Size (GB)", justify="right")
    st_table.add_column("Replicas", justify="right")
    st_table.add_column("Multiplied By", justify="right")
    st_table.add_column("Rate $/GB-mo", justify="right")
    st_table.add_column("Hourly ($)", justify="right")
    st_table.add_column("Monthly ($)", justify="right")

    for s in result.storage:
        st_table.add_row(
            s.name,
            s.kind,
            s.namespace or "",
            (s.volume_type or ""),
            f"{s.size_gb:.3f}",
            str(s.replicas),
            str(s.multiply_by_replicas),
            f"{s.rate_gb_month:.3f}",
            f"{s.hourly:.4f}",
            f"{s.monthly:.2f}",
        )

    console.print(st_table)

    if result.load_balancers:
        lb_table = Table(title="Load Balancer Cost Estimates")
        lb_table.add_column("Service")
        lb_table.add_column("Namespace")
        lb_table.add_column("Type")
        lb_table.add_column("Hourly ($)", justify="right")
        lb_table.add_column("Monthly ($)", justify="right")
        for lb in result.load_balancers:
            lb_table.add_row(
                lb.name,
                lb.namespace or "",
                lb.service_type,
                f"{lb.hourly:.4f}",
                f"{lb.monthly:.2f}",
            )
        console.print(lb_table)

    total_table = Table(title="Totals")
    total_table.add_column("Metric")
    total_table.add_column("Value ($)", justify="right")
    total_table.add_row("Compute Hourly", f"{result.totals.compute_hourly:.4f}")
    total_table.add_row("Compute Monthly", f"{result.totals.compute_monthly:.2f}")
    total_table.add_row("Storage Hourly", f"{result.totals.storage_hourly:.4f}")
    total_table.add_row("Storage Monthly", f"{result.totals.storage_monthly:.2f}")
    total_table.add_row("LB Hourly", f"{result.totals.lb_hourly:.4f}")
    total_table.add_row("LB Monthly", f"{result.totals.lb_monthly:.2f}")
    total_table.add_row(
        "Grand Hourly",
        f"{(result.totals.compute_hourly + result.totals.storage_hourly + result.totals.lb_hourly):.4f}",
    )
    total_table.add_row(
        "Grand Monthly",
        f"{(result.totals.compute_monthly + result.totals.storage_monthly + result.totals.lb_monthly):.2f}",
    )
    console.print(total_table)

    # Bin-packing simulation (if present)
    if result.binpacking is not None:
        bp = result.binpacking
        bp_summary = Table(title="Bin-Packing Simulation Summary")
        bp_summary.add_column("Instance")
        bp_summary.add_column("Nodes", justify="right")
        bp_summary.add_column("CPU cap/node", justify="right")
        bp_summary.add_column("Mem cap/node (GB)", justify="right")
        bp_summary.add_column("CPU util", justify="right")
        bp_summary.add_column("Mem util", justify="right")
        bp_summary.add_row(
            bp.instance_type,
            str(bp.node_count),
            f"{bp.cpu_capacity_per_node:.2f}",
            f"{bp.mem_capacity_gb_per_node:.2f}",
            f"{bp.cpu_utilization*100:.1f}%",
            f"{bp.mem_utilization*100:.1f}%",
        )
        console.print(bp_summary)

        bp_nodes = Table(title="Bin-Packing: Node Allocation Details")
        bp_nodes.add_column("Node")
        bp_nodes.add_column("CPU used / cap", justify="right")
        bp_nodes.add_column("Mem used / cap (GB)", justify="right")
        bp_nodes.add_column("Allocations")
        for n in bp.nodes:
            allocs = ", ".join(
                f"{a.workload} x{a.replicas}" if a.namespace is None else f"{a.workload} ({a.namespace}) x{a.replicas}"
                for a in n.allocations
            )
            bp_nodes.add_row(
                f"node-{n.index}",
                f"{n.cpu_used:.2f} / {n.cpu_capacity:.2f}",
                f"{n.mem_used_gb:.2f} / {n.mem_capacity_gb:.2f}",
                allocs,
            )
        console.print(bp_nodes)


def render_json(result: EstimationResult) -> str:
    data = result.model_dump()
    return json.dumps(data, indent=2, sort_keys=True)


def render_csv(result: EstimationResult) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Resource",
            "Kind",
            "Namespace",
            "Replicas",
            "CPU/rep (vCPU)",
            "Mem/rep (GB)",
            "Hourly ($)",
            "Monthly ($)",
        ]
    )
    for w in result.workloads:
        writer.writerow(
            [
                w.name,
                w.kind,
                w.namespace or "",
                w.replicas,
                f"{w.cpu_vcpu_per_replica:.3f}",
                f"{w.memory_gb_per_replica:.3f}",
                f"{w.hourly:.4f}",
                f"{w.monthly:.2f}",
            ]
        )
    return output.getvalue()
