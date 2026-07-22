"""Regression tests for one-shot reality-verifier claim collection."""
import json
import os
import sys
import tempfile

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
GIG_SKILL_DIR = os.path.dirname(TESTS_DIR)
SCRIPTS_DIR = os.path.join(GIG_SKILL_DIR, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import gig_reality_claims  # noqa: E402


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_legacy_completed_audit_consumes_already_judged_claims():
    with tempfile.TemporaryDirectory() as tmp:
        write_jsonl(
            os.path.join(tmp, "shuppin.jsonl"),
            [{"service_id": "4312985", "status": "confirmed_live", "ts": 100}],
        )
        write_jsonl(
            os.path.join(tmp, "audit-reality.jsonl"),
            [{"ts": 200, "verdict": False, "claims_checked": 1, "evidence_captured": 4, "evidence_required": 4}],
        )

        claims, watermark = gig_reality_claims.collect_claims(tmp, 5)

        assert claims == []
        assert watermark == 200


def test_only_newer_claims_are_collected_and_latest_entity_wins():
    with tempfile.TemporaryDirectory() as tmp:
        write_jsonl(
            os.path.join(tmp, "shuppin.jsonl"),
            [
                {"service_id": "old", "status": "old", "ts": 100},
                {"service_id": "new", "status": "first", "ts": 201},
                {"service_id": "new", "status": "latest", "ts": 202},
                {"requestId": "N/A", "status": "summary", "ts": 203},
            ],
        )
        write_jsonl(
            os.path.join(tmp, "applied.jsonl"),
            [{"requestId": "5166000", "status": "applied", "ts": 204}],
        )
        write_jsonl(
            os.path.join(tmp, "audit-reality.jsonl"),
            [{"ts": 200, "verdict": True, "claims_checked": 1, "evidence_captured": 4, "evidence_required": 4}],
        )

        claims, watermark = gig_reality_claims.collect_claims(tmp, 5)

        assert watermark == 200
        assert [(c["kind"], c.get("service_id") or c.get("requestId"), c["ts"]) for c in claims] == [
            ("shuppin", "new", 202),
            ("applied", "5166000", 204),
        ]


def test_explicit_claims_through_ts_beats_later_infra_audit_timestamp():
    with tempfile.TemporaryDirectory() as tmp:
        write_jsonl(
            os.path.join(tmp, "shuppin.jsonl"),
            [{"service_id": "retry-me", "status": "confirmed_live", "ts": 250}],
        )
        write_jsonl(
            os.path.join(tmp, "audit-reality.jsonl"),
            [
                {"ts": 200, "verdict": True, "claims_checked": 1, "claims_through_ts": 200},
                {"ts": 300, "verdict": False, "failure_reason": "cdp_down", "claims_checked": 1},
            ],
        )

        claims, watermark = gig_reality_claims.collect_claims(tmp, 5)

        assert watermark == 200
        assert len(claims) == 1
        assert claims[0]["service_id"] == "retry-me"


if __name__ == "__main__":
    test_legacy_completed_audit_consumes_already_judged_claims()
    test_only_newer_claims_are_collected_and_latest_entity_wins()
    test_explicit_claims_through_ts_beats_later_infra_audit_timestamp()
    print("3 passed")
