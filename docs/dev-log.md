# cka-coach Dev Log

---

## 2026-05-03 — feature/testbed-setup live testing and extensions (Amazon Q Developer)

### AI-DLC phase
Construction (extended) — live testing against real AWS environment revealed gaps
not covered by the original inception brief. All changes are tracked in the
inception brief post-inception changes table.

### What we did
- Ran the full testbed workflow against real AWS instances (`cka-coach-cp`, `cka-coach-worker`)
- Fixed fabricated ELS data when no cluster present (kubectl error output filter)
- Fixed misleading kubectl client-only version shown without cluster
- Redesigned Phase 2 as individual guided steps with beginner-friendly tone
- Deferred kubelet install to Phase 3 (not needed until kubeadm init)
- Added containerd CRI plugin check (real failure hit during testing)
- Fixed node name mismatch between AWS tags and VM hostnames
- Removed step locking in Phase 2 — students can move freely
- Added Mark all complete / Undo buttons per step
- Replaced button-click progress bar with evidence-based phase status strip
- Added Phase 5 — deploy cka-coach to cluster (L8 capstone)
- Added `phase_evidence.py` module for observable phase inference
- Added observer context banner to both dashboard and testbed pages
- Raised GitHub issues #5, #6, #7 during session
- Added learning moments: venv confusion, kubectl error misread, containerd CRI disabled
- Added secrets and credentials rules file
- Added AWS IAM user `cka-coach-admin`, configured AWS CLI

### Current AI-DLC status
- Inception: ✅ approved
- Construction: ✅ complete (with post-inception extensions)
- Operations: 🔲 in progress — PR not yet raised, full end-to-end test not yet complete

### What remains before PR
- [ ] Complete Phase 5 test — deploy cka-coach to control plane, verify ELS panel goes 🟢
- [ ] Test teardown end to end
- [ ] Update README with testbed feature
- [ ] Save session chat log
- [ ] Raise PR

### Chat log
`docs/aidlc/chats/2026-05-03-testbed-testing-and-scripts.md`

### Key commits this session
- `664b2b8` — observer context banner
- `88d8b3e` — kubectl error filter
- `c57f3f7` — Phase 2 redesign
- `3875b29` — containerd CRI step
- `76f2c0d` — node name mismatch fix
- `1c1447e` — step locking removed
- `6eba5a2` — evidence-based phase strip + Phase 5

---

## 2026-04-29 — feature/testbed-setup construction complete (Amazon Q Developer)

### What we did
- Built all six backend modules in `src/testbed/`
- Built `ui/pages/4_Testbed.py` Streamlit page
- Validated each module with test scripts
- Raised GitHub issues #1–#4 for future platform support
- Wrote build log at `docs/aidlc/build-log-testbed-setup.md`

### Chat log
`docs/aidlc/chats/2026-04-29-phase3-kickoff.md`

### Next session
PR review and merge of `feature/testbed-setup` into `main`.

---

## 2026-04-29 — Phase 3 kickoff session (Amazon Q Developer)

### What we did
- Reviewed the full repo structure copied from phase2
- Assessed the current UI: single-page `ui/dashboard.py` (1,786 lines) with custom HTML/CSS injected via `st.html()`
- Discussed three UI modernisation options with effort estimates
- Updated README from Phase 2 → Phase 3 (commit `8c9a299`)

### UI modernisation options

| Option | Approach | Net LoC | Sessions | Risk |
|---|---|---|---|---|
| 1 | Multi-page split + theme + table cleanup | ~-120, 4 new files | 1 | Low |
| 2 | Option 1 + streamlit-aggrid interactive table | ~-150, 4 new files | 1 | Low-medium |
| 3 | FastAPI + React/HTMX frontend replacement | ~+1,500–2,000 | Multiple | High |

### Decision
Start with Option 1. Split `dashboard.py` into:
- `pages/1_ELS_Console.py`
- `pages/2_Networking.py`
- `pages/3_Lessons.py`

Add `.streamlit/config.toml` dark theme to replace injected CSS hacks.
Replace HTML ELS table with native Streamlit components.
Network visual HTML (`render_network_visual_html`) stays as-is — complexity justifies it.

### Key file sizes (phase3 baseline)
- `ui/dashboard.py` — 1,786 lines
- `src/dashboard_presenters.py` — 1,565 lines
- `src/state_collector.py` — 2,076 lines
- `src/agent.py` — 823 lines
- `src/lessons.py` — 894 lines
- Total — ~9,400 lines

### Chat log
`docs/aidlc/chats/2026-04-29-phase3-kickoff.md`

### Next session
Begin Option 1 — multi-page split of `dashboard.py`.

---

## Convention

Compacted chat sessions are saved to `docs/aidlc/chats/YYYY-MM-DD-<topic>.md`.
This dev-log links to each one and summarises decisions made.
To resume a session, paste the compact summary from the relevant chat file at the start of a new Q chat.
