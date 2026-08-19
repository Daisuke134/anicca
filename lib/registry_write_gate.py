#!/usr/bin/env python3
"""registry_write_gate.py — REQ-CEO-008 shared write-gate primitives: an atomic (write-to-temp +
rename) registry writer and an append-only JSONL writer. Reused by bin/ceo_run.py (--apply-decision)
and lib/ceo_budget.py (hard-budget-breach pause), so both write paths share ONE tmp+rename
implementation (REQ-CEO-013's "same write-gate path as REQ-CEO-008").

Pure I/O helpers only -- no judgment, no registry-shape validation (that lives in the callers).
"""
import json
import os
import tempfile


def atomic_write_registry(path, data):
    """Writes `data` to `path` via write-to-temp-file + os.replace (atomic rename on POSIX).
    Raises on any failure (e.g. a read-only containing directory) WITHOUT ever touching the
    original file -- the temp file is created fresh in the same directory and only replaces the
    original once the write+flush fully succeeds."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".loop-registry-", suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def append_jsonl(path, row):
    """Appends ONE newline-terminated JSON line to `path` (creating parent dirs + the file if
    absent). Never rewrites existing lines (REQ-CEO-005 append-only convention)."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
