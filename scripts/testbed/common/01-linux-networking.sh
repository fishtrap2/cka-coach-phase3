#!/usr/bin/env bash
# =============================================================================
# 01-linux-networking.sh
#
# ELS layer: L1 — Linux Kernel / Host Networking
#
# Purpose:
#   Collect evidence of where this Linux node sits in the network.
#   Run this on each VM (control plane and worker) via SSH.
#
# What this teaches:
#   Before Kubernetes runs, the student should understand the host network
#   that Kubernetes will build on top of. Every pod, every CNI interface,
#   every route that Kubernetes creates lives on top of what you see here.
#
# Usage:
#   ssh -i ~/.ssh/aws-instance-cp.pem ubuntu@<public-ip> 'bash -s' < 01-linux-networking.sh
#   or copy to the node and run: bash 01-linux-networking.sh
# =============================================================================

set -euo pipefail

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RESET='\033[0m'

section() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${BOLD}$1${RESET}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
}

echo -e "${BOLD}"
echo "============================================================"
echo " L1 — Linux Host Networking Evidence"
echo " ELS: Everything Lives Somewhere — this is where your node lives"
echo "============================================================"
echo -e "${RESET}"

# --- Hostname ---
# The node's identity on the network. Kubernetes uses this as the node name
# unless overridden. Mismatches between hostname and DNS cause hard-to-debug issues.
section "Hostname"
echo "hostname:      $(hostname)"
echo "hostname -f:   $(hostname -f 2>/dev/null || echo '(fqdn not set)')"
echo "hostname -i:   $(hostname -i 2>/dev/null || echo '(not resolvable)')"

# --- Kernel ---
# The Linux kernel version. Kubernetes has minimum kernel requirements.
# CNI plugins like Calico and Cilium depend on specific kernel features.
section "Kernel (L1)"
uname -a

# --- Network interfaces ---
# Every interface here is a potential packet path. After Kubernetes and CNI
# are installed, you will see new interfaces appear here (cali*, vxlan.calico,
# cilium_host etc.). This is your baseline before any of that exists.
section "Network interfaces — ip addr (L1)"
ip addr

# --- Routing table ---
# The kernel routing table determines where packets go. After CNI is installed,
# new routes will appear here for pod CIDRs. This is your baseline.
section "Routing table — ip route (L1)"
ip route

# --- DNS resolution ---
# Kubernetes DNS (CoreDNS) will add cluster.local resolution later.
# This shows what DNS the node uses before Kubernetes touches it.
section "DNS resolution — resolvectl status (L1)"
if command -v resolvectl &>/dev/null; then
    resolvectl status 2>/dev/null || echo "(resolvectl not available)"
else
    echo "(resolvectl not found — checking /etc/resolv.conf)"
    cat /etc/resolv.conf
fi

# --- Listening sockets ---
# Shows what is already listening on this node before Kubernetes.
# After kubeadm init, you will see kube-apiserver (6443), etcd (2379-2380),
# kubelet (10250), and more appear here.
section "Listening sockets — ss -tulpen (L1)"
ss -tulpen 2>/dev/null || ss -tulpn

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN} L1 evidence collection complete.${RESET}"
echo -e "${GREEN} Save this output — compare it after Kubernetes and CNI are installed.${RESET}"
echo -e "${GREEN} The differences show exactly what Kubernetes added to this node.${RESET}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
