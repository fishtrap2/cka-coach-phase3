# cka-coach Phase 3 — Repo Architecture Summary

This document gives a module-by-module architecture summary of the
`cka-coach-phase3` repository, plus a practical dependency map.

Phase 3 significantly expanded the codebase beyond the Phase 2 baseline.
The original scope was UI modernisation. The actual delivery was a testbed
workflow foundation, L0 infrastructure visibility, and observer context —
all of which Phase 4 and 5 depend on.

---

## High-Level Shape

The repository is now organised around two parallel pipelines:

### Pipeline 1 — ELS Dashboard (inherited from Phase 2)

1. `state_collector.py` gathers live cluster and host evidence
2. Deterministic Python logic classifies and normalises that evidence
3. `dashboard_presenters.py` reshapes evidence into UI-friendly models
4. `ui/dashboard.py` renders the Streamlit ELS console
5. `agent.py` uses structured state as the basis for LLM explanations

### Pipeline 2 — Testbed Workflow (new in Phase 3)

1. `testbed/testbed_state.py` defines structured state for the workflow
2. `testbed/aws_validator.py` or `testbed/kind_validator.py` validates L0
3. `testbed/prereq_checker.py` guides L1-L3 node prerequisites
4. `testbed/k8s_installer.py` generates kubeadm commands and parses output
5. `testbed/cni_installer.py` handles CNI installation per chosen path
6. `testbed/teardown.py` guides kubeadm reset and node cleanup
7. `testbed/phase_evidence.py` infers current phase from observable signals
8. `ui/pages/4_Testbed.py` renders the guided testbed Streamlit page

### Cross-cutting concerns (new in Phase 3)

- `observer_context.py` — detects where cka-coach is running
- `observer_platform.py` — detects cloud platform and collects L0 metadata

---

## Core Runtime Modules (ELS Dashboard)

### `src/state_collector.py`

The collection and evidence engine. The most important backend module.

- runs kubectl, systemctl, ip, iptables, crictl through safe wrappers
- builds the shared `state` object used by dashboard and agent
- owns CNI detection, cluster/node reconciliation, health flags, provenance
- Phase 3 changes: kubectl connection errors filtered before returning output;
  client-only kubectl version suppressed when no cluster is reachable

### `src/dashboard_presenters.py`

The dashboard presentation layer. Does not collect evidence — reshapes
the shared `state` into UI-ready models.

- networking panel summaries
- CNI summary text and component inventory
- network visual model construction and HTML rendering
- node/runtime per-layer evidence formatting including L0

### `ui/dashboard.py`

The main Streamlit application. Orchestrates the full ELS console page.

Phase 3 changes:
- Observer context banner (where cka-coach is running, browser client context)
- L0 row enriched with cloud platform metadata and cost estimate
- Graceful degradation when no OpenAI API key is set
- `llm_available()` gates the Explain button

### `src/agent.py`

The LLM-facing explanation layer.

Design principle: the model does not own cluster truth. Python computes
deterministic ELS/CNI state first; the LLM explains that structured result.

Phase 3 changes:
- Lazy OpenAI client initialisation — no crash on missing API key
- `llm_available()` function for UI gating

---

## Testbed Workflow Modules (new in Phase 3)

### `src/testbed/testbed_state.py`

The single source of truth for the testbed workflow.

Defines:
- `CheckResult` — atomic evidence unit (name, passed, detail, remediation, ELS layer)
- `NodeState` — per-VM state including instance metadata and launch time
- `TestbedState` — top-level state with phase, CNI selection, nodes, cost tracking
- Platform constants: `PLATFORM_AWS`, `PLATFORM_KIND`
- CNI constants: `CNI_CALICO`, `CNI_CILIUM`, `CNI_BRIDGE`
- Phase constants and labels

### `src/testbed/aws_validator.py`

AWS environment validation (L0). Supports two modes:
- Mode 1: detect and validate an existing environment
- Mode 2: guided provisioning for new students

Uses AWS CLI via subprocess. Checks credentials, instance state, VPC,
security groups, and K8s port readiness.

### `src/testbed/kind_validator.py`

KIND environment validation (L0 shortcut).

Checks: kind CLI, Docker, cluster existence, kubectl context, node readiness.
Surfaces the explicit ELS layer visibility warning — KIND hides L0, L1, L2, L3.

### `src/testbed/prereq_checker.py`

Node prerequisite checks (L1-L3). Option A implementation — generates
commands for the student to run and confirm. No SSH required.

Steps: swap, kernel modules, sysctl, containerd, containerd CRI plugin, runc.
Kubelet deferred to Phase 3 (k8s_installer) — not needed until kubeadm init.

### `src/testbed/k8s_installer.py`

Kubernetes installation guidance (L4.5, L5, L7).

- builds kubeadm init command with correct pod CIDR per CNI
- parses kubeadm init output to extract join command
- parses kubectl get nodes and kubectl get pods -A for validation
- includes kubelet/kubeadm/kubectl apt repo setup as Step 1

### `src/testbed/cni_installer.py`

CNI installation guidance (L4.3). Three paths:
- Calico (default) — Tigera Operator, operator-managed
- Cilium — eBPF dataplane
- Bridge (no CNI) — teaching moment: shows what breaks without CNI

Parsers handle AWS tag vs VM hostname mismatch in node readiness checks.

### `src/testbed/teardown.py`

Kubernetes teardown and node cleanup guidance.

- worker reset before control plane (correct order)
- kubeadm reset + CNI config removal + iptables flush + K8s directory removal
- verify-clean commands per node
- confirmation gate before any destructive commands shown

### `src/testbed/phase_evidence.py`

Evidence-based phase inference. Queries observable signals rather than
relying on button clicks to track progress.

- `check_aws_phase()` — instances running
- `check_prereqs_phase()` — student-confirmed steps
- `check_k8s_phase()` — kubectl get nodes returns nodes
- `check_cni_phase()` — all nodes Ready
- `check_cka_coach_phase()` — HTTP check to port 8501 (uses localhost on VM to avoid hairpin NAT)
- `collect_cost_summary()` — per-instance uptime and estimated cost from known On Demand rates

---

## Observer Modules (new in Phase 3)

### `src/observer_context.py`

Detects where cka-coach is running and what it can see from there.

Modes: mac_no_cluster, mac_with_cluster, node_no_cluster, node_with_cluster,
node_in_cluster.

Surfaces in the observer banner on every page. Also exposes
`get_browser_client_ip()` for the three-machine architecture teaching moment.

### `src/observer_platform.py`

Detects the cloud platform and collects L0 instance metadata.

- AWS: IMDSv2 token + AWS API for all testbed nodes, cost calculation
- GCP: instance metadata service
- KIND: local Docker, no cloud metadata
- Unknown: no metadata service reachable

Feeds the L0 row in the ELS table with real instance-id, type, AMI, AZ,
region, and running cost for all testbed nodes.

---

## ELS / Schema Layer (unchanged from Phase 2)

### `src/els_model.py`
Loads the ELS schema and builds the in-memory layer registry.

### `src/els.py`
Small schema loader for the YAML ELS model.

### `src/els_mapper.py`
Maps normalised collected state into ELS layers.

### `src/schemas/els_schema.yaml`
Declarative definition of the ELS model — layers, descriptions, debug commands.

### `src/schemas.py`
TypedDict-style response contracts for coach responses and ELS results.

---

## UI Pages

### `ui/dashboard.py`
Main ELS console. Single-page Streamlit app.

### `ui/pages/4_Testbed.py`
Dedicated testbed workflow page. Five-phase guided setup with:
- Platform selector (AWS / KIND)
- Evidence-based phase status strip
- L0 cost strip
- Per-node guided prerequisite steps
- Phase 5: deploy cka-coach to cluster

---

## Support Modules (largely unchanged)

### `src/command_boundaries.py`
Normalises commands into Cluster vs Node boundaries.

### `src/config.py`
Environment-driven configuration — OpenAI model, context size limits.

### `src/lessons.py`
Lesson catalog and coaching workflow model. Currently collapsed in UI —
active coaching deferred while testbed foundation was built.

### `src/main.py`
CLI entrypoint using Typer — layers, scan, ask, dump-state commands.

### `src/tools.py`
Legacy lightweight shell helper. Still used for simple CLI scan paths.

---

## Tests (unchanged from Phase 2)

### `tests/test_cni_detection.py`
Main regression suite for CNI detection, reconciliation, health classification.

### `tests/test_lessons.py`
Lesson catalog behavior and progression.

Note: no automated tests were added for Phase 3 testbed modules.
Manual validation against the reference AWS environment was used instead.
See `docs/aidlc/inception-testbed-setup.md` for the test plan.

---

## Dependency Map

### ELS dashboard dependencies

```
ui/dashboard.py
  -> state_collector.collect_state
  -> dashboard_presenters.*
  -> agent.ask_llm, llm_available
  -> command_boundaries.*
  -> els_model.ELS_LAYERS
  -> lessons.*
  -> observer_context.collect_observer_context, get_browser_client_ip
  -> observer_platform.collect_l0_metadata

src/agent.py
  -> config
  -> schemas
  -> els
  -> els_model
  -> els_mapper
  -> command_boundaries
```

### Testbed workflow dependencies

```
ui/pages/4_Testbed.py
  -> testbed.testbed_state.*
  -> testbed.aws_validator.validate_aws_environment
  -> testbed.kind_validator.validate_kind_environment
  -> testbed.prereq_checker.*
  -> testbed.k8s_installer.*
  -> testbed.cni_installer.*
  -> testbed.teardown.*
  -> testbed.phase_evidence.collect_phase_evidence, collect_cost_summary
  -> observer_context.collect_observer_context, get_browser_client_ip

src/testbed/phase_evidence.py
  -> testbed.testbed_state
  -> (subprocess: kubectl, curl, aws CLI)

src/testbed/aws_validator.py
  -> testbed.testbed_state
  -> (subprocess: aws CLI)

src/testbed/kind_validator.py
  -> testbed.testbed_state
  -> (subprocess: kind, kubectl, docker)
```

### Observer dependencies

```
src/observer_platform.py
  -> testbed.phase_evidence.HOURLY_RATES
  -> (subprocess: curl IMDSv2, aws CLI, kubectl)

src/observer_context.py
  -> (stdlib: platform, socket, subprocess)
  -> (streamlit: st.context.headers for browser IP)
```

---

## Mental Model of the Codebase

### 1. Collection layer
- `state_collector.py` — live cluster/host evidence
- `testbed/aws_validator.py` — L0 AWS evidence
- `testbed/kind_validator.py` — L0 KIND evidence
- `observer_platform.py` — L0 cloud metadata

### 2. Domain / mapping layer
- `els.py`, `els_model.py`, `els_mapper.py` — ELS model
- `testbed/testbed_state.py` — testbed structured state
- `testbed/phase_evidence.py` — phase inference
- `observer_context.py` — observer mode detection
- `lessons.py` — lesson workflow model

### 3. Presentation layer
- `dashboard_presenters.py` — ELS dashboard models
- `ui/dashboard.py` — ELS console
- `ui/pages/4_Testbed.py` — testbed workflow

### 4. Explanation layer
- `agent.py` — LLM explanation, teaching voice

### 5. Guidance layer (new in Phase 3)
- `testbed/prereq_checker.py` — L1-L3 guided steps
- `testbed/k8s_installer.py` — kubeadm guidance
- `testbed/cni_installer.py` — CNI installation paths
- `testbed/teardown.py` — safe teardown guidance

---

## Architectural Centers of Gravity

The strongest current centers of gravity in Phase 3:

- `src/state_collector.py` — evidence engine
- `src/testbed/` — testbed workflow (new)
- `ui/pages/4_Testbed.py` — testbed UI (new)
- `src/observer_platform.py` — L0 visibility (new)
- `tests/test_cni_detection.py` — regression safety net

The main architectural tension is that the testbed workflow and the ELS
dashboard are two largely independent pipelines sharing only the Streamlit
session and some common utilities. Phase 4 will need to decide whether to
unify them under a common state model or keep them separate.

---

## One-Line Summary

cka-coach Phase 3 is a Kubernetes evidence engine plus a guided testbed
workflow, organised around the ELS model, with L0 cloud infrastructure
visibility and observer context as the new centre of gravity.
