# ELS Architecture Rules

cka-coach uses the Everything Lives Somewhere (ELS) model as its primary mental model.

## Canonical ELS layers

Use this model unless the user explicitly changes it:

- L0: Virtual Hardware / Cloud Infrastructure
- L1: Linux Kernel
- L2: OCI Runtime
- L3: Container Runtime / CRI
- L4: Node Agents and Networking
- L4.1: kubelet
- L4.2: kube-proxy
- L4.3: CNI / Pod Networking / dataplane evidence
- L4.5: Kubernetes API Layer
- L5: Kubernetes Controllers
- L6: Operators / Custom Controllers
- L7: Kubernetes Objects / Manifests
- L8: Application Pods
- L9: Applications

## Architecture expectations

All new features must identify where they live in the ELS model.

For Kubernetes and networking features, prefer structured output with:
- interpretation
- what we know
- cluster evidence
- node evidence
- unknowns
- confidence
- next steps

## Networking-specific rules

For CNI detection, do not rely on one signal only. Prefer multi-source evidence:
- /etc/cni/net.d files
- kube-system pods
- operator CRDs
- NetworkPolicy resources
- node routes
- iptables/IPVS/eBPF signals when available
- component versions when available

Keep confidence separate from health.

Example:
- Confidence: high that Calico is installed
- Health: degraded because one Calico component is not ready

## Calico-specific expectations

When Calico is detected, surface:
- calico-node
- calico-kube-controllers
- tigera-operator if present
- calico-apiserver if present
- typha if present
- goldmane if present
- whisker if present
- Installation CR if available
- IPPools if available
- policy presence and namespace scope if available