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

## Calico expectations

Calico should be installed by default for the Phase 3 testbed unless the user asks for another CNI.

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