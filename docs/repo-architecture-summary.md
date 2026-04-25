# cka-coach Phase 2 — Repo Architecture Summary

This document gives a module-by-module architecture summary of the `cka-coach-phase2` repository, plus a practical dependency map.

---

## High-Level Shape

The repository is organized around a fairly clear pipeline:

1. `state_collector.py` gathers live cluster and host evidence.
2. Deterministic Python logic classifies and normalizes that evidence.
3. `dashboard_presenters.py` reshapes the evidence into UI-friendly models.
4. `ui/dashboard.py` renders the Streamlit application.
5. `agent.py` uses the structured state as the basis for LLM explanations.
6. Tests focus mainly on CNI detection and lesson workflow behavior.

---

## Core Runtime Modules

### `src/state_collector.py`

This is the collection and evidence engine.

It:

- runs `kubectl`, `systemctl`, `ip`, `iptables`, `crictl`, and related commands through safe wrappers
- builds the shared `state` object used by both the dashboard and the agent
- owns:
  - CNI detection
  - cluster vs node reconciliation
  - health flags
  - provenance loading
  - Calico runtime checks
  - stale interface and stale taint detection

Architecturally, this is the most important backend module in the repository.

### `src/dashboard_presenters.py`

This is the dashboard presentation layer.

It does not collect evidence. Instead, it reshapes the shared `state` into UI-ready models.

It owns:

- networking panel summaries
- CNI summary text
- networking component inventory
- network visual model construction
- HTML rendering for the visual panel
- node/runtime per-layer evidence formatting

If `state_collector.py` is truth gathering, this file is truth presentation.

### `ui/dashboard.py`

This is the main Streamlit application.

It orchestrates the page:

- collect state
- summarize ELS layers
- render the ELS table
- render the networking panel
- render the network visual panel
- render lessons
- render explain output

It contains a mix of UI assembly and summary glue logic. This is the main integration surface of the app.

### `src/agent.py`

This is the LLM-facing explanation layer.

Important design choice:

- the model does not own cluster truth
- Python computes deterministic ELS/CNI state first
- the LLM explains that structured result afterward

It builds:

- prompts
- traces
- structured JSON answers
- guided investigation plans

This is the teaching/explanation voice, not the source of truth.

### `src/main.py`

This is the CLI entrypoint using Typer.

It supports commands like:

- `layers`
- `scan`
- `ask`
- `dump-state`

This is the non-Streamlit interface to the same backend logic.

---

## ELS / Schema Layer

### `src/els_model.py`

Loads the ELS schema and builds the in-memory layer registry.

It preserves:

- layer names
- descriptions
- debug commands
- normalized command boundaries

This is the canonical ELS layer metadata used by the app.

### `src/els.py`

A very small schema loader for the YAML ELS model.

Tiny file, but foundational.

### `src/els_mapper.py`

Maps normalized collected state into ELS layers.

This is the deterministic bridge between:

- collected runtime evidence
- the YAML ELS model

It decides which evidence belongs to which layer.

### `src/schemas/els_schema.yaml`

The declarative definition of the ELS model.

It contains:

- layer descriptions
- lives/execution metadata
- debug commands
- subcomponents

This is one of the conceptual backbone files in the repo.

### `src/schemas.py`

TypedDict-style response contracts.

Defines shapes for:

- coach responses
- ELS results
- investigation steps
- traces

Mostly a type/contract module.

---

## UI Support / Command Formatting

### `src/command_boundaries.py`

Normalizes commands into `Cluster` vs `Node`.

Used by:

- dashboard rendering
- explain output
- ELS debug command presentation

This is a useful architectural seam because it keeps boundary-aware command formatting reusable.

### `src/config.py`

Small environment-driven configuration module.

Mainly handles:

- default OpenAI model selection
- prompt/context size limits

### `src/tools.py`

Older lightweight shell helper module.

It looks more like legacy/simple support code compared to `state_collector.py`.

Still useful for quick CLI scan-style paths.

---

## Lesson / Workflow Layer

### `src/lessons.py`

Implements the lesson/coaching workflow model.

It owns:

- lesson catalog
- step status model
- per-node cleanup/remediation state
- generated scripts
- lesson progress handling

This is the foundation for active coaching, even though parts of the UI are still collapsed or under construction.

---

## Tests

### `tests/test_cni_detection.py`

Main regression suite for networking and CNI behavior.

It heavily covers:

- CNI detection
- reconciliation
- health classification
- networking panel behavior

This is effectively the main safety net for Phase 2 logic.

### `tests/test_lessons.py`

Focused on:

- lesson catalog behavior
- cleanup lesson state
- lesson progression

---

## Docs

### `README.md`

Primary product-level entrypoint.

### `docs/phase2-roadmap.md`

Forward-looking roadmap and planning.

### `docs/explanation-quality-bar.md`

Important product-calibration document for student-facing answer quality.

### `docs/calico_known_good_baseline.md`

Operational reference for Calico verification.

### `docs/learning-path.md`

Learning and product-framing document.

---

## Dependency Map

Below is the practical module dependency map for the repo.

### Core application dependencies

```text
ui/dashboard.py
  -> state_collector.collect_state
  -> dashboard_presenters.*
  -> agent.ask_llm
  -> command_boundaries.*
  -> els_model.ELS_LAYERS
  -> lessons.*

src/main.py
  -> tools
  -> agent.ask_llm
  -> els_model.ELS_LAYERS
  -> state_collector.collect_state

src/agent.py
  -> config
  -> schemas
  -> els
  -> els_model
  -> els_mapper
  -> command_boundaries

src/els_model.py
  -> els
  -> command_boundaries

src/els_mapper.py
  -> els
```

### Architectural flow

```text
state_collector.py
  -> shared structured state
      -> dashboard_presenters.py
      -> agent.py
      -> lessons.py
      -> ui/dashboard.py summary glue

els_schema.yaml
  -> els.py
      -> els_model.py
      -> els_mapper.py
          -> agent.py
          -> ui/dashboard.py
```

### Test dependencies

```text
tests/test_cni_detection.py
  -> dashboard_presenters
  -> state_collector
  -> command_boundaries

tests/test_lessons.py
  -> lessons
```

---

## Mental Model of the Codebase

You can think about the repository in four main layers:

### 1. Collection layer

- `state_collector.py`

This gathers the live facts.

### 2. Domain / mapping layer

- `els.py`
- `els_model.py`
- `els_mapper.py`
- parts of `state_collector.py`
- `lessons.py`

This interprets the facts and structures them into educational/runtime meaning.

### 3. Presentation layer

- `dashboard_presenters.py`
- `ui/dashboard.py`

This turns the structured facts into a student-facing UI.

### 4. Explanation layer

- `agent.py`

This explains the deterministic result in teaching language.

---

## Architectural Read

The strongest current centers of gravity in the repo are:

- `src/state_collector.py`
- `src/dashboard_presenters.py`
- `ui/dashboard.py`
- `tests/test_cni_detection.py`

That tells us the project is currently strongest in:

- evidence collection
- evidence interpretation
- dashboarded visibility
- regression-tested networking logic

The main tradeoff is that some logic is split across collector, presenters, and dashboard glue. That means the repo is still in a rapidly evolving product architecture rather than a fully separated domain/app/view stack.

---

## One-Line Summary

cka-coach Phase 2 is a Kubernetes evidence engine plus a teaching dashboard, organized around the ELS model, with networking and CNI visibility as the current center of gravity.
