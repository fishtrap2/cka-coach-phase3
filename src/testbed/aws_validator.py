"""
aws_validator.py

AWS environment validation for the cka-coach testbed workflow.

Supports two modes:
- Mode 1: detect and validate an existing environment
- Mode 2: guided provisioning for new students (validation only — provisioning
  is handled interactively in the UI)

ELS layer: L0 — Virtual Hardware / Cloud Infrastructure

All AWS calls use boto3. No AWS calls are made unless explicitly invoked.
"""

import subprocess
import json
from typing import Any, Dict, List, Optional, Tuple

from testbed.testbed_state import (
    CheckResult,
    NodeState,
    TestbedState,
)

# ---------------------------------------------------------------------------
# Expected instance tags for the reference environment.
# Teardown is scoped to these tags — never touches untagged instances.
# ---------------------------------------------------------------------------

EXPECTED_TAGS = ["cka-coach-cp", "cka-coach-worker"]
EXPECTED_ROLES = {
    "cka-coach-cp": "control-plane",
    "cka-coach-worker": "worker",
}

MIN_INSTANCE_TYPES = {"t3.medium", "t3.large", "t3.xlarge", "m5.large", "m5.xlarge"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_aws(args: List[str]) -> Tuple[bool, Dict[str, Any], str]:
    """
    Run an AWS CLI command and return (success, parsed_json, error_text).
    Never uses shell=True.
    """
    cmd = ["aws"] + args + ["--output", "json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return False, {}, result.stderr.strip()
        return True, json.loads(result.stdout) if result.stdout.strip() else {}, ""
    except FileNotFoundError:
        return False, {}, "aws CLI not found — install with: brew install awscli"
    except subprocess.TimeoutExpired:
        return False, {}, "aws CLI timed out"
    except json.JSONDecodeError as e:
        return False, {}, f"failed to parse aws output: {e}"


def _tag_value(instance: Dict, key: str = "Name") -> str:
    for tag in instance.get("Tags", []):
        if tag.get("Key") == key:
            return tag.get("Value", "")
    return ""


def _parse_instances(reservations: List[Dict]) -> List[Dict]:
    instances = []
    for reservation in reservations:
        for instance in reservation.get("Instances", []):
            instances.append(instance)
    return instances


# ---------------------------------------------------------------------------
# AWS credential check
# ---------------------------------------------------------------------------

def check_aws_credentials() -> CheckResult:
    """Verify AWS CLI is configured and credentials are valid."""
    ok, data, err = _run_aws(["sts", "get-caller-identity"])
    if not ok:
        return CheckResult(
            name="AWS credentials",
            passed=False,
            detail=err,
            remediation="Run `aws configure` and enter a valid Access Key ID and Secret Access Key.",
            els_layer="L0",
            command="aws sts get-caller-identity",
        )
    arn = data.get("Arn", "unknown")
    # Warn if running as root
    is_root = ":root" in arn
    detail = f"Authenticated as {arn}"
    if is_root:
        detail += " — WARNING: running as root user, consider using an IAM user instead"
    return CheckResult(
        name="AWS credentials",
        passed=True,
        detail=detail,
        els_layer="L0",
        command="aws sts get-caller-identity",
    )


# ---------------------------------------------------------------------------
# Instance detection
# ---------------------------------------------------------------------------

def detect_instances() -> Tuple[List[NodeState], List[CheckResult]]:
    """
    Detect cka-coach instances by Name tag.
    Returns (nodes, checks).
    """
    checks = []
    ok, data, err = _run_aws([
        "ec2", "describe-instances",
        "--filters", "Name=tag:Name,Values=cka-coach-cp,cka-coach-worker",
    ])

    if not ok:
        checks.append(CheckResult(
            name="Detect instances",
            passed=False,
            detail=err,
            remediation="Check AWS CLI credentials and region with `aws sts get-caller-identity`.",
            els_layer="L0",
            command="aws ec2 describe-instances --filters Name=tag:Name,Values=cka-coach-cp,cka-coach-worker",
        ))
        return [], checks

    instances = _parse_instances(data.get("Reservations", []))
    if not instances:
        checks.append(CheckResult(
            name="Detect instances",
            passed=False,
            detail="No instances tagged cka-coach-cp or cka-coach-worker found in this region.",
            remediation="Launch two EC2 instances and tag them Name=cka-coach-cp and Name=cka-coach-worker.",
            els_layer="L0",
            command="aws ec2 describe-instances",
        ))
        return [], checks

    nodes = []
    for instance in instances:
        name = _tag_value(instance)
        role = EXPECTED_ROLES.get(name, "worker")
        nodes.append(NodeState(
            name=name,
            role=role,
            instance_id=instance.get("InstanceId", ""),
            public_ip=instance.get("PublicIpAddress", ""),
            private_ip=instance.get("PrivateIpAddress", ""),
            instance_type=instance.get("InstanceType", ""),
            state=instance.get("State", {}).get("Name", ""),
        ))

    found_names = [node.name for node in nodes]
    checks.append(CheckResult(
        name="Detect instances",
        passed=True,
        detail=f"Found: {', '.join(found_names)}",
        els_layer="L0",
        command="aws ec2 describe-instances",
    ))
    return nodes, checks


# ---------------------------------------------------------------------------
# Per-node validation checks
# ---------------------------------------------------------------------------

def check_instance_running(node: NodeState) -> CheckResult:
    return CheckResult(
        name=f"{node.name} — instance state",
        passed=node.state == "running",
        detail=f"State: {node.state}",
        remediation=f"Start the instance: aws ec2 start-instances --instance-ids {node.instance_id}",
        els_layer="L0",
        command=f"aws ec2 describe-instances --instance-ids {node.instance_id}",
    )


def check_instance_type(node: NodeState) -> CheckResult:
    passed = node.instance_type in MIN_INSTANCE_TYPES
    return CheckResult(
        name=f"{node.name} — instance type",
        passed=passed,
        detail=f"Type: {node.instance_type}",
        remediation="Use t3.medium or larger for a Kubernetes lab node.",
        els_layer="L0",
        command=f"aws ec2 describe-instances --instance-ids {node.instance_id}",
    )


def check_public_ip(node: NodeState) -> CheckResult:
    passed = bool(node.public_ip)
    return CheckResult(
        name=f"{node.name} — public IP",
        passed=passed,
        detail=f"Public IP: {node.public_ip or 'none'}",
        remediation="Assign an Elastic IP or enable auto-assign public IP on the subnet.",
        els_layer="L0",
        command=f"aws ec2 describe-instances --instance-ids {node.instance_id}",
    )


def check_private_ip(node: NodeState) -> CheckResult:
    passed = bool(node.private_ip)
    return CheckResult(
        name=f"{node.name} — private IP",
        passed=passed,
        detail=f"Private IP: {node.private_ip or 'none'}",
        els_layer="L0",
        command=f"aws ec2 describe-instances --instance-ids {node.instance_id}",
    )


# ---------------------------------------------------------------------------
# VPC / same-network check
# ---------------------------------------------------------------------------

def check_same_vpc(nodes: List[NodeState]) -> CheckResult:
    """Verify all nodes are in the same VPC."""
    ok, data, err = _run_aws([
        "ec2", "describe-instances",
        "--instance-ids"] + [node.instance_id for node in nodes if node.instance_id],
    )
    if not ok:
        return CheckResult(
            name="Same VPC check",
            passed=False,
            detail=err,
            els_layer="L0",
            command="aws ec2 describe-instances",
        )

    instances = _parse_instances(data.get("Reservations", []))
    vpc_ids = {instance.get("VpcId", "") for instance in instances}
    passed = len(vpc_ids) == 1 and "" not in vpc_ids
    return CheckResult(
        name="Same VPC check",
        passed=passed,
        detail=f"VPCs observed: {', '.join(vpc_ids) or 'none'}",
        remediation="Both instances must be in the same VPC for private IP reachability.",
        els_layer="L0",
        command="aws ec2 describe-instances",
    )


# ---------------------------------------------------------------------------
# Security group check
# ---------------------------------------------------------------------------

def check_security_groups(nodes: List[NodeState]) -> List[CheckResult]:
    """Check that required Kubernetes ports are open between nodes."""
    checks = []
    ok, data, err = _run_aws([
        "ec2", "describe-instances",
        "--instance-ids"] + [node.instance_id for node in nodes if node.instance_id],
    )
    if not ok:
        checks.append(CheckResult(
            name="Security group check",
            passed=False,
            detail=err,
            els_layer="L0",
            command="aws ec2 describe-instances",
        ))
        return checks

    instances = _parse_instances(data.get("Reservations", []))
    sg_ids = set()
    for instance in instances:
        for sg in instance.get("SecurityGroups", []):
            sg_ids.add(sg.get("GroupId", ""))

    if not sg_ids:
        checks.append(CheckResult(
            name="Security group check",
            passed=False,
            detail="No security groups found on instances.",
            remediation="Attach a security group that allows traffic between nodes.",
            els_layer="L0",
            command="aws ec2 describe-security-groups",
        ))
        return checks

    ok, sg_data, err = _run_aws([
        "ec2", "describe-security-groups",
        "--group-ids"] + list(sg_ids),
    )
    if not ok:
        checks.append(CheckResult(
            name="Security group check",
            passed=False,
            detail=err,
            els_layer="L0",
            command="aws ec2 describe-security-groups",
        ))
        return checks

    # Collect all ingress rules
    all_rules = []
    for sg in sg_data.get("SecurityGroups", []):
        all_rules.extend(sg.get("IpPermissions", []))

    # Check for all-traffic rule within the security group (simplest lab setup)
    has_all_traffic = any(
        rule.get("IpProtocol") == "-1" for rule in all_rules
    )

    checks.append(CheckResult(
        name="Security group — inter-node traffic",
        passed=has_all_traffic,
        detail=(
            f"Security groups: {', '.join(sg_ids)} — all-traffic rule between nodes: {'yes' if has_all_traffic else 'no'}"
        ),
        remediation=(
            "Add an inbound rule to allow all traffic within the security group. "
            "This is the simplest lab setup and ensures all Kubernetes ports are open."
        ),
        els_layer="L0",
        command=f"aws ec2 describe-security-groups --group-ids {' '.join(sg_ids)}",
    ))
    return checks


# ---------------------------------------------------------------------------
# Top-level validator — runs all L0 checks and populates TestbedState
# ---------------------------------------------------------------------------

def validate_aws_environment(state: TestbedState) -> TestbedState:
    """
    Run all L0 AWS environment checks and populate state.

    This is the entry point called by the UI. It mutates state in place
    and returns it so the UI can store it in session state.
    """
    state.aws_checks = []

    # 1. Credentials
    cred_check = check_aws_credentials()
    state.aws_checks.append(cred_check)
    if not cred_check.passed:
        return state

    # 2. Detect instances
    nodes, detect_checks = detect_instances()
    state.aws_checks.extend(detect_checks)
    if not nodes:
        return state

    state.nodes = nodes

    # 3. Per-node checks
    for node in state.nodes:
        node.checks = [
            check_instance_running(node),
            check_instance_type(node),
            check_public_ip(node),
            check_private_ip(node),
        ]

    # 4. Cross-node checks
    if len(state.nodes) >= 2:
        state.aws_checks.append(check_same_vpc(state.nodes))
        state.aws_checks.extend(check_security_groups(state.nodes))

    # 5. Cost note (placeholder for future L0 cost visibility)
    running = [node for node in state.nodes if node.state == "running"]
    if running:
        state.notes.append(
            f"{len(running)} instance(s) running — remember to stop them when done to avoid unnecessary AWS charges."
        )

    return state
