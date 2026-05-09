#!/usr/bin/env bash
# =============================================================================
# 01-aws-metadata.sh
#
# ELS layer: L0 — Virtual Hardware / Cloud Infrastructure
#
# Purpose:
#   Query the AWS Instance Metadata Service (IMDS) from inside the VM.
#   Run this on each VM (control plane and worker) via SSH.
#
# What this teaches:
#   Every EC2 instance has a metadata service at 169.254.169.254.
#   This is how the VM knows who it is, where it is, and what IAM role it has.
#   Kubernetes components (kubelet, cloud-controller-manager) use this service
#   to identify the node to the cluster.
#
# IMDSv2 note:
#   AWS now requires IMDSv2 (token-based) by default on new instances.
#   IMDSv1 (direct curl with no token) returns nothing — not an error, just silence.
#   This script uses IMDSv2 only, which is the correct and secure approach.
#
# Usage:
#   ssh -i ~/.ssh/aws-instance-cp.pem ubuntu@<public-ip> 'bash -s' < 01-aws-metadata.sh
#   or copy to the node and run: bash 01-aws-metadata.sh
# =============================================================================

set -euo pipefail

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RESET='\033[0m'

IMDS_BASE="http://169.254.169.254/latest/meta-data"
IMDS_TOKEN_URL="http://169.254.169.254/latest/api/token"

section() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${BOLD}$1${RESET}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
}

meta() {
    # Query a metadata path using the IMDSv2 token
    curl -sf -H "X-aws-ec2-metadata-token: ${TOKEN}" "${IMDS_BASE}/${1}" 2>/dev/null \
        || echo "(not available)"
}

echo -e "${BOLD}"
echo "============================================================"
echo " L0 — AWS Instance Metadata Evidence (IMDSv2)"
echo " ELS: Everything Lives Somewhere — this is the cloud substrate"
echo "============================================================"
echo -e "${RESET}"

# --- Get IMDSv2 token ---
# IMDSv2 requires a PUT request to get a session token first.
# The token is valid for up to 6 hours (21600 seconds).
# Without this token, all metadata requests return nothing — not an error.
section "Step 1 — Obtain IMDSv2 session token"
echo -e "${YELLOW}Why: AWS IMDSv2 requires a token to prevent SSRF attacks.${RESET}"
echo -e "${YELLOW}Without it, curl returns empty — a common gotcha for new students.${RESET}"
echo ""
echo "Command: curl -s -X PUT \"${IMDS_TOKEN_URL}\" -H \"X-aws-ec2-metadata-token-ttl-seconds: 21600\""
echo ""

TOKEN=$(curl -sf -X PUT "${IMDS_TOKEN_URL}" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null || true)

if [[ -z "${TOKEN}" ]]; then
    echo -e "${YELLOW}WARNING: Could not obtain IMDSv2 token.${RESET}"
    echo "This may mean:"
    echo "  - The metadata service is disabled on this instance"
    echo "  - You are not running this script on an EC2 instance"
    echo "  - Network access to 169.254.169.254 is blocked"
    exit 1
fi

echo -e "${GREEN}Token obtained successfully (not shown for security).${RESET}"

# --- Instance identity ---
# The fundamental identity of this VM in AWS.
section "Instance identity (L0)"
echo "instance-id:       $(meta instance-id)"
echo "instance-type:     $(meta instance-type)"
echo "ami-id:            $(meta ami-id)"

# --- Location ---
# Where in AWS this VM physically runs. Availability Zone maps to a
# physical data centre. Region is the geographic grouping.
section "Location (L0)"
echo "availability-zone: $(meta placement/availability-zone)"
echo "region:            $(meta placement/region)"

# --- Network identity ---
# The IP addresses AWS assigned to this VM.
# private-ipv4 is the VPC address — this is what Kubernetes uses for node-to-node traffic.
# public-ipv4 is the internet-facing address — this is how you SSH in.
section "Network identity (L0 → L1)"
echo "private-ipv4:      $(meta local-ipv4)"
echo "public-ipv4:       $(meta public-ipv4)"
echo "mac:               $(meta mac)"
MAC=$(meta mac)
echo "vpc-id:            $(meta network/interfaces/macs/${MAC}/vpc-id)"
echo "subnet-id:         $(meta network/interfaces/macs/${MAC}/subnet-id)"
echo "vpc-ipv4-cidr:     $(meta network/interfaces/macs/${MAC}/vpc-ipv4-cidr-block)"
echo "subnet-ipv4-cidr:  $(meta network/interfaces/macs/${MAC}/subnet-ipv4-cidr-block)"

# --- Security groups ---
# The firewall rules applied to this VM at the AWS network level.
# These are enforced before packets even reach the Linux kernel.
section "Security groups (L0)"
echo "security-groups:"
meta security-groups | while read -r sg; do
    echo "  - ${sg}"
done

# --- IAM role ---
# The AWS identity this VM has been granted. Kubernetes components use this
# to call AWS APIs (e.g. creating load balancers, EBS volumes).
# If no role is attached, this section will show 'not available'.
section "IAM role (L0)"
IAM_INFO=$(curl -sf -H "X-aws-ec2-metadata-token: ${TOKEN}" \
    "${IMDS_BASE}/iam/info" 2>/dev/null || echo "")

if [[ -z "${IAM_INFO}" ]]; then
    echo "No IAM role attached to this instance."
    echo "See issue #5 — attaching an IAM role removes the need for credentials files."
else
    echo "${IAM_INFO}"
    echo ""
    echo "IAM security credentials path:"
    curl -sf -H "X-aws-ec2-metadata-token: ${TOKEN}" \
        "${IMDS_BASE}/iam/security-credentials/" 2>/dev/null \
        | while read -r role; do
            echo "  Role: ${role}"
        done
fi

# --- User data ---
# Any startup script passed to this instance at launch time.
section "User data (L0)"
USERDATA=$(curl -sf -H "X-aws-ec2-metadata-token: ${TOKEN}" \
    "http://169.254.169.254/latest/user-data" 2>/dev/null || echo "(none)")
echo "${USERDATA}"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN} L0 metadata evidence collection complete.${RESET}"
echo -e "${GREEN} This is the cloud substrate your Kubernetes cluster runs on.${RESET}"
echo -e "${GREEN} Every layer above this (L1 kernel → L8 pods) lives here.${RESET}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
