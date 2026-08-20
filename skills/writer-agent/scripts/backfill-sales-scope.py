#!/usr/bin/env python3
"""backfill-sales-scope.py — stamp `scope` (+ artifact key where derivable) onto sales rows.

`state/sales-ledger.jsonl` is append-only runtime data, so the rewrite is defensive:

  1. copy the file to `<name>.<UTC timestamp>.bak` FIRST,
  2. rewrite into a sibling temp file and `os.replace()` it in (atomic on the same fs),
  3. assert the row count is unchanged; if it is not, restore from the backup and fail.

Only `scope`, `scope_reason`, `artifact_id`, `artifact_known` and `rejected_artifact_id` are
added. No existing field is edited or removed. A row whose `source_url` names no single
published article stays account-scoped — that is a correct outcome, not a gap.

CLI:
    backfill-sales-scope.py [--state-dir <dir>] [--dry-run]
stdout: one JSON summary. Logs go to stderr.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "article_artifact_attribution", _HERE / "artifact_attribution.py"
)
attribution = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(attribution)

DEFAULT_STATE_DIR = Path(
    os.environ.get(
        "WRITER_STATE_DIR",
        os.path.expanduser("~/profitable-claude/skills/writer-agent/state"),
    )
)


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    state = Path(args.state_dir)
    ledger = state / "sales-ledger.jsonl"
    if not ledger.exists():
        print(f"[backfill] no sales ledger at {ledger}", file=sys.stderr)
        return 1

    rows = read_jsonl(ledger)
    index = attribution.build_artifact_index(read_jsonl(state / "articles.jsonl"))
    scoped = [attribution.classify_sales_row(row, index) for row in rows]
    counts = Counter(row["scope"] for row in scoped)
    summary = {
        "ledger": str(ledger),
        "rows_before": len(rows),
        "rows_after": len(scoped),
        "scope_counts": dict(counts),
        "artifact_ids": sorted(
            {row["artifact_id"] for row in scoped if row.get("artifact_id")}
        ),
        "dry_run": args.dry_run,
        "backup": None,
    }

    if args.dry_run:
        json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = ledger.with_name(f"{ledger.name}.{stamp}.bak")
    shutil.copy2(ledger, backup)
    print(f"[backfill] backed up {len(rows)} rows to {backup}", file=sys.stderr)
    summary["backup"] = str(backup)

    tmp = ledger.with_name(f"{ledger.name}.{stamp}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for row in scoped:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(tmp, ledger)

    written = len(read_jsonl(ledger))
    if written != len(rows):
        shutil.copy2(backup, ledger)
        print(
            f"[backfill] row count changed ({len(rows)} -> {written}); restored backup",
            file=sys.stderr,
        )
        return 1
    summary["rows_after"] = written
    print(f"[backfill] rewrote {written} rows, count preserved", file=sys.stderr)
    json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
