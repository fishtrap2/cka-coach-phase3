# AWS Lab Environment Rules

cka-coach supports two modes for the AWS lab environment lesson:
- **Existing environment** — detect and validate what is already running
- **New environment** — guided provisioning walkthrough for students starting from scratch

Both modes must result in the same validated baseline before Kubernetes installation begins.

---

## Reference environment (cka-coach maintainer)

This is the known-good reference environment cka-coach was developed against:

- Region: `ca-central-1`
- VPC: `vpc-0bcb93bd854282981` — default VPC, `172.31.0.0/16`
- Instances:
  - `cka-coach-cp` — `t3.large`, `172.31.2.240` (control plane)
  - `cka-coach-worker` — `t3.large`, `172.31.15.36` (worker)
- Both instances in the same VPC, reachable on private IPs

---

## AWS prerequisites for new students

### IAM setup
- Do not use root credentials for lab work
- Create a dedicated IAM user (e.g. `cka-coach-admin`) with `AdministratorAccess`
- Store credentials securely (macOS Keychain, 1Password, or similar)
- Configure AWS CLI: `aws configure`
- Validate with: `aws sts get-caller-identity`

### EC2 instance requirements
- OS: Ubuntu 22.04 LTS (recommended) or similar Debian-based Linux
- Instance type: `t3.medium` minimum, `t3.large` recommended
- Count: 2 instances — one control plane, one worker
- Storage: 20GB root volume minimum
- Tag instances clearly: `Name: cka-coach-cp` and `Name: cka-coach-worker`

### VPC / networking
- Use the default VPC unless the student has a reason not to
- Both instances must be in the same VPC
- Both instances should be in the same subnet for simplicity
- Assign public IPs for SSH access from the student's machine
- Private IPs must be reachable between instances (same VPC = default yes)

### Security group requirements
The security group must allow the following between the two instances:

| Port / Protocol | Direction | Purpose |
|---|---|---|
| 22 TCP | inbound from student IP | SSH access |
| 6443 TCP | between nodes | Kubernetes API server |
| 2379-2380 TCP | between nodes | etcd |
| 10250 TCP | between nodes | kubelet |
| 10251-10252 TCP | between nodes | kube-scheduler, kube-controller-manager |
| 179 TCP | between nodes | Calico BGP (if used) |
| 4789 UDP | between nodes | VXLAN overlay (Calico / Cilium) |
| 8472 UDP | between nodes | Flannel VXLAN (if used) |
| ICMP | between nodes | ping / connectivity validation |
| All traffic | within security group | simplest lab rule — allow all between nodes |

For a lab environment, the simplest approach is to allow all traffic between instances in the same security group and restrict SSH to the student's IP only.

---

## Validation steps before Kubernetes installation

cka-coach must validate the following before proceeding to Kubernetes installation:

1. Both instances are running (`aws ec2 describe-instances`)
2. Both instances have private IPs in the same VPC
3. SSH access works to both instances
4. Instances can ping each other on private IPs
5. Required ports are open in the security group
6. OS is a supported Linux distribution
7. Instance type meets minimum requirements

Validation must be explicit — show the student what was checked and what passed or failed.

---

## Two-mode lesson flow

### Mode 1 — Existing environment
1. Run `aws ec2 describe-instances` to detect running instances
2. Identify control plane and worker by Name tag or prompt student to confirm
3. Run validation checklist above
4. Report pass/fail per check with remediation hints for failures
5. Proceed to Kubernetes installation lesson when all checks pass

### Mode 2 — New environment (guided provisioning)
1. Explain what will be created and why (ELS L0 teaching moment)
2. Check AWS CLI credentials and region
3. Identify or create a suitable VPC and subnet
4. Create security group with required rules
5. Launch control plane instance with correct sizing and tags
6. Launch worker instance with correct sizing and tags
7. Wait for both instances to reach running state
8. Run validation checklist above
9. Proceed to Kubernetes installation lesson when all checks pass

---

## Cost awareness

Students must be made aware of running costs:

- `t3.large` costs approximately $0.08/hour per instance
- Two instances running 8 hours = ~$1.30
- Always stop instances when not in use (`aws ec2 stop-instances`)
- Stopped instances do not incur compute charges but do incur EBS storage charges
- Terminate instances when the lab is fully complete to avoid all ongoing charges
- Elastic IPs incur charges when not associated with a running instance — release them after use

cka-coach should surface a cost reminder at the start and end of every lab session.

## L0 Cost Visibility (future feature)

The ELS L0 panel should show a live running cost estimate for the student's lab environment:

- Instances currently running and elapsed uptime this session
- Estimated cost so far (instance type × uptime × hourly rate)
- Projected cost if left running for 8 hours
- A clear reminder to stop instances when done

This makes L0 tangible — students see that a running cluster has a real cost attached, not just an abstract infrastructure layer.

Implementation options:
- Query AWS Cost Explorer (`aws ce get-cost-and-usage`) for actual spend
- Or calculate locally from instance type + uptime from `aws ec2 describe-instances` (simpler, no Cost Explorer permissions needed)

The cost panel should be non-intrusive — a small always-visible strip at the top of the L0 section, not a modal or warning.

---

## ELS mapping

The AWS lab environment maps to:

- **L0** — Virtual Hardware / Cloud Infrastructure (EC2, VPC, security groups)

All lab environment setup is L0 work. The student must understand that everything above L0 (kernel, runtime, Kubernetes) runs on top of this foundation.
