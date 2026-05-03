"""
prereq_checker.py

Node prerequisite checks for the cka-coach testbed workflow.

Redesigned as individual guided steps with beginner-friendly tone.
Each step explains why Kubernetes needs this configuration before
the student runs anything.

Kubelet / kubeadm / kubectl installation is deferred to Phase 3
(k8s_installer.py) — it is not needed until kubeadm init runs.

ELS layers covered:
- L1: swap, kernel modules, sysctl
- L2: runc (installed as part of containerd)
- L3: containerd

Option B (SSH-based automatic checking) is tracked in GitHub issue #1.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from testbed.testbed_state import CheckResult, NodeState


# ---------------------------------------------------------------------------
# Individual prereq steps
# ---------------------------------------------------------------------------

PREREQ_STEPS = [
    {
        "id": "swap",
        "els_layer": "L1",
        "title": "Disable swap",
        "why": (
            "Kubernetes will refuse to start if swap is enabled on this node. "
            "For now, just know that K8s needs swap off to manage memory reliably across pods. "
            "We will explore why in detail in the L1 kernel lesson."
        ),
        "check_commands": ["swapon --show"],
        "check_hint": (
            "If this command produces no output, swap is already off — you are good. "
            "If you see lines of output, swap is on and needs to be disabled."
        ),
        "fix_commands": [
            "sudo swapoff -a",
            "sudo sed -i '/ swap / s/^/#/' /etc/fstab",
        ],
        "fix_hint": (
            "The first command turns swap off now. "
            "The second makes it permanent so it stays off after a reboot."
        ),
        "confirm_question": "Did `swapon --show` produce no output (swap is off)?",
    },
    {
        "id": "kernel_modules",
        "els_layer": "L1",
        "title": "Load kernel modules",
        "why": (
            "Kubernetes networking depends on two Linux kernel modules: "
            "`overlay` (used by the container filesystem) and `br_netfilter` (used by pod networking). "
            "Without these, containers and pod networking will not work. "
            "We will explore what these modules do in the L1 kernel and L4.3 CNI lessons."
        ),
        "check_commands": ["lsmod | grep -E 'overlay|br_netfilter'"],
        "check_hint": (
            "You should see two lines — one containing 'overlay' and one containing 'br_netfilter'. "
            "If either is missing, run the fix commands below."
        ),
        "fix_commands": [
            "sudo modprobe overlay",
            "sudo modprobe br_netfilter",
            "cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf",
            "overlay",
            "br_netfilter",
            "EOF",
        ],
        "fix_hint": (
            "The first two commands load the modules now. "
            "The last block writes them to a config file so they load automatically on reboot."
        ),
        "confirm_question": "Does `lsmod | grep -E 'overlay|br_netfilter'` show both modules?",
    },
    {
        "id": "sysctl",
        "els_layer": "L1",
        "title": "Configure kernel networking settings",
        "why": (
            "Kubernetes needs the Linux kernel to forward network packets between pods and nodes. "
            "These two settings enable that. Without them, pod-to-pod and pod-to-service "
            "networking will silently fail. "
            "We will explore what these settings do in the L1 kernel and L4.3 CNI lessons."
        ),
        "check_commands": [
            "sysctl net.ipv4.ip_forward",
            "sysctl net.bridge.bridge-nf-call-iptables",
        ],
        "check_hint": (
            "Both values should show = 1. "
            "If either shows = 0, run the fix commands below."
        ),
        "fix_commands": [
            "cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf",
            "net.ipv4.ip_forward=1",
            "net.bridge.bridge-nf-call-iptables=1",
            "EOF",
            "sudo sysctl --system",
        ],
        "fix_hint": (
            "The first block writes the settings to a config file. "
            "The last command applies them immediately without a reboot."
        ),
        "confirm_question": "Do both sysctl values show = 1?",
    },
    {
        "id": "containerd",
        "els_layer": "L3",
        "title": "Install and start containerd",
        "why": (
            "containerd is the container runtime — the software that actually runs containers on this node. "
            "Kubernetes does not run containers directly; it delegates that job to containerd. "
            "Without containerd, Kubernetes cannot start any pods. "
            "We will explore how containerd fits into the ELS model in the L3 container runtime lesson."
        ),
        "check_commands": ["systemctl is-active containerd"],
        "check_hint": (
            "If the output is `active`, containerd is running and you are good. "
            "If it says `inactive` or `not-found`, run the fix commands below."
        ),
        "fix_commands": [
            "# Step 1 — add the Docker apt repository (containerd is distributed by Docker)",
            "sudo apt-get update",
            "sudo apt-get install -y ca-certificates curl",
            "sudo install -m 0755 -d /etc/apt/keyrings",
            "sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc",
            "sudo chmod a+r /etc/apt/keyrings/docker.asc",
            'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null',
            "sudo apt-get update",
            "# Step 2 — install containerd",
            "sudo apt-get install -y containerd.io",
            "# Step 3 — configure containerd to use the systemd cgroup driver (required by Kubernetes)",
            "sudo containerd config default | sudo tee /etc/containerd/config.toml",
            "sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml",
            "sudo systemctl enable --now containerd",
        ],
        "fix_hint": (
            "This installs containerd from the Docker apt repository and configures it to use "
            "the systemd cgroup driver. Kubernetes requires this cgroup driver setting — "
            "we will explain why in the L3 container runtime lesson."
        ),
        "confirm_question": "Does `systemctl is-active containerd` show `active`?",
    },
    {
        "id": "runc",
        "els_layer": "L2",
        "title": "Verify runc is installed",
        "why": (
            "runc is the low-level OCI runtime that containerd uses to actually create and start containers. "
            "It is installed automatically with containerd.io — you do not need to install it separately. "
            "We will explore what runc does in the L2 OCI runtime lesson."
        ),
        "check_commands": ["runc --version"],
        "check_hint": (
            "You should see a runc version string. "
            "If you see 'not found', containerd.io may not have installed correctly — "
            "re-run the containerd fix commands above."
        ),
        "fix_commands": [],
        "fix_hint": (
            "runc is installed as part of containerd.io. "
            "If it is missing, re-run the containerd install steps above."
        ),
        "confirm_question": "Does `runc --version` show a version string?",
    },
]


# ---------------------------------------------------------------------------
# Step state — tracks student progress through the prereq steps per node
# ---------------------------------------------------------------------------

@dataclass
class PrereqStepState:
    step_id: str
    confirmed: bool = False
    fix_shown: bool = False


@dataclass
class NodePrereqState:
    node_name: str
    role: str
    private_ip: str
    public_ip: str = ""
    steps: List[PrereqStepState] = field(default_factory=list)

    def __post_init__(self):
        if not self.steps:
            self.steps = [PrereqStepState(step_id=s["id"]) for s in PREREQ_STEPS]

    def current_step_index(self) -> int:
        for i, step in enumerate(self.steps):
            if not step.confirmed:
                return i
        return len(self.steps)

    def all_done(self) -> bool:
        return all(s.confirmed for s in self.steps)

    def get_step(self, step_id: str) -> PrereqStepState:
        for s in self.steps:
            if s.step_id == step_id:
                return s
        return PrereqStepState(step_id=step_id)


def build_ssh_instruction(node: NodeState) -> str:
    return f"ssh ubuntu@{node.public_ip or node.private_ip}"


def build_node_prereq_state(node: NodeState) -> NodePrereqState:
    return NodePrereqState(
        node_name=node.name,
        role=node.role,
        private_ip=node.private_ip,
        public_ip=node.public_ip,
    )
