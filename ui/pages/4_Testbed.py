"""
4_Testbed.py

Guided two-VM Kubernetes testbed setup and teardown page.

Follows the UI and learning experience rules:
- Progressive disclosure — show what matters first
- Every step identifies its ELS layer
- Beginner-friendly tone — explain why before asking the student to run anything
- Confirmation gates before destructive operations
- Cost reminder at start and end of session
"""

import sys
import os
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from testbed.testbed_state import (
    TestbedState,
    CNI_OPTIONS,
    CNI_DESCRIPTIONS,
    PLATFORM_AWS,
    PLATFORM_KIND,
    PLATFORM_OPTIONS,
    PLATFORM_LABELS,
    PHASE_AWS_VALIDATION,
    PHASE_PREREQUISITES,
    PHASE_K8S_INSTALL,
    PHASE_CNI_INSTALL,
    PHASE_COMPLETE,
    PHASE_TEARDOWN,
    PHASE_ORDER,
    PHASE_LABELS,
)
from testbed.aws_validator import validate_aws_environment
from testbed.kind_validator import validate_kind_environment, KIND_WARNING
from testbed.prereq_checker import (
    PREREQ_STEPS,
    NodePrereqState,
    build_ssh_instruction,
    build_node_prereq_state,
)
from testbed.phase_evidence import (
    collect_phase_evidence,
    collect_cost_summary,
    infer_likely_phase,
    EVIDENCE_OBSERVED,
    EVIDENCE_STUDENT_CONFIRMED,
)
from testbed.k8s_installer import (
    build_k8s_install_bundle,
    process_init_output,
    process_validation_output,
    build_node_ready_check,
    build_pods_check,
    get_teaching_note as k8s_note,
    K8sInstallBundle,
)
from testbed.cni_installer import (
    build_cni_install_bundle,
    parse_cni_validation_output,
    get_teaching_note as cni_note,
    CNIInstallBundle,
)
from testbed.teardown import (
    build_teardown_bundle,
    process_worker_teardown,
    process_cp_teardown,
    get_teaching_note as teardown_note,
    TeardownBundle,
)
from observer_context import collect_observer_context, get_browser_client_ip

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(layout="wide", page_title="cka-coach — Testbed")
st.title("🖥️ Testbed Setup")
st.caption("Guided two-VM Kubernetes cluster setup and teardown — powered by the ELS model.")

# Observer context banner
_observer = collect_observer_context()
_browser_ip = get_browser_client_ip()
_banner_color = "🟢" if _observer.cluster_reachable else "🟡"

_observer_lines = [f"{_banner_color} **{_observer.summary}**", _observer.consequence]
if _observer.mode in ("node_with_cluster", "node_no_cluster", "node_in_cluster"):
    _observer_lines.append(
        "💻 All evidence collection runs on this EC2 node — not your browser."
    )
    if _browser_ip:
        _observer_lines.append(
            f"🌐 You are viewing this from: **{_browser_ip}** (your browser / Mac) — "
            "the browser is a display surface only."
        )
    else:
        _observer_lines.append(
            "🌐 Your browser is a display surface only — it connects to this node over HTTP. "
            "Your Mac IP is not exposed without a reverse proxy."
        )
st.info("  \n".join(_observer_lines))

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "testbed_state" not in st.session_state:
    st.session_state["testbed_state"] = TestbedState()
if "k8s_bundle" not in st.session_state:
    st.session_state["k8s_bundle"] = None
if "cni_bundle" not in st.session_state:
    st.session_state["cni_bundle"] = None
if "teardown_bundle" not in st.session_state:
    st.session_state["teardown_bundle"] = None
if "prereq_states" not in st.session_state:
    st.session_state["prereq_states"] = {}

state: TestbedState = st.session_state["testbed_state"]


def _save_state():
    st.session_state["testbed_state"] = state


def _render_checks(checks, show_remediation: bool = True):
    for check in checks:
        icon = "✅" if check.passed else "❌"
        st.markdown(f"{icon} **[{check.els_layer}] {check.name}** — {check.detail}")
        if not check.passed and show_remediation and check.remediation:
            st.caption(f"↳ {check.remediation}")


def _render_commands(commands: list):
    st.code("\n".join(commands), language="bash")


def _phase_progress():
    try:
        idx = PHASE_ORDER.index(state.phase)
        total = len(PHASE_ORDER)
        st.progress(idx / (total - 1))
        st.caption(f"Phase {idx + 1} of {total}: {PHASE_LABELS.get(state.phase, state.phase)}")
    except ValueError:
        pass


def _render_cost_strip():
    """
    Render a persistent L0 cost strip showing per-instance uptime and estimated cost.
    Replaces the simple _cost_reminder warning with real evidence-based cost data.
    """
    if not state.nodes:
        return
    summary = collect_cost_summary(state.nodes)
    if not summary.instances:
        return

    with st.container(border=True):
        st.caption("💰 L0 — Running cost estimate (On Demand, ca-central-1)")
        cols = st.columns(len(summary.instances) + 2)
        for i, inst in enumerate(summary.instances):
            with cols[i]:
                if inst.state == "running":
                    st.metric(
                        label=inst.name,
                        value=f"${inst.estimated_cost_usd:.4f}",
                        delta=f"{inst.uptime_hours}h @ ${inst.hourly_rate}/hr",
                        delta_color="off",
                    )
                else:
                    st.metric(
                        label=inst.name,
                        value="$0.00",
                        delta="stopped — EBS charges apply",
                        delta_color="off",
                    )
        with cols[len(summary.instances)]:
            if summary.running_count > 0:
                st.metric(
                    label="Total so far",
                    value=f"${summary.total_running_cost_usd:.4f}",
                    delta=f"~${summary.projected_8h_cost_usd:.2f} if left 8h",
                    delta_color="inverse",
                )
        with cols[len(summary.instances) + 1]:
            if summary.running_count > 0:
                instance_ids = " ".join(
                    n.instance_id for n in state.nodes
                    if n.state == "running" and n.instance_id
                )
                st.caption("Stop when done:")
                st.code(
                    f"aws ec2 stop-instances --instance-ids {instance_ids}",
                    language="bash",
                )


def _cost_reminder():
    """Lightweight fallback used in phase completion screens."""
    running = [n for n in state.nodes if n.state == "running"]
    if running:
        st.warning(
            f"⚠️ {len(running)} instance(s) currently running — remember to stop them "
            "when done to avoid unnecessary AWS charges."
        )


# ---------------------------------------------------------------------------
# Phase indicator + Platform + CNI selector
# ---------------------------------------------------------------------------

# L0 cost strip
_render_cost_strip()

# Platform selector
platform_col, cni_col = st.columns(2)
with platform_col:
    selected_platform = st.selectbox(
        "Testbed platform",
        options=PLATFORM_OPTIONS,
        index=PLATFORM_OPTIONS.index(state.selected_platform),
        format_func=lambda p: PLATFORM_LABELS[p],
        key="platform_selector",
    )
    if selected_platform != state.selected_platform:
        state.selected_platform = selected_platform
        state.nodes = []
        state.aws_checks = []
        state.notes = []
        state.phase = PHASE_AWS_VALIDATION
        st.session_state["prereq_states"] = {}
        st.session_state["k8s_bundle"] = None
        st.session_state["cni_bundle"] = None
        _save_state()
        st.rerun()

# KIND warning
if state.selected_platform == PLATFORM_KIND:
    st.warning(KIND_WARNING)

# CNI selector
with cni_col:
    selected_cni = st.selectbox(
        "CNI path",
        options=CNI_OPTIONS,
        index=CNI_OPTIONS.index(state.selected_cni),
        format_func=lambda cni: CNI_DESCRIPTIONS[cni],
        key="cni_selector",
    )
    if selected_cni != state.selected_cni:
        state.selected_cni = selected_cni
        st.session_state["cni_bundle"] = None
        _save_state()

# ---------------------------------------------------------------------------
# Evidence-based phase status strip
# ---------------------------------------------------------------------------

if "phase_evidence" not in st.session_state:
    st.session_state["phase_evidence"] = None

cp = state.control_plane()
cp_public_ip = cp.public_ip if cp else ""

# On page load, hint if cluster already looks deployed
if st.session_state["phase_evidence"] is None:
    quick_evidence = collect_phase_evidence(
        state.nodes,
        st.session_state.get("prereq_states", {}),
        cp_public_ip,
    )
    observed_count = sum(
        1 for e in quick_evidence
        if e.status in (EVIDENCE_OBSERVED, EVIDENCE_STUDENT_CONFIRMED)
    )
    if observed_count >= 3:
        st.session_state["phase_evidence"] = quick_evidence
        inferred = infer_likely_phase(quick_evidence)
        if inferred != state.phase:
            state.phase = inferred
            _save_state()

evidence = st.session_state["phase_evidence"]

with st.container(border=True):
    ev_cols = st.columns([3, 1])
    with ev_cols[0]:
        if evidence:
            for ev in evidence:
                st.markdown(f"{ev.icon} **{ev.label}** — {ev.detail}")
        else:
            st.caption("Run evidence check to see observed cluster state.")
    with ev_cols[1]:
        if st.button("🔍 Run evidence check", key="run_evidence"):
            with st.spinner("Checking cluster state..."):
                st.session_state["phase_evidence"] = collect_phase_evidence(
                    state.nodes,
                    st.session_state.get("prereq_states", {}),
                    cp_public_ip,
                )
                inferred = infer_likely_phase(st.session_state["phase_evidence"])
                if inferred != state.phase:
                    state.phase = inferred
                    _save_state()
                st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Phase 1 — AWS Environment Validation (L0)
# ---------------------------------------------------------------------------

aws_all_passed = bool(state.aws_checks) and all(c.passed for c in state.aws_checks) and all(n.passed() for n in state.nodes)

with st.expander(
    f"{'✅' if aws_all_passed else '🔲'} Phase 1 — {PHASE_LABELS[PHASE_AWS_VALIDATION]}",
    expanded=(state.phase == PHASE_AWS_VALIDATION),
):
    st.caption(
        "Validate that your environment is ready before touching Kubernetes."
        + (" KIND handles L1-L3 automatically — no manual prerequisites needed." if state.selected_platform == PLATFORM_KIND else "")
    )

    if st.button("Run AWS validation", key="run_aws_validation") if state.selected_platform == PLATFORM_AWS else st.button("Run KIND validation", key="run_kind_validation"):
        with st.spinner("Checking environment..."):
            if state.selected_platform == PLATFORM_KIND:
                state = validate_kind_environment(state)
            else:
                state = validate_aws_environment(state)
            _save_state()

    if state.aws_checks:
        _render_checks(state.aws_checks)

    if state.nodes:
        st.markdown("**Detected instances**")
        for node in state.nodes:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Name", node.name)
                col2.metric("Role", node.role)
                col3.metric("State", node.state)
                col4.metric("Type", node.instance_type)
                st.caption(f"Private IP: {node.private_ip} | Public IP: {node.public_ip or 'none'}")
                _render_checks(node.checks)

    _cost_reminder()
    for note in state.notes:
        st.info(note)

    if aws_all_passed and state.phase == PHASE_AWS_VALIDATION:
        if st.button("✅ AWS validation passed — proceed to prerequisites", key="advance_to_prereqs"):
            state.advance_phase()
            _save_state()
            st.rerun()

# ---------------------------------------------------------------------------
# Phase 2 — Node Prerequisites (L1, L2, L3)
# ---------------------------------------------------------------------------

# Initialise prereq state for each node
# Reset if step count has changed (e.g. new steps added)
for node in state.nodes:
    existing = st.session_state["prereq_states"].get(node.name)
    if existing is None or len(existing.steps) != len(PREREQ_STEPS):
        st.session_state["prereq_states"][node.name] = build_node_prereq_state(node)

all_prereqs_done = (
    bool(state.nodes)
    and all(
        st.session_state["prereq_states"].get(n.name, NodePrereqState(
            node_name=n.name, role=n.role, private_ip=n.private_ip
        )).all_done()
        for n in state.nodes
    )
)

with st.expander(
    f"{'✅' if all_prereqs_done else '🔲'} Phase 2 — {PHASE_LABELS[PHASE_PREREQUISITES]}",
    expanded=(state.phase == PHASE_PREREQUISITES),
):
    if state.selected_platform == PLATFORM_KIND:
        st.success(
            "✅ KIND manages L1–L3 automatically — no manual prerequisites needed.  \n"
            "KIND nodes come pre-configured with containerd and the required kernel settings.  \n"
            "Note: this means you cannot observe or learn these layers in KIND — they are hidden."
        )
        if state.phase == PHASE_PREREQUISITES:
            if st.button("✅ Skip prerequisites — proceed to Kubernetes install", key="kind_skip_prereqs"):
                state.advance_phase()
                _save_state()
                st.rerun()
    else:
        st.caption(
            "Before Kubernetes can run, each node needs a few things configured at the kernel and runtime level. "
            "We will go through them one at a time. For each step: read why it matters, run the check command, "
            "then confirm whether it passed or needs fixing."
        )

        if not state.nodes:
            st.info("Complete Phase 1 validation first to detect your nodes.")
        else:
            for node in state.nodes:
                prereq_state: NodePrereqState = st.session_state["prereq_states"][node.name]
                current_idx = prereq_state.current_step_index()

                with st.container(border=True):
                    st.markdown(f"### {node.name} ({node.role})")
                    st.caption(
                        f"SSH into this node: `{build_ssh_instruction(node)}`  \n"
                        "Keep your SSH session open — you will run commands there for each step below."
                    )

                    done_count = sum(1 for s in prereq_state.steps if s.confirmed)
                    st.progress(done_count / len(PREREQ_STEPS))
                    st.caption(f"{done_count} of {len(PREREQ_STEPS)} steps complete")

                    shortcut_col1, shortcut_col2 = st.columns([2, 1])
                    shortcut_col1.caption(
                        "Already configured this node? Mark all steps complete to skip ahead."
                    )
                    if shortcut_col2.button(f"Mark all complete", key=f"mark_all_{node.name}"):
                        for s in prereq_state.steps:
                            s.confirmed = True
                        st.session_state["prereq_states"][node.name] = prereq_state
                        st.rerun()

                    for idx, step_def in enumerate(PREREQ_STEPS):
                        step_state = prereq_state.get_step(step_def["id"])
                        step_key = f"{node.name}_{step_def['id']}"

                        if step_state.confirmed:
                            col_a, col_b = st.columns([4, 1])
                            col_a.markdown(f"✅ **[{step_def['els_layer']}] {step_def['title']}** — done")
                            if col_b.button("Undo", key=f"undo_{step_key}"):
                                step_state.confirmed = False
                                st.session_state["prereq_states"][node.name] = prereq_state
                                st.rerun()
                            continue

                        with st.container(border=True):
                            st.markdown(f"**[{step_def['els_layer']}] Step {idx + 1}: {step_def['title']}**")
                            st.info(f"**Why Kubernetes needs this:**  \n{step_def['why']}")
                            st.markdown("**Run this on the node to check current state:**")
                            _render_commands(step_def["check_commands"])
                            st.caption(step_def["check_hint"])

                            passed = st.radio(
                                f"Result for: {step_def['confirm_question']}",
                                options=["— select —", "✅ Yes, it passed", "❌ No, it needs fixing"],
                                key=f"radio_{step_key}",
                                index=0,
                            )

                            if passed == "✅ Yes, it passed":
                                if st.button(f"Confirm and continue", key=f"confirm_{step_key}"):
                                    step_state.confirmed = True
                                    st.session_state["prereq_states"][node.name] = prereq_state
                                    st.rerun()
                            elif passed == "❌ No, it needs fixing":
                                if step_def["fix_commands"]:
                                    st.markdown("**Run these fix commands on the node:**")
                                    _render_commands(step_def["fix_commands"])
                                    st.caption(step_def["fix_hint"])
                                    st.caption("After running the fix commands, re-run the check command above and select ✅ Yes when it passes.")
                                else:
                                    st.caption(step_def["fix_hint"])

        if all_prereqs_done and state.phase == PHASE_PREREQUISITES:
            if st.button("✅ All prerequisites done — proceed to Kubernetes install", key="advance_to_k8s"):
                state.advance_phase()
                _save_state()
                st.rerun()

# ---------------------------------------------------------------------------
# Phase 3 — Kubernetes Installation (L4.5, L5, L7)
# ---------------------------------------------------------------------------

with st.expander(
    f"🔲 Phase 3 — {PHASE_LABELS[PHASE_K8S_INSTALL]}",
    expanded=(state.phase == PHASE_K8S_INSTALL),
):
    st.caption("Install Kubernetes using kubeadm on the control plane, then join the worker node.")

    if not state.nodes:
        st.info("Complete AWS validation first.")
    else:
        if st.session_state["k8s_bundle"] is None:
            st.session_state["k8s_bundle"] = build_k8s_install_bundle(state)

        k8s: K8sInstallBundle = st.session_state["k8s_bundle"]
        cp = state.control_plane()
        workers = state.workers()

        # Step 0 — install kubelet/kubeadm/kubectl (deferred from phase 2)
        with st.container(border=True):
            st.markdown("**Step 1 — Install kubelet, kubeadm, and kubectl on both nodes**")
            st.info(
                "**Why Kubernetes needs this (L4.1):**  \n"
                "kubelet is the node agent that runs on every node and manages pods. "
                "kubeadm is the tool that bootstraps the cluster. "
                "kubectl is the command-line tool you use to talk to the cluster. "
                "We will explore each of these in detail in the L4.1 and L4.5 lessons."
            )
            k8s_install_cmds = [
                "# Add the Kubernetes apt repository",
                "sudo apt-get update",
                "sudo apt-get install -y apt-transport-https ca-certificates curl gpg",
                "curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.32/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg",
                "echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.32/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list",
                "sudo apt-get update",
                "# Install kubelet, kubeadm, kubectl and pin their versions",
                "sudo apt-get install -y kubelet kubeadm kubectl",
                "sudo apt-mark hold kubelet kubeadm kubectl",
            ]
            st.caption("Run these commands on **both nodes** (control plane and worker):")
            _render_commands(k8s_install_cmds)
            kubelet_done = st.checkbox("I have installed kubelet, kubeadm, and kubectl on both nodes", key="kubelet_done")

        # Step 2 — kubeadm init
        if kubelet_done:
            with st.container(border=True):
                st.markdown("**Step 2 — kubeadm init on control plane**")
                st.info(
                    f"**Why Kubernetes needs this (L4.5):**  \n"
                    f"{k8s_note('kubeadm init')}"
                )
                st.caption(f"Run this on **{cp.name if cp else 'control plane'}** only:")
                st.code(k8s.init_command, language="bash")
                st.markdown("**Then configure kubectl (run on control plane):**")
                st.code("\n".join(k8s.kubeconfig_commands), language="bash")

                init_output = st.text_area(
                    "Paste the full output of kubeadm init here",
                    key="k8s_init_output",
                    height=150,
                    placeholder="Paste kubeadm init output here — we need it to extract the join command for the worker...",
                )
                if st.button("Parse init output", key="parse_k8s_init"):
                    k8s.init_output = init_output
                    k8s = process_init_output(k8s, state, cp)
                    st.session_state["k8s_bundle"] = k8s
                    _save_state()
                    st.rerun()

                if k8s.init_checks:
                    _render_checks(k8s.init_checks)

        # Step 3 — kubeadm join
        if k8s.init_done and workers:
            with st.container(border=True):
                st.markdown(f"**Step 3 — kubeadm join on {workers[0].name}**")
                st.info(
                    f"**Why Kubernetes needs this (L4.1):**  \n"
                    f"{k8s_note('kubeadm join')}"
                )
                st.caption(f"Run this on **{workers[0].name}** only:")
                if k8s.join_command:
                    st.code(k8s.join_command, language="bash")
                else:
                    st.info("Join command will appear here after init output is parsed above.")

                join_done = st.checkbox("I have run the join command on the worker", key="join_done")
                if join_done:
                    k8s.join_done = True
                    st.session_state["k8s_bundle"] = k8s

        # Step 4 — validation
        if k8s.join_done:
            with st.container(border=True):
                st.markdown("**Step 4 — validate cluster state**")
                st.info(
                    f"**What to expect (L4.5 / L4.3):**  \n"
                    f"{k8s_note('node ready')}"
                )
                st.caption("Run these on the **control plane**:")
                st.code(f"{build_node_ready_check()}\n{build_pods_check()}", language="bash")

                nodes_output = st.text_area("Paste kubectl get nodes output", key="k8s_nodes_output", height=100)
                pods_output = st.text_area("Paste kubectl get pods -A output", key="k8s_pods_output", height=100)

                if st.button("Parse validation output", key="parse_k8s_validation"):
                    k8s.nodes_output = nodes_output
                    k8s.pods_output = pods_output
                    k8s = process_validation_output(k8s, [n.name for n in state.nodes])
                    st.session_state["k8s_bundle"] = k8s
                    st.rerun()

                if k8s.node_checks or k8s.pod_checks:
                    _render_checks(k8s.node_checks + k8s.pod_checks)
                    st.caption(k8s_note("system pods"))

        k8s_ready = k8s.join_done and bool(k8s.pod_checks) and all(c.passed for c in k8s.pod_checks)
        if k8s_ready and state.phase == PHASE_K8S_INSTALL:
            if st.button("✅ Kubernetes installed — proceed to CNI install", key="advance_to_cni"):
                state.advance_phase()
                _save_state()
                st.rerun()

# ---------------------------------------------------------------------------
# Phase 4 — CNI Installation (L4.3)
# ---------------------------------------------------------------------------

with st.expander(
    f"🔲 Phase 4 — {PHASE_LABELS[PHASE_CNI_INSTALL]}",
    expanded=(state.phase == PHASE_CNI_INSTALL),
):
    st.caption(f"Install the chosen CNI: **{CNI_DESCRIPTIONS[state.selected_cni]}**")

    if st.session_state["cni_bundle"] is None:
        st.session_state["cni_bundle"] = build_cni_install_bundle(state)

    cni: CNIInstallBundle = st.session_state["cni_bundle"]

    with st.container(border=True):
        st.markdown("**Install commands**")
        st.info(f"**Why Kubernetes needs this (L4.3):**  \n{cni_note(state.selected_cni)}")
        _render_commands(cni.install_commands)

    with st.container(border=True):
        st.markdown("**Validation commands**")
        st.code("\n".join(cni.validation_commands), language="bash")

        cni_output = st.text_area(
            "Paste CNI validation output",
            key="cni_validation_output",
            height=150,
            placeholder="Paste the combined output of the validation commands here...",
        )
        if st.button("Parse CNI validation output", key="parse_cni_output"):
            cni.validation_output = cni_output
            cni = parse_cni_validation_output(cni, [n.name for n in state.nodes])
            st.session_state["cni_bundle"] = cni
            st.rerun()

        if cni.parsed:
            _render_checks(cni.checks)

    if cni.all_passed() and state.phase == PHASE_CNI_INSTALL:
        if st.button("✅ CNI installed — cluster is ready", key="advance_to_complete"):
            state.advance_phase()
            _save_state()
            st.rerun()

# ---------------------------------------------------------------------------
# Phase 5 — Deploy cka-coach to the cluster (L8)
# ---------------------------------------------------------------------------

with st.expander(
    f"{'✅' if evidence and any(e.phase_id == 'cka_coach' and e.status == EVIDENCE_OBSERVED for e in evidence) else '🔲'} "
    f"Phase 5 — L8 — Deploy cka-coach to the cluster",
    expanded=(state.phase == PHASE_COMPLETE),
):
    st.caption(
        "Move cka-coach from your Mac into the cluster. "
        "Once running on the control plane node, cka-coach can directly observe "
        "L1 through L8 — kernel, runtime, kubelet, CNI, and pods — instead of "
        "being limited to what it can see from outside."
    )
    st.info(
        "💡 **ELS teaching moment (L8):**  \n"
        "Right now cka-coach runs on your Mac and can only see what the AWS API and kubectl expose. "
        "When it runs on the control plane node it becomes a workload in the cluster — "
        "an application at L8 with direct access to the host at L1. "
        "The ELS panel will go from mostly 🟡 to mostly 🟢. "
        "This is the first capstone: you built the cluster, now deploy your first workload into it."
    )

    cp = state.control_plane()
    cp_public_ip = cp.public_ip if cp else ""
    cp_private_ip = cp.private_ip if cp else ""
    cp_name = cp.name if cp else "cka-coach-cp"

    with st.container(border=True):
        st.markdown("**Step 1 — SSH into the control plane**")
        st.code(
            f"ssh -i ~/.ssh/aws-instance-cp.pem ubuntu@{cp_public_ip or '<control-plane-public-ip>'}",
            language="bash",
        )

    with st.container(border=True):
        st.markdown("**Step 2 — Clone cka-coach and install dependencies**")
        st.code(
            "git clone https://github.com/fishtrap2/cka-coach-phase3.git\n"
            "cd cka-coach-phase3\n"
            "python3 -m venv venv\n"
            "source venv/bin/activate\n"
            "pip install -r requirements.txt",
            language="bash",
        )

    with st.container(border=True):
        st.markdown("**Step 3 — Set your OpenAI API key**")
        st.warning(
            "⚠️ Set the key as an environment variable in your SSH session only. "
            "Do not write it to any file on the VM. "
            "See issue #5 for the future IAM role approach."
        )
        st.code("export OPENAI_API_KEY=<your-openai-api-key>", language="bash")

    with st.container(border=True):
        st.markdown("**Step 4 — Open port 8501 in your AWS security group**")
        st.caption(
            "Streamlit runs on port 8501. You need to allow inbound TCP 8501 "
            "from your Mac's IP in the security group."
        )
        st.code(
            f"# Find your Mac's public IP\n"
            f"curl -s ifconfig.me\n\n"
            f"# Then in AWS Console or CLI, add inbound rule:\n"
            f"# Type: Custom TCP | Port: 8501 | Source: <your-mac-ip>/32",
            language="bash",
        )

    with st.container(border=True):
        st.markdown("**Step 5 — Run cka-coach with host evidence enabled**")
        st.code(
            "streamlit run ui/dashboard.py --server.address=0.0.0.0 -- --allow-host-evidence",
            language="bash",
        )
        if cp_public_ip:
            st.success(
                f"🟢 Open in your browser: http://{cp_public_ip}:8501  \n"
                "The observer banner should show: 🟢 Observer: Linux node — connected to cluster  \n"
                "The ELS panel should now show real observed state for L1 through L4.3."
            )
        else:
            st.caption("Run AWS validation first to get the control plane public IP.")

    st.divider()
    st.markdown("**Verify cka-coach is running on the cluster**")
    st.caption(
        "If this check fails but you can open the URL in your browser, "
        "re-run AWS validation above to refresh the current public IP — "
        "it changes every time the instance stops and starts."
    )
    if st.button("🔍 Check if cka-coach is reachable", key="check_cka_coach"):
        with st.spinner(f"Checking http://{cp_public_ip}:8501 ..."):
            # Always re-query AWS for the freshest public IP
            from testbed.aws_validator import detect_instances
            fresh_nodes, _ = detect_instances()
            fresh_cp = next((n for n in fresh_nodes if n.role == "control-plane"), None)
            fresh_ip = fresh_cp.public_ip if fresh_cp and fresh_cp.public_ip else cp_public_ip
            from testbed.phase_evidence import check_cka_coach_phase
            ev = check_cka_coach_phase(fresh_ip)
            if ev.status == EVIDENCE_OBSERVED:
                st.success(ev.detail)
            else:
                st.warning(ev.detail)

# ---------------------------------------------------------------------------
# Phase 5 — Complete (old)
# ---------------------------------------------------------------------------

if state.phase == PHASE_COMPLETE:
    st.success(f"🎉 Cluster is ready. Kubernetes is running with {CNI_DESCRIPTIONS[state.selected_cni]}.")
    _cost_reminder()

    st.divider()
    st.markdown("## 🚀 Next step — run cka-coach from inside the cluster")
    st.info(
        "Now that your cluster is running, you can clone cka-coach onto the control plane node "
        "and run it from there. This gives cka-coach direct access to host-level evidence — "
        "kubelet, containerd, runc, kernel, and CNI config — so the ELS panel shows real "
        "observed state instead of visibility-limited."
    )

    cp = state.control_plane()
    cp_public_ip = cp.public_ip if cp else "<control-plane-public-ip>"

    with st.container(border=True):
        st.markdown("**Step 1 — SSH into the control plane**")
        st.code(f"ssh -i ~/.ssh/aws-instance-cp.pem ubuntu@{cp_public_ip}", language="bash")

    with st.container(border=True):
        st.markdown("**Step 2 — Clone cka-coach and install dependencies**")
        st.code(
            "git clone https://github.com/fishtrap2/cka-coach-phase3.git\n"
            "cd cka-coach-phase3\n"
            "python3 -m venv venv\n"
            "source venv/bin/activate\n"
            "pip install -r requirements.txt",
            language="bash",
        )

    with st.container(border=True):
        st.markdown("**Step 3 — Set your OpenAI API key**")
        st.warning(
            "⚠️ Do not write your API key to any file on this VM. "
            "Set it as an environment variable in your SSH session only. "
            "See issue #5 for the future IAM role approach that removes the need for this."
        )
        st.code("export OPENAI_API_KEY=<your-openai-api-key>", language="bash")

    with st.container(border=True):
        st.markdown("**Step 4 — Run cka-coach with host evidence enabled**")
        st.code(
            "streamlit run ui/dashboard.py --allow-host-evidence --server.address=0.0.0.0",
            language="bash",
        )
        st.caption(
            f"Then open: http://{cp_public_ip}:8501 in your browser.  \n"
            "The observer banner should show: 🟢 Observer: Linux node (cka-coach-cp) — connected to cluster.  \n"
            "The ELS panel should now show real observed state for L1 through L4.3."
        )

    st.caption(
        "Next steps: explore the ELS Console to inspect your running cluster, "
        "or use the Teardown section below to reset and try a different CNI."
    )

# ---------------------------------------------------------------------------
# Teardown (always visible — gated by confirmation)
# ---------------------------------------------------------------------------

st.divider()
with st.expander("⚠️ Teardown — Reset and Clean", expanded=(state.phase == PHASE_TEARDOWN)):
    st.warning(
        "Teardown will run `kubeadm reset` on all nodes and remove CNI state, "
        "iptables rules, and Kubernetes data directories. "
        "This cannot be undone. Your AWS instances will remain running."
    )

    if not state.nodes:
        st.info("Complete AWS validation first to detect your nodes.")
    else:
        confirmed = st.checkbox(
            "I understand this will destroy the Kubernetes cluster on my lab nodes",
            key="teardown_confirm",
        )

        if confirmed:
            if st.session_state["teardown_bundle"] is None:
                st.session_state["teardown_bundle"] = build_teardown_bundle(state)

            td: TeardownBundle = st.session_state["teardown_bundle"]
            td.confirmed = True
            workers = state.workers()
            cp = state.control_plane()

            if workers:
                with st.container(border=True):
                    st.markdown(f"**Step 1 — Reset worker: {workers[0].name}**")
                    st.caption(teardown_note("why worker first"))
                    _render_commands(td.worker_commands)
                    st.code("\n".join(td.verify_commands), language="bash")

                    worker_reset = st.text_area(f"Paste kubeadm reset output from {workers[0].name}", key="worker_reset_output", height=100)
                    worker_verify = st.text_area(f"Paste verify output from {workers[0].name}", key="worker_verify_output", height=100)

                    if st.button("Parse worker teardown output", key="parse_worker_teardown"):
                        td.worker_reset_output = worker_reset
                        td.worker_verify_output = worker_verify
                        td = process_worker_teardown(td, workers[0])
                        st.session_state["teardown_bundle"] = td
                        st.rerun()

                    if td.worker_reset_checks or td.worker_verify_checks:
                        _render_checks(td.worker_reset_checks + td.worker_verify_checks)
                        st.caption(teardown_note("cni residuals"))

            if cp and td.worker_done:
                with st.container(border=True):
                    st.markdown(f"**Step 2 — Reset control plane: {cp.name}**")
                    _render_commands(td.cp_commands)
                    st.code("\n".join(td.verify_commands), language="bash")

                    cp_reset = st.text_area(f"Paste kubeadm reset output from {cp.name}", key="cp_reset_output", height=100)
                    cp_verify = st.text_area(f"Paste verify output from {cp.name}", key="cp_verify_output", height=100)

                    if st.button("Parse control plane teardown output", key="parse_cp_teardown"):
                        td.cp_reset_output = cp_reset
                        td.cp_verify_output = cp_verify
                        td = process_cp_teardown(td, cp)
                        st.session_state["teardown_bundle"] = td
                        st.rerun()

                    if td.cp_reset_checks or td.cp_verify_checks:
                        _render_checks(td.cp_reset_checks + td.cp_verify_checks)
                        st.caption(teardown_note("clean state"))

            if td.all_passed():
                st.success("✅ Both nodes are clean. Ready for a fresh Kubernetes install.")
                _cost_reminder()
                if st.button("Reset testbed workflow", key="reset_testbed"):
                    st.session_state["testbed_state"] = TestbedState()
                    st.session_state["k8s_bundle"] = None
                    st.session_state["cni_bundle"] = None
                    st.session_state["teardown_bundle"] = None
                    st.session_state["prereq_states"] = {}
                    st.rerun()
