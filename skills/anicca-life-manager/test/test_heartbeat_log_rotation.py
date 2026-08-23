from __future__ import annotations

import gzip
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import lateness_check as lc  # noqa: E402


def test_oversized_heartbeat_log_is_archived_without_data_loss(tmp_path: Path, monkeypatch) -> None:
    ledger = tmp_path / "heartbeat_log.jsonl"
    original = '{"event":1}\n{"event":2}\n'
    ledger.write_text(original, encoding="utf-8")
    monkeypatch.setattr(lc, "HEARTBEAT_LOG_MAX_BYTES", 1)

    lc._rotate_heartbeat_log_if_needed(ledger)

    archives = sorted(tmp_path.glob("heartbeat_log.*.jsonl.gz"))
    assert len(archives) == 1
    assert gzip.open(archives[0], "rt", encoding="utf-8").read() == original
    assert ledger.exists()
    assert ledger.read_text(encoding="utf-8") == ""


def test_orphan_rotating_heartbeat_log_is_restored_before_new_writes(tmp_path: Path) -> None:
    ledger = tmp_path / "heartbeat_log.jsonl"
    orphan = tmp_path / ".heartbeat_log.jsonl.crashed.rotating"
    original = '{"event":"orphan"}\n'
    orphan.write_text(original, encoding="utf-8")

    lc._rotate_heartbeat_log_if_needed(ledger)

    assert ledger.read_text(encoding="utf-8") == original
    assert not orphan.exists()
