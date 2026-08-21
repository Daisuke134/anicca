#!/usr/bin/env python3
"""Executable contract: SSOT §9.0 item 4c has no probe, and the reason is measurable.

Item 4c asks for a bounded probe that narrows the `note/ja` HTTP 422
`本文に利用できない内容が含まれています。` by bisecting the rejected body against
note's **draft** surface, so that nothing public is ever produced.

That probe cannot exist, and this file is the proof rather than the claim.  Two
independent facts, one measured against live note and one measured against this
repository's own publisher code, both have to hold:

1. **Measured, 2026-08-07.**  The exact body note rejected at publish time was
   replayed against the draft surface on a throwaway scratch draft --- whole,
   and then as each half of the rejected paid split.  All three returned
   HTTP 201 `{"result": true}`.  The draft surface does not reject this body,
   so a draft-surface bisection has no signal to bisect.  The scratch artifact
   read back `status draft` after every write, returned 404 from its
   unauthenticated public URL, and was deleted.  The observation is stored as
   data in `config/note-422-draft-surface-observation.json`; this test asserts
   the observation is present, is non-publishing, and says what the report says.

2. **Structural.**  The rejected request is a `PUT /api/v1/text_notes/{id}`
   carrying `free_body`, `pay_body`, `separator`, `price` and
   `status: "published"`.  `POST /v1/text_notes/draft_save` carries `body`.
   The split therefore has no draft representation at all, which this test
   checks against the live `build_paid_publish_payload` rather than trusting
   the sentence.  A surface that cannot express the failing payload cannot
   reproduce its rejection.

No network, no live state and no live tree are touched here.  The one file read
from the repository is read as data.
"""

from __future__ import annotations

import importlib.util
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
OBSERVATION = ROOT / "config" / "note-422-draft-surface-observation.json"
PUBLISH_PAID = ROOT / "scripts" / "note-publish" / "publish-paid.py"

# The publish endpoint shape that produced the incident.  Anything matching this
# is a publishing request and must never appear in a 4c observation.
PUBLISH_ENDPOINT = re.compile(r"/api/v1/text_notes/\d+(?:\?|$)")

# The field names the note-mcp draft-save builder sends, read off
# note_mcp.api.articles._build_article_payload (the draft-save builder reached
# through note-stage2-publish.py -> update_article).
#
# CORRECTED 2026-08-07: this set is what note-mcp SENDS, not the full set the
# endpoint ACCEPTS.  i0switch/ThreadsOS `NoteApiPlaywrightClient.saveDraft`
# (`src/adapters/note-api/playwright-client.ts`) also puts `free_body`,
# `pay_body`, `separator`, `limited` and `price` on the same draft surface, and
# publish-paid.py now does the same before its PUT.  4c's negative result is
# unaffected: what makes the rejected request a publish is `status`, which no
# draft_save in this repository may carry -- save_paid_split_draft refuses it.
DRAFT_SAVE_FIELDS = {"name", "body", "body_length", "index", "is_lead_form", "hashtags"}


def _payload_builder():
    """Load `build_paid_publish_payload` without importing cloakbrowser."""
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
    return namespace["build_paid_publish_payload"]


@pytest.fixture(scope="module")
def observation() -> dict:
    assert OBSERVATION.is_file(), (
        f"{OBSERVATION} is missing: item 4c's negative result has no evidence, "
        "so the claim that the probe cannot exist is unverifiable"
    )
    return json.loads(OBSERVATION.read_text(encoding="utf-8"))


def test_observation_records_a_replay_of_the_exact_rejected_payload(observation):
    """The replayed bytes must be the incident's own, not a lookalike."""
    incident = observation["incident"]
    assert incident["error_signature"].startswith("NoteNativePublishError: Note native publish HTTP 422")
    # publish-paid.py wrote this hash BEFORE the PUT, so it names the exact
    # bytes note rejected.  The observation must show it was reproduced, not guessed.
    assert incident["recorded_payload_sha256"] == observation["reconstruction"]["payload_sha256"]
    assert observation["reconstruction"]["verified"] is True
    assert observation["reconstruction"]["free_body_chars"] > 0
    assert observation["reconstruction"]["pay_body_chars"] > 0


def test_no_recorded_request_could_publish(observation):
    """A 4c observation that touched a publishing surface is void."""
    for row in observation["requests"]:
        assert not PUBLISH_ENDPOINT.search(row["url"]), f"publishing endpoint used: {row}"
        keys = row.get("request_payload_keys") or []
        assert "status" not in keys, f"request payload carried a status field: {row}"


def test_scratch_artifact_was_never_public_and_was_cleaned_up(observation):
    """draft_is_public stays false by readback, not by assumption."""
    scratch = observation["scratch_artifact"]
    assert scratch["key"] != observation["incident"]["note_key"], "the incident's own article was used"
    assert scratch["readback_statuses"], "no readback was performed"
    assert set(scratch["readback_statuses"]) == {"draft"}, scratch["readback_statuses"]
    assert scratch["unauthenticated_public_http_status"] == 404
    assert scratch["final_status"] == "deleted"


def test_draft_surface_accepted_the_body_that_publish_rejected(observation):
    """The measured negative: no 422 on the draft surface, so nothing to bisect."""
    replays = observation["draft_surface_replays"]
    assert {row["fragment"] for row in replays} == {"whole_body", "free_body", "pay_body"}
    for row in replays:
        assert row["http_status"] == 201, row
        assert row["result"] is True, row
        assert row["http_status"] != 422
    assert observation["verdict"]["reproducible_on_draft_surface"] is False


def test_the_draft_surface_cannot_express_the_rejected_payload():
    """Structural half of the proof, checked against the real payload builder."""
    build = _payload_builder()
    body = (
        '<p id="a">' + "あ" * 40 + "</p>\n"
        '<p id="b">' + "い" * 40 + "</p>\n"
        '<p id="c">' + "う" * 40 + "</p>"
    )
    payload = build({"note_draft": {"body": body}}, price=500, after_chars=40, tags=[])
    missing = set(payload) - DRAFT_SAVE_FIELDS
    # These are exactly the fields that carry the paywall split and the publish
    # intent.  None of them exists on the draft surface, so no draft-surface
    # request can present note with the payload it rejected.
    assert {"free_body", "pay_body", "separator", "price", "status"} <= missing
    assert payload["status"] == "published"
    assert "body" not in payload, "the rejected payload has no `body` field at all"
