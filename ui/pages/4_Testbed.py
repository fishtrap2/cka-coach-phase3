"""
4_Testbed.py

Guided two-VM Kubernetes testbed setup and teardown page.

Follows the UI and learning experience rules:
- Progressive disclosure — show what matters first
- Raw evidence behind expanders
- Every step identifies its ELS layer
- Confirmation gates before destructive operations
- Cost reminder at start and end of session
"""

import sys
import os
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from testbed.testbed_state import (
    TestbedState,
    NodeState,
    CNI_CALICO,
    CNI_CILIUM,
    CNI_BRIDGE,
    CNI_OPTIONS,
    CNI_DESCRIPTIONS,
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
from testbed.prereq_checker import (
    build_prereq_bundle,
    build_ssh_instruction,
    parse_prereq_output,
    get_teaching_note as prereq_note,
    NodePrereqBundle,
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
from observer_context import collect_observer_context

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(layout="wide", page_title="cka-coach — Testbed")
st.title("🖥️ Testbed Setup")
st.caption("Guided two-VM Kubernetes cluster setup and teardown — powered by the ELS model.")

# --------------------------
# Observer Context Banner
# --------------------------
_observer = collect_observer_context()
_banner_color = "🟢" if _observer.cluster_reachable else "🟡"
st.info(
    f"{_banner_color} **{_observer.summary}**  \n{_observer.consequence}"
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

if "testbed_state" not in st.session_state:
    st.session_state["testbed_state"] = TestbedState()

if "k8s_bundle" not in st.session_state:
    st.session_state["k8s_bundle"] = None

if "cni_bundle" not in st.session_state:
    st.session_state["cni_bundle"] = None

if "teardown_bundle" not in st.session_state:
    st.session_state["teardown_bundle"] = None

if "prereq_bundles" not in st.session_state:
    st.session_state["prereq_bundles"] = {}

state: TestbedState = st.session_state["testbed_state"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_state():
    st.session_state["testbed_state"] = state


def _check_icon(passed: bool) -> str:
    return "✅" if passed else "❌"


def _render_checks(checks, show_remediation: bool = True):
    for check in checks:
        icon = _check_icon(check.passed)
        st.markdown(f"{icon} **[{check.els_layer}] {check.name}** — {check.detail}")
        if not check.passed and show_remediation and check.remediation:
            st.caption(f"↳ {check.remediation}")


def _render_commands(commands: list, language: str = "bash"):
    code = "\n".join(cmd for cmd in commands if not cmd.startswith("#") or cmd.strip() == "")
    comments = [cmd for cmd in commands if cmd.startswith("#")]
    st.code("\n".join(commands), language=language)


def _phase_progress():
    try:
        idx = PHASE_ORDER.index(state.phase)
        total = len(PHASE_ORDER)
        st.progress(idx / (total - 1))
        st.caption(f"Phase {idx + 1} of {total}: {PHASE_LABELS.get(state.phase, state.phase)}")
    except ValueError:
        pass


def _cost_reminder():
    running = [n for n in state.nodes if n.state == "running"]
    if running:
        st.warning(
            f"⚠️ {len(running)} instance(s) currently running — remember to stop them "
            "when done to avoid unnecessary AWS charges. "
            "`aws ec2 stop-instances --instance-ids " +
            " ".join(n.instance_id for n in running if n.instance_id) + "`"
        )


# ---------------------------------------------------------------------------
# Phase indicator + CNI selector
# ---------------------------------------------------------------------------

top_col1, top_col2 = st.columns([2, 1])

with top_col1:
    _phase_progress()

with top_col2:
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

st.divider()

# ---------------------------------------------------------------------------
# Phase 1 — AWS Environment Validation (L0)
# ---------------------------------------------------------------------------

with st.expander(
    f"{'✅' if state.aws_checks and all(c.passed for c in state.aws_checks) else '🔲'} "
    f"Phase 1 — {PHASE_LABELS[PHASE_AWS_VALIDATION]}",
    expanded=(state.phase == PHASE_AWS_VALIDATION),
):
    st.caption("Validate that your AWS environment is ready before touching Kubernetes.")

    if st.button("Run AWS validation", key="run_aws_validation"):
        with st.spinner("Querying AWS environment..."):
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

    if state.notes:
        for note in state.notes:
            st.info(note)

    aws_passed = bool(state.aws_checks) and all(c.passed for c in state.aws_checks)
    node_checks_passed = all(n.passed() for n in state.nodes) if state.nodes else False

    if aws_passed and node_checks_passed and state.phase == PHASE_AWS_VALIDATION:
        if st.button("✅ AWS validation passed — proceed to prerequisites", key="advance_to_prereqs"):
            state.advance_phase()
            _save_state()
            st.rerun()

# ---------------------------------------------------------------------------
# Phase 2 — Node Prerequisites (L1–L4.1)
# ---------------------------------------------------------------------------

with st.expander(
    f"{'✅' if state.phase not in [PHASE_AWS_VALIDATION] and all(st.session_state['prereq_bundles'].get(n.name, NodePrereqBundle(node_name=n.name, role=n.role, private_ip=n.private_ip)).all_passed() for n in state.nodes) and state.nodes else '🔲'} "
    f"Phase 2 — {PHASE_LABELS[PHASE_PREREQUISITES]}",
    expanded=(state.phase == PHASE_PREREQUISITES),
):
    st.caption("Check that each node has the required kernel settings, container runtime, and kubelet installed.")

    if not state.nodes:
        st.info("Complete AWS validation first to detect your nodes.")
    else:
        for node in state.nodes:
            bundle_key = node.name
            if bundle_key not in st.session_state["prereq_bundles"]:
                st.session_state["prereq_bundles"][bundle_key] = build_prereq_bundle(node)

            bundle: NodePrereqBundle = st.session_state["prereq_bundles"][bundle_key]

            with st.container(border=True):
                st.markdown(f"**{node.name}** ({node.role})")
                st.caption(f"SSH: `{build_ssh_instruction(node)}`")

                with st.expander("Commands to run on this node", expanded=False):
                    st.caption(
                        "**Step 1** — Copy all commands below and run them in your SSH session on this node. "
                        "Then paste the combined output into the box below and click Parse."
                    )
                    _render_commands(bundle.commands)
                    st.caption(
                        f"SSH: `{build_ssh_instruction(node)}`"
                    )

                with st.expander("ELS teaching notes", expanded=False):
                    for section in ["swap", "kernel modules", "sysctl", "containerd", "kubelet", "runc"]:
                        note = prereq_note(section)
                        if note:
                            st.markdown(f"**{section}**")
                            st.caption(note)

                paste_key = f"prereq_paste_{node.name}"
                pasted = st.text_area(
                    f"**Step 2** — Paste output from {node.name}",
                    key=paste_key,
                    height=150,
                    placeholder="Paste the combined output of all commands here...",
                )

                if st.button(f"Parse output — {node.name}", key=f"parse_prereq_{node.name}"):
                    bundle.paste_output = pasted
                    bundle = parse_prereq_output(bundle)
                    st.session_state["prereq_bundles"][bundle_key] = bundle
                    st.rerun()

                if bundle.parsed:
                    passed_checks = [c for c in bundle.checks if c.passed]
                    failed_checks = [c for c in bundle.checks if not c.passed]

                    if failed_checks:
                        st.markdown("**Step 3 — Fix these issues then re-run the check commands above**")
                        for check in failed_checks:
                            st.error(f"❌ [{check.els_layer}] {check.name}: {check.detail}")
                            if check.remediation:
                                st.code(check.remediation, language="bash")
                        if passed_checks:
                            st.markdown("**Already passing:**")
                            for check in passed_checks:
                                st.markdown(f"✅ [{check.els_layer}] {check.name}: {check.detail}")
                    else:
                        _render_checks(bundle.checks)

    all_prereqs_passed = (
        bool(state.nodes)
        and all(
            st.session_state["prereq_bundles"].get(
                n.name, NodePrereqBundle(node_name=n.name, role=n.role, private_ip=n.private_ip)
            ).all_passed()
            for n in state.nodes
        )
    )

    if all_prereqs_passed and state.phase == PHASE_PREREQUISITES:
        if st.button("✅ Prerequisites passed — proceed to Kubernetes install", key="advance_to_k8s"):
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

        # Step 1 — kubeadm init
        with st.container(border=True):
            st.markdown("**Step 1 — kubeadm init on control plane**")
            st.caption(k8s_note("kubeadm init"))
            st.code(k8s.init_command, language="bash")
            st.markdown("**Then configure kubectl:**")
            st.code("\n".join(k8s.kubeconfig_commands), language="bash")

            init_output = st.text_area(
                "Paste kubeadm init output",
                key="k8s_init_output",
                height=150,
                placeholder="Paste the full output of kubeadm init here...",
            )
            if st.button("Parse init output", key="parse_k8s_init"):
                k8s.init_output = init_output
                k8s = process_init_output(k8s, state, cp)
                st.session_state["k8s_bundle"] = k8s
                _save_state()
                st.rerun()

            if k8s.init_checks:
                _render_checks(k8s.init_checks)

        # Step 2 — kubeadm join
        if k8s.init_done and workers:
            with st.container(border=True):
                st.markdown(f"**Step 2 — kubeadm join on {workers[0].name}**")
                st.caption(k8s_note("kubeadm join"))
                if k8s.join_command:
                    st.code(k8s.join_command, language="bash")
                else:
                    st.info("Join command will appear here after init output is parsed.")

                join_done = st.checkbox("I have run the join command on the worker", key="join_done")
                if join_done:
                    k8s.join_done = True
                    st.session_state["k8s_bundle"] = k8s

        # Step 3 — validation
        if k8s.join_done:
            with st.container(border=True):
                st.markdown("**Step 3 — validate cluster state**")
                st.caption(k8s_note("node ready"))
                st.code(f"{build_node_ready_check()}\n{build_pods_check()}", language="bash")

                nodes_output = st.text_area(
                    "Paste kubectl get nodes output",
                    key="k8s_nodes_output",
                    height=100,
                )
                pods_output = st.text_area(
                    "Paste kubectl get pods -A output",
                    key="k8s_pods_output",
                    height=100,
                )
                if st.button("Parse validation output", key="parse_k8s_validation"):
                    k8s.nodes_output = nodes_output
                    k8s.pods_output = pods_output
                    k8s = process_validation_output(
                        k8s, [n.name for n in state.nodes]
                    )
                    st.session_state["k8s_bundle"] = k8s
                    st.rerun()

                if k8s.node_checks or k8s.pod_checks:
                    _render_checks(k8s.node_checks + k8s.pod_checks)
                    st.caption(k8s_note("system pods"))

        k8s_ready = k8s.join_done and bool(k8s.pod_checks) and all(
            c.passed for c in k8s.pod_checks
        )
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
        st.caption(cni_note(state.selected_cni))
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

    if state.selected_cni == CNI_BRIDGE:
        st.info(
            "Bridge path — nodes are expected to be NotReady. "
            "This is the teaching moment: without a CNI, cross-node pod communication fails."
        )

    if cni.all_passed() and state.phase == PHASE_CNI_INSTALL:
        if st.button("✅ CNI installed — cluster is ready", key="advance_to_complete"):
            state.advance_phase()
            _save_state()
            st.rerun()

# ---------------------------------------------------------------------------
# Phase 5 — Complete
# ---------------------------------------------------------------------------

if state.phase == PHASE_COMPLETE:
    st.success(
        f"🎉 Cluster is ready. "
        f"Kubernetes is running with {CNI_DESCRIPTIONS[state.selected_cni]}."
    )
    _cost_reminder()
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

            # Worker teardown
            if workers:
                with st.container(border=True):
                    st.markdown(f"**Step 1 — Reset worker: {workers[0].name}**")
                    st.caption(teardown_note("why worker first"))
                    _render_commands(td.worker_commands)

                    worker_reset = st.text_area(
                        f"Paste kubeadm reset output from {workers[0].name}",
                        key="worker_reset_output",
                        height=100,
                    )
                    worker_verify = st.text_area(
                        f"Paste verify output from {workers[0].name}",
                        key="worker_verify_output",
                        height=100,
                        help="Run the verify commands above on the worker node",
                    )
                    st.code("\n".join(td.verify_commands), language="bash")

                    if st.button(f"Parse worker teardown output", key="parse_worker_teardown"):
                        td.worker_reset_output = worker_reset
                        td.worker_verify_output = worker_verify
                        td = process_worker_teardown(td, workers[0])
                        st.session_state["teardown_bundle"] = td
                        st.rerun()

                    if td.worker_reset_checks or td.worker_verify_checks:
                        _render_checks(td.worker_reset_checks + td.worker_verify_checks)
                        st.caption(teardown_note("cni residuals"))

            # Control plane teardown
            if cp and td.worker_done:
                with st.container(border=True):
                    st.markdown(f"**Step 2 — Reset control plane: {cp.name}**")
                    _render_commands(td.cp_commands)

                    cp_reset = st.text_area(
                        f"Paste kubeadm reset output from {cp.name}",
                        key="cp_reset_output",
                        height=100,
                    )
                    cp_verify = st.text_area(
                        f"Paste verify output from {cp.name}",
                        key="cp_verify_output",
                        height=100,
                    )

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
                    st.session_state["prereq_bundles"] = {}
                    st.rerun()
