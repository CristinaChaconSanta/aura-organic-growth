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
