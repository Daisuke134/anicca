from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "resume_failure_circuit.py"


def invoke(*args: object) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_same_failure_opens_once_and_code_change_rearms(tmp_path: Path) -> None:
    """A deterministic pair failure stops retries until its executable context changes."""
    circuit = tmp_path / "circuit.json"
    state = tmp_path / "publication-state.json"
    code = tmp_path / "publisher.py"
    dependency = tmp_path / "eyecatch.py"
    error = tmp_path / "error.txt"
    state.write_text('{"pairs":{"note/ja":{"status":"intent"}}}\n')
    code.write_text("version = 1\n")
    dependency.write_text("selector = 1\n")
    error.write_text("TimeoutError: upload button is absent\n")
    common = (
        "--circuit",
        circuit,
        "--state",
        state,
        "--code-file",
        code,
        "--code-file",
        dependency,
        "--pair",
        "note/ja",
    )

    assert invoke("check", *common) == {
        "action": "run",
        "pair": "note/ja",
        "reason": "no-failure",
    }
    assert invoke(
        "failure", *common, "--error-file", error, "--threshold", 2
    ) == {
        "action": "retry",
        "count": 1,
        "notify": False,
        "pair": "note/ja",
        "signature": "TimeoutError: upload button is absent",
    }
    assert invoke(
        "failure", *common, "--error-file", error, "--threshold", 2
    ) == {
        "action": "open",
        "count": 2,
        "notify": True,
        "pair": "note/ja",
        "signature": "TimeoutError: upload button is absent",
    }
    assert invoke("check", *common) == {
        "action": "block",
        "count": 2,
        "notify": False,
        "pair": "note/ja",
        "reason": "same-failure-circuit-open",
        "signature": "TimeoutError: upload button is absent",
    }

    code.write_text("version = 2\n")
    assert invoke("check", *common) == {
        "action": "run",
        "pair": "note/ja",
        "reason": "execution-context-changed",
    }


def test_success_clears_failure_history(tmp_path: Path) -> None:
    """A verified successful execution closes only the selected pair circuit."""
    circuit = tmp_path / "circuit.json"
    state = tmp_path / "publication-state.json"
    code = tmp_path / "publisher.py"
    error = tmp_path / "error.txt"
    state.write_text('{"pairs":{"note/ja":{"status":"intent"}}}\n')
    code.write_text("version = 1\n")
    error.write_text("TimeoutError: deterministic\n")
    common = (
        "--circuit",
        circuit,
        "--state",
        state,
        "--code-file",
        code,
        "--pair",
        "note/ja",
    )
    invoke("failure", *common, "--error-file", error, "--threshold", 1)

    assert invoke("success", *common) == {
        "action": "closed",
        "pair": "note/ja",
    }
    assert invoke("check", *common) == {
        "action": "run",
        "pair": "note/ja",
        "reason": "no-failure",
    }


def test_run_stops_identical_command_failure_and_notifies_once(tmp_path: Path) -> None:
    """The guarded runner executes twice, opens, then suppresses an unchanged third run."""
    circuit = tmp_path / "circuit.json"
    state = tmp_path / "publication-state.json"
    code = tmp_path / "publisher.py"
    log = tmp_path / "resume.log"
    calls = tmp_path / "calls"
    notifications = tmp_path / "notifications"
    command = tmp_path / "fail"
    notifier = tmp_path / "notify"
    state.write_text('{"pairs":{"note/ja":{"status":"intent"}}}\n')
    code.write_text("version = 1\n")
    command.write_text(
        "#!/usr/bin/env bash\n"
        "echo call >>\"$CALLS\"\n"
        "echo 'TimeoutError: upload button is absent' >&2\n"
        "exit 7\n"
    )
    notifier.write_text(
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$1\" >>\"$NOTIFICATIONS\"\n"
    )
    command.chmod(0o755)
    notifier.chmod(0o755)
    common = [
        sys.executable,
        str(SCRIPT),
        "run",
        "--circuit",
        str(circuit),
        "--state",
        str(state),
        "--code-file",
        str(code),
        "--pair",
        "note/ja",
        "--threshold",
        "2",
        "--log",
        str(log),
        "--notify-command",
        str(notifier),
        "--",
        str(command),
    ]
    env = {**os.environ, "CALLS": str(calls), "NOTIFICATIONS": str(notifications)}

    first = subprocess.run(common, env=env, check=False)
    second = subprocess.run(common, env=env, check=False)
    third = subprocess.run(common, env=env, check=False)

    assert first.returncode == 7
    assert second.returncode == 0
    assert third.returncode == 0
    assert calls.read_text().splitlines() == ["call", "call"]
    messages = notifications.read_text().splitlines()
    assert len(messages) == 1
    assert "note/ja" in messages[0]
    assert "TimeoutError: upload button is absent" in messages[0]
    assert "same-failure-circuit-open" in log.read_text()


def test_run_bounds_a_hung_publisher_and_records_timeout(tmp_path: Path) -> None:
    """A publisher that never returns cannot occupy the resume worker forever."""
    circuit = tmp_path / "circuit.json"
    state = tmp_path / "publication-state.json"
    code = tmp_path / "publisher.py"
    log = tmp_path / "resume.log"
    command = tmp_path / "hang"
    state.write_text('{"pairs":{"note/ja":{"status":"intent"}}}\n')
    code.write_text("version = 1\n")
    command.write_text("#!/usr/bin/env bash\nsleep 30\n")
    command.chmod(0o755)
    argv = [
        sys.executable,
        str(SCRIPT),
        "run",
        "--circuit",
        str(circuit),
        "--state",
        str(state),
        "--code-file",
        str(code),
        "--pair",
        "note/ja",
        "--threshold",
        "2",
        "--timeout-seconds",
        "0.1",
        "--log",
        str(log),
        "--",
        str(command),
    ]

    started = time.monotonic()
    completed = subprocess.run(argv, text=True, capture_output=True, check=False)
    elapsed = time.monotonic() - started

    assert completed.returncode == 124
    assert elapsed < 2
    decision = json.loads(completed.stdout)
    assert decision == {
        "action": "retry",
        "count": 1,
        "notify": False,
        "pair": "note/ja",
        "signature": "publisher-timeout-seconds=0.1",
    }
    assert "publisher-timeout-seconds=0.1" in log.read_text()
