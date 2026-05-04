"""
phase_evidence.py

Evidence-based phase status for the testbed workflow.

Rather than relying on button clicks to track progress, this module
queries observable signals to determine what has actually been achieved.

Each phase maps to a concrete observable check:
- L0  AWS        : aws ec2 describe-instances — instances running
- L1-L3 Prereqs  : student-confirmed (SSH evidence pending issue #1)
- L4.5 K8s       : kubectl get nodes — nodes present
- L4.3 CNI       : kubectl get nodes — nodes Ready
- L8  cka-coach  : HTTP check to port 8501 on control plane public IP

ELS layers: L0, L1-L3, L4.5, L4.3, L8
"""

import subprocess
from dataclasses import dataclass
from typing import List, Optional


EVIDENCE_UNKNOWN = "unknown"
EVIDENCE_OBSERVED = "observed"
EVIDENCE_NOT_OBSERVED = "not_observed"
EVIDENCE_STUDENT_CONFIRMED = "student_confirmed"


@dataclass
class PhaseEvidence:
    phase_id: str
    label: str
    els_layer: str
    status: str                  # observed, not_observed, unknown, student_confirmed
    detail: str                  # what was seen
    icon: str                    # 🟢 🟡 🔴


def _run(cmd: List[str], timeout: int = 8) -> tuple[bool, str]:
    """Run a command, return (success, output)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        output = (result.stdout or result.stderr or "").strip()
        return result.returncode == 0, output
    except Exception as e:
        return False, str(e)


def check_aws_phase(nodes: list) -> PhaseEvidence:
    """L0 — check if AWS instances are running."""
    running = [n for n in nodes if getattr(n, "state", "") == "running"]
    total = len(nodes)

    if not nodes:
        return PhaseEvidence(
            phase_id="aws",
            label="L0 — AWS Environment",
            els_layer="L0",
            status=EVIDENCE_NOT_OBSERVED,
            detail="No instances detected — run AWS validation",
            icon="🟡",
        )
    if len(running) == total and total >= 2:
        return PhaseEvidence(
            phase_id="aws",
            label="L0 — AWS Environment",
            els_layer="L0",
            status=EVIDENCE_OBSERVED,
            detail=f"{len(running)}/{total} instances running",
            icon="🟢",
        )
    return PhaseEvidence(
        phase_id="aws",
        label="L0 — AWS Environment",
        els_layer="L0",
        status=EVIDENCE_NOT_OBSERVED,
        detail=f"{len(running)}/{total} instances running",
        icon="🔴",
    )


def check_prereqs_phase(prereq_states: dict, node_names: List[str]) -> PhaseEvidence:
    """L1-L3 — student-confirmed prerequisites."""
    if not node_names:
        return PhaseEvidence(
            phase_id="prereqs",
            label="L1–L3 — Node Prerequisites",
            els_layer="L1",
            status=EVIDENCE_UNKNOWN,
            detail="No nodes detected yet",
            icon="🟡",
        )
    all_done = all(
        prereq_states.get(name) and prereq_states[name].all_done()
        for name in node_names
    )
    if all_done:
        return PhaseEvidence(
            phase_id="prereqs",
            label="L1–L3 — Node Prerequisites",
            els_layer="L1",
            status=EVIDENCE_STUDENT_CONFIRMED,
            detail="All prerequisite steps confirmed on all nodes",
            icon="🟢",
        )
    confirmed_nodes = [
        name for name in node_names
        if prereq_states.get(name) and prereq_states[name].all_done()
    ]
    return PhaseEvidence(
        phase_id="prereqs",
        label="L1–L3 — Node Prerequisites",
        els_layer="L1",
        status=EVIDENCE_NOT_OBSERVED,
        detail=f"{len(confirmed_nodes)}/{len(node_names)} nodes confirmed",
        icon="🟡",
    )


def check_k8s_phase() -> PhaseEvidence:
    """L4.5 — check if kubectl can reach the cluster and nodes exist."""
    ok, output = _run(["kubectl", "get", "nodes", "--no-headers"])
    if not ok or not output.strip():
        return PhaseEvidence(
            phase_id="k8s",
            label="L4.5 — Kubernetes",
            els_layer="L4.5",
            status=EVIDENCE_NOT_OBSERVED,
            detail="kubectl cannot reach cluster — kubeadm init may not have run yet",
            icon="🟡",
        )
    lines = [l for l in output.splitlines() if l.strip()]
    node_count = len(lines)
    return PhaseEvidence(
        phase_id="k8s",
        label="L4.5 — Kubernetes",
        els_layer="L4.5",
        status=EVIDENCE_OBSERVED,
        detail=f"{node_count} node(s) observed via kubectl",
        icon="🟢",
    )


def check_cni_phase() -> PhaseEvidence:
    """L4.3 — check if all nodes are Ready (CNI working)."""
    ok, output = _run(["kubectl", "get", "nodes", "--no-headers"])
    if not ok or not output.strip():
        return PhaseEvidence(
            phase_id="cni",
            label="L4.3 — CNI",
            els_layer="L4.3",
            status=EVIDENCE_NOT_OBSERVED,
            detail="kubectl cannot reach cluster",
            icon="🟡",
        )
    lines = [l for l in output.splitlines() if l.strip()]
    ready = [l for l in lines if len(l.split()) >= 2 and l.split()[1] == "Ready"]
    not_ready = [l for l in lines if len(l.split()) >= 2 and l.split()[1] == "NotReady"]

    if lines and len(ready) == len(lines):
        node_names = [l.split()[0] for l in ready]
        return PhaseEvidence(
            phase_id="cni",
            label="L4.3 — CNI",
            els_layer="L4.3",
            status=EVIDENCE_OBSERVED,
            detail=f"All nodes Ready: {', '.join(node_names)}",
            icon="🟢",
        )
    return PhaseEvidence(
        phase_id="cni",
        label="L4.3 — CNI",
        els_layer="L4.3",
        status=EVIDENCE_NOT_OBSERVED,
        detail=f"{len(ready)} Ready, {len(not_ready)} NotReady — CNI may not be installed yet",
        icon="🟡",
    )


def check_cka_coach_phase(cp_public_ip: str) -> PhaseEvidence:
    """L8 — check if cka-coach is reachable on the control plane."""
    if not cp_public_ip:
        return PhaseEvidence(
            phase_id="cka_coach",
            label="L8 — cka-coach on cluster",
            els_layer="L8",
            status=EVIDENCE_NOT_OBSERVED,
            detail="Control plane public IP not known yet",
            icon="🟡",
        )
    ok, output = _run(
        ["curl", "-s", "--max-time", "4", "-o", "/dev/null", "-w", "%{http_code}",
         f"http://{cp_public_ip}:8501"],
        timeout=6,
    )
    if ok and output.strip() in ("200", "302", "303"):
        return PhaseEvidence(
            phase_id="cka_coach",
            label="L8 — cka-coach on cluster",
            els_layer="L8",
            status=EVIDENCE_OBSERVED,
            detail=f"cka-coach reachable at http://{cp_public_ip}:8501",
            icon="🟢",
        )
    return PhaseEvidence(
        phase_id="cka_coach",
        label="L8 — cka-coach on cluster",
        els_layer="L8",
        status=EVIDENCE_NOT_OBSERVED,
        detail=f"cka-coach not yet reachable at http://{cp_public_ip}:8501",
        icon="🟡",
    )


def collect_phase_evidence(
    nodes: list,
    prereq_states: dict,
    cp_public_ip: str = "",
) -> List[PhaseEvidence]:
    """
    Collect evidence for all five phases.
    Safe to call with no cluster present — each check handles its own failure.
    """
    node_names = [n.name for n in nodes]
    return [
        check_aws_phase(nodes),
        check_prereqs_phase(prereq_states, node_names),
        check_k8s_phase(),
        check_cni_phase(),
        check_cka_coach_phase(cp_public_ip),
    ]


def infer_likely_phase(evidence: List[PhaseEvidence]) -> str:
    """
    Infer the most likely current phase from evidence.
    Used on page load to give the student a hint about where they are.
    """
    from testbed.testbed_state import (
        PHASE_AWS_VALIDATION, PHASE_PREREQUISITES,
        PHASE_K8S_INSTALL, PHASE_CNI_INSTALL, PHASE_COMPLETE,
    )
    phase_map = [
        ("aws", PHASE_AWS_VALIDATION),
        ("prereqs", PHASE_PREREQUISITES),
        ("k8s", PHASE_K8S_INSTALL),
        ("cni", PHASE_CNI_INSTALL),
        ("cka_coach", PHASE_COMPLETE),
    ]
    last_observed = PHASE_AWS_VALIDATION
    for ev in evidence:
        for phase_id, phase_const in phase_map:
            if ev.phase_id == phase_id and ev.status == EVIDENCE_OBSERVED:
                last_observed = phase_const
    return last_observed
