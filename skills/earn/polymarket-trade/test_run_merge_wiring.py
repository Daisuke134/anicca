#!/usr/bin/env python3
"""Integration tests for the real PM live-pass shell control flow.

The external wallet/SDK boundary is replaced by a tiny executable, while the
real run.sh still owns ordering, exit-code handling, and trace persistence.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


RUN_SH = Path(__file__).with_name("run.sh")
EXPECTED_CALLS = [
    "redeem.py",
    "merge.py",
    "bundle_arb.py",
    "market_maker.py",
    "pick.py",
]


def _build_harness(tmp_path: Path) -> tuple[Path, Path, Path]:
    skill_dir = tmp_path / "earn" / "polymarket-trade"
    skill_dir.mkdir(parents=True)
    run_sh = skill_dir / "run.sh"
    shutil.copy2(RUN_SH, run_sh)

    for name in EXPECTED_CALLS:
        (skill_dir / name).touch()

    agent_home = tmp_path / "agent"
    fake_python = agent_home / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text(
        """#!/bin/bash
set -u
script_name="$(basename "$1")"
printf '%s\\n' "$script_name" >> "$PM_TEST_CALLS"
case "$script_name" in
  redeem.py) echo "redeem-ok" ;;
  merge.py)
    echo "merge-result"
    exit "${PM_TEST_MERGE_RC:-0}"
    ;;
  bundle_arb.py) echo "arb-ok" ;;
  market_maker.py) echo "market-maker-ok" ;;
  pick.py) printf '%s\\n' '{"action":"WAIT","reason":"controlled-test"}' ;;
  *) echo "unexpected script: $script_name" >&2; exit 90 ;;
esac
"""
    )
    fake_python.chmod(0o755)

    calls_file = tmp_path / "calls.txt"
    return run_sh, agent_home, calls_file


def _run_live_pass(tmp_path: Path, merge_rc: int = 0) -> tuple[subprocess.CompletedProcess[str], list[str], list[dict]]:
    run_sh, agent_home, calls_file = _build_harness(tmp_path)
    env = {
        **os.environ,
        "PATH": "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "PM_TRADE_AGENT_HOME": str(agent_home),
        "POLYGON_WALLET_PRIVATE_KEY": "0x" + ("1" * 64),
        "PM_TEST_CALLS": str(calls_file),
        "PM_TEST_MERGE_RC": str(merge_rc),
    }
    result = subprocess.run(
        ["/bin/bash", str(run_sh)],
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
        check=False,
    )
    calls = calls_file.read_text().splitlines()
    trace_file = run_sh.parent.parent / "state" / "pm-trade.trace.jsonl"
    traces = [
        json.loads(line)
        for line in trace_file.read_text().splitlines()
        if line.strip()
    ]
    return result, calls, traces


def test_live_pass_recovers_balanced_positions_before_cash_gated_strategies(tmp_path: Path) -> None:
    """Removing or moving the merge invocation must break the observed call order."""
    result, calls, _ = _run_live_pass(tmp_path)

    assert result.returncode == 0, result.stderr
    assert calls == EXPECTED_CALLS


def test_merge_failure_is_traced_and_does_not_disable_later_strategies(tmp_path: Path) -> None:
    """A temporary merge/RPC failure must not turn the earning pass into a one-way stop."""
    result, calls, traces = _run_live_pass(tmp_path, merge_rc=7)

    assert result.returncode == 0, result.stderr
    assert calls == EXPECTED_CALLS
    assert any(row.get("action") == "merge" and row.get("exit") == 7 for row in traces)
