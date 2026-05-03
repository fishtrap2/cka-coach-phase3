"""
cni_installer.py

CNI installation guidance for the cka-coach testbed workflow.

Option A implementation: generates CNI install commands for the student to run
and parses pasted output to validate the result.

Supports three CNI paths:
- Calico (default) — operator-managed, policy-capable, VXLAN or BGP
- Cilium — eBPF dataplane
- Bridge (no CNI) — shows what breaks without a CNI plugin

Per lab safety rules, CNI removal is not supported in-place.
To switch CNI the student must reset Kubernetes and reinstall from scratch.
This is the correct CKA mental model.

ELS layer: L4.3 — CNI / Pod Networking / dataplane evidence
"""

from dataclasses import dataclass, field
from typing import Dict, List

from testbed.testbed_state import (
    CheckResult,
    CNI_CALICO,
    CNI_CILIUM,
    CNI_BRIDGE,
    NodeState,
    TestbedState,
)


# ---------------------------------------------------------------------------
# CNI install commands
# ---------------------------------------------------------------------------

CALICO_INSTALL_COMMANDS = [
    "# Install the Tigera Operator",
    "kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/tigera-operator.yaml",
    "",
    "# Install the Calico custom resources (IPPool, Installation CR)",
    "kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/custom-resources.yaml",
    "",
    "# Watch Calico components come up",
    "watch kubectl get pods -n calico-system",
]

CILIUM_INSTALL_COMMANDS = [
    "# Install the Cilium CLI",
    "CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)",
    "curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-amd64.tar.gz",
    "sudo tar -C /usr/local/bin -xzvf cilium-linux-amd64.tar.gz",
    "",
    "# Install Cilium into the cluster",
    "cilium install",
    "",
    "# Watch Cilium components come up",
    "cilium status --wait",
]

BRIDGE_OBSERVE_COMMANDS = [
    "# No CNI will be installed — observe the cluster in a CNI-absent state",
    "kubectl get nodes",
    "kubectl get pods -A",
    "kubectl describe node <node-name> | grep -A5 'Conditions'",
]

CNI_INSTALL_COMMANDS = {
    CNI_CALICO: CALICO_INSTALL_COMMANDS,
    CNI_CILIUM: CILIUM_INSTALL_COMMANDS,
    CNI_BRIDGE: BRIDGE_OBSERVE_COMMANDS,
}


# ---------------------------------------------------------------------------
# CNI validation commands
# ---------------------------------------------------------------------------

CALICO_VALIDATION_COMMANDS = [
    "kubectl get pods -n calico-system",
    "kubectl get pods -n tigera-operator",
    "kubectl get nodes",
    "kubectl get installation default -o jsonpath='{.status.variant}'",
]

CILIUM_VALIDATION_COMMANDS = [
    "kubectl get pods -n kube-system -l k8s-app=cilium",
    "kubectl get pods -n kube-system -l name=cilium-operator",
    "kubectl get nodes",
    "cilium status 2>/dev/null || echo 'cilium CLI not available'",
]

BRIDGE_VALIDATION_COMMANDS = [
    "kubectl get nodes",
    "kubectl get pods -A",
]

CNI_VALIDATION_COMMANDS = {
    CNI_CALICO: CALICO_VALIDATION_COMMANDS,
    CNI_CILIUM: CILIUM_VALIDATION_COMMANDS,
    CNI_BRIDGE: BRIDGE_VALIDATION_COMMANDS,
}


# ---------------------------------------------------------------------------
# Shared node readiness helper
# Handles AWS tag name vs VM hostname mismatch
# ---------------------------------------------------------------------------

def _nodes_ready_in_output(output: str, node_names: List[str]) -> List[CheckResult]:
    """
    Check node readiness from kubectl get nodes output.

    AWS tag names (e.g. cka-coach-cp) may differ from the VM hostname
    set inside the instance (e.g. control-plane). This helper checks
    all observed nodes first — if all are Ready it passes regardless
    of name matching.
    """
    lines = output.splitlines()
    ready_nodes = []
    not_ready_nodes = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[1] in ("Ready", "NotReady"):
            if parts[1] == "Ready":
                ready_nodes.append(parts[0])
            else:
                not_ready_nodes.append(parts[0])

    # All observed nodes are Ready — pass directly
    if ready_nodes and not not_ready_nodes:
        return [CheckResult(
            name="All nodes Ready after CNI",
            passed=True,
            detail=f"Ready: {', '.join(ready_nodes)}",
            els_layer="L4.3",
            command="kubectl get nodes",
        )]

    # Fall back to per-expected-name matching with partial match
    checks = []
    for name in node_names:
        matched_ready = any(name in n or n in name for n in ready_nodes)
        matched_not_ready = any(name in n or n in name for n in not_ready_nodes)
        checks.append(CheckResult(
            name=f"Node {name} — Ready after CNI",
            passed=matched_ready or (not matched_not_ready and bool(ready_nodes)),
            detail="Ready" if matched_ready else "NotReady — CNI may still be initialising",
            remediation="Wait 60s and re-check. If still NotReady: kubectl describe node <name>",
            els_layer="L4.3",
            command="kubectl get nodes",
        ))
    return checks


# ---------------------------------------------------------------------------
# Output parsers
# ---------------------------------------------------------------------------

def parse_calico_output(output: str, node_names: List[str]) -> List[CheckResult]:
    checks = []
    lines = output.splitlines()

    operator_lines = [l for l in lines if "tigera-operator" in l]
    operator_running = any("Running" in l for l in operator_lines)
    checks.append(CheckResult(
        name="tigera-operator",
        passed=operator_running,
        detail="Running" if operator_running else "Not running — check: kubectl get pods -n tigera-operator",
        remediation="kubectl describe pod -n tigera-operator <pod> for details",
        els_layer="L4.3",
        command="kubectl get pods -n tigera-operator",
    ))

    calico_node_lines = [l for l in lines if "calico-node" in l]
    calico_node_running = any("Running" in l for l in calico_node_lines)
    checks.append(CheckResult(
        name="calico-node",
        passed=calico_node_running,
        detail="Running" if calico_node_running else "Not running — CNI dataplane not yet active",
        remediation="kubectl describe pod -n calico-system <calico-node-pod> for details",
        els_layer="L4.3",
        command="kubectl get pods -n calico-system",
    ))

    controllers_lines = [l for l in lines if "calico-kube-controllers" in l]
    controllers_running = any("Running" in l for l in controllers_lines)
    checks.append(CheckResult(
        name="calico-kube-controllers",
        passed=controllers_running,
        detail="Running" if controllers_running else "Not running",
        remediation="kubectl describe pod -n calico-system <calico-kube-controllers-pod> for details",
        els_layer="L4.3",
        command="kubectl get pods -n calico-system",
    ))

    checks.extend(_nodes_ready_in_output(output, node_names))
    return checks


def parse_cilium_output(output: str, node_names: List[str]) -> List[CheckResult]:
    checks = []
    lines = output.splitlines()

    cilium_lines = [l for l in lines if "cilium" in l.lower() and "operator" not in l.lower()]
    cilium_running = any("Running" in l for l in cilium_lines)
    checks.append(CheckResult(
        name="cilium DaemonSet",
        passed=cilium_running,
        detail="Running" if cilium_running else "Not running",
        remediation="kubectl describe pod -n kube-system <cilium-pod> for details",
        els_layer="L4.3",
        command="kubectl get pods -n kube-system -l k8s-app=cilium",
    ))

    operator_lines = [l for l in lines if "cilium-operator" in l.lower()]
    operator_running = any("Running" in l for l in operator_lines)
    checks.append(CheckResult(
        name="cilium-operator",
        passed=operator_running,
        detail="Running" if operator_running else "Not running",
        remediation="kubectl describe pod -n kube-system <cilium-operator-pod> for details",
        els_layer="L4.3",
        command="kubectl get pods -n kube-system -l name=cilium-operator",
    ))

    checks.extend(_nodes_ready_in_output(output, node_names))
    return checks


def parse_bridge_output(output: str, node_names: List[str]) -> List[CheckResult]:
    """
    For the bridge (no CNI) path, NotReady is the expected state.
    This is the teaching moment.
    """
    lines = output.splitlines()
    not_ready_nodes = [
        line.split()[0] for line in lines
        if len(line.split()) >= 2 and line.split()[1] == "NotReady"
    ]
    all_not_ready = bool(not_ready_nodes)
    return [CheckResult(
        name="Nodes NotReady (expected without CNI)",
        passed=all_not_ready,
        detail=(
            f"NotReady: {', '.join(not_ready_nodes)} — correct, no CNI installed. "
            "Cross-node pod communication will fail."
        ) if all_not_ready else "Nodes appear Ready — unexpected without a CNI plugin",
        els_layer="L4.3",
        command="kubectl get nodes",
    )]


CNI_PARSERS = {
    CNI_CALICO: parse_calico_output,
    CNI_CILIUM: parse_cilium_output,
    CNI_BRIDGE: parse_bridge_output,
}


# ---------------------------------------------------------------------------
# CNI install bundle
# ---------------------------------------------------------------------------

@dataclass
class CNIInstallBundle:
    selected_cni: str = CNI_CALICO
    install_commands: List[str] = field(default_factory=list)
    validation_commands: List[str] = field(default_factory=list)
    validation_output: str = ""
    checks: List[CheckResult] = field(default_factory=list)
    parsed: bool = False

    def all_passed(self) -> bool:
        return self.parsed and all(check.passed for check in self.checks)

    def failed_checks(self) -> List[CheckResult]:
        return [check for check in self.checks if not check.passed]


def build_cni_install_bundle(state: TestbedState) -> CNIInstallBundle:
    cni = state.selected_cni
    return CNIInstallBundle(
        selected_cni=cni,
        install_commands=CNI_INSTALL_COMMANDS.get(cni, []),
        validation_commands=CNI_VALIDATION_COMMANDS.get(cni, []),
    )


def parse_cni_validation_output(
    bundle: CNIInstallBundle,
    node_names: List[str],
) -> CNIInstallBundle:
    parser = CNI_PARSERS.get(bundle.selected_cni)
    if parser:
        bundle.checks = parser(bundle.validation_output, node_names)
        bundle.parsed = True
    return bundle


# ---------------------------------------------------------------------------
# Teaching notes
# ---------------------------------------------------------------------------

CNI_TEACHING_NOTES: Dict[str, str] = {
    CNI_CALICO: (
        "L4.3 — Calico is installed via the Tigera Operator, which manages the full "
        "Calico lifecycle. The operator creates calico-node (a DaemonSet on every node) "
        "which wires up pod networking using VXLAN or BGP. "
        "calico-kube-controllers handles garbage collection and policy enforcement. "
        "Nodes will move from NotReady to Ready once calico-node is running on each node."
    ),
    CNI_CILIUM: (
        "L4.3 — Cilium uses eBPF instead of iptables for packet forwarding and policy enforcement. "
        "The cilium DaemonSet runs on every node and replaces kube-proxy's role in service routing. "
        "cilium-operator handles cluster-wide tasks like IPAM and node management. "
        "Nodes will move from NotReady to Ready once the cilium pod is running on each node."
    ),
    CNI_BRIDGE: (
        "L4.3 — Without a CNI plugin, the cluster is in a degraded state. "
        "Pods on the same node can communicate, but cross-node pod traffic will fail. "
        "Nodes stay NotReady because kubelet cannot confirm pod networking is functional. "
        "This is the teaching moment: CNI is not optional for a working Kubernetes cluster."
    ),
    "removal": (
        "CNI removal is unreliable. Leftover iptables rules, virtual interfaces, "
        "kernel state, and config files make in-place CNI migration dangerous. "
        "The correct approach is: kubeadm reset on all nodes, clean up node state, "
        "reinstall Kubernetes, then install the new CNI from scratch. "
        "This is the real-world answer and the correct CKA mental model."
    ),
}


def get_teaching_note(section: str) -> str:
    return CNI_TEACHING_NOTES.get(section, "")
