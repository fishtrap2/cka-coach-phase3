# Coding and Repository Rules

## General coding standards

- Use small, focused changes.
- Avoid broad rewrites unless explicitly requested.
- Preserve existing public function names unless there is a clear migration path.
- Prefer readable Python over clever abstractions.
- Add comments where the code teaches the student something useful.
- Keep UI logic, state collection, and AI explanation logic separated where practical.

## Python standards

- Use type hints for new functions where reasonable.
- Use dataclasses or typed dictionaries for structured state where helpful.
- Avoid shell=True unless absolutely necessary.
- Capture command output, exit code, and stderr.
- Never assume kubectl, crictl, helm, kubeadm, or systemctl are available without checking.

## CLI / shell command rules

All shell commands must:
- be explicit
- have a clear purpose
- be safe to print for the user
- handle failure
- avoid destructive operations unless gated by confirmation

For destructive or host-changing operations, require:
- dry-run or preview mode where possible
- explanation of impact
- explicit confirmation
- clear rollback or recovery notes when feasible

## Git / workflow rules

- Do not mix unrelated features in one change.
- Prefer feature branches.
- Include docs updates when behavior changes.
- Include test or validation steps in the final response.
- Never modify secrets, .env files, kubeconfigs, private keys, or API keys.