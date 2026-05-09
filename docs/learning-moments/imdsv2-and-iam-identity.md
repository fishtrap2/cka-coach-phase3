# Learning Moment — IMDSv2, Instance Metadata, and IAM

## The question

After running `01-aws-metadata.sh` on the control plane, the output showed
instance-id, VPC CIDR, subnet, region, and more — all without any AWS credentials
configured on the VM.

The question: **how is it possible that the VM can query all of this without IAM credentials?**

---

## The answer — two completely separate things

The metadata service and IAM are separate concepts that are often confused.

### 1. The metadata service (169.254.169.254) — no IAM required

The metadata service is **not an AWS API call**. It is a local HTTP service
that runs on the hypervisor underneath every EC2 instance. It is only reachable
from inside the VM via a link-local address (`169.254.169.254`) — you cannot
reach it from the internet or from another VM.

It answers questions like:
- What is my instance-id?
- What is my private IP?
- What VPC am I in?
- What IAM role was I launched with?

**No IAM credentials are needed** because this is not going through the AWS API.
The hypervisor already knows all of this — it created the VM. The metadata service
just exposes it to the VM itself.

Think of it like asking the hotel reception what room you are in.
You do not need to prove your identity — you are already standing in the hotel.

```
Your VM
  │
  └── curl http://169.254.169.254/...
        │
        └── Hypervisor (AWS infrastructure)
              └── Returns: "you are i-03658657280f01308 in vpc-0bcb93bd854282981"
```

### 2. The AWS API (aws ec2 describe-instances etc.) — IAM required

The AWS CLI commands (`aws ec2 describe-instances`, `aws sts get-caller-identity`)
**do** go through the AWS API. They require IAM credentials — either:
- An access key + secret (configured via `aws configure`)
- An IAM role attached to the instance (picked up automatically)

This is why `02-aws-identity.sh` failed on the VM with `aws CLI not found` —
and even if the CLI were installed, it would need credentials to call the AWS API.

---

## What the output revealed

The script output showed:

```
IAM role (L0)
No IAM role attached to this instance.
See issue #5 — attaching an IAM role removes the need for credentials files.
```

This is the key gap. The VM has no IAM role attached, so:
- The metadata service works fine (no IAM needed)
- AWS CLI calls from inside the VM would fail without credentials

---

## The two-script design explained

This is why the scripts are split:

| Script | Where to run | Needs IAM? | What it uses |
|---|---|---|---|
| `01-aws-metadata.sh` | Inside the VM | No | Metadata service (hypervisor) |
| `02-aws-identity.sh` | From your Mac | Yes | AWS CLI + IAM credentials |

`02-aws-identity.sh` is designed to run from your Mac where `aws configure`
has already set up credentials for `cka-coach-admin`. It should not be run
from inside the VM unless an IAM role is attached.

---

## The IAM role solution (issue #5)

If you attach an IAM role to the EC2 instance, the metadata service exposes
temporary credentials for that role:

```bash
# With an IAM role attached, this works from inside the VM:
curl -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/iam/security-credentials/<role-name>
```

The AWS SDK and CLI automatically check this endpoint for credentials.
That means `aws ec2 describe-instances` would work from inside the VM
**without any credentials file** — the role provides them automatically.

This is the correct AWS answer for any workload running on EC2:
- No credentials files on the VM
- No environment variables with secrets
- The IAM role is the identity — scoped to exactly what the workload needs

---

## ELS mapping

| Concept | ELS layer | Notes |
|---|---|---|
| Metadata service (169.254.169.254) | L0 | Hypervisor-provided, no IAM needed |
| IAM role on instance | L0 | Cloud identity attached at launch |
| AWS CLI API calls | L0 | Requires IAM credentials |
| Temporary role credentials via IMDS | L0 | Provided by metadata service when role is attached |

---

## Key takeaway

The metadata service and IAM are not the same thing:

- **Metadata service** — the VM asking the hypervisor "who am I?" — no credentials needed
- **IAM** — the VM (or operator) asking AWS "what am I allowed to do?" — credentials required

A VM with no IAM role can still query its own metadata.
A VM with an IAM role can query the AWS API without any credentials file.
A VM with no IAM role and no credentials file cannot call the AWS API at all.

This distinction is fundamental to understanding how AWS security works at L0.
