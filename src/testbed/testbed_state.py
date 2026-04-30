"""
testbed_state.py

Structured state for the cka-coach testbed workflow.

Every phase of the testbed (AWS validation, prerequisites, Kubernetes install,
CNI install, teardown) writes into this state. The UI reads from it.

ELS layers covered: L0 through L8.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Check result — the atomic unit of evidence in the testbed workflow.
# Every validation step produces one of these.
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    name: str                        # human-readable check name
    passed: bool                     # True = passed, False = failed
    detail: str                      # what was observed
    remediation: str = ""            # what the student should do if failed
    els_layer: str = ""              # which ELS layer this check belongs to
    command: str = ""                # command used to collect evidence


# ---------------------------------------------------------------------------
# Per-node state — one of these per VM in the testbed.
# ---------------------------------------------------------------------------

@dataclass
class NodeState:
    name: str                        # e.g. cka-coach-cp
    role: str                        # control-plane or worker
    instance_id: str = ""
    public_ip: str = ""
    private_ip: str = ""
    instance_type: str = ""
    state: str = ""                  # running, stopped, terminated
    ssh_reachable: bool = False
    ping_reachable: bool = False
    checks: List[CheckResult] = field(default_factory=list)

    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def failed_checks(self) -> List[CheckResult]:
        return [check for check in self.checks if not check.passed]


# ---------------------------------------------------------------------------
# CNI selection — student chooses one of these at the start of the lesson.
# ---------------------------------------------------------------------------

CNI_CALICO = "calico"
CNI_CILIUM = "cilium"
CNI_BRIDGE = "bridge"

CNI_OPTIONS = [CNI_CALICO, CNI_CILIUM, CNI_BRIDGE]

CNI_DESCRIPTIONS = {
    CNI_CALICO: "Calico (default) — policy-capable, operator-managed, VXLAN or BGP transport",
    CNI_CILIUM: "Cilium — eBPF dataplane, modern alternative to Calico",
    CNI_BRIDGE: "Default bridge (no CNI) — shows what breaks without a CNI plugin",
}

CNI_POD_CIDRS = {
    CNI_CALICO: "192.168.0.0/16",
    CNI_CILIUM: "10.0.0.0/16",
    CNI_BRIDGE: "10.244.0.0/16",
}


# ---------------------------------------------------------------------------
# Testbed phases — the student moves through these in order.
# ---------------------------------------------------------------------------

PHASE_AWS_VALIDATION = "aws_validation"
PHASE_PREREQUISITES = "prerequisites"
PHASE_K8S_INSTALL = "k8s_install"
PHASE_CNI_INSTALL = "cni_install"
PHASE_COMPLETE = "complete"
PHASE_TEARDOWN = "teardown"

PHASE_ORDER = [
    PHASE_AWS_VALIDATION,
    PHASE_PREREQUISITES,
    PHASE_K8S_INSTALL,
    PHASE_CNI_INSTALL,
    PHASE_COMPLETE,
]

PHASE_LABELS = {
    PHASE_AWS_VALIDATION: "L0 — AWS Environment Validation",
    PHASE_PREREQUISITES: "L1–L4.1 — Node Prerequisites",
    PHASE_K8S_INSTALL: "L4.5 — Kubernetes Installation",
    PHASE_CNI_INSTALL: "L4.3 — CNI Installation",
    PHASE_COMPLETE: "Complete — Cluster Ready",
    PHASE_TEARDOWN: "Teardown — Reset and Clean",
}


# ---------------------------------------------------------------------------
# Top-level testbed state — the single source of truth for the UI.
# ---------------------------------------------------------------------------

@dataclass
class TestbedState:
    # Current phase
    phase: str = PHASE_AWS_VALIDATION

    # CNI selection
    selected_cni: str = CNI_CALICO

    # Per-node state
    nodes: List[NodeState] = field(default_factory=list)

    # Phase-level check results (cluster-wide checks that don't belong to a node)
    aws_checks: List[CheckResult] = field(default_factory=list)
    k8s_checks: List[CheckResult] = field(default_factory=list)
    cni_checks: List[CheckResult] = field(default_factory=list)

    # kubeadm join command — generated during init, shown to student for worker
    kubeadm_join_command: str = ""

    # Teardown state
    teardown_confirmed: bool = False
    teardown_checks: List[CheckResult] = field(default_factory=list)

    # Cost tracking (placeholder for future L0 cost visibility feature)
    estimated_cost_usd: float = 0.0
    session_uptime_minutes: int = 0

    # Free-form notes for the UI to surface
    notes: List[str] = field(default_factory=list)

    def current_phase_label(self) -> str:
        return PHASE_LABELS.get(self.phase, self.phase)

    def control_plane(self) -> Optional[NodeState]:
        return next((node for node in self.nodes if node.role == "control-plane"), None)

    def workers(self) -> List[NodeState]:
        return [node for node in self.nodes if node.role == "worker"]

    def all_nodes_passed(self, checks_attr: str = "checks") -> bool:
        return all(node.passed() for node in self.nodes)

    def phase_index(self) -> int:
        try:
            return PHASE_ORDER.index(self.phase)
        except ValueError:
            return 0

    def advance_phase(self) -> None:
        idx = self.phase_index()
        if idx < len(PHASE_ORDER) - 1:
            self.phase = PHASE_ORDER[idx + 1]

    def to_dict(self) -> Dict[str, Any]:
        # Minimal serialisation for Streamlit session state storage
        return {
            "phase": self.phase,
            "selected_cni": self.selected_cni,
            "kubeadm_join_command": self.kubeadm_join_command,
            "teardown_confirmed": self.teardown_confirmed,
            "estimated_cost_usd": self.estimated_cost_usd,
            "session_uptime_minutes": self.session_uptime_minutes,
            "notes": self.notes,
            "nodes": [
                {
                    "name": node.name,
                    "role": node.role,
                    "instance_id": node.instance_id,
                    "public_ip": node.public_ip,
                    "private_ip": node.private_ip,
                    "instance_type": node.instance_type,
                    "state": node.state,
                    "ssh_reachable": node.ssh_reachable,
                    "ping_reachable": node.ping_reachable,
                }
                for node in self.nodes
            ],
        }
