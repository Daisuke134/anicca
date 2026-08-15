"""A buyer's request is what they said and what they sent -- not how well we fetched it.

Order 91000002, 2026-08-07. The buyer's five images were downloaded at 22:00 and written
to ``source/buyer-attachments/``. At 22:21 the same five, byte-identical on disk and
never re-sent, were recorded as ``attachment_download_not_observed`` with a
``size_bytes`` of 2306867 -- the page's display string "2.2MB" multiplied by 1048576,
against 2124659 real bytes. ``feedback_sha256`` hashes the whole manifest, so the
unchanged message acquired a second identity: 832bd54f at 22:00, 47ae9126 at 22:21.

That is the promissory loop 2f12101e was written to end, re-opened from the other side.
A confirmed delivery is recorded against one digest; the next poll observes a different
one, calls it a new request, and rebuilds.

These tests pin three things:
  * the size in a manifest is a measurement or it is absent -- never a rounded label;
  * bytes already on disk are found, not re-reported as a download failure;
  * the digest is a function of the buyer's message, so two observations of one message
    agree and two different messages do not.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "coconala_queue_snapshot.py"
SPEC = importlib.util.spec_from_file_location("coconala_queue_snapshot", SCRIPT)
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)

PROJECT = "91000002"
BUYER_TEXT = "画像を差し替えると周囲の枠まで一緒に動いてしまいます。"
REFERENCE = "message:js-talkroomMessage-900000045:attachment:0"
# 2124659 bytes is what IMG_0001.jpeg actually measures on disk; the page renders
# "2.2MB", which the old code turned into 2.2 * 1048576 = 2306867.
IMAGE = b"\xff\xd8\xff\xe0" + b"jpeg-ish payload " * 1024
DISPLAY_SIZE = "2.2MB"
ROUNDED_FROM_DISPLAY = 2306867


def _talkroom(messages: list[dict[str, object]]) -> dict[str, object]:
    return {
        "url": "https://coconala.com/talkrooms/90000002",
        "transaction_state": "取引中",
        "messages": messages,
    }


def _attachment(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "filename": "IMG_0001.jpeg",
        "content_type": "image/jpeg",
        "size_text": DISPLAY_SIZE,
        "href": None,
        "reference": REFERENCE,
    }
    base.update(overrides)
    return base


def _download_succeeded(payload: bytes = IMAGE, **overrides: object) -> dict[str, object]:
    """What the capture path hands over when the bytes actually arrived."""
    return _attachment(
        data_base64=base64.b64encode(payload).decode("ascii"),
        size_bytes=len(payload),
        capture_error=None,
        **overrides,
    )


def _download_failed(**overrides: object) -> dict[str, object]:
    """What it hands over when the click produced no file this pass."""
    return _attachment(capture_error="attachment_download_not_observed", **overrides)


def _message(attachments: list[dict[str, object]], text: str = BUYER_TEXT) -> dict[str, object]:
    return {"side": "buyer", "text": text, "attachments": attachments}


def _sidecar(projects: Path, project_id: str = PROJECT) -> dict[str, object]:
    return json.loads(
        (projects / project_id / "requirements" / "live-buyer-reply.json")
        .read_text(encoding="utf-8")
    )


def _observe(projects: Path, attachments, at: str, text: str = BUYER_TEXT):
    return collector.persist_latest_paid_buyer_reply(
        _talkroom([_message(attachments, text)]), PROJECT, projects, at,
    )


# --------------------------------------------------------------------------
# 1. size is a measurement
# --------------------------------------------------------------------------

def test_size_bytes_is_measured_from_the_bytes_not_multiplied_from_the_label(tmp_path):
    projects = tmp_path / "projects"
    _observe(projects, [_download_succeeded()], "2026-08-07T13:00:00+00:00")
    attachment = _sidecar(projects)["attachments"][0]
    assert attachment["size_bytes"] == len(IMAGE)
    assert attachment["size_bytes"] != ROUNDED_FROM_DISPLAY


def test_a_size_we_never_measured_is_absent_rather_than_estimated(tmp_path):
    """No bytes anywhere: the honest size is nothing, not 2.2 x 1048576."""
    projects = tmp_path / "projects"
    _observe(projects, [_download_failed()], "2026-08-07T13:00:00+00:00")
    attachment = _sidecar(projects)["attachments"][0]
    assert attachment["size_bytes"] is None
    assert attachment["capture_error"] == "attachment_download_not_observed"
    # The label the page showed is still worth keeping -- as a label.
    assert attachment["size_display"] == DISPLAY_SIZE


# --------------------------------------------------------------------------
# 2. bytes on disk are found
# --------------------------------------------------------------------------

def test_an_attachment_already_on_disk_is_not_reported_as_a_failed_download(tmp_path):
    """The 91000002 defect, exactly: fetched at 22:00, 'not observed' at 22:21."""
    projects = tmp_path / "projects"
    _observe(projects, [_download_succeeded()], "2026-08-07T13:00:00+00:00")
    stored = Path(_sidecar(projects)["attachments"][0]["source_path"])
    assert stored.is_file()

    _observe(projects, [_download_failed()], "2026-08-07T13:21:00+00:00")
    attachment = _sidecar(projects)["attachments"][0]
    assert attachment["capture_error"] is None
    assert attachment["source_path"] == str(stored)
    assert attachment["sha256"] == hashlib.sha256(IMAGE).hexdigest()
    assert attachment["size_bytes"] == len(IMAGE)


def test_two_stored_files_sharing_a_name_are_not_guessed_between(tmp_path):
    """Storage is content-addressed, so one filename can name two different files.

    Attributing either one to a manifest row would be a guess. The honest answer is
    the same as never having fetched it.
    """
    projects = tmp_path / "projects"
    _observe(projects, [_download_succeeded()], "2026-08-07T13:00:00+00:00")
    other = IMAGE + b"different"
    directory = projects / PROJECT / "source" / "buyer-attachments"
    (directory / f"{hashlib.sha256(other).hexdigest()[:12]}-IMG_0001.jpeg").write_bytes(other)

    _observe(projects, [_download_failed()], "2026-08-07T13:21:00+00:00")
    attachment = _sidecar(projects)["attachments"][0]
    assert attachment["capture_error"] == "attachment_download_not_observed"
    assert attachment["sha256"] is None
    assert attachment["size_bytes"] is None


# --------------------------------------------------------------------------
# 3. one message, one identity
# --------------------------------------------------------------------------

def test_the_same_message_observed_twice_produces_one_digest(tmp_path):
    """One observation downloads the file, the other does not. Same request."""
    projects = tmp_path / "projects"
    captured = _observe(projects, [_download_succeeded()], "2026-08-07T13:00:00+00:00")
    missed = _observe(projects, [_download_failed()], "2026-08-07T13:21:00+00:00")
    assert captured["feedback_sha256"] == missed["feedback_sha256"]


def test_the_digest_holds_even_when_the_bytes_were_never_in_hand(tmp_path):
    """A file we have never fetched must not change identity when it finally arrives.

    Otherwise the instability is only deferred: the first successful download of an
    old attachment would re-open a request that was already answered.
    """
    projects = tmp_path / "projects"
    never = _observe(projects, [_download_failed()], "2026-08-07T13:00:00+00:00")
    arrived = _observe(projects, [_download_succeeded()], "2026-08-07T14:00:00+00:00")
    assert never["feedback_sha256"] == arrived["feedback_sha256"]


def test_a_different_message_produces_a_different_digest(tmp_path):
    projects = tmp_path / "projects"
    first = _observe(projects, [_download_succeeded()], "2026-08-07T13:00:00+00:00")
    changed_text = _observe(
        projects, [_download_succeeded()], "2026-08-07T14:00:00+00:00",
        text="やっぱり枠は元のままにしてください。",
    )
    assert first["feedback_sha256"] != changed_text["feedback_sha256"]


def test_a_different_file_produces_a_different_digest(tmp_path):
    """Same words, a different attachment: a different request."""
    projects = tmp_path / "projects"
    first = _observe(projects, [_download_succeeded()], "2026-08-07T13:00:00+00:00")
    other = _observe(
        projects,
        [_download_succeeded(
            payload=IMAGE + b"other",
            filename="IMG_0002.jpeg",
            reference="message:js-talkroomMessage-900000064:attachment:0",
        )],
        "2026-08-07T14:00:00+00:00",
    )
    assert first["feedback_sha256"] != other["feedback_sha256"]


def test_an_extra_attachment_produces_a_different_digest(tmp_path):
    projects = tmp_path / "projects"
    one = _observe(projects, [_download_succeeded()], "2026-08-07T13:00:00+00:00")
    two = _observe(
        projects,
        [_download_succeeded(),
         _download_succeeded(
             payload=IMAGE + b"second",
             filename="IMG_0002.jpeg",
             reference="message:js-talkroomMessage-900000064:attachment:1",
         )],
        "2026-08-07T14:00:00+00:00",
    )
    assert one["feedback_sha256"] != two["feedback_sha256"]


# --------------------------------------------------------------------------
# 4. the orders already on disk keep their digests
# --------------------------------------------------------------------------

def test_an_order_with_no_attachments_keeps_the_digest_it_already_stored(tmp_path):
    """The migration guard.

    Every live order whose stored ``handled_buyer_feedback_sha256`` still matched on
    2026-08-07 (only 91000027) carries an empty attachment list. Narrowing what a
    manifest row contributes must therefore leave the envelope alone, so those orders
    hash to the same bytes as before and no fleet-wide rebuild is triggered.
    """
    projects = tmp_path / "projects"
    result = _observe(projects, [], "2026-08-07T13:00:00+00:00")
    text = _sidecar(projects)["feedback_text"]
    legacy = hashlib.sha256(json.dumps(
        {"feedback_text": text, "attachments": []},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    assert result["feedback_sha256"] == legacy


def test_the_sidecar_is_refreshed_when_observation_improves_though_identity_does_not(tmp_path):
    """A stable digest must not freeze a stale record of where the bytes are.

    The builder reads ``source_path`` out of this file; leaving it null forever
    because the digest matched is how 90000004 came to ask a buyer for a spec that
    was already on disk.
    """
    projects = tmp_path / "projects"
    _observe(projects, [_download_failed()], "2026-08-07T13:00:00+00:00")
    assert _sidecar(projects)["attachments"][0]["source_path"] is None

    _observe(projects, [_download_succeeded()], "2026-08-07T14:00:00+00:00")
    refreshed = _sidecar(projects)["attachments"][0]
    assert refreshed["source_path"] is not None
    assert refreshed["sha256"] == hashlib.sha256(IMAGE).hexdigest()
