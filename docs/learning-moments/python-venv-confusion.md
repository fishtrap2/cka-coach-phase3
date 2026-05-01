# Learning Moment — Python venv Confusion

## What happened

Running `streamlit run ui/dashboard.py` from inside `cka-coach-phase3` failed with
`zsh: command not found: streamlit` even after running `pip install -r requirements.txt`.

The pip output revealed the problem:

```
Requirement already satisfied: streamlit in /Users/michaelweir/cka-coach/venv/...
```

pip was installing into the **old** `cka-coach` (phase1) venv, not the phase3 venv.
The `streamlit` binary was landing in the wrong place, so the shell couldn't find it.

---

## Why this happened

When you run `source venv/bin/activate`, your shell updates `PATH` to point to that
venv's `bin/` directory. But if a previous venv was already active (or the shell had
stale PATH entries), the activation may not fully override the old environment.

The tell is in the pip output path:
- ✅ Correct: `Installing in /Users/michaelweir/cka-coach-phase3/venv/...`
- ❌ Wrong: `Installing in /Users/michaelweir/cka-coach/venv/...`

Always check `which pip` and `which python3` after activating a venv to confirm
you are where you think you are.

---

## ELS parallel

This is the same class of problem as CNI residuals in Kubernetes:

| Mac Python | Kubernetes |
|---|---|
| Old venv still active in shell PATH | Old CNI config still in `/etc/cni/net.d/` |
| pip installs into wrong venv | kubelet picks up wrong CNI plugin |
| `streamlit` not found in expected location | Pod networking fails unexpectedly |
| Fix: delete and recreate venv cleanly | Fix: kubeadm reset + clean node state |

The lesson in both cases: **stale environment state causes silent misdirection**.
The fix is always to start clean rather than patch over the old state.

---

## The fix

```bash
cd /Users/michaelweir/cka-coach-phase3
deactivate 2>/dev/null        # exit any active venv
rm -rf venv                   # remove the broken venv
python3 -m venv venv          # create a fresh one
source venv/bin/activate      # activate it
which pip                     # confirm: should show .../cka-coach-phase3/venv/bin/pip
which python3                 # confirm: should show .../cka-coach-phase3/venv/bin/python3
pip install -r requirements.txt
streamlit run ui/dashboard.py
```

The `which pip` and `which python3` checks after activation are the equivalent of
`kubectl get nodes` after a kubeadm join — confirm the environment is what you
expect before proceeding.

---

## Rule of thumb

Before running any Python project:

1. `deactivate` any existing venv
2. `cd` into the project directory
3. `source venv/bin/activate`
4. `which pip` — confirm it points inside the current project's venv
5. Then install or run

---

## ELS layer

This is an L3 / local environment concern — the equivalent of container runtime
configuration on your development machine. Getting the runtime environment right
is a prerequisite for everything above it.
