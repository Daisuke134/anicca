#!/usr/bin/env python3
"""Turn what B2 already recorded into a counted summary of why it applied to so few jobs.

The pass report said "応募: 0件" and nothing else, so a lane that never ran and a lane that
inspected 35 jobs and found every one of them closed produced the identical sentence. The
first is an outage and the second is the market; conflating them left the operator anxious
and left the loop unable to name its own bottleneck.

Pure functions only: the caller supplies already-parsed evidence.
"""
from __future__ import annotations

from typing import Any


# Measured wording, 2026-08-06, from application-decisions.json reason_codes. The planner
# writes free text, so one cause arrives in several spellings and counting raw strings
# would split it. Matching is substring-based and case-insensitive.
#
# Only two causes are mechanical facts about the POSTING. The first real run put 18 of 29
# rejections into a catch-all and the verbatim samples were all capability limits the
# keyword list had not anticipated -- phone_call_required,
# ILLUSTRATION_PRODUCTION_NOT_SUPPORTED, 公的資格が必要, 機械設計・試作品製作が必要.
# Chasing that with an ever-longer list is endless, so the default is inverted: anything
# that is not closed and not already-applied is a statement about US, and it is quoted.
REASON_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "already",
        ("すでに応募", "既応募", "応募済み", "already_applied", "already applied"),
    ),
    (
        "closed",
        ("募集終了", "受付終了", "応募受付停止", "受付停止", "applications_closed",
         "application_closed", "not_accepting", "accepting_applications_false"),
    ),
)


def normalise_reason(value: Any) -> str:
    """One reason string to one of three buckets.

    closed and already are mechanical states of the posting. Everything else -- including
    wording nobody has seen before -- is "capability": a statement that we could not do the
    work. summarise() quotes those verbatim, because "we declined illustration work eleven
    times this week" is a decision about what to build next, and a bare count hides it.
    """
    if not isinstance(value, str):
        return "capability"
    text = value.strip().lower()
    if not text:
        return "capability"
    for bucket, needles in REASON_PATTERNS:
        if any(needle.lower() in text for needle in needles):
            return bucket
    return "capability"


OTHER_EXAMPLE_LIMIT = 3
OTHER_EXAMPLE_CHARS = 20


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def summarise(commit_results: Any, decisions: Any) -> dict[str, Any]:
    """Count one pass's application outcomes from the evidence B2 already writes.

    commit_results is agent-B2/parent-commit.json's "results"; decisions is
    agent-B2/application-decisions.json. Either may be None when the lane did not run, and
    either may be malformed when a pass was killed mid-write -- both degrade to "did not
    run" rather than raising, because this is on the reporting path of every pass.
    """
    rows = _rows(commit_results)
    summary: dict[str, Any] = {
        "ran": bool(rows),
        "inspected": len(rows),
        "applied": 0,
        "submit_failed": 0,
        "readback_inconclusive": 0,
        "quarantined": 0,
        "ineligible": 0,
        "reasons": {},
        "other_examples": [],
    }
    for row in rows:
        status = str(row.get("status") or "")
        if status in ("confirmed", "recovered_prepared_confirmed"):
            summary["applied"] += 1
        elif status.startswith(
            ("submission_runtime_failed", "submission_failed", "pre_submit_aborted")
        ):
            summary["submit_failed"] += 1
        elif status.startswith("readback_inconclusive"):
            # §FG': not a submit failure and never a strike -- but a candidate waiting on an
            # inconclusive readback still has to be visible, or a pass full of them reads
            # as a quiet market.
            summary["readback_inconclusive"] += 1
        elif status.startswith("quarantined"):
            summary["quarantined"] += 1
        elif status == "ineligible":
            summary["ineligible"] += 1

    counts: dict[str, int] = {}
    examples: list[str] = []
    seen: set[str] = set()
    decision_rows = _rows((decisions or {}).get("decisions") if isinstance(decisions, dict) else None)
    for row in decision_rows:
        if row.get("eligibility") == "eligible":
            continue
        codes = row.get("reason_codes")
        codes = codes if isinstance(codes, list) and codes else [""]
        bucket = normalise_reason(codes[0])
        counts[bucket] = counts.get(bucket, 0) + 1
        # Quote the capability rejections, not a catch-all: closed and already are
        # mechanical and say nothing, while "we could not do this" names the skill we do
        # not have yet. That is the one line here with product value.
        if bucket == "capability" and len(examples) < OTHER_EXAMPLE_LIMIT:
            # De-duplicate on the full reason, not on the truncated one: several distinct
            # rejections can share a 20-character prefix, and collapsing those would report
            # one example where the cap of three is meant to show the spread of new wording.
            text = str(codes[0] or "").strip()
            if text and text not in seen:
                seen.add(text)
                examples.append(text[:OTHER_EXAMPLE_CHARS])
    summary["reasons"] = counts
    summary["other_examples"] = examples
    return summary


BUCKET_LABELS_JA: tuple[tuple[str, str], ...] = (
    ("closed", "募集終了"),
    ("already", "既応募"),
    ("capability", "実務不可"),
    ("other", "その他"),
)


def render_line(summary: dict[str, Any]) -> str:
    """One Japanese line naming the batch behind the number.

    Always shows the breakdown, including on passes that did apply: on 2026-08-06 four
    applications hid the fact that 33 of 37 inspections were spent on jobs already applied
    to or already closed, and that waste is the actual bottleneck.
    """
    applied = int(summary.get("applied") or 0)
    if not summary.get("ran"):
        return f"- 応募: {applied}件（レーン未実行）"
    parts: list[str] = []
    reasons = summary.get("reasons") or {}
    for bucket, label in BUCKET_LABELS_JA:
        count = int(reasons.get(bucket) or 0)
        if count:
            parts.append(f"{label}{count}")
    if int(summary.get("submit_failed") or 0):
        parts.append(f"送信失敗{int(summary['submit_failed'])}")
    if int(summary.get("readback_inconclusive") or 0):
        parts.append(f"確認不能{int(summary['readback_inconclusive'])}")
    if int(summary.get("quarantined") or 0):
        parts.append(f"隔離{int(summary['quarantined'])}")
    examples = summary.get("other_examples") or []
    if examples:
        parts.append("例: " + "、".join(str(text) for text in examples))
    detail = f"（{' / '.join(parts)}）" if parts else ""
    return f"- 応募: {applied}件 ／ 検査{int(summary.get('inspected') or 0)}{detail}"
