# cka-coach — Phase 3

> "What is actually happening inside your Kubernetes cluster?"

> _Built with Amazon Q Developer using the AI-Driven Development Life Cycle (AI-DLC)_

---

## ⚠️ Use at your own risk

**cka-coach-phase3 is a development release.**

This repo was used as a live testbed for applying AI-DLC methodology and
Amazon Q Developer to continue the cka-coach project. It is not a polished
product release. Features are functional but rough in places, the UI has not
been fully modernised, and some workflows are still being refined.

**What this means for you:**

- The testbed setup workflow (AWS, KIND) works but is opinionated and AWS-specific
- The ELS dashboard is functional but the UI modernisation planned for Phase 3 was
  partially deferred in favour of building the testbed foundation
- The Explain feature requires an OpenAI API key — the dashboard works without one
- Running from source on a VM or locally is the supported path

**Upcoming releases will address this:**

- **Phase 4** — multi-testbed support (AWS, GCP, KIND, bare metal), a proper
  landing page coordinating multiple active testbeds, and a stable student
  learning journey across environments
- **Phase 5** — deep networking visibility: underlay/overlay protocol stack,
  bits-on-the-wire view, node networking, pod networking, service networking,
  and load balancing — showing what each point in the network is doing from
  both a protocol stack and NAT/SNAT perspective, built on the Phase 4 testbeds

---

## What Phase 3 actually delivered

Phase 3 started as a UI modernisation milestone. During development against
a real AWS testbed, the scope evolved to include foundational infrastructure
that Phase 4 and 5 depend on.

### Guided testbed setup (NEW)

A five-phase guided workflow for building a two-VM Kubernetes testbed:

- **Phase 1** — AWS environment validation (EC2, VPC, security groups, IAM)
- **Phase 2** — Node prerequisites (kernel modules, sysctl, containerd, runc)
- **Phase 3** — Kubernetes installation (kubeadm init/join, kubelet, kubeconfig)
- **Phase 4** — CNI installation (Calico default, Cilium, or bridge/no-CNI)
- **Phase 5** — Deploy cka-coach onto the control plane node

Supports **AWS** (full) and **KIND** (Stage 1 shortcut with explicit ELS layer warnings).

### L0 infrastructure visibility (NEW)

- Cloud platform detection (AWS EC2, GCP, KIND, unknown)
- Instance metadata in the ELS table L0 row (instance-id, type, AMI, AZ, region)
- All testbed nodes shown with per-instance uptime and running cost estimate
- Projected 8-hour cost and stop-instances reminder
- Observer context banner — shows where cka-coach is running and where the
  browser is connecting from

### L0 orientation scripts (NEW)

Shell scripts for hands-on L0 evidence collection:

```
scripts/testbed/common/
  01-linux-networking.sh     # hostname, ip addr, ip route, resolvectl, ss

scripts/testbed/providers/aws/
  01-aws-metadata.sh         # IMDSv2 instance metadata with AWS console cross-references
  02-aws-identity.sh         # IAM identity, instance table, SG rules, K8s port check, cost
```

### Evidence-based phase tracking (NEW)

The testbed page detects what has actually been built rather than relying
on button clicks — querying AWS, kubectl, and HTTP to infer current phase.

### Dashboard improvements

- Observer context banner on every page
- Graceful degradation when no OpenAI API key is set
- kubectl connection errors no longer produce fabricated ELS data
- L0 row in ELS table shows real cloud infrastructure evidence

### Learning moments (NEW)

Documented real failures and concepts encountered during live testbed testing:

- Python venv confusion and the ELS parallel
- kubectl error output misread as resource data
- containerd CRI plugin disabled
- IMDSv2 vs IAM — why the metadata service needs no credentials
- EC2 IAM roles, instance profiles, and temporary credentials
- AWS hairpin NAT — why VMs can't reach themselves via public IP
- Stream editing and syntax checking before commits
- Recover from dirty kubeadm init/join state
- Localhost is relative — accessing Calico Whisker from a Mac with SSH and kubectl port-forward

---

## Phase 2 — Networking Visibility Milestone (v0.6.0)

Phase 2 introduced a **complete networking understanding layer** grounded in
real cluster evidence.

- CNI detection (Calico, Cilium) with confidence-based interpretation
- Network Visual Panel — pod → veth → host → overlay → remote node
- CNI state provenance — distinguishes active CNI, residual artifacts, unknown states
- Known-good baseline + cleanup lesson

---

## The ELS Model (Everything Lives Somewhere)

cka-coach is built around the ELS model:

Applications
↓
Pods
↓
Kubernetes Objects (desired state)
↓
Controllers / Operators
↓
Node Agents (kubelet, kube-proxy, CNI)
↓
Container Runtime (containerd)
↓
OCI Runtime (runc)
↓
Linux Kernel (namespaces, cgroups)
↓
Infrastructure (EC2, VPC, IAM)

Every explanation maps back to **where something actually lives**.

---

## Who this is for

- CKA / LFS258 students
- Engineers learning Kubernetes networking
- Anyone asking:
  - "why is this not working?"
  - "where is this actually happening?"

---

## Product Philosophy

cka-coach is not a dashboard.

It is a **teaching system** that:

1. Shows current state
2. Explains why
3. Provides evidence
4. Highlights uncertainty
5. Guides the student forward

The coach speaks as a gracious, benevolent expert who never assumes the
student shares accumulated experience — and never leaves an easily
misunderstood item unexplained.

---

## How to run

### From source (local Mac or Linux)

```bash
git clone https://github.com/fishtrap2/cka-coach-phase3.git
cd cka-coach-phase3
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=your_key_here   # optional — dashboard works without it
streamlit run ui/dashboard.py
```

### From source on an EC2 node (recommended for full ELS visibility)

```bash
git clone https://github.com/fishtrap2/cka-coach-phase3.git
cd cka-coach-phase3
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=your_key_here
streamlit run ui/dashboard.py --server.address=0.0.0.0 -- --allow-host-evidence
```

Then open `http://<node-public-ip>:8501` in your browser.

Running on the node gives cka-coach direct access to host-level evidence —
kubelet, containerd, kernel, CNI config — so the ELS panel shows real
observed state instead of visibility-limited.

### Testbed setup

Use the Testbed page in the sidebar to guide you through building a
two-VM Kubernetes cluster on AWS or a local KIND cluster.

---

## Roadmap

### Phase 4 (upcoming)
- Multi-testbed hub — track AWS, GCP, KIND, and bare metal environments simultaneously
- Landing page showing all active testbeds, K8s version, CNI, and student stage
- Stable learning journey across environments
- GCP testbed support
- Persistent environment registry

### Phase 5 (planned)
- Deep networking visibility built on Phase 4 testbeds
- Underlay/overlay protocol stack — bits on the wire
- Node networking, pod networking, service networking, load balancing
- What each network point is doing from a protocol stack and NAT/SNAT perspective
- Inter/intra pod, node, and cluster networking scenarios from basic to advanced

---

## Status

- Phase 1: completed (public repo)
- Phase 2: networking foundation complete
- Phase 3: testbed foundation + L0 visibility complete — use at own risk
- Phase 4: multi-testbed hub — upcoming
- Phase 5: deep networking visibility — planned

---

## Related

Phase 1 repo: [https://github.com/fishtrap2/cka-coach](https://github.com/fishtrap2/cka-coach)
