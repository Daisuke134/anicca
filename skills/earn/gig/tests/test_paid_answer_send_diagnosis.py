#!/usr/bin/env python3
"""The field the send gate decides on has to appear in the send gate's failure.

2026-08-08 00:56:32, order 91000001:

    paid_answer_send_not_ready:{"url":"https://coconala.com/talkrooms/90000001",
     "form_present":true,"textarea_present":true,"formal_delivery_control_present":true,
     "formal_delivery_control_checked":false,"form_has_artifact":false,
     "send_button_present":true,"send_button_disabled":false}

Every clause of ``answer_send_ready`` is satisfied there except one -- ``textarea_value ==
message`` -- and that is the only one the report leaves out, so the send that stalled a
paying customer cannot be diagnosed from its own error. Worse, ``send_button_disabled`` is
false, and this marketplace disables that button on an empty box (measured on the same
error id at 2026-08-03, where an unfilled textarea reported ``send_button_disabled: true``),
so text did arrive -- it arrived *different*, and how it differed was not recorded.

Derived numbers only. The remote page's text is not copied into a log line, for the reason
delivery_attempt.py gives for not copying it into a ledger.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "coconala_paid_progress_browser", SKILL / "scripts" / "coconala_paid_progress_browser.py"
)
browser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser)

MESSAGE = "ご購入後すぐに着手できず、申し訳ありません。『Pokéquest』について確認させてください。"


def test_a_match_is_reported_as_a_match():
    result = browser.textarea_diagnosis({"textarea_value": MESSAGE}, MESSAGE)
    assert result["textarea_matches_expected"] is True
    assert result["first_difference_index"] == -1
    assert result["textarea_value_length"] == result["expected_length"] == len(MESSAGE)


def test_a_dropped_character_names_where_it_diverged():
    """The one character in 91000001's question outside JIS X 0208 is the é of Pokéquest."""
    mangled = MESSAGE.replace("é", "")
    result = browser.textarea_diagnosis({"textarea_value": mangled}, MESSAGE)
    assert result["textarea_matches_expected"] is False
    assert result["first_difference_index"] == MESSAGE.index("é")
    assert result["expected_length"] - result["textarea_value_length"] == 1


def test_an_empty_box_is_distinguishable_from_a_mangled_one():
    empty = browser.textarea_diagnosis({"textarea_value": ""}, MESSAGE)
    assert empty["textarea_value_length"] == 0
    assert empty["first_difference_index"] == 0


def test_a_truncated_value_reports_the_cut_point():
    result = browser.textarea_diagnosis({"textarea_value": MESSAGE[:10]}, MESSAGE)
    assert result["first_difference_index"] == 10
    assert result["textarea_matches_expected"] is False


def test_an_unreadable_field_says_so_rather_than_inventing_a_number():
    assert browser.textarea_diagnosis({}, MESSAGE) == {"textarea_value_readable": False}
    assert browser.textarea_diagnosis({"textarea_value": None}, MESSAGE) == {
        "textarea_value_readable": False
    }


def test_the_diagnosis_quotes_neither_side():
    result = browser.textarea_diagnosis({"textarea_value": MESSAGE}, MESSAGE)
    rendered = repr(result)
    assert "Pokémon" not in rendered
    assert "ご購入" not in rendered
    assert all(isinstance(value, (bool, int)) for value in result.values())


def test_the_send_gate_still_refuses_everything_it_refused_before():
    """The diagnosis is an explanation, never a relaxation."""
    ready = {
        "formal_delivery_control_checked": False,
        "textarea_present": True,
        "textarea_value": MESSAGE,
        "send_button_present": True,
        "send_button_disabled": False,
    }
    assert browser.answer_send_ready(ready, MESSAGE) is True
    assert browser.answer_send_ready({**ready, "textarea_value": MESSAGE + "。"}, MESSAGE) is False
    assert browser.answer_send_ready({**ready, "send_button_disabled": True}, MESSAGE) is False
    assert browser.answer_send_ready({**ready, "formal_delivery_control_checked": True}, MESSAGE) is False
