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

# ---------------------------------------------------------------------------
# Well-known port descriptions
# ---------------------------------------------------------------------------
port_description() {
    local port=$1 proto=$2
    case "${proto}:${port}" in
        tcp:22)    echo "SSH — remote terminal access" ;;
        tcp:80)    echo "HTTP — web traffic" ;;
        tcp:443)   echo "HTTPS — secure web traffic" ;;
        tcp:6443)  echo "Kubernetes API server" ;;
        tcp:2379)  echo "etcd client API" ;;
        tcp:2380)  echo "etcd peer communication" ;;
        tcp:10250) echo "kubelet API" ;;
        tcp:10257) echo "kube-controller-manager" ;;
        tcp:10259) echo "kube-scheduler" ;;
        tcp:179)   echo "Calico BGP" ;;
        tcp:8501)  echo "cka-coach Streamlit UI" ;;
        tcp:8080)  echo "HTTP alternate" ;;
        tcp:8443)  echo "HTTPS alternate" ;;
        udp:4789)  echo "VXLAN overlay (Calico/Cilium)" ;;
        udp:8472)  echo "Flannel VXLAN" ;;
        udp:53)    echo "DNS" ;;
        tcp:53)    echo "DNS" ;;
        *)         echo "" ;;
    esac
}

port_label() {
    local port=$1 proto=$2
    local desc
    desc=$(port_description "$port" "$proto")
    if [[ -n "$desc" ]]; then
        echo "${port} (${desc})"
    else
        echo "${port}"
    fi
}
check_port() {
    # Check if a required K8s port is covered by any inbound rule
    # $1 = protocol (tcp/udp), $2 = port, $3 = description
    local proto=$1 port=$2 desc=$3
    local covered=false
    while IFS= read -r line; do
        local rule_proto rule_from rule_to
        rule_proto=$(echo "$line" | awk '{print $1}')
        rule_from=$(echo "$line"  | awk '{print $2}')
        rule_to=$(echo "$line"    | awk '{print $3}')
        # -1 means all protocols and all ports in AWS security group rules.
        # It is a sentinel value meaning 'any' — not a real protocol number.
        # A rule with protocol -1 covers every Kubernetes port automatically.
        if [[ "$rule_proto" == "-1" ]]; then
            covered=true; break
        fi
        if [[ "$rule_proto" == "$proto" ]] && \
           [[ "$rule_from" != "None" ]] && [[ "$rule_to" != "None" ]] && \
           [[ "$port" -ge "$rule_from" ]] && [[ "$port" -le "$rule_to" ]]; then
            covered=true; break
        fi
    done <<< "$ALL_RULES"
    local proto_upper
    proto_upper=$(echo "$proto" | tr '[:lower:]' '[:upper:]')
    if $covered; then
        echo -e "  ${GREEN}\u2705 ${proto_upper} ${port}${RESET}  \u2014 ${desc}"
    else
        echo -e "  ${RED}\u274c ${proto_upper} ${port}${RESET}  \u2014 ${desc}  ${RED}(NOT COVERED \u2014 kubeadm may fail)${RESET}"
    fi
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

# ---------------------------------------------------------------------------
# Operator identity
# ---------------------------------------------------------------------------
section "Operator identity — aws sts get-caller-identity (L0)"
echo -e "${YELLOW}Why: Before touching any infrastructure, confirm who you are.${RESET}"
echo -e "${YELLOW}This prevents accidental changes to the wrong AWS account.${RESET}"
echo ""

IDENTITY=$(aws sts get-caller-identity)
echo "$IDENTITY"
echo ""

ACCOUNT=$(echo "$IDENTITY" | python3 -c "import sys,json; print(json.load(sys.stdin)['Account'])" 2>/dev/null || echo "unknown")
ARN=$(echo "$IDENTITY"     | python3 -c "import sys,json; print(json.load(sys.stdin)['Arn'])"     2>/dev/null || echo "unknown")
USERID=$(echo "$IDENTITY"  | python3 -c "import sys,json; print(json.load(sys.stdin)['UserId'])"  2>/dev/null || echo "unknown")

echo -e "${YELLOW}Reading the output:${RESET}"
echo ""
echo "  UserId:  ${USERID}"
echo "  └ The unique ID of the IAM user or role making this call."
echo "    In the AWS Console: IAM → Users → your user → Summary → User ARN."
echo ""
echo "  Account: ${ACCOUNT}"
echo "  └ Your AWS account number. Every resource in AWS belongs to an account."
echo "    In the AWS Console: top-right menu → account name → Account ID."
echo "    This number appears in all ARNs and is how AWS bills you."
echo ""
echo "  Arn:     ${ARN}"
echo "  └ Amazon Resource Name — the globally unique identifier for this IAM identity."
echo "    ARN format: arn:partition:service:region:account-id:resource"
echo "    Example:    arn:aws:iam::208790449186:user/cka-coach-admin"
echo "                         ^^^  ^^^          ^^^^^^^^^^^^^^^^^^^"
echo "                         |    |            resource (user/cka-coach-admin)"
echo "                         |    service (iam)"
echo "                         partition (aws = standard commercial)"
echo ""
echo "    In the AWS Console: IAM → Users → your user → ARN field."
echo "    Every AWS resource has an ARN — EC2 instances, VPCs, security groups,"
echo "    S3 buckets, IAM roles. ARNs are how IAM policies refer to resources."

# ---------------------------------------------------------------------------
# Region
# ---------------------------------------------------------------------------
section "Active region (L0)"
REGION=$(aws configure get region 2>/dev/null || echo "not configured")
echo "Active region: ${REGION}"
echo ""
echo "  └ All resources (instances, VPCs, security groups) are region-scoped."
echo "    In the AWS Console: top-right dropdown (e.g. Canada (Central) = ca-central-1)."
echo "    If your instances are not showing up, you may be in the wrong region."

# ---------------------------------------------------------------------------
# Testbed instances
# ---------------------------------------------------------------------------
section "Testbed instances — aws ec2 describe-instances (L0)"
echo -e "${YELLOW}Why: This is the authoritative L0 view of your testbed.${RESET}"
echo -e "${YELLOW}It shows instance state, type, IPs, AZ, and tags from the AWS perspective.${RESET}"
echo ""
echo "  Name          — the Name tag you set when launching (cka-coach-cp / cka-coach-worker)"
echo "  InstanceId    — unique VM identifier (same as instance-id in the metadata service)"
echo "  State         — running / stopped / terminated"
echo "  Type          — hardware profile (t3.large = 2 vCPU, 8GB RAM)"
echo "  AZ            — which physical data centre within the region"
echo "  PrivateIP     — VPC address — what Kubernetes uses for node-to-node traffic"
echo "  PublicIP      — internet-facing address — how you SSH in (changes on stop/start)"
echo "  VPC           — the virtual network both nodes share"
echo "  Subnet        — the subnet within the VPC"
echo "  KeyPair       — the SSH key pair used to access this instance"
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

# ---------------------------------------------------------------------------
# VPC
# ---------------------------------------------------------------------------
section "VPC (L0)"
echo "  └ The Virtual Private Cloud — the isolated network your instances live in."
echo "    In the AWS Console: VPC → Your VPCs."
echo "    All inter-node Kubernetes traffic travels through this VPC."
echo "    The VPC CIDR (e.g. 172.31.0.0/16) must not overlap with your pod CIDR"
echo "    (e.g. 192.168.0.0/16 for Calico) or routing will break silently."
echo ""

aws ec2 describe-vpcs \
    --query 'Vpcs[*].{VpcId:VpcId,CIDR:CidrBlock,Default:IsDefault,State:State}' \
    --output table

# ---------------------------------------------------------------------------
# Security groups — with K8s port readiness check
# ---------------------------------------------------------------------------
section "Security groups on testbed instances (L0)"
echo "  └ The firewall rules applied to your instances at the AWS network level."
echo "    In the AWS Console: EC2 → Security Groups, or EC2 → Instances → Security tab."
echo "    These rules are enforced by AWS before packets even reach the Linux kernel."
echo "    If required Kubernetes ports are blocked here, kubeadm will fail silently"
echo "    or nodes will appear to join but never become Ready."
echo ""

SG_IDS=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=cka-coach-cp,cka-coach-worker" \
    --query 'Reservations[*].Instances[*].SecurityGroups[*].GroupId' \
    --output text 2>/dev/null | tr '\t' '\n' | sort -u)

if [[ -z "${SG_IDS}" ]]; then
    echo "No security groups found — run AWS validation first."
else
    for SG in ${SG_IDS}; do
        SG_DETAIL=$(aws ec2 describe-security-groups --group-ids "${SG}" 2>/dev/null)
        SG_NAME=$(echo "$SG_DETAIL" | python3 -c \
            "import sys,json; sgs=json.load(sys.stdin)['SecurityGroups']; print(sgs[0]['GroupName'])" \
            2>/dev/null || echo "unknown")

        echo ""
        echo -e "${BOLD}Security group: ${SG} (${SG_NAME})${RESET}"
        echo ""
        echo "  Note: AWS Security Groups are STATEFUL and instance-level only."
        echo "  They do not show NACLs (subnet-level) — default VPC NACLs allow all traffic."
        echo "  Source Port is not a concept in SG rules — only destination port and source are specified."
        echo "  Protocol -1 means 'all protocols and all ports' — it is a sentinel value meaning any/wildcard,"
        echo "  not a real protocol number. A single -1 rule covers every port Kubernetes needs."
        echo ""
        echo "  Inbound rules (what traffic AWS allows IN to instances in this group):"
        echo "  ┌──────────┬──────────────────────────┬────────────────────────────────────┬──────────────────────────────────┐"
        echo "  │ Protocol │ Source                   │ Destination Port / Service         │ Description                      │"
        echo "  ├──────────┼──────────────────────────┼────────────────────────────────────┼──────────────────────────────────┤"

        # Extract rules for display and port checking
        ALL_RULES=$(echo "$SG_DETAIL" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for sg in data['SecurityGroups']:
    for rule in sg.get('IpPermissions', []):
        proto = rule.get('IpProtocol', '-1')
        from_p = str(rule.get('FromPort', 'All'))
        to_p = str(rule.get('ToPort', 'All'))
        cidrs = [r.get('CidrIp','') for r in rule.get('IpRanges',[])]
        sg_sources = [p.get('GroupId','') for p in rule.get('UserIdGroupPairs',[])]
        sources = cidrs + sg_sources
        for src in sources:
            print(f'{proto} {from_p} {to_p} {src}')
        if not sources:
            print(f'{proto} {from_p} {to_p} (any)')
" 2>/dev/null || echo "")

        echo "$ALL_RULES" | while IFS= read -r line; do
            proto=$(echo "$line" | awk '{print $1}')
            from_p=$(echo "$line" | awk '{print $2}')
            to_p=$(echo "$line"   | awk '{print $3}')
            src=$(echo "$line"    | awk '{print $4}')
            proto_upper=$(echo "$proto" | tr '[:lower:]' '[:upper:]')
            if [[ "$proto" == "-1" ]]; then
                src_label="${src}"
                port_label="All ports"
                desc="-1 = all protocols/ports (any traffic allowed from this source)"
            elif [[ "$from_p" == "$to_p" ]]; then
                port_label=$(port_label "$from_p" "$proto")
                desc=$(port_description "$from_p" "$proto")
                src_label="${src}"
            else
                port_label="${from_p}-${to_p}"
                desc="port range"
                src_label="${src}"
            fi
            printf "  │ %-8s │ %-24s │ %-34s │ %-32s │\n" \
                "${proto_upper}" "${src_label}" "${port_label}" "${desc}"
        done

        echo "  └──────────┴──────────────────────────┴────────────────────────────────────┴──────────────────────────────────┘"

        # --- Kubernetes port readiness check ---
        echo ""
        echo -e "${BOLD}  Kubernetes port readiness check:${RESET}"
        echo "  These are the ports Kubernetes requires between nodes."
        echo "  A missing port here will cause silent failures during cluster setup."
        echo ""
        echo -e "  ${GREEN}✅ = port is covered by an inbound rule — traffic will be allowed${RESET}"
        echo -e "  ${RED}❌ = port is NOT covered — this will likely cause Kubernetes to fail${RESET}"
        echo ""
        check_port tcp  6443  "Kubernetes API server (kubeadm init / kubectl)"
        check_port tcp  2379  "etcd client API (control plane only)"
        check_port tcp  2380  "etcd peer communication (control plane only)"
        check_port tcp  10250 "kubelet API (required on all nodes)"
        check_port tcp  10257 "kube-controller-manager"
        check_port tcp  10259 "kube-scheduler"
        check_port tcp  179   "Calico BGP (if using BGP mode)"
        check_port udp  4789  "VXLAN overlay (Calico VXLAN / Cilium)"
        check_port tcp  8501  "cka-coach Streamlit UI"
        echo ""
        echo "  Note: if you see 'All traffic' in the rules above, all ports are covered."
        echo "  In the AWS Console: EC2 → Security Groups → ${SG} → Inbound rules tab."
    done
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN} L0 identity and instance evidence collection complete.${RESET}"
echo -e "${GREEN} You now have the operator view of your testbed.${RESET}"
echo -e "${GREEN} Compare with 01-aws-metadata.sh (the VM's own view) for the full L0 picture.${RESET}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
