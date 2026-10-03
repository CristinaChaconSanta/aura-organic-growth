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
- [x] T3 `AGENTS.md` map + slim CLAUDE.md under 200 lines by moving detailed rules to `docs/`. Route: delegated writer (2+ non-trivial files).
  - Evidence: 57be6ee. CLAUDE.md 225 -> 64 lines, AGENTS.md 59, docs/reglas.md 109, operacion.md 47, productos.md 26. Content-preservation check: 0 original non-heading lines missing.
- [x] T4 `CHECKPOINTS.md` + `progress/` convention for subagent results. Route: inline.
  - Evidence: 960d22e. CHECKPOINTS.md 26 lines; progress/current.md and history.md; init.sh checks AGENTS.md, CHECKPOINTS.md, progress/current.md and CLAUDE.md < 200 lines. ./init.sh exit 0, 175 passed.
- [x] T5 Global skill `nuevo-arnes` that scaffolds this template; optional Magika upload validation. Route: delegated writer.
- [x] T6 Slim global CLAUDE.md via Gentle AI (backup first). Route: inline, needs user confirmation.

## Acceptance criteria
- `./init.sh` exits 0 on a clean tree and non-zero when a test fails.
- Hooks run without the agent invoking them.
- CLAUDE.md under 200 lines; no approved rule lost (diff check).
- Global CLAUDE.md under 200 lines, backup kept.

## Progress
- 2026-10-03: branch created from master at 694519e (Cursor's 8 commits). Document created.
- 2026-10-03: T1 ce81c7a, T2 e2fcc72. Native review (high risk, granted, 4 lenses): R3-001 CRITICAL, stop gate could loop when the flag was unreadable. Fixed in 202b326 (fail-open unless flag is explicitly false; tests/test_harness_hooks.py, 5 cases). Targeted validation approved and acknowledged. Reviewed boundary: 202b326.

- 2026-10-03: native review of T3-T4 (high risk, granted, 4 lenses): approved with no findings, acknowledged. Reviewed boundary: deb241b.
- 2026-10-03: T5 skill at ~/.claude/skills/nuevo-arnes/ (SKILL.md 45 lines, template/, addons/magika.md). Evidence: throwaway Python project, init.sh exit 0 clean / 1 failing test, hook tests 5 passed, stop gate exit 2 / 0, bash -n OK. Node path and Magika add-on not exercised. Lives outside git.
- 2026-10-03: T6 global ~/.claude/CLAUDE.md 441 -> 149 lines via `gentle-ai uninstall -agent claude-code -component sdd -y`. Backup: ~/.claude/backups/pre-slim-2026-10-03/. Persona block unchanged (diff). Review agents restored from backup to ~/.claude/agents/ (agent-routing still uses native review). SDD per project: `gentle-ai install --agent claude-code --component sdd --scope workspace` (verified in a probe dir; writes a 408-line .claude/CLAUDE.md, so only for projects that use SDD).

## Open decisions (Cristina)
- LinkedIn: commit 694519e makes the contacts bot use the Aura LinkedIn account. Resolved 2026-10-03: Cristina authorized Cursor to use a different LinkedIn account.

## Next step
None. Feature complete; merge to master is Cristina's decision.
