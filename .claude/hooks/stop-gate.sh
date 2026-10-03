#!/usr/bin/env bash
# Stop hook: run init.sh before the agent ends its turn.
# On failure, exit 2 so Claude Code feeds the reason back and the agent keeps working.
# It blocks only when stdin explicitly says stop_hook_active is false. If the flag is true,
# missing, or unreadable (no python3, empty or malformed stdin), it lets the agent stop,
# so a broken input can never cause an endless block-and-retry loop.

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

active=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["stop_hook_active"])' 2>/dev/null)

if ./init.sh > /tmp/aura_init.log 2>&1; then
  exit 0
fi

if [ "$active" != "False" ]; then
  echo "[harness] init.sh still failing; stopping anyway. See /tmp/aura_init.log" >&2
  exit 0
fi

echo "[harness] init.sh failed. Fix it before finishing:" >&2
grep -E '\[FAIL\]' /tmp/aura_init.log | sed 's/\x1b\[[0-9;]*m//g' >&2
exit 2
