"""
observer_platform.py

Detects the cloud platform cka-coach is running on and collects
L0 evidence from the hypervisor metadata service.

Supported platforms:
- AWS EC2    — IMDSv2 at 169.254.169.254
- GCP        — metadata at metadata.google.internal
- KIND       — local Docker, no cloud metadata
- Unknown    — no metadata service reachable

Cost data:
- AWS: calculated from instance type + uptime using known On Demand rates
- GCP: placeholder (future)
- KIND / Unknown: free or not applicable

ELS layer: L0 — Virtual Hardware / Cloud Infrastructure
"""

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from testbed.phase_evidence import HOURLY_RATES


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

PLATFORM_AWS     = "aws"
PLATFORM_GCP     = "gcp"
PLATFORM_KIND    = "kind"
PLATFORM_UNKNOWN = "unknown"


def _curl(url: str, headers: list = None, method: str = "GET",
          timeout: int = 2) -> tuple[bool, str]:
    cmd = ["curl", "-sf", "--max-time", str(timeout)]
    if method == "PUT":
        cmd += ["-X", "PUT"]
    for h in (headers or []):
        cmd += ["-H", h]
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 1)
        return r.returncode == 0 and bool(r.stdout.strip()), r.stdout.strip()
    except Exception:
        return False, ""


def _get_imdsv2_token() -> str:
    ok, token = _curl(
        "http://169.254.169.254/latest/api/token",
        headers=["X-aws-ec2-metadata-token-ttl-seconds: 21600"],
        method="PUT",
        timeout=2,
    )
    return token if ok else ""


def _is_kind() -> bool:
    try:
        r = subprocess.run(
            ["kubectl", "get", "nodes", "-o", "jsonpath={.items[*].spec.providerID}"],
            capture_output=True, text=True, timeout=5,
        )
        return "kind://" in (r.stdout or "")
    except Exception:
        return False


def detect_platform() -> str:
    """Detect which cloud platform cka-coach is running on."""
    # KIND check first — it has no metadata service
    if _is_kind():
        return PLATFORM_KIND

    # AWS — try IMDSv2 token
    token = _get_imdsv2_token()
    if token:
        return PLATFORM_AWS

    # GCP — metadata server responds to a specific header
    ok, _ = _curl(
        "http://metadata.google.internal/computeMetadata/v1/instance/id",
        headers=["Metadata-Flavor: Google"],
        timeout=2,
    )
    if ok:
        return PLATFORM_GCP

    return PLATFORM_UNKNOWN


# ---------------------------------------------------------------------------
# L0 instance metadata
# ---------------------------------------------------------------------------

@dataclass
class L0InstanceMetadata:
    platform: str = PLATFORM_UNKNOWN
    instance_id: str = ""
    instance_type: str = ""
    ami_id: str = ""
    availability_zone: str = ""
    region: str = ""
    private_ip: str = ""
    public_ip: str = ""
    # Cost
    uptime_hours: float = 0.0
    hourly_rate_usd: float = 0.0
    estimated_cost_usd: float = 0.0
    projected_8h_cost_usd: float = 0.0
    cost_note: str = ""
    # Evidence quality
    observed: bool = False
    note: str = ""


def _collect_aws_metadata() -> L0InstanceMetadata:
    token = _get_imdsv2_token()
    if not token:
        return L0InstanceMetadata(
            platform=PLATFORM_AWS,
            note="IMDSv2 token not available — metadata service unreachable",
        )

    def meta(path: str) -> str:
        ok, val = _curl(
            f"http://169.254.169.254/latest/meta-data/{path}",
            headers=[f"X-aws-ec2-metadata-token: {token}"],
        )
        return val if ok else ""

    instance_id    = meta("instance-id")
    instance_type  = meta("instance-type")
    ami_id         = meta("ami-id")
    az             = meta("placement/availability-zone")
    region         = meta("placement/region")
    private_ip     = meta("local-ipv4")
    public_ip      = meta("public-ipv4")

    # Launch time for cost calculation
    ok, launch_raw = _curl(
        "http://169.254.169.254/latest/meta-data/",
        headers=[f"X-aws-ec2-metadata-token: {token}"],
    )

    # Try to get launch time via AWS CLI (available if IAM role attached)
    uptime_hours = 0.0
    hourly_rate  = HOURLY_RATES.get(instance_type, 0.0)
    cost         = 0.0
    cost_note    = ""

    try:
        r = subprocess.run(
            ["aws", "ec2", "describe-instances",
             "--filters", f"Name=private-ip-address,Values={private_ip}",
             "--query", "Reservations[0].Instances[0].LaunchTime",
             "--output", "text"],
            capture_output=True, text=True, timeout=8,
        )
        launch_str = (r.stdout or "").strip()
        if launch_str and launch_str != "None":
            launch_dt = datetime.fromisoformat(
                launch_str.replace("Z", "+00:00")
            )
            uptime_hours = (
                datetime.now(timezone.utc) - launch_dt
            ).total_seconds() / 3600
            cost = uptime_hours * hourly_rate
            cost_note = (
                f"On Demand Linux {instance_type} in {region or az[:len(az)-1] if az else 'unknown'}"
            )
    except Exception:
        cost_note = "Launch time not available — AWS CLI or IAM role may not be configured"

    return L0InstanceMetadata(
        platform=PLATFORM_AWS,
        instance_id=instance_id,
        instance_type=instance_type,
        ami_id=ami_id,
        availability_zone=az,
        region=region,
        private_ip=private_ip,
        public_ip=public_ip,
        uptime_hours=round(uptime_hours, 1),
        hourly_rate_usd=hourly_rate,
        estimated_cost_usd=round(cost, 4),
        projected_8h_cost_usd=round(hourly_rate * 8, 2),
        cost_note=cost_note,
        observed=bool(instance_id),
        note="AWS EC2 — evidence from IMDSv2 metadata service",
    )


def _collect_gcp_metadata() -> L0InstanceMetadata:
    def meta(path: str) -> str:
        ok, val = _curl(
            f"http://metadata.google.internal/computeMetadata/v1/instance/{path}",
            headers=["Metadata-Flavor: Google"],
        )
        return val if ok else ""

    instance_id   = meta("id")
    instance_type = meta("machine-type").rsplit("/", 1)[-1]
    zone          = meta("zone").rsplit("/", 1)[-1]
    region        = "-".join(zone.split("-")[:-1]) if zone else ""
    private_ip    = meta("network-interfaces/0/ip")
    public_ip     = meta("network-interfaces/0/access-configs/0/external-ip")

    return L0InstanceMetadata(
        platform=PLATFORM_GCP,
        instance_id=instance_id,
        instance_type=instance_type,
        ami_id="",                    # GCP uses images not AMIs
        availability_zone=zone,
        region=region,
        private_ip=private_ip,
        public_ip=public_ip,
        cost_note="GCP cost visibility coming soon",
        observed=bool(instance_id),
        note="GCP Compute Engine — evidence from instance metadata service",
    )


def _collect_kind_metadata() -> L0InstanceMetadata:
    return L0InstanceMetadata(
        platform=PLATFORM_KIND,
        cost_note="KIND runs on local Docker — no cloud compute charges",
        observed=True,
        note="KIND — Kubernetes in Docker on local machine. No cloud infrastructure cost.",
    )


def collect_l0_metadata() -> L0InstanceMetadata:
    """
    Detect platform and collect L0 instance metadata.
    Safe to call from any environment — returns honest unknown if nothing is detectable.
    """
    platform = detect_platform()
    if platform == PLATFORM_AWS:
        return _collect_aws_metadata()
    if platform == PLATFORM_GCP:
        return _collect_gcp_metadata()
    if platform == PLATFORM_KIND:
        return _collect_kind_metadata()
    return L0InstanceMetadata(
        platform=PLATFORM_UNKNOWN,
        note="No cloud metadata service detected — running on unknown infrastructure or local machine.",
        cost_note="No cloud charges detected",
    )
