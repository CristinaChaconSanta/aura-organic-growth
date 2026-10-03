#!/usr/bin/env bash
# PostToolUse hook: run the test suite after every Edit/Write.
# On failure, exit 2 so Claude Code shows the failing tests to the agent right away.

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

out=$(.venv/bin/python -m pytest -q -x 2>&1)
if [ $? -eq 0 ]; then
  exit 0
fi

echo "[harness] Tests fail after this edit:" >&2
echo "$out" | tail -15 >&2
exit 2
