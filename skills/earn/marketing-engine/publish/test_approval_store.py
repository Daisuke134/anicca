import json
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from approval_store import record_visual_approval


def test_visual_approval_requires_explicit_owner_confirmation_and_is_idempotent(tmp_path):
    asset = tmp_path / "preview.mp4"
    asset.write_bytes(b"preview")
    ledger = tmp_path / "approvals.jsonl"
    with pytest.raises(ValueError, match="explicit owner confirmation required"):
        record_visual_approval(
            ledger_path=ledger, approval_id="visual.accepted.preview", asset_path=asset,
            product_id="ebook-ja", account_id="tiktok.obou_anicca",
            owner_confirmation="", confirmation_ref="telegram:5113",
            approved_at="2026-08-02T00:00:00Z")
    first = record_visual_approval(
        ledger_path=ledger, approval_id="visual.accepted.preview", asset_path=asset,
        product_id="ebook-ja", account_id="tiktok.obou_anicca",
        owner_confirmation="Approve 5113", confirmation_ref="telegram:5123",
        approved_at="2026-08-02T00:00:00Z")
    second = record_visual_approval(
        ledger_path=ledger, approval_id="visual.accepted.preview", asset_path=asset,
        product_id="ebook-ja", account_id="tiktok.obou_anicca",
        owner_confirmation="Approve 5113", confirmation_ref="telegram:5123",
        approved_at="2026-08-02T00:00:00Z")
    assert first["created"] is True
    assert second["created"] is False
    row = json.loads(ledger.read_text().strip())
    assert row["status"] == "accepted"
    assert row["confirmation_ref"] == "telegram:5123"


def test_visual_approval_conflicting_replay_fails(tmp_path):
    asset = tmp_path / "preview.mp4"
    asset.write_bytes(b"preview")
    ledger = tmp_path / "approvals.jsonl"
    args = dict(ledger_path=ledger, approval_id="visual.accepted.preview", asset_path=asset,
                product_id="ebook-ja", account_id="tiktok.obou_anicca",
                owner_confirmation="Approve 5113", confirmation_ref="telegram:5123",
                approved_at="2026-08-02T00:00:00Z")
    record_visual_approval(**args)
    with pytest.raises(ValueError, match="conflicting visual approval replay"):
        record_visual_approval(**(args | {"confirmation_ref": "telegram:other"}))
