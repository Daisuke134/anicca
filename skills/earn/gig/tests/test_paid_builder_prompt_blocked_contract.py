#!/usr/bin/env python3
"""The builder is told, by name and by schema, where a BLOCKED diagnosis goes.

Order 91000002 produced ``evidence/acceptance-blocked.json`` every hour and no prompt ever
asked for it -- that file was the model's own initiative, and initiative is not a design.
Meanwhile "return blocked/error" named no file, so the cheapest honest move was invisible
and the cheapest dishonest move (ship any .md over 1024 bytes) passed every gate.

This renders the real prompt argument out of gig_pass.sh rather than grepping the source,
so a schema that is written but never reaches the model cannot pass.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
MARKER = "You are the high-value paid-work builder."


def _prompt_argument() -> str:
    for line in (SKILL / "gig_pass.sh").read_text(encoding="utf-8").splitlines():
        if MARKER in line:
            return line.strip().rstrip("\\").strip()
    raise AssertionError("the PAID_WORK builder prompt was not found in gig_pass.sh")


@pytest.fixture(scope="module")
def rendered() -> str:
    """The prompt as the runner receives it, with the pass's variables filled in."""
    script = (
        'feedback_clause=""; trusted_clause=""; paid_domain_skills=""; '
        'builder_queue_json="{}"; TOP_PROJECT_ROOT="/tmp/project"; '
        'SCHEMA="/tmp/schema.json"; printf "%s\\n" ' + _prompt_argument()
    )
    done = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    assert MARKER in done.stdout
    return done.stdout


def test_the_blocked_file_is_named(rendered):
    assert "PROJECT_ROOT/evidence/acceptance-blocked.json" in rendered


@pytest.mark.parametrize(
    "key",
    # Exactly the keys ask_buyer.py reads: status (blocked_state), feedback_sha256
    # (blocker_key), checks[].result (missing_items), requirements_path
    # (paid_work_evidence.fresh_blocked_state), plus version and blocker.
    ['"version"', '"status"', '"BLOCKED"', '"requirements_path"', '"feedback_sha256"',
     '"checks"', '"command"', '"result"', '"blocker"'],
)
def test_the_schema_the_question_lane_reads_is_spelled_out(rendered, key):
    assert key in rendered


def test_declaring_pass_is_still_forbidden_when_blocked(rendered):
    assert "do NOT claim PASS" in rendered
    # Naming the deterministic consequence, so the model is not left to discover the gate
    # by having its delivery rejected.
    assert "acceptance_status=PASS を主張することはできません" in rendered


def test_the_escape_that_actually_shipped_is_named(rendered):
    """A 1879-byte 確認資料 .md standing in for the deliverable passed every gate."""
    assert "do NOT deliver a summary, plan, confirmation, or requirements-gathering document" in rendered


# ---------------------------------------------------------------------------
# Forbidding the escape moved the pressure instead of removing it.
#
# 2026-08-07 12:41: the buyer asked 「どちらを確認すればよいでしょうか？」. The classifier called
# that a revision, so delivery_action was work_required, so the work gate said an artifact
# was the only legal output and answering was forbidden. The builder read the clause above
# -- verified present in the live PAID_WORK.prompt.txt -- and still built, because under
# that gate a file was the only shape its answer could take: artifacts/delivery-v3.md, 2154
# bytes, telling the buyer which message to open and which attachment to click.
#
# So the prompt now names the buyer's own message as the thing that decides, and names the
# document shape rather than adding another adjective to "summary, plan, confirmation".


def test_a_buyers_question_is_not_a_build_request(rendered):
    assert "それは制作の指示ではありません" in rendered
    assert "成果物を一切作らないでください" in rendered


def test_the_document_shape_that_was_actually_produced_is_named(rendered):
    """Concrete about the observed shape, not one more adjective."""
    assert "状況を説明する文書" in rendered
    assert "買い手にファイルの開き方や確認場所を案内する文書" in rendered
    # The measured instance, so the model can recognise the shape rather than parse a rule.
    assert "どこを確認すればいいでしょうか" in rendered


def test_the_required_output_is_a_blocked_record_for_the_current_feedback(rendered):
    assert "今回のフィードバックの SHA256 で書き直した evidence/acceptance-blocked.json" in rendered
    # Why a rewrite and not a re-use: 91000002 had a BLOCKED record on disk the whole time,
    # written at 03:04 about digest 57b8719d, and the buyer had moved on to 43981596.
    assert "古い SHA256 のままの記録は無効" in rendered
