import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
STOP_GATE = REPO / ".claude" / "hooks" / "stop-gate.sh"


@pytest.fixture
def failing_repo(tmp_path):
    """A repo copy whose init.sh always fails, so only the loop guard decides the exit code."""
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(STOP_GATE, hooks / "stop-gate.sh")
    init = tmp_path / "init.sh"
    init.write_text("#!/usr/bin/env bash\necho '[FAIL]  probe'\nexit 1\n")
    init.chmod(0o755)
    return tmp_path


def run_gate(repo: Path, stdin: str) -> int:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(repo)}
    return subprocess.run(
        ["bash", str(repo / ".claude" / "hooks" / "stop-gate.sh")],
        input=stdin, text=True, capture_output=True, env=env,
    ).returncode


def test_blocks_once_when_flag_is_false(failing_repo):
    assert run_gate(failing_repo, '{"stop_hook_active": false}') == 2


@pytest.mark.parametrize("stdin", [
    '{"stop_hook_active": true}',
    "",
    "not json",
    "{}",
])
def test_never_blocks_when_flag_is_true_missing_or_unreadable(failing_repo, stdin):
    assert run_gate(failing_repo, stdin) == 0


CURSOR_GATE = REPO / ".cursor" / "hooks" / "stop-gate.sh"


def make_cursor_repo(tmp_path: Path, init_exit: int) -> Path:
    hooks = tmp_path / ".cursor" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(CURSOR_GATE, hooks / "stop-gate.sh")
    init = tmp_path / "init.sh"
    init.write_text(f"#!/usr/bin/env bash\necho '[FAIL]  probe'\nexit {init_exit}\n")
    init.chmod(0o755)
    return tmp_path


def run_cursor_gate(repo: Path, stdin: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "CURSOR_PROJECT_DIR": str(repo)}
    return subprocess.run(
        ["bash", str(repo / ".cursor" / "hooks" / "stop-gate.sh")],
        input=stdin, text=True, capture_output=True, env=env,
    )


def test_cursor_gate_sends_followup_when_init_fails(tmp_path):
    result = run_cursor_gate(make_cursor_repo(tmp_path, 1), '{"status": "completed", "loop_count": 0}')
    assert result.returncode == 0
    assert "probe" in json.loads(result.stdout)["followup_message"]


@pytest.mark.parametrize("stdin", [
    '{"status": "completed", "loop_count": 2}',
    '{"status": "aborted", "loop_count": 0}',
    '{"status": "error", "loop_count": 0}',
    "",
    "not json",
    "{}",
])
def test_cursor_gate_stays_silent_on_loop_limit_abort_or_bad_input(tmp_path, stdin):
    result = run_cursor_gate(make_cursor_repo(tmp_path, 1), stdin)
    assert result.returncode == 0
    assert result.stdout == ""


def test_cursor_gate_stays_silent_when_init_passes(tmp_path):
    result = run_cursor_gate(make_cursor_repo(tmp_path, 0), '{"status": "completed", "loop_count": 0}')
    assert result.stdout == ""
