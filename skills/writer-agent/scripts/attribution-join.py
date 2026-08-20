#!/usr/bin/env python3
"""attribution-join.py — per artifact: publish identity -> engagement -> attributable revenue.

Reads the real runtime ledgers under `state/` (articles.jsonl, funnel.jsonl, own-metrics.jsonl,
sales-ledger.jsonl) and prints ONE JSON document on stdout. Every log line goes to stderr, so
the stdout stream stays machine-consumable (same discipline as the loop's other JSON scripts).

Nothing is measured or published here: this is a pure read-side join over ledgers that other
scripts wrote. Unmeasured revenue stays "unknown" — it is never turned into 0.

CLI:
    attribution-join.py [--state-dir <dir>] [--artifact-id <id>]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
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
        "ARTICLE_STATE_DIR",
        os.environ.get("WRITER_STATE_DIR", Path(__file__).resolve().parents[1] / "state"),
    )
)


def read_jsonl(path: Path) -> list[dict]:
    """Skip unparseable lines loudly on stderr rather than dropping them silently."""
    if not path.exists():
        print(f"[attribution-join] missing ledger: {path}", file=sys.stderr)
        return []
    rows = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print(
                f"[attribution-join] {path.name}:{lineno} unparseable: {exc}",
                file=sys.stderr,
            )
    print(f"[attribution-join] {path.name}: {len(rows)} rows", file=sys.stderr)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR))
    parser.add_argument(
        "--artifact-id", help="restrict the artifacts array to one attribution key"
    )
    args = parser.parse_args(argv)

    state = Path(args.state_dir)
    report = attribution.join_revenue(
        articles=read_jsonl(state / "articles.jsonl"),
        funnel=read_jsonl(state / "funnel.jsonl"),
        own_metrics=read_jsonl(state / "own-metrics.jsonl"),
        sales=read_jsonl(state / "sales-ledger.jsonl"),
    )
    if args.artifact_id:
        report["artifacts"] = [
            a for a in report["artifacts"] if a["artifact_id"] == args.artifact_id
        ]
    report["state_dir"] = str(state)
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
