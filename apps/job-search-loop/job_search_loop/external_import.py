from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .ledger import Ledger
from .summary import write_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("import",))
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--company", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--source-message-id", required=True)
    parser.add_argument("--applied-at", required=True)
    parser.add_argument("--evidence-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parsed = parser.parse_args(argv)
    ledger = Ledger(parsed.ledger)
    try:
        result = ledger.import_external_application(
            company=parsed.company,
            title=parsed.title,
            owner=parsed.owner,
            source=parsed.source,
            source_message_id=parsed.source_message_id,
            applied_at=parsed.applied_at,
            evidence_sha256=parsed.evidence_sha256,
        )
    finally:
        ledger.close()
    receipt = {
        **result,
        "owner": parsed.owner,
        "source": parsed.source,
        "source_message_id": parsed.source_message_id,
        "applied_at": parsed.applied_at,
        "evidence_sha256": parsed.evidence_sha256,
    }
    write_summary(parsed.output, receipt)
    os.chmod(parsed.output, 0o600)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
