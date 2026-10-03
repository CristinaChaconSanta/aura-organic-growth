# Hybrid AI harness (pilot)

## Objective
Give this repo its own AI harness that combines Gentle AI (Engram memory, ODD tasks, orchestrator delegation, risk-based review) with the per-project structure from betta-tech/ejemplo-harness-subagentes (AGENTS.md map, init.sh gate, hooks, checkpoints, file-based subagent results).

## Problem
- Verification depends on the agent remembering to run tests; nothing enforces it.
- No start/close gate: an agent can begin work on a broken tree.
- CLAUDE.md is 225 lines (guideline: under 200) and is loaded whole every session.
- The global ~/.claude/CLAUDE.md is 441 lines (~16k tokens), loaded in every project.

## Scope (authorized by Cristina, 2026-10-03)
- Project harness for aura-organic-growth (pilot).
- Package it as an on-demand skill template, with Magika as an option for apps that receive user files.
- Slim the global CLAUDE.md through Gentle AI, with a backup, never by hand-editing managed blocks.

## Constraints
- Move content, never delete approved business rules (axiom, principles, rules approved by Cristina).
- aura-lead-intelligence stays read-only.
- No push. Work-unit commits on branch `chore/harness-hibrido`.
- TDD: not configured (ordinary checks). Runner: `.venv/bin/python -m pytest -q`.

## Tasks
- [x] T1 `init.sh` gate: .venv present, harness files present, pytest green; gitleaks and pip-audit when installed (warn if missing). Route: inline.
  - Evidence: exit 0 on clean tree (170 passed); exit 1 with a probe failing test.
- [x] T2 `.claude/settings.json` hooks: tests after Edit/Write, `init.sh` on Stop. Route: inline.
  - Evidence: post-edit hook exit 0 clean / exit 2 with failing test; stop gate exit 0 clean / exit 2 broken / exit 0 broken with stop_hook_active (no loop).
- [ ] T3 `AGENTS.md` map + slim CLAUDE.md under 200 lines by moving detailed rules to `docs/`. Route: delegated writer (2+ non-trivial files).
- [ ] T4 `CHECKPOINTS.md` + `progress/` convention for subagent results. Route: inline.
- [ ] T5 Global skill `nuevo-arnes` that scaffolds this template; optional Magika upload validation. Route: delegated writer.
- [ ] T6 Slim global CLAUDE.md via Gentle AI (backup first). Route: inline, needs user confirmation.

## Acceptance criteria
- `./init.sh` exits 0 on a clean tree and non-zero when a test fails.
- Hooks run without the agent invoking them.
- CLAUDE.md under 200 lines; no approved rule lost (diff check).
- Global CLAUDE.md under 200 lines, backup kept.

## Progress
- 2026-10-03: branch created from master at 694519e (Cursor's 8 commits). Document created.
- 2026-10-03: T1 ce81c7a, T2 e2fcc72. Native review (high risk, granted, 4 lenses): R3-001 CRITICAL, stop gate could loop when the flag was unreadable. Fixed in 202b326 (fail-open unless flag is explicitly false; tests/test_harness_hooks.py, 5 cases). Targeted validation approved and acknowledged. Reviewed boundary: 202b326.

## Open decisions (Cristina)
- LinkedIn: commit 694519e makes the contacts bot use the Aura LinkedIn account. Not pushed; revert with `git revert 694519e` if rejected.

## Next step
T3 `AGENTS.md` map + slim CLAUDE.md (delegated writer).
