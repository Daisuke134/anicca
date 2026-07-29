import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import gig_context_packet


def test_paid_work_packet_is_stable_allowlisted_and_bounded():
    item = {
        "request_id": "req-42",
        "talkroom_id": "room-42",
        "contract_id": "contract-42",
        "queue_class": "buyer_feedback_or_revision",
        "delivery_date": "2026-08-01",
        "talkroom_state": "取引中",
        "buyer_feedback_sha256": "a" * 64,
        "buyer_feedback_requirements_path": "/project/requirements/live-buyer-reply.json",
        "buyer_feedback_pending_artifact": True,
        "buyer_reply_after_artifact_observed": True,
        "delivery_action": "progress",
        "blockers": ["formal_delivery_not_confirmed"],
        "buyer": "secret@example.com",
        "title": "must not enter model context",
        "messages": [{"text": "x" * 100_000}] * 100,
        "delivery_evidence": {
            "present": True,
            "status": "ok",
            "artifact_version": "v7",
            "acceptance_status": "PASS",
            "package_sha256": "b" * 64,
            "acceptance_delta": ["y" * 10_000] * 100,
            "artifact_path": "/secret/customer/artifact.zip",
        },
    }

    first = gig_context_packet.paid_work_packet(item)
    second = gig_context_packet.paid_work_packet(item)
    encoded = gig_context_packet.serialize_packet(first)

    assert first == second
    assert len(encoded) == first["metrics"]["byte_count"]
    assert first["metrics"]["byte_count"] <= 8192
    assert first["metrics"]["conservative_token_ceiling"] <= 8192
    assert set(first["fields"]) == {
        "request_id",
        "talkroom_id",
        "contract_id",
        "queue_class",
        "delivery_date",
        "talkroom_state",
        "buyer_feedback_sha256",
        "buyer_feedback_requirements_path",
        "buyer_feedback_pending_artifact",
        "buyer_reply_after_artifact_observed",
        "delivery_action",
        "blockers",
        "delivery_evidence",
    }
    assert set(first["fields"]["delivery_evidence"]) == {
        "present",
        "status",
        "artifact_version",
        "acceptance_status",
        "package_sha256",
        "acceptance_delta",
    }
    assert len(first["fields"]["delivery_evidence"]["acceptance_delta"]) == 8
    assert "secret@example.com" not in encoded.decode()
    assert "must not enter model context" not in encoded.decode()
    assert "artifact_path" not in encoded.decode()


def test_packet_serialization_round_trips_with_exact_metrics():
    packet = gig_context_packet.paid_work_packet({
        "request_id": "req-1",
        "queue_class": "buyer_feedback_or_revision",
        "buyer_feedback_sha256": "c" * 64,
    })
    encoded = gig_context_packet.serialize_packet(packet)

    assert json.loads(encoded) == packet
    assert len(encoded) == packet["metrics"]["byte_count"]


def test_delivery_packet_uses_the_same_allowlist_without_raw_history():
    item = {
        "request_id": "req-delivery",
        "talkroom_id": "room-delivery",
        "delivery_action": "formal",
        "messages": [{"body": "private-history"}] * 1_000,
        "delivery_evidence": {
            "present": True,
            "status": "ok",
            "artifact_version": "v9",
            "acceptance_status": "PASS",
            "package_sha256": "d" * 64,
            "artifact_path": "/customer/private/final.zip",
        },
    }

    packet = gig_context_packet.paid_delivery_packet(item)
    encoded = gig_context_packet.serialize_packet(packet)

    assert packet["kind"] == "gig_paid_delivery"
    assert packet["metrics"]["byte_count"] <= 8192
    assert "private-history" not in encoded.decode()
    assert "artifact_path" not in encoded.decode()


def test_reply_packet_keeps_only_the_latest_bounded_conversation():
    context = {
        "conversation": [
            {"side": "seller" if index % 2 == 0 else "buyer", "body": f"old-{index}-" + "x" * 2_000}
            for index in range(100)
        ] + [{"side": "buyer", "body": "latest buyer request"}],
        "verified_research": {"source": "verified", "raw": "r" * 100_000},
    }

    packet = gig_context_packet.reply_composition_packet(context)
    encoded = gig_context_packet.serialize_packet(packet)
    rows = packet["fields"]["conversation"]

    assert packet["kind"] == "gig_reply_composition"
    assert len(rows) == 8
    assert rows[-1] == {"side": "buyer", "body": "latest buyer request"}
    assert all("old-0-" not in row["body"] for row in rows)
    assert packet["metrics"]["byte_count"] <= 8192
    assert packet["metrics"]["conservative_token_ceiling"] <= 8192
