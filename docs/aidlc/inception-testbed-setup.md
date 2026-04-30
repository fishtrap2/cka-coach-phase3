# Inception Brief — Guided Two-VM Kubernetes Testbed Setup and Teardown

---

## Problem Statement

A CKA/LFS258 student needs two Linux VMs with Kubernetes installed and a CNI configured before any meaningful cluster learning can happen. Currently there is no guided path in cka-coach to get from zero to a working two-node cluster. Students either follow generic tutorials that don't align with the ELS model, or get stuck on prerequisites before they've learned anything.

---

## Student Value

- Student starts cka-coach with two blank AWS VMs and ends with a working two-node Kubernetes cluster
- Every step is explained in ELS terms — the student knows *why* they are doing it, not just *what* to run
- Failures are caught early with clear remediation hints
- The student can tear down and rebuild the cluster cleanly, which is the correct mental model for CNI switching

---

## ELS Layers Affected

| Layer | What changes |
|---|---|
| L0 | AWS EC2 instances, VPC, security groups — validated before anything else |
| L1 | Kernel prerequisites (swap, modules, sysctl) set on both VMs |
| L2 | OCI runtime (runc) installed as part of containerd setup |
| L3 | containerd installed and configured on both VMs |
| L4.1 | kubelet installed and started on both VMs |
| L4.2 | kube-proxy deployed as part of kubeadm init |
| L4.3 | CNI installed (Calico default, Cilium or bridge as alternatives) |
| L4.5 | kubeadm init creates the API server and etcd on control plane |
| L5 | kube-controller-manager and kube-scheduler deployed as static pods |
| L7 | kubeconfig written, cluster objects created |
| L8 | System pods reach Running state as validation signal |

---

## UI Manifestation

The testbed workflow will be implemented as a **dedicated Streamlit page** (`ui/pages/4_Testbed.py`), not as part of the existing Lesson section.

### Rationale

- The existing lesson console in `dashboard.py` is marked "Under Construction" and partially collapsed — building on it now adds risk
- The testbed workflow has distinct UI needs: AWS validation panel, per-node status, cost strip, step-by-step guided flow with confirmation gates
- A self-contained page keeps the testbed workflow independent and reviewable on its own
- In a future session, we can decide whether to unify the testbed page with the lesson system or keep them separate

### Page structure

The testbed page will follow the UI and learning experience rules:

1. **Phase indicator** — where the student is in the overall workflow
2. **AWS environment panel** — instance status, VPC, connectivity validation (L0)
3. **Prerequisites panel** — per-node kernel, runtime, kubelet checks (L1–L4.1)
4. **Kubernetes status panel** — kubeadm init/join progress, node readiness (L4.5, L5)
5. **CNI status panel** — CNI selection, install progress, validation (L4.3)
6. **Next action** — single clear call to action at all times
7. **Evidence** — raw output behind expanders, not shown by default
8. **Cost strip** — running instance cost at L0 (future feature, placeholder now)

The existing Lesson section remains untouched by this work.

---

## Proposed Repo Structure

```
src/
  testbed/
    __init__.py
    aws_validator.py        # Mode 1 + Mode 2 AWS environment checks
    prereq_checker.py       # L0-L3 prerequisite validation per node
    k8s_installer.py        # kubeadm init / join logic and output parsing
    cni_installer.py        # CNI path selection and install (Calico / Cilium / bridge)
    teardown.py             # kubeadm reset + node cleanup
    testbed_state.py        # structured state for the testbed workflow

docs/aidlc/
  inception-testbed-setup.md   # this brief

ui/
  pages/
    4_Testbed.py            # new Streamlit page for the testbed workflow
```

No changes to existing `src/` files unless a shared utility is needed.

---

## Safety Risks

| Risk | Mitigation |
|---|---|
| kubeadm reset destroys a working cluster | Require explicit `--reset-kubernetes` confirmation before teardown |
| CNI removal leaves stale kernel state | Follow the rule: always reset K8s fully, never attempt in-place CNI removal |
| SSH commands run on wrong node | Always show the target node name before running any remote command |
| Student runs teardown on production | Scope teardown strictly to instances tagged `cka-coach-*` |
| AWS costs left running | Surface cost reminder at start and end of every testbed session |
| Destructive scripts auto-executed | Scripts are generated for review only — never auto-run without explicit student confirmation |

---

## Acceptance Criteria

**AWS environment validation**
- [ ] cka-coach detects both instances by Name tag (`cka-coach-cp`, `cka-coach-worker`)
- [ ] Validates both instances are running and in the same VPC
- [ ] Reports pass/fail per check with remediation hints

**Prerequisites**
- [ ] Checks swap is disabled on both nodes
- [ ] Checks required kernel modules are loaded (`overlay`, `br_netfilter`)
- [ ] Checks sysctl settings (`net.bridge.bridge-nf-call-iptables`, `net.ipv4.ip_forward`)
- [ ] Checks containerd is installed and running
- [ ] Checks kubelet is installed

**Kubernetes installation**
- [ ] kubeadm init runs on control plane with correct pod CIDR for chosen CNI
- [ ] kubeconfig is written and accessible
- [ ] kubeadm join command is generated and shown to student for worker node
- [ ] Both nodes reach Ready state before proceeding

**CNI installation**
- [ ] Student selects CNI path at start of lesson (Calico / Cilium / bridge)
- [ ] Calico path: tigera-operator, calico-node, calico-kube-controllers all reach Running
- [ ] Cilium path: cilium-operator and cilium DaemonSet reach Running
- [ ] Bridge path: cluster shows expected Pending/not-ready state with explanation
- [ ] cka-coach validates CNI state using existing `state_collector` + `dashboard_presenters` evidence

**Teardown**
- [ ] Student is warned clearly before any destructive step
- [ ] kubeadm reset runs on worker first, then control plane
- [ ] Node-level cleanup script generated (CNI config, interfaces, iptables)
- [ ] Student confirms each node is clean before proceeding

**ELS teaching**
- [ ] Every step identifies which ELS layer is being configured
- [ ] Each step includes a "why this matters" explanation
- [ ] Common failure modes are shown per step

---

## Test Plan

**Manual validation steps (no automated tests yet)**

1. Run the testbed workflow against the reference environment (`cka-coach-cp` + `cka-coach-worker`)
2. Verify each acceptance criterion above passes
3. Deliberately break a prerequisite (e.g. leave swap on) and confirm cka-coach catches it
4. Run the full teardown and confirm both nodes are clean
5. Reinstall with a different CNI and confirm the workflow completes cleanly

**Existing tests to rerun after changes**
- `tests/test_cni_detection.py`
- `tests/test_lessons.py`

---

## Docs Updates Required

- `README.md` — add testbed setup to the feature list
- `docs/dev-log.md` — add entry when construction begins
- `docs/aidlc/chats/` — save session log at end of construction
- `docs/learning-moments/` — add a learning moment for CNI-as-architectural-decision

---

## Human Approval Required Before Construction

Per `aidlc-workflow-rules.md`, the following need your sign-off before any code is written:

- [ ] Proposed repo structure (`src/testbed/`, `ui/pages/4_Testbed.py`)
- [ ] CNI path selection model (Calico default, Cilium + bridge as alternatives)
- [ ] Teardown safety gates (confirmation flags, scope to `cka-coach-*` tags)
- [ ] Whether SSH to the VMs is in scope for Phase 3 or out of scope

---

## Status

- [x] Inception approved
- [ ] Construction started
- [ ] Construction complete
- [ ] Operations sign-off
