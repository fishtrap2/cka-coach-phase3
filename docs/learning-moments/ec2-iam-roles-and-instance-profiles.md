# Learning Moment — EC2 IAM Roles, Instance Profiles, and Temporary Credentials

## The question

How can a VM call the AWS API without any credentials file or `aws configure`?

---

## The answer — IAM roles for EC2

When you attach an IAM role to an EC2 instance, AWS automatically vends
temporary credentials to that VM via the metadata service. The AWS CLI and
SDK check the metadata service automatically — no credentials file needed,
no environment variables, nothing to leak.

This is the correct AWS answer for any workload running on EC2.

---

## The three objects involved

This confuses many students because there are three separate AWS objects:

### 1. The IAM Role

The role defines:
- **What it can do** — the permissions policies attached to it
- **Who can assume it** — the trust policy

The trust policy for an EC2 role says:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

This says: "EC2 instances are allowed to assume this role."

Note on `"Version": "2012-10-17"`:
This is not a date that ages. It is a fixed identifier for the IAM policy
language grammar version. There are only two versions that have ever existed:
- `2012-10-17` — current, supports policy variables — always use this
- `2008-10-17` — original, does not support policy variables

AWS has never released a newer version. Always use `2012-10-17`.

### 2. The Instance Profile

The instance profile is a container that holds the role and is what actually
gets attached to the EC2 instance. It is a separate object from the role.

In the AWS Console, when you create a role for EC2, the console creates the
instance profile automatically with the same name. Via the CLI, you create
them separately:

```bash
aws iam create-instance-profile --instance-profile-name cka-coach-node-role
aws iam add-role-to-instance-profile \
  --instance-profile-name cka-coach-node-role \
  --role-name cka-coach-node-role
```

In the AWS Console: IAM → Roles → your role → Instance profiles tab.

### 3. The Association

The instance profile is attached to the EC2 instance:

```bash
aws ec2 associate-iam-instance-profile \
  --instance-id i-03658657280f01308 \
  --iam-instance-profile Name=cka-coach-node-role
```

In the AWS Console: EC2 → Instances → select instance → Actions → Security →
Modify IAM role.

---

## How the VM gets credentials

Once the role is attached, the metadata service vends temporary credentials
automatically. From inside the VM:

```bash
# Get IMDSv2 token first
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

# See which role is attached
curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/iam/security-credentials/
# Output: cka-coach-node-role

# Get the actual temporary credentials
curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/iam/security-credentials/cka-coach-node-role
```

The output looks like:
```json
{
  "Code": "Success",
  "Type": "AWS-HMAC",
  "AccessKeyId": "ASIA...",
  "SecretAccessKey": "...",
  "Token": "...",
  "Expiration": "2026-05-10T22:00:00Z"
}
```

**What to notice:**

- `AccessKeyId` starts with `ASIA` — not `AKIA`
  - `AKIA` = long-lived access key from an IAM user (what `aws configure` uses)
  - `ASIA` = temporary credentials from an assumed role
  - This distinction matters — if you ever see `AKIA` in a metadata response,
    something is wrong

- There is a `Token` field — temporary credentials always include a session token.
  Long-lived access keys do not have a token field.

- There is an `Expiration` — these credentials rotate automatically, typically
  every hour. The AWS SDK refreshes them before they expire. You never need to
  rotate them manually.

- You never see these in a file — `cat ~/.aws/credentials` on the VM will show
  nothing. The AWS CLI finds them via the metadata service automatically.

---

## The IAM prefix legend

AWS uses prefixes in IDs to tell you what type of object you are looking at:

| Prefix | Object type |
|---|---|
| `AKIA` | Long-lived access key (IAM user) |
| `ASIA` | Temporary credentials (assumed role) |
| `AROA` | IAM Role ID |
| `AIPA` | Instance Profile ID |
| `AIDА` | IAM User ID |
| `AGPA` | IAM Group ID |

In the AWS Console these IDs appear in the Summary section of each object.
They are also visible in CloudTrail logs — useful for auditing who did what.

---

## What `aws sts get-caller-identity` shows from inside the VM

After attaching the role, from inside the VM with no credentials file:

```bash
aws sts get-caller-identity
```

Output:
```json
{
  "UserId": "AROATBHHBNQRKNYVLYLT4:i-03658657280f01308",
  "Account": "208790449186",
  "Arn": "arn:aws:sts::208790449186:assumed-role/cka-coach-node-role/i-03658657280f01308"
}
```

**What to notice:**

- `Arn` says `assumed-role` not `user` — the VM is acting as the role
- The session name after the last `/` is the instance ID — AWS uses this to
  track which specific VM assumed the role. In CloudTrail logs you can see
  exactly which instance made each API call.
- `UserId` is `RoleId:SessionName` — the role ID plus the instance ID

---

## Why this matters for Kubernetes

This pattern is fundamental to how Kubernetes integrates with AWS:

- **Node IAM role** — the EC2 nodes in an EKS cluster use an instance profile
  to call AWS APIs (create EBS volumes, register with the cluster)
- **IRSA (IAM Roles for Service Accounts)** — pods in EKS can assume roles
  without node-level credentials, using a similar token-based mechanism
- **kube2iam / kiam** — older tools that proxy metadata requests to give
  pods role-based credentials on self-managed clusters

Understanding the EC2 instance profile pattern is the foundation for all of these.

---

## ELS mapping

| Object | ELS layer | Notes |
|---|---|---|
| IAM role | L0 | Cloud identity — defines what the VM is allowed to do |
| Instance profile | L0 | Container that attaches the role to the EC2 instance |
| Temporary credentials | L0 | Vended by metadata service, consumed by AWS SDK/CLI |
| `aws sts get-caller-identity` | L0 | Confirms the VM's current AWS identity |

---

## How we set this up for cka-coach

```bash
# 1. Create the role with EC2 trust policy
aws iam create-role \
  --role-name cka-coach-node-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# 2. Attach read-only permissions
aws iam attach-role-policy \
  --role-name cka-coach-node-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess

# 3. Create instance profile and add role
aws iam create-instance-profile --instance-profile-name cka-coach-node-role
aws iam add-role-to-instance-profile \
  --instance-profile-name cka-coach-node-role \
  --role-name cka-coach-node-role

# 4. Attach to instances
aws ec2 associate-iam-instance-profile \
  --instance-id i-03658657280f01308 \
  --iam-instance-profile Name=cka-coach-node-role

aws ec2 associate-iam-instance-profile \
  --instance-id i-0fd6ab273954085ca \
  --iam-instance-profile Name=cka-coach-node-role
```
