import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "coconala_outcomes.py"
SPEC = importlib.util.spec_from_file_location("coconala_outcomes", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _delivery_receipt(root: Path, payload: dict) -> dict:
    evidence = root / "evidence" / "paid-direct-live"
    evidence.mkdir(parents=True)
    (evidence / "latest.json").write_text(json.dumps(payload), encoding="utf-8")
    return next(row for row in MODULE.outcomes(root)["receipts"] if row["receipt_id"] == "delivery")


def test_initial_verified_delivery_counts_without_deduplication(tmp_path):
    receipt = _delivery_receipt(tmp_path, {
        "readback": 1,
        "items": [{
            "status": "completed",
            "send_performed": True,
            "deduplicated": False,
        }],
    })

    assert receipt["state"] == "proven"
    assert receipt["verified_count"] == 1


def test_failed_or_unverified_delivery_does_not_count(tmp_path):
    receipt = _delivery_receipt(tmp_path, {
        "readback": 0,
        "items": [
            {"status": "failed", "send_performed": True, "deduplicated": False},
            {"status": "completed", "send_performed": False, "deduplicated": False},
        ],
    })

    assert receipt["state"] == "waiting"
    assert receipt["verified_count"] == 0


def test_verified_replay_deduplication_still_counts(tmp_path):
    receipt = _delivery_receipt(tmp_path, {
        "readback": 1,
        "items": [{
            "status": "completed",
            "send_performed": False,
            "deduplicated": True,
        }],
    })

    assert receipt["state"] == "proven"
    assert receipt["verified_count"] == 1
