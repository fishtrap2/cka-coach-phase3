# Q Developer Chat — 2026-05-10 — Testbed Completion, KIND, L0 Cost, Observer

## Compact Summary

**Project:** `cka-coach-phase3`
**Branch:** `feature/testbed-setup` (not yet merged — PR pending)
**Repo:** `/Users/michaelweir/cka-coach-phase3`

---

## What was done this session

### AWS IAM role setup
- Created `cka-coach-node-role` IAM role with EC2 trust policy
- Attached `AmazonEC2ReadOnlyAccess` and `AmazonSSMReadOnlyAccess`
- Created instance profile and attached to both EC2 instances
- AWS CLI v2 installed on control plane via direct download (apt package missing)
- `aws sts get-caller-identity` confirmed working from inside VM with no credentials file

### L0 orientation scripts
- `scripts/testbed/common/01-linux-networking.sh` — hostname, uname, ip addr, ip route, resolvectl, ss
- `scripts/testbed/providers/aws/01-aws-metadata.sh` — IMDSv2 with AWS console cross-references per field
- `scripts/testbed/providers/aws/02-aws-identity.sh` — ARN explanation, enriched SG table, K8s port readiness check, cost estimate
- `docs/testbed/l0-orientation.md` — narrative orientation guide

### Cost visibility
- `collect_cost_summary()` added to `phase_evidence.py`
- `launch_time` field added to `NodeState`
- L0 cost strip added to testbed page (`_render_cost_strip()`)
- L0 cost and all-nodes view added to ELS table L0 row in dashboard
- `observer_platform.py` created — detects AWS/GCP/KIND, collects instance metadata

### KIND platform support
- `kind_validator.py` created — `kind get clusters`, `kubectl get nodes`
- `PLATFORM_AWS`, `PLATFORM_KIND` added to `testbed_state.py`
- Platform selector added to testbed page
- KIND warning shown with explicit ELS layer visibility statement
- Phase 2 skipped for KIND with explanation

### Observer banner improvements
- `get_browser_client_ip()` added to `observer_context.py`
- Three-machine architecture message shown when running on EC2 node
- Browser IP shown if reverse proxy sets X-Forwarded-For, otherwise explains why not available

### Bug fixes
- `_render_cost_strip` called before definition — fixed
- Standalone L0 panel removed from dashboard — data moved into ELS table L0 row
- `List`/`Dict` missing from `observer_platform.py` typing imports — fixed
- OpenAI client lazy-initialised — dashboard loads without API key
- Explain button gated behind `llm_available()` check
- Phase 5 command syntax fixed: `--server.address=0.0.0.0 -- --allow-host-evidence`
- Hairpin NAT fix — use `localhost:8501` when check runs on control plane
- `check_cka_coach_phase` always re-queries AWS for fresh public IP

### Product decisions and docs
- `docs/aidlc/product-decision-testbed-platform-strategy.md` — KIND limitations, four curriculum stages, multi-testbed vision
- Voice and tone rules added: `06-voice-and-tone-rules.md`

### Learning moments added
- `imdsv2-and-iam-identity.md` — metadata service vs IAM, no credentials needed for IMDS
- `ec2-iam-roles-and-instance-profiles.md` — role, instance profile, temporary credentials, IAM prefix legend
- `aws-hairpin-nat.md` — why VMs can't reach themselves via public IP
- `stream-editing-and-syntax-checking.md` — ast.parse, bash -n, grep -n, sed -n, pre-commit hooks

### Key commits
- `028abcc` — L0 cost strip in testbed
- `726556b` — L0 infrastructure panel in dashboard (later moved to ELS table)
- `0b4a30f` — product decision doc: testbed platform strategy
- `bf9f819` — KIND platform support
- `d6689e8` — fix List/Dict imports
- `8208abd` — lazy OpenAI client, llm_available()
- `f6521b8` — cost strip call order fix, L0 into ELS table
- `72c82b5` — hairpin NAT fix, Phase 5 syntax fix
- `ce0d7c0` — stream editing learning moment

---

## Current AI-DLC status

- Inception: ✅ approved
- Construction: ✅ complete (significant post-inception extensions)
- Operations: 🔲 in progress — PR not yet raised

## What remains before PR

- [ ] Final end-to-end test of Phase 5 (cka-coach reachability check)
- [ ] Update README with testbed and KIND features
- [ ] Raise PR from `feature/testbed-setup` → `main`

## AWS environment state

- Both instances running: `cka-coach-cp` (3.96.170.24) and `cka-coach-worker`
- IAM role `cka-coach-node-role` attached to both instances
- Kubernetes installed with Calico CNI — both nodes Ready
- cka-coach running on control plane at `http://3.96.170.24:8501`
- Port 8501 open for Mac IP `104.158.112.124`

## Next session

1. Final Phase 5 verification
2. Update README
3. Raise PR
4. Begin planning Phase 4 (multi-testbed hub, curriculum stages)
