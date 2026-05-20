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
from typing import Dict, List, Optional

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
    # Cost for this node
    uptime_hours: float = 0.0
    hourly_rate_usd: float = 0.0
    estimated_cost_usd: float = 0.0
    projected_8h_cost_usd: float = 0.0
    cost_note: str = ""
    # All testbed nodes (from AWS API)
    all_nodes: List[dict] = field(default_factory=list)
    total_cost_usd: float = 0.0
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

    hourly_rate  = HOURLY_RATES.get(instance_type, 0.0)
    uptime_hours = 0.0
    cost         = 0.0
    cost_note    = ""
    all_nodes: List[dict] = []
    total_cost   = 0.0
    projected_8h = 0.0

    # Query all testbed instances via AWS API (IAM role required)
    try:
        r = subprocess.run(
            ["aws", "ec2", "describe-instances",
             "--filters", "Name=tag:Name,Values=cka-coach-cp,cka-coach-worker",
             "--query", "Reservations[*].Instances[*].["
                        "Tags[?Key==`Name`]|[0].Value,"
                        "InstanceId,InstanceType,State.Name,"
                        "Placement.AvailabilityZone,LaunchTime,"
                        "PrivateIpAddress,PublicIpAddress]",
             "--output", "text"],
            capture_output=True, text=True, timeout=8,
        )
        now = datetime.now(timezone.utc)
        for line in (r.stdout or "").splitlines():
            parts = line.strip().split("\t")
            if len(parts) < 8:
                continue
            name, iid, itype, state, iaz, launch_str, priv, pub = parts[:8]
            rate = HOURLY_RATES.get(itype, 0.0)
            node_uptime = 0.0
            node_cost   = 0.0
            if state == "running" and launch_str and launch_str != "None":
                try:
                    launch_dt = datetime.fromisoformat(
                        launch_str.replace("Z", "+00:00")
                    )
                    node_uptime = (now - launch_dt).total_seconds() / 3600
                    node_cost   = node_uptime * rate
                    total_cost += node_cost
                    projected_8h += rate * 8
                except Exception:
                    pass
            all_nodes.append({
                "name": name, "instance_id": iid,
                "instance_type": itype, "state": state,
                "az": iaz, "private_ip": priv,
                "public_ip": pub if pub != "None" else "",
                "uptime_hours": round(node_uptime, 1),
                "hourly_rate": rate,
                "cost": round(node_cost, 4),
            })
        if all_nodes:
            cost_note = f"{region} | On Demand Linux"
            uptime_hours = next(
                (n["uptime_hours"] for n in all_nodes if n["instance_id"] == instance_id),
                0.0,
            )
            cost = next(
                (n["cost"] for n in all_nodes if n["instance_id"] == instance_id),
                0.0,
            )
    except Exception as e:
        cost_note = f"AWS API unavailable: {e}"

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
        projected_8h_cost_usd=round(projected_8h, 2),
        cost_note=cost_note,
        observed=bool(instance_id),
        note="AWS EC2 — evidence from IMDSv2 + AWS API",
        all_nodes=all_nodes,
        total_cost_usd=round(total_cost, 4),
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
