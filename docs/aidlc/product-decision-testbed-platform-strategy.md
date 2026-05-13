# Product Decision — Testbed Platform Strategy and KIND Limitations

**Date:** 2026-05-10  
**Status:** Decided  
**Author:** cka-coach maintainer + Amazon Q Developer  

---

## Decision

KIND (Kubernetes in Docker) will be supported in cka-coach as a **Stage 1
shortcut only**, with an explicit and prominent explanation of what it hides
and why the student must eventually move to real infrastructure.

KIND will never be presented as equivalent to a real cloud testbed.

---

## Context

During Phase 3 development and live testbed testing, a fundamental pedagogical
question emerged:

> Should cka-coach support KIND as a primary learning environment?

The answer is no — and the reasoning is central to the ELS model itself.

---

## The ELS argument against KIND as a primary path

The ELS model exists to teach students that **everything lives somewhere real**.
KIND makes L0 invisible.

```
KIND cluster
    └── Docker container (pretending to be a node)
           └── Your Mac/Linux kernel (shared, not isolated)
                  └── No hypervisor boundary
                         └── No IAM
                                └── No VPC
                                       └── No security groups
                                              └── No real L0
```

A student running KIND can get `kubectl get nodes` to show Ready. But they
have learned nothing about:

- Why the node has the identity it has
- What controls what the node can do in the cloud
- How the network boundary is enforced at L0
- What happens when the node is compromised
- Why pod security matters when the underlying host is shared
- How IAM roles, VPC CIDRs, and security groups relate to Kubernetes

The LFS258 course makes the same mistake — students build a testbed and get
a working cluster, but learn nothing at the hypervisor and Linux kernel layers.
These are precisely the layers that drive understanding of the whole system.

**KIND does not fix this. It makes it worse by hiding L0 entirely.**

---

## What KIND is actually good for

KIND is appropriate for:

- Testing a Helm chart before deploying to real infrastructure
- CI/CD pipelines where a throwaway cluster is needed
- Rapid iteration on Kubernetes manifests
- Situations where L0 is genuinely irrelevant to the task at hand

It is not appropriate for learning how Kubernetes integrates with real
infrastructure, because that integration does not exist in KIND.

---

## The curriculum stage mapping

| Stage | Platform | What L0 teaches |
|---|---|---|
| 1 — Foundational | KIND acceptable as shortcut | K8s objects, controllers, CNI concepts |
| 2 — Transformational | AWS or GCP required | IAM, VPC, security groups, real L0 |
| 3 — Automation & Scaling | AWS or GCP required | Cloud APIs, cost, scaling, real infra |
| 4 — Human + AI | Any | AI-assisted operations, verification, trust |

Stage 1 students who use KIND must be explicitly told what they are missing
and why they will need to return to real infrastructure for Stage 2.

---

## The four curriculum stages

### Stage 1 — Foundational

The student learns the ELS model, Kubernetes fundamentals, and CNI concepts.
KIND is acceptable here because the focus is on L4.5 and above.

cka-coach runs from source, cloned onto the student's machine or a VM.

### Stage 2 — Transformational Kubernetes

The student builds a real cloud testbed (AWS or GCP), installs Kubernetes
from scratch, and understands how Kubernetes integrates with real infrastructure.

This is where L0 becomes non-negotiable. IAM roles, VPC topology, security
groups, and cloud cost are all first-class learning objectives.

cka-coach moves from the student's laptop into the cluster (Phase 5 of the
testbed workflow). The ELS panel goes from mostly 🟡 to mostly 🟢.

### Stage 3 — Automation and Scaling

The student learns platform engineering — data pipelines, messaging, ML
infrastructure, observability. cka-coach itself becomes a containerised
workload, then a Service, then a platform component.

### Stage 4 — Human + AI

The student learns AI-assisted operations. The question is not "how do I
type kubectl commands" but "how do I verify what the AI did, when do I
trust it, and when do I override it."

The honest answer to "will humans type kubectl manually in 5 years?" is
probably no. But they must understand what kubectl does — because the AI
assistant that does it for them will make mistakes, and the human needs to
know when to trust it and when to override it.

cka-coach at Stage 4 is itself an example of this model: the AI explains,
the human verifies, the evidence is always shown.

---

## The KIND warning text

When a student selects KIND in cka-coach, they must see:

> **KIND gives you a working Kubernetes cluster in minutes.**
>
> But it runs inside Docker on your local machine — there is no real L0.
> No hypervisor, no IAM, no VPC, no security groups. The node identity,
> network boundary, and security model that matter in production do not
> exist here.
>
> You can learn Kubernetes objects, controllers, and CNI concepts in KIND.
> You cannot learn how Kubernetes integrates with real infrastructure.
>
> For Stage 2 and beyond, you will need a real testbed on AWS or GCP.
> The testbed workflow in cka-coach will guide you through building one.
>
> **ELS layers visible in KIND:** L4.5, L5, L6, L7, L8, L9  
> **ELS layers hidden in KIND:** L0, L1 (partially), L2, L3 (partially)

---

## The multi-testbed vision (Phase 4)

The student may eventually run multiple environments simultaneously:

```
cka-coach Hub
    ├── Testbed A: AWS ca-central-1 | K8s v1.32 | Calico | Stage 2
    ├── Testbed B: KIND local       | K8s v1.30 | Cilium | Stage 1
    └── Testbed C: GCP us-central1  | not yet built
```

This requires:
- A concept of registered environments with persistent state
- A landing page that shows all active testbeds and their stage
- Per-testbed cka-coach instances that report back to the hub

This is Phase 4 scope. It should not be built until the Stage 1 and Stage 2
learning paths are solid.

---

## What this means for the current codebase

### Keep

- `aws_validator.py` — real L0 validation, first-class path
- `phase_evidence.py` — evidence-based phase checking
- All platform-agnostic modules (prereq, k8s, cni, teardown)
- The L0 cost strip and instance metadata in the ELS table

### Add (Phase 3 completion)

- KIND support as Stage 1 shortcut with the warning above
- Platform selector in the Testbed page (AWS / KIND / GCP coming soon)
- `kind_validator.py` — minimal, just `kind get clusters` + `kubectl get nodes`
- Explicit labelling of which ELS layers are visible per platform

### Defer to Phase 4

- Multi-testbed hub / landing page
- GCP full support
- Persistent environment registry
- Cross-testbed state tracking

---

## Related issues

- #2 — GCP environment validator
- #3 — KIND environment validator
- #7 — cka-coach deployment progression as ELS capstone model
- #8 — Completed phases should show summary state when collapsed
