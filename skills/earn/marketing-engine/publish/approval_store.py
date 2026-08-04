#!/usr/bin/env python3
"""Durable, idempotent owner visual approvals."""

from __future__ import annotations

import json
import os
import pathlib
import tempfile

from intent_store import _epoch, file_sha256


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def record_visual_approval(*, ledger_path: pathlib.Path, approval_id: str,
                           asset_path: pathlib.Path, product_id: str,
                           account_id: str, owner_confirmation: str,
                           confirmation_ref: str, approved_at: str) -> dict:
    require(approval_id.startswith("visual.accepted."), "accepted approval ID required")
    require(bool(owner_confirmation.strip()), "explicit owner confirmation required")
    require(bool(confirmation_ref.strip()), "owner confirmation reference required")
    _epoch(approved_at)
    asset = pathlib.Path(asset_path).resolve()
    require(asset.is_file(), "visual approval asset missing")
    row = {
        "schema_version": "marketing.visual-approval.v1",
        "approval_id": approval_id,
        "status": "accepted",
        "asset_path": str(asset),
        "asset_sha256": file_sha256(asset),
        "product_id": product_id,
        "account_id": account_id,
        "owner_confirmation": owner_confirmation.strip(),
        "confirmation_ref": confirmation_ref.strip(),
        "approved_at": approved_at,
    }
    path = pathlib.Path(ledger_path)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()] if path.is_file() else []
    for existing in rows:
        if existing.get("approval_id") == approval_id:
            require(existing == row, "conflicting visual approval replay")
            return {"created": False, "approval": row}
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n"
                      for item in rows + [row])
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"created": True, "approval": row}
