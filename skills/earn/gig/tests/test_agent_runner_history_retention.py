from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


RUNNER_DIR = Path(__file__).resolve().parents[4] / "runtime/agent-runner"
sys.path.insert(0, str(RUNNER_DIR))
SPEC = importlib.util.spec_from_file_location("gig_agent_runner_history_test", RUNNER_DIR / "agent_runner.py")
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_prune_history_keeps_only_newest_generations(tmp_path: Path) -> None:
    history = tmp_path / "history"
    history.mkdir()
    names = [
        "20260820T000000000000Z-oldest",
        "20260821T000000000000Z-old",
        "20260822T000000000000Z-middle",
        "20260823T000000000000Z-new",
        "20260824T000000000000Z-newest",
    ]
    for name in names:
        generation = history / name
        generation.mkdir()
        (generation / "attempt-01.stdout.log").write_bytes(b"x" * 16)

    result = runner.prune_history_generations(history, keep=3)

    assert sorted(path.name for path in history.iterdir()) == names[-3:]
    assert result == {"removed": 2, "bytes_reclaimed": 32, "errors": 0}


def test_prune_history_never_removes_loose_or_latest_files(tmp_path: Path) -> None:
    history = tmp_path / "history"
    history.mkdir()
    (history / "receipt.jsonl").write_text("{}\n", encoding="utf-8")
    for name in ("20260823T000000000000Z-old", "20260824T000000000000Z-new"):
        (history / name).mkdir()

    result = runner.prune_history_generations(history, keep=1)

    assert (history / "receipt.jsonl").is_file()
    assert (history / "20260824T000000000000Z-new").is_dir()
    assert result["removed"] == 1
