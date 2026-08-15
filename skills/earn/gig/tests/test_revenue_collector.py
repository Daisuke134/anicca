import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import revenue_collector as collector


def test_existing_earning_payout_state_is_reconciled(tmp_path: Path, monkeypatch):
    ledger = tmp_path / "earnings.jsonl"
    ledger.write_text(json.dumps({
        "requestId": "90000010",
        "idem_key": "coconala:revenue:90000010:2026/07/26 14:24",
        "payout_requested": False,
    }) + "\n", encoding="utf-8")
    monkeypatch.setattr(collector, "EARNINGS", ledger)

    parsed = {"rows": [{
        "talkroom_id": "90000010",
        "closed_at": "2026/07/26 14:24",
        "buyer": "buyer_handle_c",
        "title": "sale",
        "jpy": 13260,
        "payout_requested": True,
    }]}
    assert collector.append_new(parsed, "https://coconala.com/mypage/revenue") == []
    saved = json.loads(ledger.read_text(encoding="utf-8"))
    assert saved["payout_requested"] is True
    assert saved["payout_state_source"] == "https://coconala.com/mypage/revenue"
    assert isinstance(saved["payout_state_observed_at"], int)


def test_existing_earning_refreshes_observation_timestamp_without_state_change(tmp_path: Path, monkeypatch):
    ledger = tmp_path / "earnings.jsonl"
    ledger.write_text(json.dumps({
        "requestId": "90000010",
        "idem_key": "coconala:revenue:90000010:2026/07/26 14:24",
        "payout_requested": True,
        "payout_state_source": "https://coconala.com/mypage/revenue",
        "payout_state_observed_at": 1,
    }) + "\n", encoding="utf-8")
    monkeypatch.setattr(collector, "EARNINGS", ledger)

    collector.append_new({"rows": [{
        "talkroom_id": "90000010",
        "closed_at": "2026/07/26 14:24",
        "payout_requested": True,
    }]}, "https://coconala.com/mypage/revenue")
    saved = json.loads(ledger.read_text(encoding="utf-8"))
    assert saved["payout_requested"] is True
    assert saved["payout_state_observed_at"] > 1


def test_dry_run_does_not_mutate_existing_state(tmp_path: Path, monkeypatch):
    ledger = tmp_path / "earnings.jsonl"
    original = json.dumps({
        "idem_key": "coconala:revenue:1:2026/01/01 00:00",
        "payout_requested": False,
    }) + "\n"
    ledger.write_text(original, encoding="utf-8")
    monkeypatch.setattr(collector, "EARNINGS", ledger)

    collector.append_new({"rows": [{
        "talkroom_id": "1",
        "closed_at": "2026/01/01 00:00",
        "payout_requested": True,
    }]}, "live", dry_run=True)
    assert ledger.read_text(encoding="utf-8") == original
