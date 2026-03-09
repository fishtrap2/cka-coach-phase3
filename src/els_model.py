ELS_LAYERS = {
    1: {
        "name": "Physical Hardware",
        "lives": ["CPU", "Memory", "Disk"],
        "debug": ["lscpu", "lsblk", "free -m"],
    },
    2: {
        "name": "Virtualization",
        "lives": ["KVM", "GCE VM", "AWS EC2"],
        "debug": ["virt-what"],
    },
    3: {
        "name": "Guest OS",
        "lives": ["Linux kernel", "systemd"],
        "debug": ["uname -a", "cat /etc/os-release"],
    },
    4: {
        "name": "Container Runtime",
        "lives": ["containerd", "runc"],
        "debug": ["crictl ps", "crictl info"],
    },
    5: {
        "name": "Node Agents",
        "lives": ["kubelet", "kube-proxy"],
        "debug": ["systemctl status kubelet"],
    },
    6: {
        "name": "Control Plane",
        "lives": ["kube-apiserver", "scheduler", "controller-manager", "etcd"],
        "debug": ["kubectl get pods -n kube-system"],
    },
    7: {
        "name": "Kubernetes Objects",
        "lives": ["Deployments", "Services"],
        "debug": ["kubectl get all"],
    },
    8: {
        "name": "Pods / Containers",
        "lives": ["Pods"],
        "debug": ["kubectl get pods -A"],
    },
    9: {
        "name": "Application Processes",
        "lives": ["application binaries"],
        "debug": ["kubectl exec"],
    },
}
