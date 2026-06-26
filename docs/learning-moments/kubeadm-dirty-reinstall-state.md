# Learning Moment — Recover from Dirty kubeadm init/join State

## What happened

A two-node Ubuntu 24.04 kubeadm lab was being reinstalled after a previous
cluster setup. The target runtime was containerd, the intended CNI was Calico,
and the nodes were:

- `control-plane`
- `worker1`

On the control plane, this command failed:

```bash
sudo kubeadm init --pod-network-cidr=192.168.0.0/16 --apiserver-advertise-address=172.31.2.240
```

The preflight errors included occupied ports `6443`, `10259`, `10257`, `10250`,
`2379`, and `2380`; existing static pod manifests under
`/etc/kubernetes/manifests`; and a non-empty `/var/lib/etcd`.

On the worker, this command failed:

```bash
sudo kubeadm join 172.31.2.240:6443 --token ... --discovery-token-ca-cert-hash sha256:...
```

The preflight errors included an existing `/etc/kubernetes/kubelet.conf`,
occupied port `10250`, and an existing `/etc/kubernetes/pki/ca.crt`.

## What kubeadm was protecting you from

`kubeadm init` and `kubeadm join` are not overwrite commands. They are careful
about existing cluster evidence because overwriting it blindly can mix old
cluster state with new cluster state.

Treat kubeadm preflight errors as evidence, not annoyance:

| Evidence | Meaning | ELS layer |
| --- | --- | --- |
| `/etc/kubernetes/manifests/*.yaml` | kubelet still has static pod source files | L4 / L4.5 |
| `kube-apiserver.yaml` | API server static pod already exists | L4.5 |
| `etcd.yaml` and `/var/lib/etcd` | cluster state already exists | L4.5 |
| port `6443` | API server may still be listening | L4.5 |
| ports `2379` and `2380` | etcd may still be listening | L4.5 |
| ports `10257` and `10259` | controller-manager or scheduler may still be listening | L5 |
| port `10250` | kubelet is still listening | L4 |
| `/etc/kubernetes/kubelet.conf` | the worker already has join state | L4 |
| `/etc/kubernetes/pki/ca.crt` | the node already has cluster trust material | L4 |
| `/etc/cni/net.d` and `/var/lib/cni` | old CNI configuration or allocation state may remain | L4 networking |
| CNI interfaces such as `cni0`, `flannel.1`, or `tunl0` | host networking residue may remain | L1/L2/L3 |

The short version:

> kubeadm preflight errors are not just errors. They are a map of what
> Kubernetes components still exist on the machine.

## Why this happened

`kubeadm init` creates control-plane static pod manifests in
`/etc/kubernetes/manifests`. The kubelet watches that directory and starts those
pods. That is why old manifest files can keep `kube-apiserver`,
`kube-controller-manager`, `kube-scheduler`, and `etcd` alive even when the
student thinks the cluster is gone.

etcd stores cluster state under `/var/lib/etcd`. If that directory is still
populated, the machine still contains old control-plane data.

`kubeadm join` writes kubelet configuration and cluster CA material on the
worker. If `/etc/kubernetes/kubelet.conf` and `/etc/kubernetes/pki/ca.crt`
already exist, kubeadm sees a node that may already belong to a cluster.

Failed or repeated installs often leave evidence behind. That evidence is the
diagnosis.

## Why not use `--ignore-preflight-errors`

Do not use `--ignore-preflight-errors` for this scenario. The preflight checks
are warning you that old Kubernetes components, data, credentials, or ports are
still present.

Ignoring those checks can produce a mixed cluster: new kubeadm configuration on
top of old static pods, old etcd data, stale kubelet credentials, or old CNI
state. That is harder for a beginner to reason about than a clean reset.

## Diagnosis before cleanup

On the control plane, check whether Kubernetes ports are still occupied:

```bash
sudo ss -lntp | egrep '6443|10259|10257|10250|2379|2380' || echo "Kubernetes ports are clear"
```

On the worker, check the kubelet port:

```bash
sudo ss -lntp | grep 10250 || echo "Port 10250 is clear"
```

Also inspect the files kubeadm reported:

```bash
sudo ls -la /etc/kubernetes
sudo ls -la /etc/kubernetes/manifests 2>/dev/null || true
sudo ls -la /var/lib/etcd 2>/dev/null || true
sudo ls -la /etc/cni/net.d 2>/dev/null || true
sudo ls -la /var/lib/cni 2>/dev/null || true
```

## Safety warning

These reset commands are destructive. They are intended only for disposable lab
clusters where it is acceptable to remove local Kubernetes state, etcd data, CNI
state, and iptables rules.

Do not run these commands on a production cluster or on a machine that contains
cluster state you need to preserve.

## Control-plane reset

Run this on `control-plane` only after confirming the lab cluster can be
destroyed:

```bash
sudo kubeadm reset -f
sudo systemctl stop kubelet

sudo rm -rf /etc/kubernetes
sudo rm -rf /var/lib/etcd
sudo rm -rf /var/lib/kubelet
sudo rm -rf /etc/cni/net.d
sudo rm -rf /var/lib/cni
sudo rm -rf ~/.kube

sudo ip link delete cni0 2>/dev/null || true
sudo ip link delete flannel.1 2>/dev/null || true
sudo ip link delete tunl0 2>/dev/null || true

sudo iptables -F
sudo iptables -t nat -F
sudo iptables -t mangle -F
sudo iptables -X

sudo systemctl restart containerd
sudo systemctl restart kubelet

sudo ss -lntp | egrep '6443|10259|10257|10250|2379|2380' || echo "Kubernetes ports are clear"
```

## Worker reset

Run this on `worker1` only after confirming the lab cluster can be destroyed:

```bash
sudo kubeadm reset -f
sudo systemctl stop kubelet

sudo rm -rf /etc/kubernetes
sudo rm -rf /var/lib/kubelet
sudo rm -rf /etc/cni/net.d
sudo rm -rf /var/lib/cni
sudo rm -rf ~/.kube

sudo ip link delete cni0 2>/dev/null || true
sudo ip link delete flannel.1 2>/dev/null || true
sudo ip link delete tunl0 2>/dev/null || true

sudo iptables -F
sudo iptables -t nat -F
sudo iptables -t mangle -F
sudo iptables -X

sudo systemctl restart containerd
sudo systemctl restart kubelet

sudo ss -lntp | grep 10250 || echo "Port 10250 is clear"
```

## Reinstall and verify

After both nodes are clean, run `kubeadm init` again on the control plane, apply
Calico, then run the fresh `kubeadm join` command on the worker.

Verify the cluster from the control plane:

```bash
kubectl get nodes -o wide
kubectl get pods -A
```

The expected result is that both nodes appear and the control-plane, kube-system,
and Calico pods become healthy.

## ELS mapping

- **L4.5 Kubernetes API Layer:** `kube-apiserver` and `etcd` are exposed by
  static pods and backed by `/var/lib/etcd`.
- **L4 Node Agents & Networking:** kubelet owns the node join state, listens on
  port `10250`, and interacts with CNI config and CNI state.
- **L5 Controllers:** `kube-controller-manager` and `kube-scheduler` run as
  static pods started by kubelet on the control plane.
- **L1/L2/L3 host networking evidence:** occupied TCP ports, iptables rules, and
  CNI interfaces show that host-level networking state still exists.

## Key lesson

Dirty reinstall failures are not random. kubeadm is showing you where the old
cluster still lives:

- control-plane residue usually means static pod manifests, etcd data, and
  occupied control-plane ports;
- worker residue usually means kubelet join config, cluster CA material, and
  port `10250`;
- CNI residue may remain on either node as config files, allocation state,
  iptables rules, or interfaces.

Separate diagnosis from cleanup. First read the evidence, then reset only the
disposable lab nodes you actually intend to destroy.
