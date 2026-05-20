# Learning Moment — AWS Hairpin NAT and Why Internal Services Use Private IPs

## What happened

cka-coach was running on the control plane at `3.96.170.24:8501`.
Opening `http://3.96.170.24:8501` in a browser from a Mac worked fine.

But when cka-coach tried to check its own reachability by curling
`http://3.96.170.24:8501` from inside the same VM, it got a connection timeout.

The VM could not reach itself via its own public IP.

---

## Why this happens — hairpin NAT

When an EC2 instance sends traffic to its own public IP, the packet leaves
the instance, hits the AWS network, and AWS does not route it back to the
same instance. The packet is dropped or times out.

This is called **hairpin NAT** (or NAT loopback) — the ability for a device
to reach itself via its external address. AWS does not support it by default.

```
VM (3.96.170.24)
    │
    └── curl http://3.96.170.24:8501
              │
              └── packet leaves VM via eth0
                        │
                        └── hits AWS network edge
                                  │
                                  └── AWS: "this is a public IP on this VPC"
                                            │
                                            └── packet dropped / timed out
                                                ✗ never returns to the VM
```

From your Mac, the same request works because it comes from outside AWS
and is routed normally to the instance.

---

## The fix

When a service needs to reach itself or another service on the same host,
use `localhost` or the private IP — not the public IP.

```bash
# Wrong — will timeout on AWS
curl http://3.96.170.24:8501

# Correct — uses the loopback interface, never leaves the VM
curl http://localhost:8501

# Also correct — uses the VPC private IP, stays inside AWS network
curl http://172.31.2.240:8501
```

cka-coach now detects when it is running on the control plane and uses
`localhost:8501` for the reachability check instead of the public IP.

---

## Why internal services should always use private IPs

This is not just a cka-coach quirk — it is a general AWS networking principle:

**Services that communicate with each other inside a VPC should always use
private IPs, not public IPs.**

Reasons:

1. **Hairpin NAT** — public IP to self doesn't work as shown above
2. **Cost** — traffic that leaves and re-enters the VPC via public IPs
   may incur data transfer charges; private IP traffic within a VPC is free
3. **Latency** — private IP traffic stays inside the AWS network and is faster
4. **Security** — traffic on private IPs never crosses the public internet,
   even if it looks like it does from the IP address

This is why Kubernetes uses private IPs for node-to-node communication,
why the kubeadm `--apiserver-advertise-address` flag uses the private IP,
and why pod CIDRs are private ranges.

---

## ELS mapping

| Concept | ELS layer | Notes |
|---|---|---|
| Public IP routing | L0 | AWS network edge behaviour |
| Hairpin NAT limitation | L0 | VPC networking constraint |
| Private IP communication | L0 → L1 | VPC internal routing |
| Kubernetes node-to-node | L4.1 / L4.3 | Always uses private IPs |
| kubeadm advertise address | L4.5 | Must be private IP |

---

## The broader lesson

A public IP is an address for reaching a service **from outside**.
A private IP is an address for reaching a service **from inside the same network**.

Using the wrong one — even when both technically refer to the same machine —
can cause silent failures that are hard to debug because the service appears
to be running and reachable from outside, but unreachable from within.

This is one of those things experienced AWS engineers know instinctively
but is not obvious until you hit it the hard way.
