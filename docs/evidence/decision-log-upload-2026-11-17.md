# Decision upload G6 / R3 — 2026-11-17

Branch: codex/decision-log-upload. No push or production changes.
Assignment overrides inherited Life Manager origin/branch requirements.
Read: delegation, audit R2/R3/G6, using-superpowers (delegated task exemption).
Astra Advisor not exposed in this harness.

Existing authenticated Manager request pattern reused. Flush is asynchronous, with disk scanning and
ACK persistence off main actor. Probability is serialized unchanged. ManagerBenchCase fields remain;
provenance and candidate IDs are additive. Local/unknown assignments are flagged fallback.
Model decisions already persist via /manager/decisions. New endpoint accepts cases and events.
Durable upload journal preserves revisions. Matching ACK suppresses retries; server locks and fsyncs
JSONL before ACK. Replay is deduplicated by subject and record ID; conflicting content is rejected.

Verification: /tmp/decision-upload-venv/bin/python -m unittest models.manager.product.tests.test_decision_upload
and git diff --check.

Offline uses actual refused TCP; online uses FastAPI TestClient against the actual router/store.
Synthetic client reloads its disk queue and replays lost ACK; store contains exactly one matching row.
Concurrent replay (20 requests/8 workers), fallback normalization, invalid probability and six reaction
kinds also pass. This does not execute the Swift uploader. Swift/Xcode unavailable: native build,
foreground retry and UI latency remain unverified; integration owner must run macOS checks.
No claim of production deployment or real intervention cases collected.

Documentation discrepancies: on-device-only recorder comment updated; team life-manager/push rules
superseded by assignment. No credentials used; all evidence identifiers are synthetic.

## Transcript

/tmp/decision-upload-venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
..
----------------------------------------------------------------------
Ran 2 tests in 0.373s

OK
OFFLINE: connection refused; durable queue retained
ONLINE: HTTP 200 twice, matching ACK; store lines=1
STORE: {"backend": "local_rule", "candidate_ids": ["fixture-item"], "decision_point_at": "2026-11-17T00:00:00Z", "delivery_id": "simulated-delivery-001", "fallback": true, "person_id": "5d2ddfcbbb83b835f7c8f3d8ebf9993e89eaed52684472fa7d93f80943e9dd21", "record_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "stimulus": {"assigned_probability": 0.125, "message_id": "fixture-item", "policy_version": "fixture-v1"}}
