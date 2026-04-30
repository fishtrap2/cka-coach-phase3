"""
prereq_checker.py

Node prerequisite checks for the cka-coach testbed workflow.

Option A implementation: generates commands for the student to run on each
node and paste back. cka-coach then parses the output and reports pass/fail.

Option B (SSH-based automatic checking) is tracked in GitHub issue #1.

ELS layers covered:
- L1: kernel modules, sysctl, swap
- L2: runc (via containerd)
- L3: containerd
- L4.1: kubelet
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from testbed.testbed_state import CheckResult, NodeState


# ---------------------------------------------------------------------------
# The prereq bundle — one per node.
# Contains the commands to run and a parser for the pasted output.
# ---------------------------------------------------------------------------

@dataclass
class NodePrereqBundle:
    node_name: str
    role: str                              # control-plane or worker
    private_ip: str
    commands: List[str] = field(default_factory=list)
    paste_output: str = ""                 # student pastes combined output here
    checks: List[CheckResult] = field(default_factory=list)
    parsed: bool = False

    def all_passed(self) -> bool:
        return self.parsed and all(check.passed for check in self.checks)

    def failed_checks(self) -> List[CheckResult]:
        return [check for check in self.checks if not check.passed]


# ---------------------------------------------------------------------------
# Command set — what the student runs on each node
# ---------------------------------------------------------------------------

# These commands are safe, read-only, and produce parseable output.
# They are grouped by ELS layer for the teaching moment.

PREREQ_COMMANDS = [
    # L1 — kernel
    "echo '=== swap ===' && swapon --show",
    "echo '=== kernel modules ===' && lsmod | grep -E 'overlay|br_netfilter'",
    "echo '=== sysctl ===' && sysctl net.bridge.bridge-nf-call-iptables net.bridge.bridge-nf-call-ip6tables net.ipv4.ip_forward 2>/dev/null",
    "echo '=== kernel version ===' && uname -r",
    # L3 — containerd
    "echo '=== containerd ===' && systemctl is-active containerd 2>/dev/null || echo 'not-found'",
    "echo '=== containerd version ===' && containerd --version 2>/dev/null || echo 'not-found'",
    # L4.1 — kubelet
    "echo '=== kubelet ===' && systemctl is-active kubelet 2>/dev/null || echo 'not-found'",
    "echo '=== kubelet version ===' && kubelet --version 2>/dev/null || echo 'not-found'",
    # L2 — runc
    "echo '=== runc ===' && runc --version 2>/dev/null || echo 'not-found'",
]


def build_prereq_bundle(node: NodeState) -> NodePrereqBundle:
    """
    Build the prereq command bundle for a node.
    Returns a NodePrereqBundle with commands ready to show the student.
    """
    return NodePrereqBundle(
        node_name=node.name,
        role=node.role,
        private_ip=node.private_ip,
        commands=PREREQ_COMMANDS,
    )


def build_ssh_instruction(node: NodeState) -> str:
    """
    Return the SSH command the student should use to connect to this node.
    Uses private IP — student must be on the same network or using a bastion.
    """
    return f"ssh ubuntu@{node.private_ip}"


# ---------------------------------------------------------------------------
# Output parser — reads the pasted combined output and produces CheckResults
# ---------------------------------------------------------------------------

def _section(output: str, marker: str) -> str:
    """Extract the text after a === marker === line."""
    lines = output.splitlines()
    capturing = False
    result = []
    for line in lines:
        if f"=== {marker} ===" in line:
            capturing = True
            continue
        if capturing:
            if line.startswith("==="):
                break
            result.append(line)
    return "\n".join(result).strip()


def parse_prereq_output(bundle: NodePrereqBundle) -> NodePrereqBundle:
    """
    Parse the student's pasted output and populate bundle.checks.
    Called after the student pastes the output into the UI.
    """
    output = bundle.paste_output
    checks = []

    # --- L1: swap ---
    swap_output = _section(output, "swap")
    swap_off = swap_output.strip() == ""
    checks.append(CheckResult(
        name=f"{bundle.node_name} — swap disabled",
        passed=swap_off,
        detail="Swap is off" if swap_off else f"Swap is on: {swap_output}",
        remediation="Run: sudo swapoff -a && sudo sed -i '/ swap / s/^/#/' /etc/fstab",
        els_layer="L1",
        command="swapon --show",
    ))

    # --- L1: kernel modules ---
    modules_output = _section(output, "kernel modules")
    has_overlay = "overlay" in modules_output
    has_br_netfilter = "br_netfilter" in modules_output
    checks.append(CheckResult(
        name=f"{bundle.node_name} — overlay module",
        passed=has_overlay,
        detail="overlay loaded" if has_overlay else "overlay not loaded",
        remediation="Run: sudo modprobe overlay && echo overlay | sudo tee /etc/modules-load.d/k8s.conf",
        els_layer="L1",
        command="lsmod | grep overlay",
    ))
    checks.append(CheckResult(
        name=f"{bundle.node_name} — br_netfilter module",
        passed=has_br_netfilter,
        detail="br_netfilter loaded" if has_br_netfilter else "br_netfilter not loaded",
        remediation="Run: sudo modprobe br_netfilter && echo br_netfilter | sudo tee -a /etc/modules-load.d/k8s.conf",
        els_layer="L1",
        command="lsmod | grep br_netfilter",
    ))

    # --- L1: sysctl ---
    sysctl_output = _section(output, "sysctl")
    ip_forward = "net.ipv4.ip_forward = 1" in sysctl_output
    bridge_iptables = "net.bridge.bridge-nf-call-iptables = 1" in sysctl_output
    checks.append(CheckResult(
        name=f"{bundle.node_name} — ip_forward",
        passed=ip_forward,
        detail="net.ipv4.ip_forward = 1" if ip_forward else "net.ipv4.ip_forward not set",
        remediation="Run: echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/k8s.conf && sudo sysctl --system",
        els_layer="L1",
        command="sysctl net.ipv4.ip_forward",
    ))
    checks.append(CheckResult(
        name=f"{bundle.node_name} — bridge-nf-call-iptables",
        passed=bridge_iptables,
        detail="net.bridge.bridge-nf-call-iptables = 1" if bridge_iptables else "not set",
        remediation="Run: echo 'net.bridge.bridge-nf-call-iptables=1' | sudo tee -a /etc/sysctl.d/k8s.conf && sudo sysctl --system",
        els_layer="L1",
        command="sysctl net.bridge.bridge-nf-call-iptables",
    ))

    # --- L3: containerd ---
    containerd_output = _section(output, "containerd")
    containerd_active = "active" in containerd_output
    checks.append(CheckResult(
        name=f"{bundle.node_name} — containerd active",
        passed=containerd_active,
        detail=f"containerd: {containerd_output.strip() or 'not found'}",
        remediation="Install containerd: sudo apt-get install -y containerd && sudo systemctl enable --now containerd",
        els_layer="L3",
        command="systemctl is-active containerd",
    ))

    containerd_ver = _section(output, "containerd version").strip()
    if containerd_ver and "not-found" not in containerd_ver:
        checks.append(CheckResult(
            name=f"{bundle.node_name} — containerd version",
            passed=True,
            detail=containerd_ver,
            els_layer="L3",
            command="containerd --version",
        ))

    # --- L4.1: kubelet ---
    kubelet_output = _section(output, "kubelet")
    # kubelet may be inactive before kubeadm init — that is expected
    kubelet_found = "not-found" not in kubelet_output
    checks.append(CheckResult(
        name=f"{bundle.node_name} — kubelet installed",
        passed=kubelet_found,
        detail=f"kubelet: {kubelet_output.strip() or 'not found'}",
        remediation=(
            "Install kubelet: sudo apt-get install -y kubelet kubeadm kubectl && "
            "sudo apt-mark hold kubelet kubeadm kubectl"
        ),
        els_layer="L4.1",
        command="systemctl is-active kubelet",
    ))

    kubelet_ver = _section(output, "kubelet version").strip()
    if kubelet_ver and "not-found" not in kubelet_ver:
        checks.append(CheckResult(
            name=f"{bundle.node_name} — kubelet version",
            passed=True,
            detail=kubelet_ver,
            els_layer="L4.1",
            command="kubelet --version",
        ))

    # --- L2: runc ---
    runc_output = _section(output, "runc").strip()
    runc_found = bool(runc_output) and "not-found" not in runc_output
    checks.append(CheckResult(
        name=f"{bundle.node_name} — runc installed",
        passed=runc_found,
        detail=runc_output if runc_found else "runc not found",
        remediation="runc is installed as part of containerd — check containerd installation.",
        els_layer="L2",
        command="runc --version",
    ))

    bundle.checks = checks
    bundle.parsed = True
    return bundle


# ---------------------------------------------------------------------------
# Teaching notes — shown alongside the commands in the UI
# ---------------------------------------------------------------------------

PREREQ_TEACHING_NOTES: Dict[str, str] = {
    "swap": (
        "L1 — Kubernetes requires swap to be disabled. "
        "The kubelet will refuse to start if swap is on, because swap undermines "
        "the memory guarantees that Kubernetes relies on for pod scheduling."
    ),
    "kernel modules": (
        "L1 — overlay and br_netfilter are kernel modules that container networking depends on. "
        "overlay enables the overlay filesystem used by containerd. "
        "br_netfilter allows iptables to see bridged traffic, which is how kube-proxy and CNI plugins work."
    ),
    "sysctl": (
        "L1 — These sysctl settings tell the kernel to forward IP packets between interfaces "
        "and to apply iptables rules to bridged traffic. Without these, pod-to-pod and "
        "pod-to-service networking will not work."
    ),
    "containerd": (
        "L3 — containerd is the CRI (Container Runtime Interface) that kubelet uses to "
        "pull images and manage container lifecycle. It sits between kubelet (L4.1) and "
        "runc (L2), which is the actual OCI runtime that creates containers."
    ),
    "kubelet": (
        "L4.1 — kubelet is the node agent. It watches for PodSpecs from the API server "
        "and makes sure the right containers are running on this node. "
        "It will be inactive until kubeadm init or join runs — that is expected at this stage."
    ),
    "runc": (
        "L2 — runc is the OCI runtime. It is invoked by containerd to actually create "
        "and start containers using Linux namespaces and cgroups. "
        "Students rarely interact with runc directly, but it is the lowest software layer "
        "before the kernel."
    ),
}


def get_teaching_note(section: str) -> str:
    return PREREQ_TEACHING_NOTES.get(section, "")
