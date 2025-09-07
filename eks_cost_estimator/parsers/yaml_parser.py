from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import yaml

from eks_cost_estimator.core.exceptions import ParseError
from eks_cost_estimator.models.resources import ServiceItem, StorageItem, WorkloadItem
from eks_cost_estimator.utils.units import parse_cpu, parse_mem_gb


SUPPORTED_WORKLOAD_KINDS = {
    "Deployment",
    "StatefulSet",
    "DaemonSet",
    "Job",
    "CronJob",
    "Pod",
}

SUPPORTED_SERVICE_KINDS = {"Service"}


@dataclass(slots=True)
class ParseOutput:
    workloads: List[WorkloadItem]
    storage: List[StorageItem]
    services: List[ServiceItem]
    assumptions: List[str]
    warnings: List[str]


def _ensure_list(x: Optional[Iterable]) -> List:
    if not x:
        return []
    return list(x)


def parse_files(paths: List[str]) -> ParseOutput:
    workloads: List[WorkloadItem] = []
    storage: List[StorageItem] = []
    assumptions: List[str] = []
    warnings: List[str] = []
    services: List[ServiceItem] = []

    # Collect standalone PVCs: (name, namespace) -> (size_gb, storageClassName)
    standalone_pvcs: Dict[Tuple[str, Optional[str]], Tuple[float, Optional[str]]] = {}
    # Track which PVC names are referenced by Deployments (shared)
    deployment_pvc_refs: set[Tuple[str, Optional[str]]] = set()

    for p in paths:
        path = Path(p)
        if not path.exists():
            raise ParseError(f"File not found: {path}")
        try:
            with path.open("r", encoding="utf-8") as f:
                docs = list(yaml.safe_load_all(f))
        except yaml.YAMLError as e:  # noqa: BLE001
            raise ParseError(f"YAML parse error in {path}: {e}") from e

        for doc in docs:
            if not doc or not isinstance(doc, dict):
                continue
            kind = doc.get("kind")
            meta = doc.get("metadata", {}) or {}
            name = meta.get("name", "unnamed")
            namespace = meta.get("namespace")

            if kind == "PersistentVolumeClaim":
                spec = doc.get("spec", {}) or {}
                resources = spec.get("resources", {}) or {}
                requests = resources.get("requests", {}) or {}
                storage_req = requests.get("storage")
                if storage_req is None:
                    warnings.append(
                        f"PVC {name}: missing storage request; skipping from storage totals"
                    )
                    continue
                size_gb = _safe_parse_mem(storage_req, warnings, context=f"PVC {name}")
                scn = spec.get("storageClassName")
                standalone_pvcs[(name, namespace)] = (size_gb, scn)
                continue

            if kind in SUPPORTED_WORKLOAD_KINDS:
                wls, st, assm, warns, dep_refs = _parse_workload(doc)
                workloads.append(wls)
                storage.extend(st)
                assumptions.extend(assm)
                warnings.extend(warns)
                for ref in dep_refs:
                    deployment_pvc_refs.add((ref, wls.namespace))
                continue

            if kind in SUPPORTED_SERVICE_KINDS:
                spec = doc.get("spec", {}) or {}
                svc_type = (spec.get("type") or "ClusterIP")
                if str(svc_type).lower() == "loadbalancer":
                    services.append(
                        ServiceItem(
                            name=name,
                            namespace=namespace,
                            kind=kind,
                            service_type=str(svc_type),
                            annotations=(doc.get("metadata", {}) or {}).get("annotations"),
                        )
                    )
                continue

    # Convert standalone PVCs to storage items, honoring shared rule for Deployments
    for (pvc_name, ns), (size_gb, scn) in standalone_pvcs.items():
        shared = (pvc_name, ns) in deployment_pvc_refs
        storage.append(
            StorageItem(
                name=pvc_name,
                namespace=ns,
                kind="PersistentVolumeClaim",
                size_gb=size_gb,
                replicas=1,  # standalone PVC is a single volume resource
                multiply_by_replicas=1 if shared else 1,
                storage_class_name=scn,
                volume_type=_derive_volume_type_from_scn(scn),
                note="shared-deployment" if shared else None,
            )
        )

    return ParseOutput(
        workloads=workloads,
        storage=storage,
        services=services,
        assumptions=assumptions,
        warnings=warnings,
    )


def _parse_workload(doc: Dict) -> Tuple[
    WorkloadItem, List[StorageItem], List[str], List[str], List[str]
]:
    kind: str = doc.get("kind", "Unknown")
    meta = doc.get("metadata", {}) or {}
    name: str = meta.get("name", "unnamed")
    namespace: Optional[str] = meta.get("namespace")
    spec = doc.get("spec", {}) or {}
    assumptions: List[str] = []
    warnings: List[str] = []
    storage_items: List[StorageItem] = []
    dep_pvc_refs: List[str] = []

    # Determine pod template depending on kind
    pod_template = None
    replicas = 1

    if kind in {"Deployment", "StatefulSet"}:
        replicas = int(spec.get("replicas", 1) or 1)
        pod_template = spec.get("template")
    elif kind == "DaemonSet":
        replicas = 1  # unknown; assumption
        assumptions.append(f"DaemonSet {name}: assumed replicas=1 for calculation")
        pod_template = spec.get("template")
    elif kind == "Job":
        replicas = 1
        pod_template = spec.get("template")
    elif kind == "CronJob":
        replicas = 1
        assumptions.append(f"CronJob {name}: treated as single Job (replicas=1)")
        job_template = spec.get("jobTemplate", {}).get("spec", {})
        pod_template = job_template.get("template")
    elif kind == "Pod":
        replicas = 1
        pod_template = {"spec": spec}
    else:
        pod_template = spec.get("template")

    containers = _ensure_list(pod_template.get("spec", {}).get("containers")) if pod_template else []
    init_containers = _ensure_list(
        pod_template.get("spec", {}).get("initContainers")
    ) if pod_template else []

    # Sum requests across all containers and initContainers
    total_cpu_vcpu = 0.0
    total_mem_gb = 0.0

    for c in containers + init_containers:
        cres = (c.get("resources", {}) or {}).get("requests", {}) or {}
        cpu = cres.get("cpu")
        mem = cres.get("memory")
        missing_any = False
        if cpu is None:
            cpu = "100m"
            missing_any = True
        if mem is None:
            mem = "128Mi"
            missing_any = True
        if missing_any:
            warnings.append(
                f"{kind} {name}: container '{c.get('name','unnamed')}' missing requests; defaulted to cpu=100m, memory=128Mi"
            )
        try:
            total_cpu_vcpu += parse_cpu(cpu)
        except ValueError:
            warnings.append(f"{kind} {name}: unknown CPU unit '{cpu}', defaulted to 0.1")
            total_cpu_vcpu += 0.1
        try:
            total_mem_gb += parse_mem_gb(mem)
        except ValueError:
            warnings.append(
                f"{kind} {name}: unknown memory unit '{mem}', defaulted to 0.128Gi"
            )
            total_mem_gb += parse_mem_gb("128Mi")

    # Volume claim templates in StatefulSet
    if kind == "StatefulSet":
        vcts = _ensure_list(spec.get("volumeClaimTemplates"))
        for tpl in vcts:
            vct_meta = tpl.get("metadata", {}) or {}
            vct_name = vct_meta.get("name", "vct")
            vct_spec = tpl.get("spec", {}) or {}
            vct_res = (vct_spec.get("resources", {}) or {}).get("requests", {}) or {}
            vct_storage = vct_res.get("storage")
            if vct_storage is None:
                warnings.append(
                    f"StatefulSet {name} volumeClaimTemplates '{vct_name}' missing storage; skipping"
                )
            else:
                size_gb = _safe_parse_mem(
                    vct_storage, warnings, context=f"StatefulSet {name} vct {vct_name}"
                )
                storage_items.append(
                    StorageItem(
                        name=f"{name}-{vct_name}",
                        namespace=namespace,
                        kind="StatefulSetVolumeClaimTemplate",
                        size_gb=size_gb,
                        replicas=replicas,
                        multiply_by_replicas=replicas,
                        storage_class_name=vct_spec.get("storageClassName"),
                        volume_type=_derive_volume_type_from_scn(vct_spec.get("storageClassName")),
                        note="statefulset-vct",
                    )
                )

    # PVC references in pod template (for Deployment shared detection)
    volumes = _ensure_list(pod_template.get("spec", {}).get("volumes")) if pod_template else []
    for v in volumes:
        pvc = (v.get("persistentVolumeClaim") or {})
        claim = pvc.get("claimName")
        if claim and kind == "Deployment":
            dep_pvc_refs.append(claim)

    wl = WorkloadItem(
        name=name,
        namespace=namespace,
        kind=kind,
        replicas=replicas,
        cpu_vcpu_per_replica=total_cpu_vcpu,
        memory_gb_per_replica=total_mem_gb,
    )

    return wl, storage_items, assumptions, warnings, dep_pvc_refs


def _safe_parse_mem(val: str, warnings: List[str], *, context: str) -> float:
    try:
        return parse_mem_gb(val)
    except ValueError:
        warnings.append(f"{context}: unknown memory unit '{val}', skipping")
        return 0.0


def _derive_volume_type_from_scn(storage_class_name: Optional[str]) -> Optional[str]:
    try:
        from eks_cost_estimator.pricing.ebs import detect_volume_type
    except Exception:  # pragma: no cover
        return None
    return detect_volume_type(storage_class_name)
