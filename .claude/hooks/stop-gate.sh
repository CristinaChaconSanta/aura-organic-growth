#!/usr/bin/env bash
# Stop hook: run init.sh before the agent ends its turn.
# On failure, exit 2 so Claude Code feeds the reason back and the agent keeps working.
# If this hook already blocked once in this turn (stop_hook_active), let it stop to avoid a loop.

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

active=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("stop_hook_active", False))' 2>/dev/null)

if ./init.sh > /tmp/aura_init.log 2>&1; then
  exit 0
fi

if [ "$active" = "True" ]; then
  echo "[harness] init.sh still failing; stopping anyway. See /tmp/aura_init.log" >&2
  exit 0
fi

echo "[harness] init.sh failed. Fix it before finishing:" >&2
grep -E '\[FAIL\]' /tmp/aura_init.log | sed 's/\x1b\[[0-9;]*m//g' >&2
exit 2
