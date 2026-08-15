import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import gig_context_packet


def _verified_application(**changes):
    value = {
        "request_id": "5205196", "offer_id": "6311743", "requester_user_id": "6231861",
        "title": "案件タイトル", "proposal_body": "応募時の提案本文", "price_jpy": 50000,
        "deliver_date": "2026-08-14", "offer_url": "https://coconala.com/mypage/offers/6311743",
    }
    value.update(changes)
    return value


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


def test_paid_work_packet_carries_the_compiled_project_context(tmp_path):
    """The read-back that was missing: the compiler wrote this file and nobody opened it."""
    project = tmp_path / "91000002"
    (project / "context").mkdir(parents=True)
    (project / "context" / "current.json").write_text(json.dumps({
        "version": 1,
        "combined_context": {
            "version": 1,
            "sources_present": ["dm", "our_commitments", "posting", "requirements", "talkroom"],
            "posting": {"path": str(project / "source" / "posting" / "request-91000002.json"),
                        "body": "枚数\n4枚\n納品ファイル形式\nTTPX"},
            "our_commitments": [{"source": "dm", "sent_at": "2026-08-06 15:46:41",
                                 "text": "最短でご購入当日から翌日中を目安に初稿をご提出します"}],
            "read_these_first": [str(project / "source" / "dm" / "thread-90000007-full.json")],
            "bytes": 400,
        },
    }, ensure_ascii=False), encoding="utf-8")

    item = {"request_id": "91000002", "talkroom_id": "90000002", "delivery_action": "work_required"}
    packet = gig_context_packet.paid_work_packet_with_context(item, project)
    encoded = gig_context_packet.serialize_packet(packet).decode()

    assert packet["fields"]["project_context"]["sources_present"] == [
        "dm", "our_commitments", "posting", "requirements", "talkroom",
    ]
    assert "4枚" in encoded
    assert "初稿" in encoded
    assert "thread-90000007-full.json" in encoded
    # Without --project-root nothing changes: the plain packet is byte-identical to before.
    assert "project_context" not in gig_context_packet.paid_work_packet(item)["fields"]


def test_a_project_without_a_compiled_context_still_produces_a_packet(tmp_path):
    item = {"request_id": "91000002", "talkroom_id": "90000002"}
    packet = gig_context_packet.paid_work_packet_with_context(item, tmp_path / "missing")
    assert "project_context" not in packet["fields"]
    assert packet["kind"] == "gig_paid_work"


def test_reply_packet_allowlists_strict_verified_application_fields_and_bounds_it():
    packet = gig_context_packet.reply_composition_packet({
        "conversation": [{"side": "buyer", "body": "価格と納期を教えてください"}],
        "counterparty_user_id": "6231861",
        "verified_application": _verified_application(
            raw_page="buyer secret and unbounded page" * 1000, buyer_email="buyer@example.com"
        ),
    })
    fields = packet["fields"]
    assert set(fields["verified_application"]) == {
        "title", "proposal_body", "price_jpy", "deliver_date",
    }
    assert fields["verified_application"]["price_jpy"] == 50000
    assert fields["verified_application"]["deliver_date"] == "2026-08-14"
    encoded = gig_context_packet.serialize_packet(packet).decode()
    assert "raw_page" not in encoded
    assert "buyer@example.com" not in encoded
    assert "counterparty_user_id" not in encoded
    assert "6231861" not in encoded
    assert "5205196" not in encoded
    assert "6311743" not in encoded
    assert "https://coconala.com/mypage/offers/6311743" not in encoded
    assert packet["metrics"]["byte_count"] <= 8192


def test_reply_packet_rejects_unverified_application_shapes():
    base = {"conversation": [{"side": "buyer", "body": "価格は？"}]}
    for invalid in (
        _verified_application(request_id="not-decimal"),
        _verified_application(proposal_body="x" * 1025),
        _verified_application(deliver_date="2026-02-30"),
    ):
        try:
            gig_context_packet.reply_composition_packet({**base, "counterparty_user_id": "6231861", "verified_application": invalid})
        except ValueError:
            continue
        raise AssertionError("invalid verified application was accepted")


def test_reply_packet_preserves_a_652_byte_official_proposal_without_silent_truncation():
    proposal = "x" * 652
    packet = gig_context_packet.reply_composition_packet({
        "conversation": [{"side": "buyer", "body": "応募時の価格を教えてください"}],
        "counterparty_user_id": "6231861",
        "verified_application": _verified_application(proposal_body=proposal),
    })
    assert packet["fields"]["verified_application"]["proposal_body"] == proposal
