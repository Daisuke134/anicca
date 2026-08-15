from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


# The paying customer this lane exists for could not be delivered to.
#
# Talkroom 90000004, "ウェブ画像の更新と軽微な調整", ¥2,500, status=paid: the buyer purchased a
# listed service directly, so there is no 募集 and therefore no request_id anywhere in the
# order. The queue row carried request_id=None, and validate_queue_contract requires an
# all-digit request_id -- so every delivery attempt since 2026-08-03 died at
# formal_queue_identity_invalid before the browser even opened. The contract only imagined
# the application path; direct purchases are keyed by their talkroom, and the projects
# directory already is: ~/gig/projects/90000004 exists and is named after the talkroom.

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "coconala_formal_delivery_browser.py"
)


def load_module():
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("formal_delivery", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path: Path, *, request_id):
    root = tmp_path / "project"
    root.mkdir()
    artifact = root / "deliverable.zip"
    artifact.write_bytes(b"final artifact bytes")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    acceptance = root / "acceptance.json"
    acceptance.write_text(
        json.dumps({"status": "PASS", "package": {"sha256": digest}}), encoding="utf-8"
    )
    manifest = {
        "status": "ok",
        "acceptance_status": "PASS",
        "project_root": str(root),
        "artifact_path": str(artifact),
        "artifact_version": "v1",
        "acceptance_evidence_path": str(acceptance),
        "acceptance_delta": ["画像を差し替えた"],
        "package_sha256": digest,
    }
    queue = {
        "delivery_action": "formal",
        "formal_delivery_checkbox": True,
        "delivery_evidence": {
            key: manifest[key]
            for key in (
                "artifact_path", "artifact_version", "acceptance_evidence_path",
                "acceptance_status", "acceptance_delta", "package_sha256",
            )
        },
        "talkroom_id": "90000004",
        "request_id": request_id,
        "marketplace_url": "https://coconala.com/talkrooms/90000004",
    }
    queue["delivery_evidence"]["acceptance_status"] = "PASS"
    manifest["acceptance_status"] = "PASS"
    queue_path = tmp_path / "queue.json"
    queue_path.write_text(json.dumps(queue), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return queue_path, manifest_path, root


def test_a_direct_service_purchase_is_deliverable_without_a_request_id(tmp_path) -> None:
    m = load_module()
    queue_path, manifest_path, root = fixture(tmp_path, request_id=None)
    contract = m.validate_queue_contract(queue_path, manifest_path, root)
    # The identity of a direct purchase is its talkroom -- the same key the projects
    # directory already uses.
    assert contract["project_id"] == "90000004"
    assert contract["talkroom_id"] == "90000004"
    assert contract["event_key"].startswith("coconala:formal:90000004:")


def test_an_application_delivery_keeps_its_request_identity(tmp_path) -> None:
    m = load_module()
    queue_path, manifest_path, root = fixture(tmp_path, request_id="91000014")
    contract = m.validate_queue_contract(queue_path, manifest_path, root)
    assert contract["project_id"] == "91000014"
    assert contract["talkroom_id"] == "90000004"


def test_a_garbage_request_id_is_still_rejected(tmp_path) -> None:
    # Absent is legitimate; malformed is not. "None" the string, spaces, letters -- those are
    # corruption, and delivering under a corrupt identity would dedupe against nothing.
    m = load_module()
    queue_path, manifest_path, root = fixture(tmp_path, request_id="None")
    with pytest.raises(ValueError, match="formal_queue_identity_invalid"):
        m.validate_queue_contract(queue_path, manifest_path, root)


def test_state_expression_reads_the_checkbox_disabled_state() -> None:
    # Regression for the incident where all three talkrooms showed present=True
    # checked=False disabled=True: the checkbox was never refusing a click, it could not
    # be clicked, and this module's DOM read had no field to say so.
    m = load_module()
    assert "formal_delivery_control_disabled" in m.state_expression("deliverable.zip")


# --revision-after-formal is trusted only if the queue item -- rebuilt fresh from the live
# snapshot every pass -- independently corroborates it, same double-confirmation shape as
# coconala_paid_progress_browser.validate_progress_contract. A caller that cannot prove the
# freshness signal gets the same failure the guard used to give unconditionally.


def test_revision_after_formal_is_accepted_when_the_queue_item_corroborates_it(tmp_path) -> None:
    m = load_module()
    queue_path, manifest_path, root = fixture(tmp_path, request_id="91000002")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue["revision_after_formal"] = True
    queue["talkroom_state"] = "納品確認待ち"
    queue["formal_delivery_observed"] = True
    queue_path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
    contract = m.validate_queue_contract(
        queue_path, manifest_path, root, revision_after_formal=True
    )
    assert contract["revision_after_formal"] is True


def test_revision_after_formal_is_refused_when_the_queue_item_does_not_corroborate_it(
    tmp_path,
) -> None:
    m = load_module()
    queue_path, manifest_path, root = fixture(tmp_path, request_id="91000002")
    # No revision_after_formal / talkroom_state / formal_delivery_observed on the queue item
    # -- the CLI flag alone must not be enough to lift the guard.
    with pytest.raises(ValueError, match="revision_formal_state_not_observed"):
        m.validate_queue_contract(queue_path, manifest_path, root, revision_after_formal=True)


def test_revision_after_formal_defaults_to_false_and_needs_no_corroboration(tmp_path) -> None:
    m = load_module()
    queue_path, manifest_path, root = fixture(tmp_path, request_id="91000002")
    contract = m.validate_queue_contract(queue_path, manifest_path, root)
    assert contract["revision_after_formal"] is False


def _corroborated_queue(queue_path: Path) -> dict:
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue["revision_after_formal"] = True
    queue["talkroom_state"] = "納品確認待ち"
    queue["formal_delivery_observed"] = True
    return queue


@pytest.mark.parametrize(
    "missing", ["revision_after_formal", "talkroom_state", "formal_delivery_observed"]
)
def test_each_corroboration_field_is_individually_required(tmp_path, missing) -> None:
    # Partial corroboration is no corroboration: any one of the three live facts absent
    # and the CLI flag is refused, not partially honoured.
    m = load_module()
    queue_path, manifest_path, root = fixture(tmp_path, request_id="91000002")
    queue = _corroborated_queue(queue_path)
    del queue[missing]
    queue_path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="revision_formal_state_not_observed"):
        m.validate_queue_contract(queue_path, manifest_path, root, revision_after_formal=True)


def test_a_disabled_live_checkbox_refuses_the_revision_flag(tmp_path) -> None:
    # A1's signal: even a fully corroborated revision cannot use a checkbox the live DOM
    # says is disabled -- that item belongs on the progress channel, never here.
    m = load_module()
    queue_path, manifest_path, root = fixture(tmp_path, request_id="91000002")
    queue = _corroborated_queue(queue_path)
    queue["formal_delivery_control_disabled"] = True
    queue_path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="revision_formal_state_not_observed"):
        m.validate_queue_contract(queue_path, manifest_path, root, revision_after_formal=True)


# §EM' (2026-08-09): google_doc_link is read straight off the manifest, never off the
# queue's delivery_evidence -- it is not in the equality-checked key list above, so a
# promotion pipeline that has never heard of this field still works unmodified.


def test_a_google_doc_link_on_the_manifest_reaches_the_composed_message(tmp_path) -> None:
    m = load_module()
    queue_path, manifest_path, root = fixture(tmp_path, request_id="91000001")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["google_doc_link"] = "https://docs.google.com/document/d/1abc/edit"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    contract = m.validate_queue_contract(queue_path, manifest_path, root)
    assert contract["message"].endswith(
        "Googleドキュメント（閲覧・コメント可）: https://docs.google.com/document/d/1abc/edit"
    )


def test_a_subscription_room_queue_item_is_refused(tmp_path) -> None:
    # B4 (spec section CC'): defense-in-depth. delivery_cadence never emits mode="formal" for
    # a subscription room, so this queue shape should not exist in production -- but if a
    # stale queue file, a hand-edited fixture, or a future caller bypasses that gate, the
    # browser must refuse rather than drive toward a checkbox the room never renders.
    m = load_module()
    queue_path, manifest_path, root = fixture(tmp_path, request_id=None)
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue["room_contract_kind"] = "subscription"
    queue_path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="subscription_room_one_shot_refused"):
        m.validate_queue_contract(queue_path, manifest_path, root)


def test_a_one_shot_or_unknown_room_queue_item_is_unaffected(tmp_path) -> None:
    m = load_module()
    queue_path, manifest_path, root = fixture(tmp_path, request_id=None)
    for kind in ("one_shot", "unknown", None):
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        if kind is None:
            queue.pop("room_contract_kind", None)
        else:
            queue["room_contract_kind"] = kind
        queue_path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
        contract = m.validate_queue_contract(queue_path, manifest_path, root)
        assert contract["talkroom_id"] == "90000004"


def test_a_missing_google_doc_link_is_not_an_error(tmp_path) -> None:
    m = load_module()
    queue_path, manifest_path, root = fixture(tmp_path, request_id="91000001")
    contract = m.validate_queue_contract(queue_path, manifest_path, root)
    assert "docs.google.com" not in contract["message"]


def test_a_non_google_url_in_google_doc_link_is_refused(tmp_path) -> None:
    # Fail-closed: this field reaches a paying customer verbatim, so it is not a free
    # string. Only a real docs.google.com link (what google_docs_publisher.py returns)
    # passes.
    m = load_module()
    queue_path, manifest_path, root = fixture(tmp_path, request_id="91000001")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["google_doc_link"] = "https://evil.example.com/phish"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="google_doc_link_invalid"):
        m.validate_queue_contract(queue_path, manifest_path, root)
