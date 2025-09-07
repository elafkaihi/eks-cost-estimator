# EKS Cost Estimator

A Python 3.11 CLI to estimate EKS compute and storage costs from Kubernetes YAML manifests before deployment.

It parses workloads and PVCs, normalizes resource requests, derives vCPU and RAM rates from a configurable baseline EC2 instance, and outputs per-resource and total costs as a table, JSON, or CSV.

## What it does

- Parses multi-document Kubernetes YAML for these kinds: Deployment, StatefulSet, DaemonSet, Job, CronJob, Pod, and PersistentVolumeClaim.
- Aggregates CPU and memory requests across all containers AND initContainers per Pod.
- Normalizes CPU to vCPUs and Memory to GB (decimal, 1 GB = 1e9 bytes). Supports CPU `m` units and memory `Ki/Mi/Gi/Ti` and `KB/MB/GB/TB`.
- Derives per-vCPU-hour and per-GB-RAM-hour from a baseline EC2 instance using weights: `cpu_weight` (default 0.60) and `mem_weight` (default 0.40).
- Estimates compute costs (per resource, monthly = hourly * 720) and storage costs. Supports EBS volume types via `storageClassName` (gp3, gp2, io1, io2, st1, sc1, standard) with per-GB-month defaults; gp3 default $0.08/GB-month. IOPS/throughput pricing excluded in MVP.
- Service/ELB costs: Services of type LoadBalancer incur a flat hourly per-LB charge (default $0.0225/h; LCUs not included in MVP).
- Handles StatefulSet `volumeClaimTemplates` (multiplied by replicas). Standalone PVCs referenced by a Deployment are treated as shared and not multiplied by replicas.
- Emits clear warnings for defaults (missing requests), DaemonSet/CronJob assumptions, and unknown units.
- Optional bin-packing simulation: pack pods onto nodes of the baseline instance using a simple best-fit heuristic to estimate node count and utilization.

## Assumptions and limitations (MVP)

- DaemonSet: replicas unknown; assumes 1 for MVP and annotates the output.
- CronJob: treated as a Job with replicas=1 for MVP.
- Storage: per-GB-month rate varies by EBS type (detected from `storageClassName` when present). IOPS/throughput pricing for io1/io2 not included in MVP.
- No bin-packing, networking egress, or CloudWatch costs in MVP. LoadBalancer hourly only; LCUs and data processing excluded.
- Live pricing: optionally query AWS Pricing API and EC2 DescribeInstanceTypes for baseline price/specs. Falls back to local cache if unavailable.
  - Bin-packing: when enabled, assumes per-node reserved overhead (defaults: 0.2 vCPU + 0.5 GB) and packs by requests using best-fit; no daemonset overheads or max pods constraints yet.

## How pricing is derived

Given a baseline instance (default `m6i.large`), with hourly price `P`, vCPUs `V`, and memory `M (GB)`:

- per_vcpu_hour = `(P * cpu_weight) / V`
- per_gb_ram_hour = `(P * mem_weight) / M`

Per-replica hourly = `vCPU_req * per_vcpu_hour + GB_req * per_gb_ram_hour`.
Resource hourly = `per-replica hourly * replicas`.
Monthly = `hourly * 720` (30 days).

Storage monthly = `size_gb * rate_gb_month * multiplier`. Defaults: `rate_gb_month=0.08`. StatefulSet `volumeClaimTemplates` are multiplied by replicas; standalone PVC referenced by Deployment is not multiplied.

## Install

```bash
python -m pip install -e .
pipx install .  # optional: installs console script `eks-cost-estimator`
pre-commit install
# Optional for live pricing
python -m pip install -e .[aws]  # installs boto3
```

## Usage

Using module entry:

```bash
python -m eks_cost_estimator.cli.main estimate tests/fixtures/deployment.yaml --output table
```

Console script (if installed):

```bash
eks-cost-estimator estimate tests/fixtures/deployment.yaml --output json
```

### Options

- `--region` default `eu-west-3`
- `--baseline-instance` default `m6i.large`
- `--baseline-price` override hourly price (USD)
- `--cpu-weight` default `0.6`
- `--mem-weight` default `0.4`
- `--output table|json|csv` default `table`
- `--detailed/--no-detailed` reserved for future detail toggles
- `--elb-hourly-price` per LoadBalancer hourly price, default `0.0225`
- `--binpack/--no-binpack` enable bin-packing simulation (default: disabled)
- `--node-overhead-cpu` reserved vCPU per node (default: `0.2`)
- `--node-overhead-mem-gb` reserved memory GB per node (default: `0.5`)
- `--live-pricing/--no-live-pricing` fetch baseline price/specs from AWS Pricing API (requires `boto3` and AWS credentials)
- `--aws-profile` AWS named profile to use for live pricing

### JSON output example

```json
{
  "baseline": {"region": "eu-west-3", "instance_type": "m6i.large", "price": 0.119, "vcpu": 2, "memory_gb": 8, "cpu_weight": 0.6, "mem_weight": 0.4},
  "derived_rates": {"per_vcpu_hour": 0.0288, "per_gb_ram_hour": 0.0048, "storage_gb_month": 0.08},
  "workloads": [
    {"name": "web", "kind": "Deployment", "replicas": 3, "cpu_vcpu_per_replica": 0.35, "memory_gb_per_replica": 0.69, "hourly": 0.04, "monthly": 28.80}
  ],
  "storage": [
    {"name": "shared-cache", "kind": "PersistentVolumeClaim", "size_gb": 50.0, "replicas": 1, "multiply_by_replicas": 1, "monthly": 4.00, "hourly": 0.0056}
  ],
  "binpacking": {
    "instance_type": "m6i.large",
    "node_count": 2,
    "cpu_capacity_per_node": 1.8,
    "mem_capacity_gb_per_node": 7.5,
    "overhead_cpu_vcpu": 0.2,
    "overhead_mem_gb": 0.5,
    "cpu_utilization": 0.75,
    "mem_utilization": 0.73,
    "nodes": [
      {"index": 1, "cpu_used": 1.8, "mem_used_gb": 7.5, "allocations": [{"workload": "web", "replicas": 2, "cpu_vcpu": 2.0, "memory_gb": 8.0}]}
    ]
  },
  "totals": {"compute_hourly": 0.04, "compute_monthly": 28.80, "storage_hourly": 0.0056, "storage_monthly": 4.00},
  "assumptions": ["CronJob foo: treated as single Job (replicas=1)", "DaemonSet bar: assumed replicas=1 for calculation"],
  "warnings": ["Deployment web: container 'sidecar' missing requests; defaulted to cpu=100m, memory=128Mi"]
}
```

## CI

GitHub Actions workflow runs pre-commit, mypy, and pytest with coverage on Python 3.11.
