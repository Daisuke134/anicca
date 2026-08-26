from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .mercor_work_store import WorkStateStore, WorkStoreError


def sync_bank_snapshot(*, snapshot_path: Path, store_path: Path) -> dict[str, Any]:
    snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    if not isinstance(snapshot, Mapping) or snapshot.get("provider") != "mercor":
        raise WorkStoreError("bank snapshot provider must be mercor")
    rows = snapshot.get("rows")
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], Mapping):
        raise WorkStoreError("bank snapshot must contain exactly one receipt row")
    row = rows[0]
    required = (
        "work_id",
        "payment_id",
        "payout_id",
        "bank_transaction_id",
        "status",
        "amount_usd",
        "evidence_ref",
    )
    if any(not isinstance(row.get(field), str) or not row[field].strip() for field in required):
        raise WorkStoreError("bank receipt has missing identity, amount, status, or evidence")
    if row["status"] != "matched":
        raise WorkStoreError("bank receipt is not matched")

    store = WorkStateStore(store_path)
    bank = store.transition(
        work_id=row["work_id"].strip(),
        event_id=f"bank:{row['bank_transaction_id'].strip()}",
        next_state="bank_matched",
        evidence_ref=row["evidence_ref"].strip(),
        payment_id=row["payment_id"].strip(),
        payout_id=row["payout_id"].strip(),
        bank_transaction_id=row["bank_transaction_id"].strip(),
        match_status="matched",
        amount_usd=row["amount_usd"].strip(),
    )
    store.transition(
        work_id=row["work_id"].strip(),
        event_id=f"revenue:{row['bank_transaction_id'].strip()}",
        next_state="revenue_recorded",
        evidence_ref=bank["evidence_ref"],
    )
    return {"status": "matched", "synced_count": 1}
