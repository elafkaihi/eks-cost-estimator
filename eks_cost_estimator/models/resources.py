from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class WorkloadItem(BaseModel):
    name: str
    namespace: Optional[str] = None
    kind: str
    replicas: int
    cpu_vcpu_per_replica: float = Field(ge=0)
    memory_gb_per_replica: float = Field(ge=0)


class StorageItem(BaseModel):
    name: str
    namespace: Optional[str] = None
    kind: str  # PersistentVolumeClaim or StatefulSetVolumeClaimTemplate
    size_gb: float
    replicas: int = 1
    multiply_by_replicas: int = 1
    storage_class_name: Optional[str] = None
    volume_type: Optional[str] = None  # e.g., gp3, gp2, io1, io2, st1, sc1, standard
    note: Optional[str] = None


class ServiceItem(BaseModel):
    name: str
    namespace: Optional[str] = None
    kind: str  # Service
    service_type: str  # ClusterIP | NodePort | LoadBalancer
    annotations: dict[str, str] | None = None
