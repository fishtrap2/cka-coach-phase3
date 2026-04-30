# UI and Learning Experience Rules

The Streamlit UI is a teaching instrument panel.

## UI principles

- Keep the first view simple.
- Avoid clutter.
- Prefer progressive disclosure.
- Show the student what matters first.
- Put raw evidence behind expanders or tabs.
- Do not show large JSON blobs by default.
- Make confidence and uncertainty visible.
- Show commands used to collect evidence when useful.

## Required UI sections for networking/testbed work

For testbed setup:
- Current phase
- Prerequisites
- Control-plane status
- Worker status
- Network reachability
- Kubernetes status
- CNI status
- Calico observability status
- Next action
- Evidence

For learning modules:
- Lesson objective
- ELS layers involved
- What the student will do
- Commands to run
- Expected observations
- Common failure modes
- Reflection question
- Completion check

## Explain output

Explain responses should use this structure unless the user asks otherwise:

1. Current interpretation
2. What we know
3. Cluster evidence
4. Node evidence
5. Unknowns
6. Confidence
7. Next steps

Keep explanations concise and educational.