#!/usr/bin/env bash
# init.sh — Start/close gate for AI agents working in this repo.
#
# Run it before starting work and before declaring any task done.
# Exit 0: the environment is ready. Non-zero: stop and fix it first.

set -u
cd "$(dirname "$0")"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; NC='\033[0m'
ok()   { printf "${GREEN}[OK]${NC}    %s\n" "$1"; }
warn() { printf "${YELLOW}[WARN]${NC}  %s\n" "$1"; }
fail() { printf "${RED}[FAIL]${NC}  %s\n" "$1"; EXIT_CODE=1; }

EXIT_CODE=0
PY=.venv/bin/python

echo "── 1. Environment ─────────────────────────────────────"
if [ -x "$PY" ]; then
  ok "$PY -> $($PY --version 2>&1)"
else
  fail "Missing $PY (create it: python3 -m venv .venv && .venv/bin/pip install -e .)"
fi

echo ""
echo "── 2. Harness files ───────────────────────────────────"
for f in CLAUDE.md AGENTS.md CHECKPOINTS.md progress/current.md odd/tasks; do
  if [ -e "$f" ]; then ok "Exists $f"; else fail "Missing $f"; fi
done
if [ -f CLAUDE.md ]; then
  CLAUDE_LINES=$(wc -l < CLAUDE.md | tr -d ' ')
  if [ "$CLAUDE_LINES" -lt 200 ]; then
    ok "CLAUDE.md has $CLAUDE_LINES lines (< 200)"
  else
    fail "CLAUDE.md has $CLAUDE_LINES lines (must be < 200; move detail to docs/)"
  fi
fi

echo ""
echo "── 3. Tests ───────────────────────────────────────────"
if [ -x "$PY" ] && [ -d tests ]; then
  if $PY -m pytest -q 2>&1 | tail -3; [ "${PIPESTATUS[0]}" -eq 0 ]; then
    ok "All tests pass"
  else
    fail "There are failing tests"
  fi
else
  warn "Tests skipped (no .venv or no tests/)"
fi

echo ""
echo "── 4. Security (optional tools) ───────────────────────"
if command -v gitleaks >/dev/null 2>&1; then
  if gitleaks git --no-banner --redact -l error . >/dev/null 2>&1; then
    ok "gitleaks: no secrets in git history"
  else
    fail "gitleaks found secrets (run: gitleaks git --redact .)"
  fi
else
  warn "gitleaks not installed (brew install gitleaks)"
fi
if [ -x .venv/bin/pip-audit ]; then
  if .venv/bin/pip-audit --skip-editable --progress-spinner off >/dev/null 2>&1; then
    ok "pip-audit: no known vulnerable dependencies"
  else
    fail "pip-audit found vulnerable dependencies (run: .venv/bin/pip-audit)"
  fi
else
  warn "pip-audit not installed (.venv/bin/pip install pip-audit)"
fi

echo ""
echo "── 5. Summary ─────────────────────────────────────────"
if [ $EXIT_CODE -eq 0 ]; then
  ok "Environment ready. You can start working."
else
  printf "${RED}[FAIL]${NC}  Environment NOT ready. Fix the errors above before continuing.\n"
fi
exit $EXIT_CODE
