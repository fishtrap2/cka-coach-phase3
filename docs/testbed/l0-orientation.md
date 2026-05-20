# L0 Orientation — Before You Install Kubernetes

Before cka-coach explains Kubernetes, students should first prove where the
testbed itself lives.

These checks collect evidence from the lower ELS layers:

- cloud substrate (L0)
- VM identity (L0)
- Linux host networking (L1)
- routing (L1)
- metadata service (L0 → L1 boundary)
- IAM role identity (L0)
- DNS resolution (L1)
- listening sockets baseline (L1)

The goal is not to memorize AWS commands.

The goal is to learn how to ask:
- **Where am I?**
- **What can I reach?**
- **What identity do I have?**
- **What evidence proves it?**

---

## The two perspectives on your testbed

There are two ways to look at your testbed at L0:

### 1. The operator view (from your Mac)

You are the cloud operator. You created these instances. You can see them
via the AWS API.

```bash
bash scripts/testbed/providers/aws/02-aws-identity.sh
```

This shows:
- Who you are (IAM identity)
- What instances exist (state, type, IPs, AZ)
- What VPC they live in
- What security group rules are applied

### 2. The VM's own view (from inside the instance)

The VM itself has an identity. It knows where it is via the AWS metadata service
at `169.254.169.254`. This is a link-local address only reachable from inside
the VM — it is not on the internet.

```bash
# SSH into the control plane first
ssh -i ~/.ssh/aws-instance-cp.pem ubuntu@<public-ip>

# Then run
bash scripts/testbed/providers/aws/01-aws-metadata.sh
bash scripts/testbed/common/01-linux-networking.sh
```

This shows:
- The instance's own identity (instance-id, type, AZ)
- Its network addresses (private IP, public IP, VPC CIDR)
- Its IAM role (if attached)
- The Linux network interfaces and routing table

---

## Why IMDSv2 matters

The AWS metadata service now requires IMDSv2 (token-based requests) by default.

If you try the old way:
```bash
curl http://169.254.169.254/latest/meta-data/local-ipv4
```

You get nothing — not an error, just silence. This is a common gotcha.

The correct way:
```bash
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

curl -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/local-ipv4
```

IMDSv2 was introduced to prevent SSRF (Server-Side Request Forgery) attacks
where a compromised application running on the VM could steal the instance's
IAM credentials by querying the metadata service. The token requirement means
only processes that can make a PUT request to the metadata service can get a token.

This is a real-world security lesson, not just a lab detail.

---

## What to look for

### On the control plane node

After running the scripts, you should be able to answer:

| Question | Where to find it |
|---|---|
| What is this node's private IP? | `ip addr` or metadata `local-ipv4` |
| What is the VPC CIDR? | metadata `vpc-ipv4-cidr-block` |
| What subnet is this node in? | metadata `subnet-ipv4-cidr-block` |
| What IAM role does it have? | metadata `iam/info` |
| What ports are already listening? | `ss -tulpen` |
| What is the default route? | `ip route` |
| What DNS server is configured? | `resolvectl status` |

### From your Mac

| Question | Where to find it |
|---|---|
| Who am I in AWS? | `aws sts get-caller-identity` |
| Are both instances running? | `aws ec2 describe-instances` |
| What security group rules exist? | `aws ec2 describe-security-groups` |
| Are the required K8s ports open? | Security group inbound rules |

---

## ELS mapping

```
L0  Cloud substrate
    ├── AWS account / IAM identity        (02-aws-identity.sh)
    ├── EC2 instance (type, AZ, state)    (02-aws-identity.sh + 01-aws-metadata.sh)
    ├── VPC / subnet / CIDR               (02-aws-identity.sh + 01-aws-metadata.sh)
    ├── Security group rules              (02-aws-identity.sh)
    └── IAM role on instance              (01-aws-metadata.sh)

L1  Linux kernel / host networking
    ├── Network interfaces (ip addr)      (01-linux-networking.sh)
    ├── Routing table (ip route)          (01-linux-networking.sh)
    ├── DNS resolution (resolvectl)       (01-linux-networking.sh)
    └── Listening sockets baseline (ss)   (01-linux-networking.sh)
```

Everything above this — container runtime (L3), kubelet (L4.1), Kubernetes API (L4.5),
pods (L8) — runs on top of what these scripts show you.

---

## Run order

```
# From your Mac — operator view
bash scripts/testbed/providers/aws/02-aws-identity.sh

# From inside each VM — VM's own view
ssh -i ~/.ssh/aws-instance-cp.pem ubuntu@<cp-public-ip>
bash scripts/testbed/providers/aws/01-aws-metadata.sh
bash scripts/testbed/common/01-linux-networking.sh

# Repeat on the worker node
ssh -i ~/.ssh/aws-instance-cp.pem ubuntu@<worker-public-ip>
bash scripts/testbed/providers/aws/01-aws-metadata.sh
bash scripts/testbed/common/01-linux-networking.sh
```

---

## Save your baseline

Run these scripts **before** installing Kubernetes and **after**.

The difference between the two outputs is exactly what Kubernetes added:
- New network interfaces (cali*, vxlan.calico, cilium_host)
- New routes (pod CIDRs via CNI)
- New listening sockets (kube-apiserver, etcd, kubelet, kube-proxy)
- New DNS entries (cluster.local via CoreDNS)

That diff is one of the most concrete ways to understand what Kubernetes
actually does to a Linux node.
