# Build Log — feature/testbed-setup

## Overview

This document records how the guided two-VM Kubernetes testbed setup and teardown
feature was built in cka-coach-phase3.

It is intentionally transparent about the process, including the role of
Amazon Q Developer as a coding assistant throughout construction.

---

## How this was built

This feature was built collaboratively using **Amazon Q Developer** inside VS Code.

The workflow followed the AI-DLC model defined in `.amazonq/rules/aidlc-workflow-rules.md`:

1. **Inception** — problem statement, ELS layer mapping, repo structure, safety risks,
   acceptance criteria, and test plan were agreed before any code was written
2. **Construction** — each module was built one at a time, validated with a test script,
   committed, and pushed before moving to the next
3. **Operations** — this build log, GitHub issues for future work, and a PR for human review

Amazon Q was used to:
- Generate each module from the agreed inception brief
- Write validation test scripts per module
- Create GitHub issues for out-of-scope platform support
- Write this build log

All code was reviewed and approved by the maintainer before merging.
No code was auto-merged or auto-deployed.

---

## What was built

### Backend modules (`src/testbed/`)

| Module | ELS layers | Purpose |
|---|---|---|
| `testbed_state.py` | L0–L8 | Structured state — single source of truth for the UI |
| `aws_validator.py` | L0 | AWS environment detection and validation |
| `prereq_checker.py` | L1–L4.1 | Node prerequisite checks (kernel, containerd, kubelet) |
| `k8s_installer.py` | L4.5, L5, L7 | kubeadm init/join command generation and output parsing |
| `cni_installer.py` | L4.3 | CNI install commands and validation for Calico, Cilium, bridge |
| `teardown.py` | L4.3, L4.1, L1 | kubeadm reset and node cleanup verification |

### UI (`ui/pages/`)

| File | Purpose |
|---|---|
| `4_Testbed.py` | Dedicated Streamlit page — five-phase guided workflow |

---

## Construction order and commits

| Step | Commit | What was built |
|---|---|---|
| 1 | `602022e` | `testbed_state.py` — structured state |
| 2 | `f038aa5` | `aws_validator.py` — L0 AWS checks |
| 3 | `894a01e` | `prereq_checker.py` — L1–L4.1 node checks |
| 4 | `aeaca46` | `k8s_installer.py` — kubeadm init/join |
| 5 | `f9ab12b` | `cni_installer.py` — Calico, Cilium, bridge |
| 6 | `fcecf0f` | `teardown.py` — kubeadm reset and cleanup |
| 7 | `50cbd54` | `4_Testbed.py` — Streamlit UI page |

---

## Validation approach

Each module was validated with a standalone Python test script before committing.
Test scripts used simulated node output to exercise the parsers without requiring
live SSH access to the VMs.

The AWS validator was tested against the real AWS environment using the
`cka-coach-admin` IAM user configured during this session.

No automated test suite was added in this branch — manual validation steps
are documented in the inception brief at `docs/aidlc/inception-testbed-setup.md`.

---

## Design decisions made during construction

### Option A for SSH (prereq_checker, k8s_installer, teardown)
cka-coach generates commands for the student to run manually and paste back,
rather than SSHing into nodes directly. This follows the lab safety rules and
avoids SSH key management complexity in Phase 3.
Option B (automatic SSH) is tracked in issue #1.

### Dedicated Testbed page, not the existing Lesson section
The existing lesson console in `dashboard.py` is marked "Under Construction".
A dedicated `4_Testbed.py` page was built instead to avoid building on an
unstable foundation. Future unification is possible.

### Platform scope — AWS only for Phase 3
The testbed workflow is AWS-specific in `aws_validator.py` only.
All other modules are platform-agnostic.
GCP, KIND, and bare metal support are tracked in issues #2, #3, #4.

### CNI removal model
In-place CNI removal is not supported. The teardown workflow always does a full
`kubeadm reset` + node cleanup. This is the correct CKA mental model and is
enforced by the lab safety rules.

---

## Known gaps and future issues

| Issue | Title |
|---|---|
| #1 | feat: SSH-based automatic prereq checking (Option B) |
| #2 | feat: GCP environment validator |
| #3 | feat: KIND environment validator |
| #4 | feat: bare metal / manual IP validator |

---

## How to run

```bash
source venv/bin/activate
streamlit run ui/dashboard.py
```

Navigate to the Testbed page in the Streamlit sidebar.

To run AWS validation, ensure AWS CLI is configured:
```bash
aws sts get-caller-identity
```

---

## Safety notes

- No destructive commands are run automatically
- Teardown requires explicit checkbox confirmation before commands are shown
- All generated scripts are for student review only — never auto-executed
- AWS operations are scoped to instances tagged `cka-coach-cp` and `cka-coach-worker`
