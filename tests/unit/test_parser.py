from __future__ import annotations

from pathlib import Path

from eks_cost_estimator.parsers.yaml_parser import parse_files


FIXTURES = Path("tests/fixtures")


def test_parser_multicontainer_sum_and_pvc(tmp_path):
    out = parse_files([str(FIXTURES / "deployment.yaml")])
    # One workload Deployment
    assert len(out.workloads) == 1
    w = out.workloads[0]
    # containers: 250m + default(100m) = 350m = 0.35 vCPU; memory 512Mi + 128Mi = 640Mi
    assert w.kind == "Deployment"
    assert w.replicas == 3
    assert 0.34 < w.cpu_vcpu_per_replica < 0.36
    assert 0.66 < w.memory_gb_per_replica < 0.68
    # PVC referenced by Deployment should be treated as shared; parsed as standalone later
    out2 = parse_files([str(FIXTURES / "pvc.yaml"), str(FIXTURES / "deployment.yaml")])
    # One workload + one PVC
    assert any(s.kind == "PersistentVolumeClaim" for s in out2.storage)
    pvc = [s for s in out2.storage if s.kind == "PersistentVolumeClaim"][0]
    assert pvc.multiply_by_replicas == 1


def test_statefulset_vct_multiply():
    out = parse_files([str(FIXTURES / "statefulset_with_vct.yaml")])
    assert len(out.workloads) == 1
    w = out.workloads[0]
    assert w.kind == "StatefulSet"
    assert w.replicas == 2
    # storage from volumeClaimTemplates should multiply by replicas
    assert any(s.kind == "StatefulSetVolumeClaimTemplate" for s in out.storage)
    st = [s for s in out.storage if s.kind == "StatefulSetVolumeClaimTemplate"][0]
    assert st.multiply_by_replicas == 2
    assert st.replicas == 2
