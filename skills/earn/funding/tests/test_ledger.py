import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.ledger import append_ledger, build_row, read_ledger  # noqa: E402


def test_read_ledger_missing_file_returns_empty_list(tmp_path):
    assert read_ledger(str(tmp_path / "nope.jsonl")) == []


def test_build_row_pure_no_mutation_of_extra():
    extra = {"plan": {"a": 1}}
    row = build_row(step="withdraw", amount_usd=1.5, status="sent", extra=extra)
    assert row["step"] == "withdraw"
    assert row["amount_usd"] == 1.5
    assert row["status"] == "sent"
    assert row["plan"] == {"a": 1}
    # calling again with the same `extra` dict must not have mutated it
    assert extra == {"plan": {"a": 1}}


def test_build_row_defaults():
    row = build_row(step="bridge", amount_usd=2.0, status="dry")
    assert row["reason"] == ""
    assert row["tx_hash"] is None
    assert row["from"] is None
    assert row["to"] is None
    assert isinstance(row["ts"], float)


def test_append_and_read_roundtrip(tmp_path):
    path = str(tmp_path / "sub" / "funding-ledger.jsonl")
    row1 = build_row(step="withdraw", amount_usd=1.0, status="sent", tx_hash="0xabc", ts=1.0)
    row2 = build_row(step="bridge", amount_usd=1.0, status="dry", ts=2.0)
    append_ledger(path, row1)
    append_ledger(path, row2)
    rows = read_ledger(path)
    assert len(rows) == 2
    assert rows[0]["tx_hash"] == "0xabc"
    assert rows[1]["step"] == "bridge"


def test_append_ledger_creates_parent_dirs(tmp_path):
    path = str(tmp_path / "a" / "b" / "c" / "funding-ledger.jsonl")
    append_ledger(path, build_row(step="withdraw", amount_usd=1.0, status="sent"))
    assert os.path.exists(path)
