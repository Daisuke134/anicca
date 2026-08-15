from __future__ import annotations

import fcntl
import os

import pytest


# Why applied.jsonl stayed empty even when applications landed.
#
# The ledger writer opens the file with os.fdopen(fd, "a") and then iterates it to check
# whether this request was already recorded. Append mode is write-only, so the iteration
# raises UnsupportedOperation: not readable — after the submit has already happened on
# Coconala. The application exists on the site and no row exists locally.
#
# It only became visible once the submit was recognised as landed; before that the pass died
# earlier and never reached the ledger. One bug was hiding behind another.


def test_append_mode_cannot_be_read_back(tmp_path) -> None:
    path = tmp_path / "applied.jsonl"
    path.write_text('{"request_id": "1"}\n', encoding="utf-8")
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        with pytest.raises(Exception):
            for _ in handle:
                pass


def test_append_plus_can_read_and_append(tmp_path) -> None:
    # a+ keeps the append semantics that make the write atomic under the lock, and can also
    # be read, which is what the duplicate check needs.
    path = tmp_path / "applied.jsonl"
    path.write_text('{"request_id": "1"}\n', encoding="utf-8")
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        assert [line.strip() for line in handle] == ['{"request_id": "1"}']
        handle.write('{"request_id": "2"}\n')
    assert path.read_text(encoding="utf-8").count("request_id") == 2


def test_the_ledger_writer_uses_a_readable_mode() -> None:
    # Guards the actual source: the duplicate check only works if the handle can be read.
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "scripts" / "application_parent.py").read_text(
        encoding="utf-8"
    )
    assert 'os.fdopen(descriptor, "a", encoding="utf-8")' not in source
    assert 'os.fdopen(descriptor, "a+", encoding="utf-8")' in source
