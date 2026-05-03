"""
observer_context.py

Detects where cka-coach itself is running and what it can see from there.

This is surfaced as a persistent banner at the top of every dashboard page
so the student always knows:
- where the app is running
- whether it can reach a cluster
- what evidence is and isn't available as a result

ELS layers:
- L1: OS / kernel of the machine cka-coach runs on
- L4.5: whether a cluster is reachable via kubeconfig
- L8: whether cka-coach is running inside a pod in the cluster
"""

import os
import platform
import socket
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class ObserverContext:
    # Where cka-coach is running
    hostname: str
    os_name: str                  # Darwin, Linux, Windows
    os_version: str
    platform_detail: str          # e.g. macOS 14.5, Ubuntu 22.04

    # Cluster reachability
    kubeconfig_present: bool
    kubeconfig_path: str
    cluster_reachable: bool
    cluster_endpoint: str         # API server address if detectable

    # Observer mode — derived from the above
    mode: str                     # mac_no_cluster, mac_with_cluster, node_no_cluster, node_in_cluster

    # What this means for evidence availability
    host_evidence_available: bool  # kubelet, containerd, /etc/cni directly readable
    summary: str                   # one-line human-readable summary
    consequence: str               # what the student should know about visibility


def _detect_platform_detail() -> str:
    system = platform.system()
    if system == "Darwin":
        mac_ver = platform.mac_ver()[0]
        return f"macOS {mac_ver}" if mac_ver else "macOS"
    if system == "Linux":
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
        return f"Linux {platform.release()}"
    return f"{system} {platform.release()}"


def _detect_kubeconfig() -> tuple[bool, str]:
    """Return (present, path)."""
    explicit = os.environ.get("KUBECONFIG", "")
    if explicit and os.path.exists(explicit):
        return True, explicit
    default = os.path.expanduser("~/.kube/config")
    if os.path.exists(default):
        return True, default
    return False, ""


def _detect_cluster_reachable() -> tuple[bool, str]:
    """
    Try kubectl cluster-info to check if the cluster is reachable.
    Returns (reachable, endpoint).
    """
    try:
        result = subprocess.run(
            ["kubectl", "cluster-info"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and "is running at" in result.stdout:
            for line in result.stdout.splitlines():
                if "is running at" in line:
                    endpoint = line.split("is running at")[-1].strip()
                    return True, endpoint
            return True, ""
        return False, ""
    except Exception:
        return False, ""


def _detect_running_in_pod() -> bool:
    """Detect if cka-coach is running inside a Kubernetes pod."""
    return (
        os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")
        and os.environ.get("KUBERNETES_SERVICE_HOST") is not None
    )


def _derive_mode(
    os_name: str,
    cluster_reachable: bool,
    in_pod: bool,
) -> str:
    if in_pod:
        return "node_in_cluster"
    if os_name == "Darwin":
        return "mac_with_cluster" if cluster_reachable else "mac_no_cluster"
    if os_name == "Linux":
        return "node_with_cluster" if cluster_reachable else "node_no_cluster"
    return "unknown_with_cluster" if cluster_reachable else "unknown_no_cluster"


def _derive_consequence(mode: str, host_evidence: bool) -> str:
    consequences = {
        "mac_no_cluster": (
            "No cluster is reachable from this Mac. "
            "The ELS panel will show visibility-limited for most layers. "
            "Use the Testbed page to set up a cluster on your AWS VMs first."
        ),
        "mac_with_cluster": (
            "cka-coach is running on your Mac and talking to a remote cluster. "
            "Cluster-level evidence (pods, nodes, events) is available. "
            "Host-level evidence (kubelet, containerd, /etc/cni) is not directly visible "
            "because cka-coach is not running on the cluster nodes."
        ),
        "node_no_cluster": (
            "cka-coach is running on a Linux node but cannot reach the cluster API. "
            "Check that the cluster is running and kubeconfig is configured correctly."
        ),
        "node_with_cluster": (
            "cka-coach is running on a cluster node with API access. "
            "Both cluster-level and some host-level evidence should be available."
        ),
        "node_in_cluster": (
            "cka-coach is running inside a pod in the cluster. "
            "Cluster-level evidence is available via the in-cluster API. "
            "Host-level evidence depends on whether host paths are mounted into the pod."
        ),
    }
    return consequences.get(mode, "Observer context is not fully determined.")


def collect_observer_context() -> ObserverContext:
    """
    Collect observer context. Called once at dashboard startup.
    Safe to call with no cluster present.
    """
    hostname = socket.gethostname()
    os_name = platform.system()
    os_version = platform.release()
    platform_detail = _detect_platform_detail()
    kubeconfig_present, kubeconfig_path = _detect_kubeconfig()
    cluster_reachable, cluster_endpoint = _detect_cluster_reachable()
    in_pod = _detect_running_in_pod()
    host_evidence = os_name == "Linux" and not in_pod

    mode = _derive_mode(os_name, cluster_reachable, in_pod)
    consequence = _derive_consequence(mode, host_evidence)

    mode_summaries = {
        "mac_no_cluster": f"Observer: {platform_detail} ({hostname}) — no cluster reachable",
        "mac_with_cluster": f"Observer: {platform_detail} ({hostname}) — connected to cluster at {cluster_endpoint}",
        "node_no_cluster": f"Observer: Linux node ({hostname}) — cluster not reachable",
        "node_with_cluster": f"Observer: Linux node ({hostname}) — connected to cluster at {cluster_endpoint}",
        "node_in_cluster": f"Observer: Pod inside cluster on node ({hostname})",
    }
    summary = mode_summaries.get(mode, f"Observer: {platform_detail} ({hostname})")

    return ObserverContext(
        hostname=hostname,
        os_name=os_name,
        os_version=os_version,
        platform_detail=platform_detail,
        kubeconfig_present=kubeconfig_present,
        kubeconfig_path=kubeconfig_path,
        cluster_reachable=cluster_reachable,
        cluster_endpoint=cluster_endpoint,
        mode=mode,
        host_evidence_available=host_evidence,
        summary=summary,
        consequence=consequence,
    )
