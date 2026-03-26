---
name: booksim-project-context
description: Use when working in the booksim-project repository or handling BookSim routing, architecture, implementation, or simulation tasks for this project. Start by reading doc/context_project_index.md, then load the project architecture, plan, and task documents before making code or experiment decisions.
---

# BookSim Project Context

Use this skill for any task inside the `booksim-project` workspace.

## Required startup sequence

Before making architectural judgments, code changes, or experiment plans, read:

1. `doc/context_project_index.md`
2. `doc/architecture_booksim_codebase.md`
3. `doc/plan_project_roadmap.md`
4. `doc/plan_current_tasks.md`

## Optional follow-up reads

- For saturation-throughput, Racke, permutation traffic, or nonblocking speedup tasks:
  read `doc/methodology_saturation_scan.md`
  then
  read `~/.codex/skills/booksim-saturation-scan/SKILL.md`

- For specific previous experiment outcomes:
  read the relevant files under `tests/analysis/` and `tests/data/`

## Operating rule

Treat the `doc/` files as the source of truth for:
- project background
- research direction
- implementation priorities
- methodology constraints
- naming conventions

Treat skills as:
- startup loaders
- workflow checklists
- experiment procedures

Do not let a skill become the only place where project facts live.
