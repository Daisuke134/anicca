#!/usr/bin/env python3
"""§EJ' (Dais 2026-08-08 verbatim): paid talkrooms never send a question-only message.

Before this change, an "ask" verdict from either first_contact_gate (pre-build, TOP_ACTION
= work_required) or first_contact_redirect (post-build, TOP_ACTION = formal|progress, wired
in 132cabcb) called run_first_contact_ask, which composed a question via
ask_buyer_when_blocked and sent it with send_paid_answer -- the exact chain the 2026-08-08
16:30:52 pass took on talkroom 90000001 (log lines "STEP FIRST_CONTACT redirect ..."
then "ASK_BUYER done (question sent on the paid talkroom talkroom=90000001)").

This is a characterization test over gig_pass.sh's TEXT, in the same style as
test_formal_delivery_routes_judge_refusal.py's test_bash_branches_on_the_number_python_
returns: gig_pass.sh has no test harness of its own, and the previous change to this exact
routing (132cabcb) was verified the same way. Run directly with python3 -- no pytest, no
fixtures, no live loop, no side effect.
"""
from __future__ import annotations

from pathlib import Path

GIG_PASS = (Path(__file__).resolve().parents[1] / "gig_pass.sh").read_text(encoding="utf-8")


def _between(start_marker: str, end_marker: str) -> str:
    """The source text strictly between two markers -- what one case branch actually does."""
    start = GIG_PASS.index(start_marker) + len(start_marker)
    end = GIG_PASS.index(end_marker, start)
    return GIG_PASS[start:end]


def test_the_ask_only_send_function_no_longer_exists() -> None:
    """Capability removed, not guarded: no function can compose+send a bare question."""
    assert "run_first_contact_ask()" not in GIG_PASS
    assert "run_first_contact_draft()" in GIG_PASS


def test_the_draft_function_calls_the_builder_not_the_ask_lane() -> None:
    """run_first_contact_draft's only production action is run_paid_work.

    It must never itself compose or send anything -- send_paid_answer stays defined for
    the builder's in-band answer path, but this function must not be a second way to
    trigger it.
    """
    body = _between("run_first_contact_draft() {", "\n}")
    assert "run_paid_work" in body
    assert "ask_buyer_when_blocked" not in body
    assert "send_paid_answer" not in body


def test_the_question_composer_is_deleted_but_the_in_band_answer_survives() -> None:
    """ask_buyer_when_blocked was the 16:31 question generator -- it must be GONE.

    It composed a clarification question into delivery/paid-answer.json whenever the
    builder wrote BLOCKED, which made every BLOCKED state a question waiting to leave.
    Deleted with the capability, not guarded off. The only remaining producer of
    paid-answer.json is the builder's own genuine in-band answer (path A in
    run_paid_work), and send_paid_answer stays defined as that path's transport.
    """
    assert "ask_buyer_when_blocked() {" not in GIG_PASS
    assert "if ask_buyer_when_blocked" not in GIG_PASS
    assert "send_paid_answer() {" in GIG_PASS
    assert "Buyer-intent answer path (A)" in GIG_PASS
    assert 'send_paid_answer "$transaction_ledger"' in GIG_PASS


def test_the_draft_attempt_rearms_the_one_attempt_brake() -> None:
    """C3: one draft per blocked state, via the ledger asked_keys() already reads.

    record_draft_attempt_for_ask appends a blocker_key row to ~/gig/ask-buyer.jsonl;
    first_contact.py decide (branch 1) and redirect both return "await" for a key already
    present, so refuse -> rebuild -> refuse cannot loop hourly.

    ★ Consumed only on build SUCCESS. ★ Recording before the build meant one infra-failed
    build spent the single attempt and the order stalled at "await" -- the buyer receives
    nothing until the 48h auto-cancel. So: exactly ONE call site, at run_paid_work's
    build-success exit, guarded on the clause; neither ask-routing branch records at
    attempt time.
    """
    assert "record_draft_attempt_for_ask() {" in GIG_PASS
    brake_body = _between("record_draft_attempt_for_ask() {", "\nrun_first_contact_draft")
    assert "ask-buyer.jsonl" in brake_body
    assert "blocker_key" in brake_body
    # Exactly one bare call in the whole file (the definition line has "() {").
    calls = [
        line.strip()
        for line in GIG_PASS.splitlines()
        if line.strip() == "record_draft_attempt_for_ask"
    ]
    assert len(calls) == 1
    # No attempt-time recording in either ask-routing branch.
    draft_body = _between("run_first_contact_draft() {", "\n}")
    gate_case = _between(
        'case "${FIRST_CONTACT_DECISION:-build}" in\n      ask)',
        "await)",
    )
    for body in (draft_body, gate_case):
        assert not any(
            line.strip() == "record_draft_attempt_for_ask" for line in body.splitlines()
        )
    # The one call sits after the last failure exit, guarded, before the success log.
    paid_work_body = _between("run_paid_work() {", "\nassess_paid_queue() {")
    success_tail = paid_work_body[paid_work_body.rindex("reconcile_paid_delivery.py"):]
    assert 'if [ -n "${FIRST_CONTACT_ASSUMPTIONS_CLAUSE:-}" ]; then' in success_tail
    assert "record_draft_attempt_for_ask" in success_tail
    assert success_tail.index("record_draft_attempt_for_ask") < success_tail.index(
        "STEP PAID_WORK done (project_root="
    )


def test_the_draft_prompt_does_not_also_order_the_builder_to_write_blocked() -> None:
    """C2: the assumptions clause replaces the 'do not build, write BLOCKED' instructions.

    Without this the builder obeys the prohibition, writes BLOCKED, and the draft path
    never produces anything -- the inversion would be dead on arrival.
    """
    assert 'FC_DRAFT_MODE="${FIRST_CONTACT_ASSUMPTIONS_CLAUSE:+1}"' in GIG_PASS
    # The question-promise sentence is a variable emptied in draft mode, not a literal.
    assert "${blocked_question_note}" in GIG_PASS
    assert 'blocked_question_note=""' in GIG_PASS
    assert "このファイルを元に、不足している情報を買い手へ質問します。BLOCKED" not in GIG_PASS


def test_the_assumptions_clause_is_bounded() -> None:
    """I1: 1200 chars, matching the sibling prior_validation_feedback bound."""
    clause_body = _between("first_contact_assumptions_clause() {", "\n}")
    assert "[:1200]" in clause_body


def test_the_pre_build_gate_falls_through_to_the_builder_on_ask() -> None:
    """first_contact_gate's "ask" case (TOP_ACTION=work_required) no longer short-circuits.

    Before: `ask) run_first_contact_ask || return 1; return 0 ;;` stopped the pass before
    the builder ever ran. Now the case body must contain no `return` -- it only logs and
    falls through into the same build that "build" reaches, carrying
    FIRST_CONTACT_ASSUMPTIONS_CLAUSE into the prompt.
    """
    gate_case = _between(
        'case "${FIRST_CONTACT_DECISION:-build}" in\n      ask)',
        "await)",
    )
    assert "run_first_contact_ask" not in gate_case
    assert "run_first_contact_draft" not in gate_case
    assert "return" not in gate_case
    assert "STEP FIRST_CONTACT draft" in gate_case


def test_the_post_build_redirect_routes_to_draft_and_does_not_return_early() -> None:
    """first_contact_redirect's "ask" case (TOP_ACTION=formal|progress, the 132cabcb wiring)
    now rebuilds instead of asking, and falls through to assess_paid_queue instead of
    returning -- the rebuilt artifact has to reach the same delivery attempt any other
    order does, or "submit it" is not actually happening.
    """
    redirect_case = _between(
        'case "${FIRST_CONTACT_DECISION:-none}" in\n          ask)',
        "await)",
    )
    assert "run_first_contact_ask" not in redirect_case
    assert "run_first_contact_draft || return 1" in redirect_case
    assert "refresh_paid_queue_after_builder" in redirect_case
    # The old branch returned unconditionally right after the send; the new one must not,
    # or the freshly built artifact never reaches assess_paid_queue this same pass.
    assert "return 0" not in redirect_case


def test_production_impossible_still_fails_through_record_failure_never_silently() -> None:
    """Fallback safety: a rebuild that cannot proceed is a recorded, visible deferral.

    run_first_contact_draft is `run_paid_work` under a new name; run_paid_work's own
    failure paths (sandbox down, contract bootstrap failed, builder failed, ...) already
    call record_failure, which appends a reasoned row to ~/gig/pass-failures.jsonl before
    returning 1 -- and both call sites propagate that with `|| return 1`. Nothing about the
    inversion may turn a stuck rebuild into either a question or a silent drop.
    """
    draft_body = _between("run_first_contact_draft() {", "\n}")
    assert "run_paid_work" in draft_body
    paid_work_body = _between("run_paid_work() {", "\nassess_paid_queue() {")
    assert paid_work_body.count("record_failure") >= 5


def test_the_assumptions_clause_is_threaded_from_decision_to_prompt() -> None:
    """The judge's/decider's open questions reach the build prompt, not a question queue."""
    assert "FIRST_CONTACT_ASSUMPTIONS_CLAUSE" in GIG_PASS
    assert 'feedback_clause="$feedback_clause$(paid_work_prior_rejection_clause)${FIRST_CONTACT_ASSUMPTIONS_CLAUSE:-}"' in GIG_PASS
    # Set only on ask, in both callers that can produce one.
    gate_body = _between("first_contact_gate() {", "\nrun_first_contact_draft")
    redirect_body = _between("first_contact_redirect() {", "\nrun_paid_work() {")
    for body in (gate_body, redirect_body):
        assert "FIRST_CONTACT_ASSUMPTIONS_CLAUSE=\"\"" in body  # reset every call
        assert "first_contact_assumptions_clause \"$decision_file\"" in body


def test_b0_inquiry_reply_is_untouched() -> None:
    """Scope boundary: pre-order buyer inquiries (B0) are not paid-talkroom outbound.

    followup_lane and the inquiry-reply machinery are a different lane entirely and this
    change must not have touched them -- asserted by the absence of the new clause/function
    names anywhere near their definitions.
    """
    assert "followup_lane() {" in GIG_PASS
    followup_body = _between("followup_lane() {", "\n}")
    assert "FIRST_CONTACT_ASSUMPTIONS_CLAUSE" not in followup_body
    assert "run_first_contact_draft" not in followup_body


TESTS = [
    test_the_ask_only_send_function_no_longer_exists,
    test_the_draft_function_calls_the_builder_not_the_ask_lane,
    test_the_question_composer_is_deleted_but_the_in_band_answer_survives,
    test_the_draft_attempt_rearms_the_one_attempt_brake,
    test_the_draft_prompt_does_not_also_order_the_builder_to_write_blocked,
    test_the_assumptions_clause_is_bounded,
    test_the_pre_build_gate_falls_through_to_the_builder_on_ask,
    test_the_post_build_redirect_routes_to_draft_and_does_not_return_early,
    test_production_impossible_still_fails_through_record_failure_never_silently,
    test_the_assumptions_clause_is_threaded_from_decision_to_prompt,
    test_b0_inquiry_reply_is_untouched,
]


if __name__ == "__main__":
    failures = []
    for test in TESTS:
        try:
            test()
        except AssertionError as exc:
            failures.append(f"{test.__name__}: {exc}")
        else:
            print(f"ok  {test.__name__}")
    if failures:
        print(f"\n{len(failures)} FAILED:")
        for line in failures:
            print(f"  {line}")
        raise SystemExit(1)
    print(f"\n{len(TESTS)} passed")
