# Q Developer Chat — 2026-05-03 — Testbed Testing, Scripts, and L0 Orientation

## Compact Summary

**Project:** `cka-coach-phase3` — Kubernetes learning system, ELS model, Streamlit UI
**Repo:** `/Users/michaelweir/cka-coach-phase3`
**Branch:** `feature/testbed-setup` (not yet merged)

### What was done this session

#### Live testbed testing against real AWS environment
- Ran full testbed workflow against `cka-coach-cp` and `cka-coach-worker` (both t3.large, ca-central-1)
- Fixed fabricated ELS data when no cluster present (kubectl error output filter)
- Fixed misleading kubectl client-only version shown without cluster
- Redesigned Phase 2 as individual guided steps with beginner-friendly tone
- Deferred kubelet install to Phase 3 (not needed until kubeadm init)
- Added containerd CRI plugin check step (real failure hit during testing)
- Fixed node name mismatch between AWS tags and VM hostnames
- Removed step locking — students can move freely between steps
- Added Mark all complete / Undo buttons per step
- Replaced button-click progress bar with evidence-based phase status strip
- Added Phase 5 — deploy cka-coach to cluster (L8 capstone)
- Added `phase_evidence.py` module for observable phase inference
- Added observer context banner to both dashboard and testbed pages
- Opened port 8501 on security group for student Mac IP

#### Bugs fixed during testing
- `agent.py` — load .env before OpenAI client initialisation
- `state_collector.py` — filter kubectl connection errors from output
- `state_collector.py` — suppress client-only kubectl version without cluster
- `cni_installer.py` — node name mismatch (AWS tag vs VM hostname)
- `k8s_installer.py` — same node name mismatch fix
- `prereq_checker.py` — syntax error from failed edit; full rewrite
- `4_Testbed.py` — stale session state when new steps added

#### L0 orientation scripts built
- `scripts/testbed/common/01-linux-networking.sh` — hostname, uname, ip addr, ip route, resolvectl, ss
- `scripts/testbed/providers/aws/01-aws-metadata.sh` — IMDSv2 token-based metadata with AWS console cross-references
- `scripts/testbed/providers/aws/02-aws-identity.sh` — aws sts get-caller-identity + ec2 describe-instances
- `docs/testbed/l0-orientation.md` — narrative orientation guide

#### Learning moments added
- `python-venv-confusion.md`
- `kubectl-error-misread-as-resource-data.md`
- `containerd-cri-plugin-disabled.md`
- `imdsv2-and-iam-identity.md`

#### Rules and docs
- `.amazonq/rules/05-secrets-and-credentials-rules.md` added
- `docs/aidlc/inception-testbed-setup.md` updated with post-inception changes table
- `docs/dev-log.md` updated

#### GitHub issues raised
- #5 — AWS IAM role for EC2
- #6 — Secrets management lesson
- #7 — cka-coach deployment progression as ELS capstone model
- #8 — Completed phases should show summary state when collapsed

### Key commits this session
- `664b2b8` — observer context banner
- `88d8b3e` — kubectl error filter
- `4e8b0be` — suppress client-only kubectl version
- `c57f3f7` — Phase 2 redesign + kubelet deferred
- `3875b29` — containerd CRI step added
- `76f2c0d` — node name mismatch fix
- `1c1447e` — step locking removed, mark-all-complete added
- `6eba5a2` — evidence-based phase strip + Phase 5
- `1495d33` — secrets rules + Phase 5 clone step
- `e820f5a` — L0 orientation scripts
- `2edb079` — AWS console cross-references in metadata script

### Current AI-DLC status
- Inception: ✅ approved
- Construction: ✅ complete (with significant post-inception extensions from live testing)
- Operations: 🔲 in progress

### What remains before PR
- [ ] Complete Phase 5 test — deploy cka-coach to control plane, verify ELS panel goes 🟢
- [ ] Test teardown end to end
- [ ] Update README with testbed feature
- [ ] Raise PR

### AWS environment state
- Both instances running: `cka-coach-cp` (35.183.70.236) and `cka-coach-worker` (3.96.157.117)
- Kubernetes installed with Calico CNI — both nodes Ready
- Port 8501 open for student Mac IP (104.158.112.124)
- No IAM role on instances yet (issue #5)
- cka-coach not yet deployed to cluster (Phase 5 pending)

### Next session
1. Deploy cka-coach to `cka-coach-cp` (Phase 5)
2. Verify ELS panel shows 🟢 from inside cluster
3. Test teardown
4. Raise PR
