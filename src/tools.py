import subprocess
def run(cmd):
    try:
        result = subprocess.check_output(cmd, shell=True, text=True)
        return result[:4000]
    except Exception as e:
        return str(e)
def kubectl_nodes():
    return run("kubectl get nodes -o wide")
def kubectl_pods():
    return run("kubectl get pods -A")
def crictl_ps():
    return run("crictl ps")
def host_processes():
    return run("ps aux | head -20")
