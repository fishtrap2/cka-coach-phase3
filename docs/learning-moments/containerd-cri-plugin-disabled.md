# Learning Moment — containerd CRI Plugin Disabled

## What happened

`kubeadm init` failed with:

```
failed to create new CRI runtime service: validate service connection: validate CRI v1
runtime API for endpoint "unix:///var/run/containerd/containerd.sock":
rpc error: code = Unimplemented desc = unknown service runtime.v1.RuntimeService
```

containerd was running (`systemctl is-active containerd` showed `active`) but
kubeadm could not talk to it.

---

## Why this happened

containerd ships with a plugin called CRI (Container Runtime Interface) — the
interface Kubernetes uses to ask containerd to start, stop, and inspect containers.

On some Ubuntu versions (particularly 24.04), the default containerd config
disables the CRI plugin:

```toml
disabled_plugins = ["cri"]
```

This means containerd starts and runs fine as a general container runtime, but
Kubernetes cannot use it because the CRI endpoint is not active.

The error `unknown service runtime.v1.RuntimeService` is containerd saying:
"I don't know what you're asking for" — because the CRI plugin that would handle
that request is disabled.

---

## ELS layer

This is an L3 (Container Runtime / CRI) issue.

The CRI interface is the boundary between:
- **L4.1** — kubelet (which speaks CRI to request containers)
- **L3** — containerd (which implements CRI to run containers)

When the CRI plugin is disabled, the L4.1 → L3 boundary is broken even though
both layers appear healthy in isolation.

```
L4.1  kubelet          ← wants to speak CRI
         ↓
      [CRI boundary]   ← BROKEN — plugin disabled
         ↓
L3    containerd       ← running, but not listening on CRI
```

---

## The fix

```bash
# Regenerate the containerd config with CRI enabled
sudo containerd config default | sudo tee /etc/containerd/config.toml

# Enable the systemd cgroup driver (required by Kubernetes)
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

# Remove any line that disables the CRI plugin
sudo sed -i '/disabled_plugins.*cri/d' /etc/containerd/config.toml

# Restart containerd to apply the new config
sudo systemctl restart containerd

# Verify Kubernetes can now talk to containerd
sudo crictl --runtime-endpoint unix:///var/run/containerd/containerd.sock info
```

---

## Why `SystemdCgroup = true` matters

While fixing the CRI plugin, we also set `SystemdCgroup = true`. This is a
separate but equally important setting.

Kubernetes uses systemd to manage cgroups (the Linux kernel feature that limits
CPU and memory per container). If containerd uses a different cgroup driver than
kubelet expects, pods will fail in subtle ways.

Setting `SystemdCgroup = true` in containerd's config ensures both kubelet and
containerd agree on how to manage cgroups.

---

## Key lesson

A component can appear healthy at its own layer while silently breaking the
layer above it.

`systemctl is-active containerd` said `active` — which was true. containerd was
running. But the CRI plugin inside containerd was disabled, so the L4.1 → L3
interface was broken.

This is why cka-coach checks each layer independently and why the ELS model
matters: **health at one layer does not guarantee the interface to the next
layer is working**.

---

## How cka-coach catches this

Phase 2 of the testbed workflow now includes a dedicated `containerd_cri` step
that checks for disabled plugins and provides the exact fix commands.

This step was added after this issue was encountered during real testbed testing.
