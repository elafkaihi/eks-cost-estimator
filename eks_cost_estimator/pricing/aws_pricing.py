from __future__ import annotations

import json
from typing import Dict, Optional, Tuple


class LivePricingError(RuntimeError):
    pass


def _session(profile: Optional[str] = None):
    try:
        import boto3  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise LivePricingError(
            "boto3 is required for live pricing. Install with `pip install boto3`."
        ) from e
    if profile:
        import botocore  # type: ignore

        return boto3.session.Session(profile_name=profile)
    return boto3.session.Session()


def get_ec2_ondemand_price(
    *, region: str, instance_type: str, profile: Optional[str] = None
) -> float:
    """Fetch On-Demand hourly USD price for a Linux/Shared instance in the given region.

    Uses AWS Pricing GetProducts. Pricing API endpoints are hosted in us-east-1.
    """

    sess = _session(profile)
    client = sess.client("pricing", region_name="us-east-1")
    resp = client.get_products(
        ServiceCode="AmazonEC2",
        Filters=[
            {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
            {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
            {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
            {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
            {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
            {"Type": "TERM_MATCH", "Field": "licenseModel", "Value": "No License required"},
            {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
        ],
        MaxResults=100,
    )
    if not resp.get("PriceList"):
        raise LivePricingError(
            f"No pricing found for {instance_type} in {region}. Check instance type/region."
        )
    # Iterate items to find the first with OnDemand terms
    for pl in resp["PriceList"]:
        product = json.loads(pl)
        terms = product.get("terms", {})
        od = terms.get("OnDemand") or {}
        for _, term in od.items():
            price_dims = term.get("priceDimensions", {}) or {}
            for _, dim in price_dims.items():
                price = dim.get("pricePerUnit", {}).get("USD")
                if price is not None:
                    try:
                        return float(price)
                    except (TypeError, ValueError):  # noqa: PERF203
                        continue
    raise LivePricingError(
        f"On-Demand price not found for {instance_type} in {region} (Linux, Shared)."
    )


def get_instance_specs(
    *, region: str, instance_type: str, profile: Optional[str] = None
) -> Tuple[float, float]:
    """Fetch vCPU and memory (GB) for an instance type via DescribeInstanceTypes."""
    sess = _session(profile)
    ec2 = sess.client("ec2", region_name=region)
    resp = ec2.describe_instance_types(InstanceTypes=[instance_type])
    its = resp.get("InstanceTypes") or []
    if not its:
        raise LivePricingError(f"Instance type not found: {instance_type} in {region}")
    it = its[0]
    vcpu = float((it.get("VCpuInfo") or {}).get("DefaultVCpus") or 0)
    mem_mib = float((it.get("MemoryInfo") or {}).get("SizeInMiB") or 0)
    if vcpu <= 0 or mem_mib <= 0:
        raise LivePricingError("Invalid instance spec data from DescribeInstanceTypes")
    return vcpu, mem_mib / 1024.0


def get_live_baseline(
    *, region: str, instance: str, profile: Optional[str] = None
) -> Dict[str, float]:
    price = get_ec2_ondemand_price(region=region, instance_type=instance, profile=profile)
    vcpu, mem_gb = get_instance_specs(region=region, instance_type=instance, profile=profile)
    return {"price": price, "vcpu": vcpu, "memory_gb": mem_gb}

