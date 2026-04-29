# Q Developer Chat — 2026-04-29 — Phase 3 Kickoff

## Compact Summary

**Project:** `cka-coach-phase3` — a Kubernetes learning system (teaching instrument panel) for CKA/LFS258 students, built around the ELS (Everything Lives Somewhere) model.

**Repo location:** `/Users/michaelweir/cka-coach-phase3`

**Stack:** Python, Streamlit, OpenAI, Kubernetes client, Pydantic

### Key files (phase3 baseline)
- `ui/dashboard.py` — 1,786 lines, single-page Streamlit UI with custom HTML/CSS
- `src/dashboard_presenters.py` — 1,565 lines, all rendering/data logic
- `src/state_collector.py` — 2,076 lines
- `src/agent.py` — 823 lines
- `src/lessons.py` — 894 lines
- Total ~9,400 lines

### Phase 3 goal
UI modernisation of the Streamlit dashboard (copied from phase2 repo).

### UI modernisation options discussed

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
Network visual HTML (`render_network_visual_html`) stays as-is.

### Completed this session
- Updated README from Phase 2 → Phase 3, added Amazon Q Developer note, updated clone URL (commit `8c9a299`)
- Created `docs/dev-log.md` (commit `15b7f4b`)
- Created `docs/aidlc/chats/` for storing compacted chat sessions

### Next session
Begin Option 1 — multi-page split of `dashboard.py`.
