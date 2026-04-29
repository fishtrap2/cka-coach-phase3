# cka-coach Product Operating Model

cka-coach is a student-first Kubernetes learning assistant, not a generic automation tool.

The product exists to help students understand where Kubernetes components live, how they interact, and how to troubleshoot through evidence. All features must preserve the Everything Lives Somewhere (ELS) learning model.

## Product principles

1. Student-first clarity beats feature volume.
2. Evidence beats confident guessing.
3. Teaching moments are first-class product outputs.
4. The dashboard is a teaching instrument panel, not an AI artifact dump.
5. The assistant must separate:
   - what it knows
   - what evidence supports it
   - what remains unknown
   - what the student should inspect next
6. Prefer small, reviewable changes over broad rewrites.
7. Do not break existing Phase 2 behavior unless the task explicitly asks for a redesign.

## Required behavior

When modifying code, preserve or improve:
- ELS layer mapping
- evidence/provenance display
- confidence vs. health separation
- concise explanations
- safe lab assumptions
- Streamlit usability

Do not introduce hidden automation that mutates the host, cluster, or network without explicit user confirmation in the UI or CLI.
