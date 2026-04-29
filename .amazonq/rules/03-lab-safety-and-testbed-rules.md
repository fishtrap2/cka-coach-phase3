# Lab Safety and Testbed Automation Rules

cka-coach may guide students through creating and destroying lab Kubernetes environments. These workflows are educational and must be safe, explicit, and reversible where possible.

## Scope

The testbed workflow should support two blank Linux VMs:
- one control-plane VM
- one worker VM

The workflow should guide the student through:
- prerequisite checks
- hostname / hosts / DNS checks
- private network reachability
- required ports
- container runtime setup
- Kubernetes installation
- kubeadm init
- kubeadm join
- CNI installation
- Calico default install
- optional Calico observability components including Goldmane and Whisker
- validation
- teardown / reset

## Safety requirements

Do not silently run destructive commands.

Any workflow that removes Kubernetes must clearly warn about:
- kubeadm reset
- removal of CNI configuration
- removal of iptables/IPVS/eBPF leftovers
- removal of kubeconfig
- deletion of Kubernetes data directories
- impact on workloads

Prefer guided step mode:
1. explain
2. show command
3. ask user to run or confirm
4. collect result
5. validate
6. proceed

## Automation boundary

cka-coach may generate scripts, but scripts must:
- default to non-destructive behavior
- include --dry-run where possible
- require explicit flags for destructive actions
- log actions
- check prerequisites
- fail safely
- be idempotent where possible

Recommended destructive flags:
- --reset-kubernetes
- --purge-cni
- --yes-i-understand-this-destroys-the-lab

## Kubernetes installation approach

Prefer kubeadm-based installation for CKA/LFS258 learning alignment.

Do not hide Kubernetes fundamentals behind Helm if that reduces student learning.

Helm may be used for installing add-ons, but the student should still see:
- what is being installed
- where it lives in ELS
- how to validate it
- how to remove it

## CNI installation paths

The lab supports three CNI paths. Calico is the default. The student chooses at the start of the lesson.

Because CNI removal is unreliable (leftover iptables rules, interfaces, kernel state, and config files), the correct teaching model is:
- remove Kubernetes fully via `kubeadm reset` + node cleanup
- reinstall Kubernetes cleanly
- install the chosen CNI from scratch

This teaches students that CNI is a cluster-level architectural decision, not a hot-swap.

### Path 1 — Default bridge (no CNI)

Install kubeadm without a CNI plugin. Use this path to show:
- what breaks without a CNI (cross-node pod communication fails)
- why CNI exists
- what the cluster looks like in a CNI-absent state

Validation must show pods stuck in Pending or not ready due to missing network.

### Path 2 — Calico (default path)

Calico is the default CNI for the Phase 3 testbed.

When installing Calico, include validation for:
- tigera-operator
- calico-node
- calico-kube-controllers
- typha if present
- calico-apiserver if present
- goldmane if enabled
- whisker if enabled
- IPPools
- tigerastatus if available

### Path 3 — Cilium

Cilium is an optional CNI path. Use this path to contrast with Calico and introduce eBPF.

When installing Cilium, include validation for:
- cilium-operator
- cilium DaemonSet (one pod per node)
- cilium-envoy if present
- `cilium status` output if cilium CLI is available
- node readiness after CNI comes up

## CNI removal rule

Do not attempt in-place CNI removal or migration. Always guide the student through:
1. explain why CNI removal is unreliable
2. `kubeadm reset` on all nodes
3. node-level cleanup (CNI config, interfaces, iptables, kernel state)
4. fresh Kubernetes install
5. CNI install from chosen path

This is the honest real-world answer and the correct CKA mental model.