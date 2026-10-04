#!/usr/bin/env bash
# Cursor stop hook: run init.sh when the agent finishes a turn.
# Cursor stop hooks cannot block; on failure this returns a followup_message that Cursor
# submits as the next user message so the agent fixes the problem.
# It stays silent when the turn was aborted or errored, when loop_count >= 2, or when
# stdin is missing or unreadable, so a broken input can never cause an endless loop.

cd "${CURSOR_PROJECT_DIR:-$(dirname "$0")/../..}"

# Must match "loop_limit" in .cursor/hooks.json. Cursor enforces that limit; this copy is a
# second guard in case Cursor ignores it. Change both together.
MAX_FOLLOWUPS=2

read -r status loop_count < <(python3 -c '
import json, sys
d = json.load(sys.stdin)
print(d["status"], int(d["loop_count"]))
' 2>/dev/null)

[ "$status" = "completed" ] || exit 0
[ -n "$loop_count" ] && [ "$loop_count" -lt "$MAX_FOLLOWUPS" ] || exit 0

log="${TMPDIR:-/tmp}/cursor_init_$$.log"
trap 'rm -f "$log"' EXIT

if ./init.sh > "$log" 2>&1; then
  exit 0
fi

fails=$(grep -E '\[FAIL\]' "$log" | sed 's/\x1b\[[0-9;]*m//g')
python3 -c '
import json, sys
msg = "init.sh falló al cerrar el turno. Corrige esto antes de dar la tarea por terminada:\n" + sys.argv[1]
print(json.dumps({"followup_message": msg}))
' "$fails"
