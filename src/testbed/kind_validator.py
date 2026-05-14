"""
kind_validator.py

KIND (Kubernetes in Docker) environment validation for the cka-coach testbed.

KIND is supported as a Stage 1 shortcut only. It hides L0, L1, L2, and L3
almost entirely. Students who use KIND must be explicitly told what they are
missing and why they will need real infrastructure for Stage 2.

See: docs/aidlc/product-decision-testbed-platform-strategy.md

ELS layers visible in KIND:  L4.5, L5, L6, L7, L8, L9
ELS layers hidden in KIND:   L0, L1 (partially), L2, L3 (partially)
"""

import subprocess
from typing import List, Tuple

from testbed.testbed_state import CheckResult, NodeState, TestbedState


KIND_WARNING = """KIND gives you a working Kubernetes cluster in minutes.

But it runs inside Docker on your local machine — there is no real L0.
No hypervisor, no IAM, no VPC, no security groups. The node identity,
network boundary, and security model that matter in production do not
exist here.

You can learn Kubernetes objects, controllers, and CNI concepts in KIND.
You cannot learn how Kubernetes integrates with real infrastructure.

For Stage 2 and beyond, you will need a real testbed on AWS or GCP.

ELS layers visible in KIND:  L4.5, L5, L6, L7, L8, L9
ELS layers hidden in KIND:   L0 (entirely), L1 (partially), L2, L3 (partially)"""


def _run(cmd: List[str], timeout: int = 10) -> Tuple[bool, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout or r.stderr or "").strip()
    except FileNotFoundError:
        return False, f"{cmd[0]} not found — install it first"
    except subprocess.TimeoutExpired:
        return False, f"{cmd[0]} timed out"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# KIND checks
# ---------------------------------------------------------------------------

def check_kind_installed() -> CheckResult:
    ok, output = _run(["kind", "version"])
    return CheckResult(
        name="kind CLI installed",
        passed=ok,
        detail=output if ok else "kind not found",
        remediation="Install KIND: https://kind.sigs.k8s.io/docs/user/quick-start/#installation",
        els_layer="L0",
        command="kind version",
    )


def check_docker_running() -> CheckResult:
    ok, output = _run(["docker", "info", "--format", "{{.ServerVersion}}"])
    return CheckResult(
        name="Docker running",
        passed=ok,
        detail=f"Docker {output}" if ok else "Docker not running or not installed",
        remediation="Start Docker Desktop or install Docker Engine",
        els_layer="L0",
        command="docker info",
    )


def check_kind_cluster() -> Tuple[CheckResult, str]:
    """Returns (check, cluster_name)."""
    ok, output = _run(["kind", "get", "clusters"])
    clusters = [c for c in output.splitlines() if c.strip()] if ok else []
    if clusters:
        return CheckResult(
            name="KIND cluster exists",
            passed=True,
            detail=f"Clusters: {', '.join(clusters)}",
            els_layer="L4.5",
            command="kind get clusters",
        ), clusters[0]
    return CheckResult(
        name="KIND cluster exists",
        passed=False,
        detail="No KIND clusters found",
        remediation="Create one: kind create cluster --name cka-coach",
        els_layer="L4.5",
        command="kind get clusters",
    ), ""


def check_kubectl_kind_context(cluster_name: str) -> CheckResult:
    context = f"kind-{cluster_name}" if cluster_name else "kind-cka-coach"
    ok, output = _run(["kubectl", "config", "use-context", context])
    if not ok:
        # Try without prefix
        ok, output = _run(["kubectl", "config", "use-context", cluster_name])
    return CheckResult(
        name="kubectl context set",
        passed=ok,
        detail=f"Context: {context}" if ok else output,
        remediation=f"Run: kubectl config use-context {context}",
        els_layer="L4.5",
        command=f"kubectl config use-context {context}",
    )


def check_kind_nodes() -> Tuple[List[CheckResult], List[NodeState]]:
    """Check nodes are Ready and build NodeState list."""
    checks = []
    nodes = []

    ok, output = _run(["kubectl", "get", "nodes", "--no-headers"])
    if not ok or not output.strip():
        checks.append(CheckResult(
            name="kubectl get nodes",
            passed=False,
            detail="Cannot reach cluster — kubeconfig may not be set",
            remediation="Run: kubectl config use-context kind-<cluster-name>",
            els_layer="L4.5",
            command="kubectl get nodes",
        ))
        return checks, nodes

    lines = [l for l in output.splitlines() if l.strip()]
    ready = [l for l in lines if len(l.split()) >= 2 and l.split()[1] == "Ready"]
    not_ready = [l for l in lines if len(l.split()) >= 2 and l.split()[1] != "Ready"]

    checks.append(CheckResult(
        name="KIND nodes Ready",
        passed=len(ready) == len(lines) and len(lines) > 0,
        detail=f"{len(ready)}/{len(lines)} nodes Ready",
        remediation="Wait for nodes to become Ready — KIND may still be initialising",
        els_layer="L4.5",
        command="kubectl get nodes",
    ))

    for line in lines:
        parts = line.split()
        name = parts[0]
        status = parts[1] if len(parts) > 1 else "Unknown"
        role = "control-plane" if "control-plane" in line else "worker"
        nodes.append(NodeState(
            name=name,
            role=role,
            state="running" if status == "Ready" else "not-ready",
            instance_type="kind-node",
        ))

    return checks, nodes


# ---------------------------------------------------------------------------
# Top-level validator
# ---------------------------------------------------------------------------

def validate_kind_environment(state: TestbedState) -> TestbedState:
    """
    Run all KIND environment checks and populate state.
    Much simpler than AWS — no cloud API, no SSH, no IAM.
    """
    state.aws_checks = []

    # 1. kind CLI
    kind_check = check_kind_installed()
    state.aws_checks.append(kind_check)
    if not kind_check.passed:
        return state

    # 2. Docker
    docker_check = check_docker_running()
    state.aws_checks.append(docker_check)
    if not docker_check.passed:
        return state

    # 3. Cluster exists
    cluster_check, cluster_name = check_kind_cluster()
    state.aws_checks.append(cluster_check)
    if not cluster_check.passed:
        state.notes.append(
            "No KIND cluster found. Create one with: kind create cluster --name cka-coach"
        )
        return state

    # 4. kubectl context
    state.aws_checks.append(check_kubectl_kind_context(cluster_name))

    # 5. Nodes
    node_checks, nodes = check_kind_nodes()
    state.aws_checks.extend(node_checks)
    state.nodes = nodes

    return state
