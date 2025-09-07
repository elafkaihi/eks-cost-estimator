from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional

import typer

from eks_cost_estimator.core.orchestrator import EstimationConfig, orchestrate
from eks_cost_estimator.output.render import render_csv, render_json, render_table


app = typer.Typer(add_completion=False, help="EKS Cost Estimator CLI")


@app.command("estimate")
def estimate(
    files: List[Path] = typer.Argument(..., help="Kubernetes YAML manifest files"),
    region: str = typer.Option("eu-west-3", "--region", help="AWS region"),
    baseline_instance: str = typer.Option(
        "m6i.large", "--baseline-instance", help="Baseline EC2 instance type"
    ),
    baseline_price: Optional[float] = typer.Option(
        None,
        "--baseline-price",
        help="Override baseline hourly price (USD)",
    ),
    cpu_weight: float = typer.Option(0.60, "--cpu-weight", help="CPU price weight"),
    mem_weight: float = typer.Option(0.40, "--mem-weight", help="Memory price weight"),
    output: str = typer.Option(
        "table",
        "--output",
        case_sensitive=False,
        help="Output format: table|json|csv",
    ),
    detailed: bool = typer.Option(
        False, "--detailed/--no-detailed", help="Include detailed output where applicable"
    ),
    elb_hourly_price: float = typer.Option(
        0.0225,
        "--elb-hourly-price",
        help="Per LoadBalancer hourly price (USD). LCUs excluded (MVP)",
    ),
    binpack: bool = typer.Option(
        False,
        "--binpack/--no-binpack",
        help="Simulate bin-packing of pods onto nodes of the baseline instance",
    ),
    node_overhead_cpu: float = typer.Option(
        0.2,
        "--node-overhead-cpu",
        help="Reserved vCPU per node for system/kube",
    ),
    node_overhead_mem_gb: float = typer.Option(
        0.5,
        "--node-overhead-mem-gb",
        help="Reserved memory (GB) per node for system/kube",
    ),
    live_pricing: bool = typer.Option(
        False,
        "--live-pricing/--no-live-pricing",
        help="Use AWS Pricing API + EC2 to fetch live price/specs",
    ),
    aws_profile: Optional[str] = typer.Option(
        None,
        "--aws-profile",
        help="AWS named profile to use for live pricing (optional)",
    ),
):
    """Estimate EKS compute and storage costs from manifests before deployment."""
    try:
        cfg = EstimationConfig(
            region=region,
            baseline_instance=baseline_instance,
            baseline_price_override=baseline_price,
            cpu_weight=cpu_weight,
            mem_weight=mem_weight,
            detailed=detailed,
            elb_hourly_price=elb_hourly_price,
            binpack=binpack,
            node_overhead_cpu=node_overhead_cpu,
            node_overhead_mem_gb=node_overhead_mem_gb,
            live_pricing=live_pricing,
            aws_profile=aws_profile,
        )
        result = orchestrate([str(p) for p in files], cfg)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Fatal error: {exc}", err=True)
        raise typer.Exit(code=1)

    fmt = output.lower()
    if fmt == "table":
        render_table(result)
    elif fmt == "json":
        typer.echo(render_json(result))
    elif fmt == "csv":
        typer.echo(render_csv(result))
    else:
        typer.echo("Unknown output format. Use table|json|csv.", err=True)
        raise typer.Exit(code=2)

    raise typer.Exit(code=0)


if __name__ == "__main__":  # pragma: no cover
    app()
