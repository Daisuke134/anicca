#!/usr/bin/env python3
"""Executable contract: the paid-split draft_save leaves the draft PRIVATE.

`publish-paid.py` now persists the paid split on note's own draft before the
irreversible PUT, sending `free_body`, `pay_body`, `separator`, `limited: true`
and a non-zero `price` to
`POST /api/v1/text_notes/draft_save?id=N&is_temp_saved=true`.

`limited: true` and a non-zero `price` are exactly the two fields that make an
article paid.  The earlier draft-surface measurement
(`config/note-422-draft-surface-observation.json`) only ever sent a **body-only**
draft_save, so "this stays private" was an inference about a payload nobody had
sent.  Inference is not good enough when the failure mode is a public artifact.

Measured 2026-08-07 on throwaway scratch drafts, twice, and stored as data in
`config/note-paid-draftsave-privacy-observation.json`.  This file asserts the
evidence exists, was obtained without ever touching a publishing surface, and
says the draft stayed private -- so the claim cannot rot into folklore.

It also pins the payload the evidence describes against the payload
`publish-paid.py` builds **today**.  If anyone adds a field to the draft_save,
the measurement no longer covers what production sends, and this test fails
rather than silently vouching for an older payload.

No network, no live state and no live tree are touched here.
"""

from __future__ import annotations

import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "config" / "note-paid-draftsave-privacy-observation.json"
PUBLISH_PAID = ROOT / "scripts" / "note-publish" / "publish-paid.py"

# The publish endpoint shape that produced the incident: PUT/POST on
# /api/v1/text_notes/{numeric id}.  The draft surface is
# /api/v1/text_notes/draft_save, which does not match because `draft_save` is
# not digits.  Anything matching this is a publishing request and must never
# appear in a privacy observation.
PUBLISH_ENDPOINT = re.compile(r"/api/v1/text_notes/\d+(?:\?|$)")

# The incident's own article, and the previous probe's scratch.  Neither may be
# the artifact this measurement was taken on.
INCIDENT_KEY = "n47735d9811e8"


def _draft_save_builder():
    """Load the real builders from publish-paid.py without importing cloakbrowser."""
    source = PUBLISH_PAID.read_text(encoding="utf-8").split("\n")
    start = next(i for i, line in enumerate(source) if line.startswith("class NoteBodyBlocks"))
    end = next(i for i, line in enumerate(source) if line.startswith("def put_paid_note"))
    namespace: dict = {
        "HTMLParser": HTMLParser,
        "re": re,
        "json": json,
        "urllib": urllib,
    }
    exec(compile("\n".join(source[start:end]), str(PUBLISH_PAID), "exec"), namespace)
    return namespace["build_paid_publish_payload"], namespace["build_paid_draft_save_payload"]


@pytest.fixture(scope="module")
def evidence() -> dict:
    assert EVIDENCE.is_file(), (
        f"{EVIDENCE} is missing: the claim that the paid-split draft_save keeps the "
        "draft private has no measurement behind it, so the two-step is unproven"
    )
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_the_measured_payload_carried_the_paid_fields(evidence):
    """A privacy measurement that omitted `limited`/`price` would prove nothing."""
    sent = evidence["sent"]
    assert sent["limited"] is True, "the paid flag was not exercised"
    assert isinstance(sent["price"], int) and sent["price"] > 0, "a zero price proves nothing"
    assert sent["carries_status_field"] is False
    assert "status" not in sent["payload_keys"]
    assert {"free_body", "pay_body", "separator", "limited", "price"} <= set(sent["payload_keys"])


def test_no_recorded_request_could_publish(evidence):
    """A privacy observation that touched a publishing surface is void."""
    for row in evidence["requests"]:
        assert not PUBLISH_ENDPOINT.search(row["url"]), f"publishing endpoint used: {row}"
        keys = row.get("request_payload_keys") or []
        assert "status" not in keys, f"request payload carried a status field: {row}"


def test_the_draft_stayed_private_when_read_authenticated(evidence):
    """The whole point: `limited: true` + a real price did not publish anything."""
    readback = evidence["authenticated_readback"]
    assert readback["http_status"] == 200
    assert readback["status"] == "draft", readback
    assert readback["publish_at"] is None, readback
    assert readback["is_limited"] is False, readback
    assert readback["is_trial"] is False, readback


def test_the_draft_was_invisible_without_a_session(evidence):
    """Read with no session at all, the scratch does not exist."""
    anonymous = evidence["anonymous_readback"]
    assert anonymous["api_http_status"] == 404, anonymous
    assert anonymous["public_url_http_status"] == 404, anonymous
    assert anonymous["public_url_contains_scratch_title"] is False, anonymous
    assert anonymous["public_url_contains_body_text"] is False, anonymous
    assert evidence["became_public_at_any_point"] is False


def test_the_split_was_actually_persisted(evidence):
    """The two-step exists to put `separator` on note's draft.  Prove it landed."""
    persisted = evidence["separator_persistence"]
    assert persisted["sent_separator"] == persisted["note_draft_separator"], persisted
    assert persisted["persisted"] is True
    # A fresh draft carries no separator, so the value above came from our write
    # and not from note's defaults.
    assert persisted["fresh_draft_separator_baseline"] is None, persisted


def test_the_scratch_was_a_throwaway_and_is_gone(evidence):
    """Never the incident's article, and cleaned up by readback rather than hope."""
    scratch = evidence["scratch_artifact"]
    assert scratch["key"] != INCIDENT_KEY, "the incident's own article was used"
    assert scratch["final_status"] == "deleted", scratch
    deletion = evidence["deletion"]
    assert deletion["delete_http_status"] == 200, deletion
    assert deletion["authenticated_status_after_delete"] == "deleted", deletion
    assert deletion["anonymous_public_url_http_status_after_delete"] == 404, deletion


def test_the_measurement_was_reproduced(evidence):
    """One observation of a privacy property is thin.  Require the confirming run."""
    confirming = evidence["confirming_run"]
    assert confirming["authenticated_status"] == "draft"
    assert confirming["is_limited"] is False
    assert confirming["publish_at"] is None
    assert confirming["anonymous_api_http_status"] == 404
    assert confirming["final_status"] == "deleted"


def test_evidence_still_describes_what_production_sends_today():
    """Pin the evidence to the live builder so it cannot silently go stale.

    If a field is added to or removed from the draft_save payload, the stored
    measurement no longer covers the request production makes, and this fails.
    """
    build_publish, build_draft_save = _draft_save_builder()
    body = (
        '<p id="a">' + "あ" * 40 + "</p>\n"
        '<p id="b">' + "い" * 40 + "</p>\n"
        '<p id="c">' + "う" * 40 + "</p>"
    )
    publish_payload = build_publish({"note_draft": {"body": body}}, price=500, after_chars=40, tags=[])
    draft_save_payload = build_draft_save(publish_payload)

    evidence_payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))["sent"]
    assert sorted(draft_save_payload) == evidence_payload["payload_keys"], (
        "publish-paid.py's draft_save payload changed since the privacy measurement; "
        "re-measure before trusting the stored evidence"
    )
    assert "status" not in draft_save_payload, "a draft_save must never carry a status field"
    assert draft_save_payload["limited"] is True
    assert draft_save_payload["price"] == 500
    # The body is not regenerated: the split must be exactly the measured body.
    assert draft_save_payload["body"] == publish_payload["free_body"] + publish_payload["pay_body"]
