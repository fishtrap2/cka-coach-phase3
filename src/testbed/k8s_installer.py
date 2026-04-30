"""
k8s_installer.py

Kubernetes installation guidance for the cka-coach testbed workflow.

Option A implementation: generates kubeadm commands for the student to run
on each node and paste back. cka-coach parses the output and reports status.

ELS layers covered:
- L4.5: Kubernetes API server and etcd (kubeadm init)
- L5:   kube-controller-manager, kube-scheduler (static pods)
- L4.1: kubelet activated by kubeadm
- L4.2: kube-proxy deployed as DaemonSet
- L7:   kubeconfig written, cluster objects created
- L8:   system pods reach Running state
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from testbed.testbed_state import (
    CheckResult,
    CNI_CALICO,
    CNI_CILIUM,
    CNI_BRIDGE,
    CNI_POD_CIDRS,
    NodeState,
    TestbedState,
)


# ---------------------------------------------------------------------------
# kubeadm init command builder
# ---------------------------------------------------------------------------

def build_kubeadm_init_command(selected_cni: str, control_plane_ip: str) -> str:
    """
    Build the kubeadm init command for the control plane node.
    Pod CIDR is chosen based on the selected CNI.
    """
    pod_cidr = CNI_POD_CIDRS.get(selected_cni, "192.168.0.0/16")
    return (
        f"sudo kubeadm init "
        f"--pod-network-cidr={pod_cidr} "
        f"--apiserver-advertise-address={control_plane_ip}"
    )


def build_kubeconfig_commands() -> List[str]:
    """Commands to configure kubectl for the ubuntu user after kubeadm init."""
    return [
        "mkdir -p $HOME/.kube",
        "sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config",
        "sudo chown $(id -u):$(id -g) $HOME/.kube/config",
    ]


def build_node_ready_check() -> str:
    return "kubectl get nodes"


def build_pods_check() -> str:
    return "kubectl get pods -A"


# ---------------------------------------------------------------------------
# kubeadm join command parser
# ---------------------------------------------------------------------------

def parse_join_command(init_output: str) -> str:
    """
    Extract the kubeadm join command from kubeadm init output.
    The join command spans two lines ending with a backslash continuation.
    """
    lines = init_output.splitlines()
    join_lines = []
    capturing = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("kubeadm join"):
            capturing = True
            join_lines.append(stripped.rstrip("\\").strip())
            if not stripped.endswith("\\"):
                break
            continue
        if capturing:
            join_lines.append(stripped.rstrip("\\").strip())
            if not stripped.endswith("\\"):
                break

    return " ".join(join_lines).strip()


# ---------------------------------------------------------------------------
# Output parsers
# ---------------------------------------------------------------------------

def parse_init_output(node: NodeState, output: str) -> List[CheckResult]:
    """Parse kubeadm init output pasted by the student."""
    checks = []

    init_success = "Your Kubernetes control-plane has initialized successfully" in output
    checks.append(CheckResult(
        name=f"{node.name} — kubeadm init",
        passed=init_success,
        detail="kubeadm init completed successfully" if init_success else "kubeadm init did not complete — check output for errors",
        remediation=(
            "Common failures:\n"
            "- swap still on: run sudo swapoff -a\n"
            "- port 6443 in use: check for existing kube-apiserver process\n"
            "- container runtime not ready: check containerd with systemctl status containerd"
        ),
        els_layer="L4.5",
        command="sudo kubeadm init ...",
    ))

    if init_success:
        checks.append(CheckResult(
            name=f"{node.name} — kubeconfig written",
            passed="admin.conf" in output,
            detail="admin.conf present in output" if "admin.conf" in output else "kubeconfig path not confirmed",
            els_layer="L7",
            command="sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config",
        ))

    return checks


def parse_nodes_output(output: str, expected_nodes: List[str]) -> List[CheckResult]:
    """
    Parse kubectl get nodes output pasted by the student.
    Checks that all expected nodes are present and Ready.
    """
    checks = []
    lines = [line for line in output.splitlines() if line.strip()]
    data_lines = lines[1:] if len(lines) > 1 else []

    ready_nodes = []
    not_ready_nodes = []
    for line in data_lines:
        parts = line.split()
        if len(parts) >= 2:
            name, status = parts[0], parts[1]
            if status == "Ready":
                ready_nodes.append(name)
            else:
                not_ready_nodes.append(f"{name} ({status})")

    for expected in expected_nodes:
        in_ready = any(expected in node for node in ready_nodes)
        in_not_ready = any(expected in node for node in not_ready_nodes)
        checks.append(CheckResult(
            name=f"Node {expected} — Ready",
            passed=in_ready,
            detail=f"Ready" if in_ready else (f"Not ready" if in_not_ready else "Not found in node list"),
            remediation=(
                "If NotReady: CNI may not be installed yet — this is expected before CNI install.\n"
                "If node is missing: check kubeadm join ran successfully on the worker."
            ),
            els_layer="L4.5",
            command="kubectl get nodes",
        ))

    return checks


def parse_system_pods_output(output: str) -> List[CheckResult]:
    """
    Parse kubectl get pods -A output.
    Checks that core control plane pods are Running.
    """
    checks = []
    expected_components = {
        "etcd": "L4.5",
        "kube-apiserver": "L4.5",
        "kube-controller-manager": "L5",
        "kube-scheduler": "L5",
        "kube-proxy": "L4.2",
    }

    lines = output.splitlines()
    for component, els_layer in expected_components.items():
        matching = [line for line in lines if component in line]
        if not matching:
            checks.append(CheckResult(
                name=f"{component} pod",
                passed=False,
                detail=f"{component} not found in pod list",
                remediation=f"Check kubeadm init completed successfully and kubectl is configured.",
                els_layer=els_layer,
                command="kubectl get pods -A",
            ))
            continue
        running = any("Running" in line for line in matching)
        checks.append(CheckResult(
            name=f"{component} pod",
            passed=running,
            detail=f"Running" if running else f"Not running: {matching[0].strip()}",
            remediation=f"Check pod logs: kubectl logs -n kube-system <pod-name>",
            els_layer=els_layer,
            command="kubectl get pods -A",
        ))

    return checks


# ---------------------------------------------------------------------------
# Installation bundles — what the UI shows per step
# ---------------------------------------------------------------------------

@dataclass
class K8sInstallBundle:
    """Tracks state for the Kubernetes installation phase."""

    # Step 1 — kubeadm init on control plane
    init_command: str = ""
    kubeconfig_commands: List[str] = field(default_factory=list)
    init_output: str = ""
    init_checks: List[CheckResult] = field(default_factory=list)
    init_done: bool = False

    # Step 2 — kubeadm join on worker
    join_command: str = ""
    join_output: str = ""
    join_done: bool = False

    # Step 3 — validation
    nodes_output: str = ""
    pods_output: str = ""
    node_checks: List[CheckResult] = field(default_factory=list)
    pod_checks: List[CheckResult] = field(default_factory=list)
    validation_done: bool = False

    def all_passed(self) -> bool:
        all_checks = self.init_checks + self.node_checks + self.pod_checks
        return bool(all_checks) and all(check.passed for check in all_checks)

    def failed_checks(self) -> List[CheckResult]:
        all_checks = self.init_checks + self.node_checks + self.pod_checks
        return [check for check in all_checks if not check.passed]


def build_k8s_install_bundle(state: TestbedState) -> K8sInstallBundle:
    """Build the install bundle from current testbed state."""
    cp = state.control_plane()
    workers = state.workers()
    bundle = K8sInstallBundle()

    if cp:
        bundle.init_command = build_kubeadm_init_command(state.selected_cni, cp.private_ip)
        bundle.kubeconfig_commands = build_kubeconfig_commands()

    # join command is populated after init output is parsed
    if state.kubeadm_join_command:
        bundle.join_command = f"sudo {state.kubeadm_join_command}"

    return bundle


def process_init_output(bundle: K8sInstallBundle, state: TestbedState, cp: NodeState) -> K8sInstallBundle:
    """
    Parse init output, extract join command, update state.
    Called after student pastes kubeadm init output.
    """
    bundle.init_checks = parse_init_output(cp, bundle.init_output)
    join_cmd = parse_join_command(bundle.init_output)
    if join_cmd:
        state.kubeadm_join_command = join_cmd
        bundle.join_command = f"sudo {join_cmd}"
        bundle.init_done = True
    return bundle


def process_validation_output(
    bundle: K8sInstallBundle,
    expected_node_names: List[str],
) -> K8sInstallBundle:
    """Parse node and pod output pasted by the student."""
    if bundle.nodes_output:
        bundle.node_checks = parse_nodes_output(bundle.nodes_output, expected_node_names)
    if bundle.pods_output:
        bundle.pod_checks = parse_system_pods_output(bundle.pods_output)
    bundle.validation_done = bool(bundle.node_checks or bundle.pod_checks)
    return bundle


# ---------------------------------------------------------------------------
# Teaching notes
# ---------------------------------------------------------------------------

K8S_TEACHING_NOTES: Dict[str, str] = {
    "kubeadm init": (
        "L4.5 — kubeadm init bootstraps the control plane. It creates the API server, "
        "etcd, controller-manager, and scheduler as static pods managed directly by kubelet. "
        "The --pod-network-cidr flag reserves an IP range for pods — this must match what "
        "your chosen CNI expects, otherwise pod networking will not work."
    ),
    "kubeconfig": (
        "L7 — The kubeconfig file is how kubectl authenticates to the API server. "
        "kubeadm writes it to /etc/kubernetes/admin.conf as root. "
        "Copying it to ~/.kube/config makes it accessible to your user."
    ),
    "kubeadm join": (
        "L4.1 — kubeadm join registers the worker node with the control plane. "
        "It uses a bootstrap token that expires after 24 hours. "
        "After joining, kubelet starts on the worker and the node appears in kubectl get nodes."
    ),
    "node ready": (
        "L4.5 / L4.3 — Nodes show NotReady until a CNI plugin is installed. "
        "This is expected and correct — the node is registered but networking is not yet wired up. "
        "Installing the CNI in the next step will bring nodes to Ready."
    ),
    "system pods": (
        "L5 — kube-controller-manager and kube-scheduler run as static pods on the control plane. "
        "Static pods are managed directly by kubelet from manifests in /etc/kubernetes/manifests, "
        "not by the API server. This is how Kubernetes bootstraps itself."
    ),
}


def get_teaching_note(section: str) -> str:
    return K8S_TEACHING_NOTES.get(section, "")
