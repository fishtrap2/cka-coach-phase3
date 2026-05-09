#!/usr/bin/env bash
# =============================================================================
# 02-aws-identity.sh
#
# ELS layer: L0 — Virtual Hardware / Cloud Infrastructure
#
# Purpose:
#   Confirm the AWS identity of the operator (who is running commands)
#   and describe the testbed instances from the outside (AWS API view).
#   Run this from your Mac — it uses the AWS CLI, not the metadata service.
#
# What this teaches:
#   There are two perspectives on your testbed:
#   1. From inside the VM (metadata service — 01-aws-metadata.sh)
#   2. From outside via the AWS API (this script)
#
#   The AWS API view is what the cloud operator sees. It shows the same
#   instances but from the control plane perspective — not from inside the VM.
#   Both views together give you the full L0 picture.
#
# Usage:
#   Run from your Mac (requires AWS CLI configured):
#   bash 02-aws-identity.sh
# =============================================================================

set -euo pipefail

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
RESET='\033[0m'

section() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${BOLD}$1${RESET}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
}

echo -e "${BOLD}"
echo "============================================================"
echo " L0 — AWS Identity and Testbed Instance Evidence"
echo " ELS: Everything Lives Somewhere — who are you, and what did you build?"
echo "============================================================"
echo -e "${RESET}"

# --- Check AWS CLI is available ---
if ! command -v aws &>/dev/null; then
    echo -e "${RED}ERROR: aws CLI not found.${RESET}"
    echo "Install with: brew install awscli"
    echo "Then configure with: aws configure"
    exit 1
fi

# --- Operator identity ---
# Who is running these commands? This is the IAM identity of the operator —
# the person or role that has permission to create and manage the testbed.
# Never use root credentials for this. Use a dedicated IAM user (e.g. cka-coach-admin).
section "Operator identity — aws sts get-caller-identity (L0)"
echo -e "${YELLOW}Why: Before touching any infrastructure, confirm who you are.${RESET}"
echo -e "${YELLOW}This prevents accidental changes to the wrong AWS account.${RESET}"
echo ""
aws sts get-caller-identity

# --- Region ---
section "Active region (L0)"
REGION=$(aws configure get region 2>/dev/null || echo "not configured")
echo "Active region: ${REGION}"
echo ""
echo -e "${YELLOW}Why: All resources (instances, VPCs, security groups) are region-scoped.${RESET}"
echo -e "${YELLOW}If your instances are not showing up, you may be in the wrong region.${RESET}"

# --- Testbed instances ---
# The AWS API view of your two VMs. This is what the cloud control plane knows
# about your instances — not what the instances know about themselves.
section "Testbed instances — aws ec2 describe-instances (L0)"
echo -e "${YELLOW}Why: This is the authoritative L0 view of your testbed.${RESET}"
echo -e "${YELLOW}It shows instance state, type, IPs, AZ, and tags from the AWS perspective.${RESET}"
echo ""

aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=cka-coach-cp,cka-coach-worker" \
    --query 'Reservations[*].Instances[*].{
        Name:Tags[?Key==`Name`]|[0].Value,
        InstanceId:InstanceId,
        State:State.Name,
        Type:InstanceType,
        AZ:Placement.AvailabilityZone,
        PrivateIP:PrivateIpAddress,
        PublicIP:PublicIpAddress,
        VPC:VpcId,
        Subnet:SubnetId,
        KeyPair:KeyName
    }' \
    --output table 2>/dev/null || {
        echo -e "${YELLOW}No instances tagged cka-coach-cp or cka-coach-worker found.${RESET}"
        echo "Either the instances don't exist yet or they are in a different region."
    }

# --- VPC ---
# The virtual network your instances live in.
section "VPC (L0)"
echo -e "${YELLOW}Why: All inter-node traffic in Kubernetes travels through this VPC.${RESET}"
echo -e "${YELLOW}The VPC CIDR must not overlap with your pod CIDR.${RESET}"
echo ""

aws ec2 describe-vpcs \
    --query 'Vpcs[*].{VpcId:VpcId,CIDR:CidrBlock,Default:IsDefault,State:State}' \
    --output table

# --- Security groups ---
# The firewall rules that control what traffic can reach your instances.
# Kubernetes requires specific ports to be open between nodes.
section "Security groups on testbed instances (L0)"
echo -e "${YELLOW}Why: If the wrong ports are blocked, kubeadm join will fail silently.${RESET}"
echo -e "${YELLOW}Required ports: 6443 (API), 2379-2380 (etcd), 10250 (kubelet), 4789 UDP (VXLAN).${RESET}"
echo ""

SG_IDS=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=cka-coach-cp,cka-coach-worker" \
    --query 'Reservations[*].Instances[*].SecurityGroups[*].GroupId' \
    --output text 2>/dev/null | tr '\t' '\n' | sort -u)

if [[ -z "${SG_IDS}" ]]; then
    echo "No security groups found — run AWS validation first."
else
    for SG in ${SG_IDS}; do
        echo "Security group: ${SG}"
        aws ec2 describe-security-groups \
            --group-ids "${SG}" \
            --query 'SecurityGroups[*].{
                Name:GroupName,
                InboundRules:IpPermissions[*].{
                    Protocol:IpProtocol,
                    FromPort:FromPort,
                    ToPort:ToPort,
                    CIDR:IpRanges[*].CidrIp
                }
            }' \
            --output table
        echo ""
    done
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN} L0 identity and instance evidence collection complete.${RESET}"
echo -e "${GREEN} You now have the operator view of your testbed.${RESET}"
echo -e "${GREEN} Compare with 01-aws-metadata.sh (the VM's own view) for the full L0 picture.${RESET}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
