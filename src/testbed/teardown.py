"""
teardown.py

Kubernetes teardown and node cleanup guidance for the cka-coach testbed workflow.

Option A implementation: generates teardown commands for the student to run
on each node in the correct order. cka-coach parses pasted output to confirm
each step completed cleanly.

Safety rules (from lab safety rules):
- Never run destructive commands silently
- Worker nodes are reset before the control plane
- Scope is strictly limited to instances tagged cka-coach-*
- Each destructive step requires explicit student confirmation in the UI
- CNI removal is not attempted in-place — full kubeadm reset is the only path

ELS layers affected: L4.3, L4.1, L3, L1 (in reverse order — teardown unwinds the stack)
"""

from dataclasses import dataclass, field
from typing import Dict, List

from testbed.testbed_state import (
    CheckResult,
    NodeState,
    TestbedState,
)


# ---------------------------------------------------------------------------
# Teardown command sets — per node role
# ---------------------------------------------------------------------------

# Worker teardown — run on the worker node first
WORKER_TEARDOWN_COMMANDS = [
    "# Step 1 — drain the node from the control plane (run on control plane)",
    "kubectl drain <worker-node-name> --ignore-daemonsets --delete-emptydir-data",
    "",
    "# Step 2 — reset Kubernetes on the worker node (run on worker)",
    "sudo kubeadm reset --force",
    "",
    "# Step 3 — clean up CNI config and interfaces (run on worker)",
    "sudo rm -rf /etc/cni/net.d/*",
    "sudo ip link delete cni0 2>/dev/null || true",
    "sudo ip link delete flannel.1 2>/dev/null || true",
    "sudo ip link delete vxlan.calico 2>/dev/null || true",
    "sudo ip link delete tunl0 2>/dev/null || true",
    "",
    "# Step 4 — flush iptables (run on worker)",
    "sudo iptables -F && sudo iptables -X",
    "sudo iptables -t nat -F && sudo iptables -t nat -X",
    "sudo iptables -t mangle -F && sudo iptables -t mangle -X",
    "",
    "# Step 5 — remove kubeconfig (run on worker)",
    "rm -rf $HOME/.kube",
]

# Control plane teardown — run after worker is clean
CONTROL_PLANE_TEARDOWN_COMMANDS = [
    "# Step 1 — delete the worker node from the cluster (run on control plane)",
    "kubectl delete node <worker-node-name>",
    "",
    "# Step 2 — reset Kubernetes on the control plane",
    "sudo kubeadm reset --force",
    "",
    "# Step 3 — clean up CNI config and interfaces",
    "sudo rm -rf /etc/cni/net.d/*",
    "sudo ip link delete cni0 2>/dev/null || true",
    "sudo ip link delete flannel.1 2>/dev/null || true",
    "sudo ip link delete vxlan.calico 2>/dev/null || true",
    "sudo ip link delete tunl0 2>/dev/null || true",
    "",
    "# Step 4 — flush iptables",
    "sudo iptables -F && sudo iptables -X",
    "sudo iptables -t nat -F && sudo iptables -t nat -X",
    "sudo iptables -t mangle -F && sudo iptables -t mangle -X",
    "",
    "# Step 5 — remove Kubernetes data directories",
    "sudo rm -rf /etc/kubernetes /var/lib/etcd /var/lib/kubelet",
    "",
    "# Step 6 — remove kubeconfig",
    "rm -rf $HOME/.kube",
]

# Post-teardown verification — run on each node to confirm clean state
VERIFY_CLEAN_COMMANDS = [
    "echo '=== cni config ===' && ls /etc/cni/net.d/ 2>/dev/null || echo 'empty'",
    "echo '=== cali interfaces ===' && ip link show | grep -E 'cali|vxlan|tunl|flannel' || echo 'none'",
    "echo '=== iptables calico chains ===' && sudo iptables -L | grep -i calico | head -5 || echo 'none'",
    "echo '=== kubernetes dirs ===' && ls /etc/kubernetes/ 2>/dev/null || echo 'empty'",
    "echo '=== kubelet status ===' && systemctl is-active kubelet 2>/dev/null || echo 'inactive'",
]


def build_worker_teardown_commands(worker: NodeState) -> List[str]:
    """Substitute the actual worker node name into the teardown commands."""
    return [
        cmd.replace("<worker-node-name>", worker.name)
        for cmd in WORKER_TEARDOWN_COMMANDS
    ]


def build_control_plane_teardown_commands(worker: NodeState) -> List[str]:
    """Substitute the actual worker node name into the control plane teardown commands."""
    return [
        cmd.replace("<worker-node-name>", worker.name)
        for cmd in CONTROL_PLANE_TEARDOWN_COMMANDS
    ]


# ---------------------------------------------------------------------------
# Output parsers
# ---------------------------------------------------------------------------

def _section(output: str, marker: str) -> str:
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


def parse_kubeadm_reset_output(node: NodeState, output: str) -> List[CheckResult]:
    """Parse kubeadm reset output pasted by the student."""
    checks = []

    reset_done = (
        "The reset process does not clean" in output
        or "reset was successful" in output.lower()
        or "[reset] succeeded" in output.lower()
        or "Deleting contents of config directories" in output
    )
    checks.append(CheckResult(
        name=f"{node.name} — kubeadm reset",
        passed=reset_done,
        detail="kubeadm reset completed" if reset_done else "kubeadm reset output not recognised — check for errors",
        remediation="Re-run: sudo kubeadm reset --force",
        els_layer="L4.5",
        command="sudo kubeadm reset --force",
    ))
    return checks


def parse_verify_clean_output(node: NodeState, output: str) -> List[CheckResult]:
    """Parse the post-teardown verification output."""
    checks = []

    # CNI config
    cni_config = _section(output, "cni config")
    cni_clean = not cni_config or cni_config.strip() in {"empty", ""}
    checks.append(CheckResult(
        name=f"{node.name} — CNI config removed",
        passed=cni_clean,
        detail="CNI config directory is empty" if cni_clean else f"Residual CNI config: {cni_config}",
        remediation="Run: sudo rm -rf /etc/cni/net.d/*",
        els_layer="L4.3",
        command="ls /etc/cni/net.d/",
    ))

    # CNI interfaces
    ifaces = _section(output, "cali interfaces")
    ifaces_clean = not ifaces or ifaces.strip() == "none"
    checks.append(CheckResult(
        name=f"{node.name} — CNI interfaces removed",
        passed=ifaces_clean,
        detail="No residual CNI interfaces" if ifaces_clean else f"Residual interfaces: {ifaces}",
        remediation="Run: sudo ip link delete <interface-name> for each residual interface listed",
        els_layer="L4.3",
        command="ip link show | grep -E 'cali|vxlan|tunl|flannel'",
    ))

    # iptables chains
    iptables = _section(output, "iptables calico chains")
    iptables_clean = not iptables or iptables.strip() == "none"
    checks.append(CheckResult(
        name=f"{node.name} — iptables chains cleared",
        passed=iptables_clean,
        detail="No residual iptables chains" if iptables_clean else f"Residual chains: {iptables}",
        remediation="Run: sudo iptables -F && sudo iptables -X && sudo iptables -t nat -F",
        els_layer="L1",
        command="sudo iptables -L | grep -i calico",
    ))

    # Kubernetes dirs
    k8s_dirs = _section(output, "kubernetes dirs")
    k8s_clean = not k8s_dirs or k8s_dirs.strip() == "empty"
    checks.append(CheckResult(
        name=f"{node.name} — Kubernetes directories removed",
        passed=k8s_clean,
        detail="Kubernetes directories removed" if k8s_clean else f"Residual dirs: {k8s_dirs}",
        remediation="Run: sudo rm -rf /etc/kubernetes /var/lib/etcd /var/lib/kubelet",
        els_layer="L4.5",
        command="ls /etc/kubernetes/",
    ))

    # kubelet inactive
    kubelet = _section(output, "kubelet status")
    kubelet_inactive = "inactive" in kubelet or "failed" in kubelet
    checks.append(CheckResult(
        name=f"{node.name} — kubelet inactive",
        passed=kubelet_inactive,
        detail=f"kubelet: {kubelet.strip()}" if kubelet else "kubelet status unknown",
        remediation="kubelet should be inactive after kubeadm reset — if still active, run: sudo systemctl stop kubelet",
        els_layer="L4.1",
        command="systemctl is-active kubelet",
    ))

    return checks


# ---------------------------------------------------------------------------
# Teardown bundle
# ---------------------------------------------------------------------------

@dataclass
class TeardownBundle:
    """Tracks state for the teardown phase."""

    # Confirmation gate — must be True before any destructive commands are shown
    confirmed: bool = False

    # Worker teardown
    worker_commands: List[str] = field(default_factory=list)
    worker_reset_output: str = ""
    worker_reset_checks: List[CheckResult] = field(default_factory=list)
    worker_verify_output: str = ""
    worker_verify_checks: List[CheckResult] = field(default_factory=list)
    worker_done: bool = False

    # Control plane teardown
    cp_commands: List[str] = field(default_factory=list)
    cp_reset_output: str = ""
    cp_reset_checks: List[CheckResult] = field(default_factory=list)
    cp_verify_output: str = ""
    cp_verify_checks: List[CheckResult] = field(default_factory=list)
    cp_done: bool = False

    # Verification commands (same for both nodes)
    verify_commands: List[str] = field(default_factory=list)

    def all_passed(self) -> bool:
        all_checks = (
            self.worker_reset_checks
            + self.worker_verify_checks
            + self.cp_reset_checks
            + self.cp_verify_checks
        )
        return bool(all_checks) and all(check.passed for check in all_checks)

    def failed_checks(self) -> List[CheckResult]:
        all_checks = (
            self.worker_reset_checks
            + self.worker_verify_checks
            + self.cp_reset_checks
            + self.cp_verify_checks
        )
        return [check for check in all_checks if not check.passed]


def build_teardown_bundle(state: TestbedState) -> TeardownBundle:
    """Build the teardown bundle from current testbed state."""
    cp = state.control_plane()
    workers = state.workers()
    worker = workers[0] if workers else None

    bundle = TeardownBundle(
        verify_commands=VERIFY_CLEAN_COMMANDS,
    )

    if worker:
        bundle.worker_commands = build_worker_teardown_commands(worker)
    if cp and worker:
        bundle.cp_commands = build_control_plane_teardown_commands(worker)

    return bundle


def process_worker_teardown(
    bundle: TeardownBundle,
    worker: NodeState,
) -> TeardownBundle:
    if bundle.worker_reset_output:
        bundle.worker_reset_checks = parse_kubeadm_reset_output(worker, bundle.worker_reset_output)
    if bundle.worker_verify_output:
        bundle.worker_verify_checks = parse_verify_clean_output(worker, bundle.worker_verify_output)
    bundle.worker_done = bool(bundle.worker_reset_checks or bundle.worker_verify_checks)
    return bundle


def process_cp_teardown(
    bundle: TeardownBundle,
    cp: NodeState,
) -> TeardownBundle:
    if bundle.cp_reset_output:
        bundle.cp_reset_checks = parse_kubeadm_reset_output(cp, bundle.cp_reset_output)
    if bundle.cp_verify_output:
        bundle.cp_verify_checks = parse_verify_clean_output(cp, bundle.cp_verify_output)
    bundle.cp_done = bool(bundle.cp_reset_checks or bundle.cp_verify_checks)
    return bundle


# ---------------------------------------------------------------------------
# Teaching notes
# ---------------------------------------------------------------------------

TEARDOWN_TEACHING_NOTES: Dict[str, str] = {
    "why reset": (
        "kubeadm reset unwinds what kubeadm init and join did. "
        "It stops the kubelet, removes static pod manifests, and cleans up "
        "certificates and etcd data. It does not clean up CNI state — "
        "that must be done manually, which is why we have the extra cleanup steps."
    ),
    "why worker first": (
        "The worker is reset before the control plane because draining the worker "
        "first ensures any running workloads are gracefully evicted. "
        "Resetting the control plane first would leave the worker in an orphaned state "
        "with no API server to communicate with."
    ),
    "cni residuals": (
        "L4.3 / L1 — CNI plugins leave behind virtual interfaces (cali*, vxlan.calico, tunl0) "
        "and iptables chains. These are kernel-level artifacts that persist after kubeadm reset. "
        "If not cleaned up, they can cause networking conflicts when a new CNI is installed. "
        "This is why in-place CNI migration is unreliable — the old CNI leaves traces at L1."
    ),
    "clean state": (
        "A clean node has: no CNI config in /etc/cni/net.d/, no residual virtual interfaces, "
        "no Calico/Cilium iptables chains, no /etc/kubernetes directory, and kubelet inactive. "
        "Only when all of these are confirmed clean is the node ready for a fresh Kubernetes install."
    ),
}


def get_teaching_note(section: str) -> str:
    return TEARDOWN_TEACHING_NOTES.get(section, "")
