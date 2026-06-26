# Learning Moment - Localhost Is Relative

## Access Whisker from your Mac: localhost, SSH tunnels, and kubectl port-forward

## What happened

A Kubernetes cluster was running on remote Ubuntu nodes. The control plane node
was named `control-plane`, Calico was installed, and Whisker was running in the
`calico-system` namespace.

The student wanted to open Whisker from a local Mac browser. That worked only
after two forwarding steps were in place:

1. `kubectl port-forward` from the control-plane node to the Whisker Service.
2. An SSH local port forward from the Mac to the control-plane node.

The core lesson:

> `localhost` depends on where you are standing.

## What Whisker is

Whisker is Calico's observability UI. It helps you view flow logs and network
observability data so you can understand how traffic is moving through the
cluster.

Whisker is not the Kubernetes dataplane itself. The dataplane is the part that
actually forwards and filters packets. Whisker is an application that lets you
inspect observability data from Calico.

## Why the Mac cannot reach Whisker directly

Whisker runs inside Kubernetes. In this lab it is exposed as a Kubernetes
Service in the `calico-system` namespace, usually as an internal `ClusterIP`
Service.

Your Mac is outside the Kubernetes service network. It cannot directly resolve
or route to an internal cluster Service such as `service/whisker`.

That is why you need a bridge from the Mac into the control-plane VM, and then
another bridge from the control-plane VM into Kubernetes.

## The two forwarding layers

The SSH tunnel connects your Mac to the control-plane node:

```bash
ssh -L 8081:localhost:8081 student@<control-plane-public-ip>
```

The `kubectl port-forward` connects the control-plane node to the Kubernetes
Service:

```bash
kubectl port-forward -n calico-system service/whisker 8081:8081
```

Then your Mac browser opens:

```text
http://localhost:8081
```

Both commands matter. If either forwarding layer is missing, the browser has no
complete path to Whisker.

## Traffic path

```text
Mac browser
  http://localhost:8081
        |
        v
Mac local port 8081
        |
        v
SSH tunnel
        |
        v
control-plane localhost:8081
        |
        v
kubectl port-forward
        |
        v
service/whisker -n calico-system
        |
        v
Whisker pod
```

Read that path slowly. The word `localhost` appears in more than one place, but
it does not mean the same machine every time.

## Verify Whisker exists

Run these on `control-plane`:

```bash
kubectl get pods -n calico-system | grep -i whisker
kubectl get svc -n calico-system | grep -i whisker
kubectl get tigerastatus
```

If Whisker is healthy, you should see Whisker pods and a Whisker Service in the
`calico-system` namespace. `kubectl get tigerastatus` gives a broader view of
Calico component health.

## Start the access path

In one terminal on `control-plane`, run:

```bash
kubectl port-forward -n calico-system service/whisker 8081:8081
```

Leave that command running.

In a terminal on your Mac, run:

```bash
ssh -L 8081:localhost:8081 student@<control-plane-public-ip>
```

Leave that SSH session running too.

Then open this from the Mac browser:

```text
http://localhost:8081
```

## Common confusion

### "I opened localhost:8081 on my Mac but nothing loaded."

`kubectl port-forward` was probably running only on the remote node, without an
SSH tunnel to the Mac. In the Mac browser, `localhost` means the Mac. The Mac
needs its own local port `8081` connected to the remote node.

### "I ran ssh -L but still nothing loaded."

`kubectl port-forward` may not be running on `control-plane`, or it may be using
a different port. The SSH tunnel can carry traffic only to something that is
actually listening on the control-plane side.

### "The Whisker service is missing."

Whisker may not be installed or enabled, or Calico observability components may
not be healthy. Check the Calico pods, Services, and `tigerastatus` output before
debugging the tunnel.

## Troubleshooting commands

Run these on `control-plane` unless noted otherwise:

```bash
kubectl get pods -A | grep -i whisker
kubectl get svc -A | grep -i whisker
kubectl get pods -n calico-system
kubectl get tigerastatus
sudo ss -lntp | grep 8081
```

If `sudo ss -lntp | grep 8081` shows nothing on `control-plane`, then
`kubectl port-forward` is not listening there.

On the Mac, make sure the SSH tunnel command is still running:

```bash
ssh -L 8081:localhost:8081 student@<control-plane-public-ip>
```

## ELS mapping

| Step | Where it lives | ELS meaning |
| --- | --- | --- |
| Mac browser | Outside the cluster / student workstation context | The browser is not inside Kubernetes |
| SSH tunnel | Between student workstation and VM | L0/L1 infrastructure access path |
| control-plane localhost | Node-local network namespace on the control-plane VM | Host-local network boundary |
| kubectl port-forward | Machine where `kubectl` is running, through the Kubernetes API | L4 Kubernetes API-assisted access path |
| `service/whisker` | Kubernetes Service in `calico-system` | L7 Kubernetes Service object / cluster service discovery |
| Whisker pod | Application Pod inside the cluster | L8 Application Pod |
| Calico / Whisker observability | Calico networking visibility | L4.3 Node Agents & Networking / CNI observability |

## Student reflection

Question:

```text
Where is localhost in each step of this path?
```

Expected answer:

- In the browser, `localhost` means the Mac.
- In the SSH command target, `localhost` means the control-plane node.
- In `kubectl port-forward`, `localhost` is bound on the machine where `kubectl`
  is running.
- The Kubernetes Service is inside the cluster network.

## Key lesson

`localhost` is not a universal place. It is relative to the machine and network
namespace where a command is running.

When the Mac successfully opens Whisker at `http://localhost:8081`, it is not
directly talking to a Kubernetes Service. It is using a two-step path:

```text
Mac localhost -> SSH tunnel -> control-plane localhost -> kubectl port-forward -> Whisker Service -> Whisker pod
```

That is a beautiful little ELS lesson: the same word can point to different
places depending on where the evidence is being observed.
