#!/usr/bin/env python3
"""Asking for a follow-up, and refusing the answer when it breaks a rule."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import followup_composer  # noqa: E402

OPEN_THREAD = {
    "messages": [{"sender": "buyer", "text": "予算感だけ教えてください"}],
    "followups_sent": 1,
    "silent_days": 6.0,
}
REFUSED_THREAD = {
    "messages": [{"sender": "buyer", "text": "他の方探して下さい。"}],
    "silent_days": 9.0,
}


def test_a_refused_thread_never_reaches_the_model():
    with pytest.raises(followup_composer.FollowupRefused) as caught:
        followup_composer.followup_prompt_for(REFUSED_THREAD)
    assert caught.value.reason == "stopped:other_seller"


def test_the_prompt_carries_the_thread_state():
    prompt = followup_composer.followup_prompt_for(OPEN_THREAD)
    assert "6 日" in prompt
    assert "1 回" in prompt
    # The purchase gate P3-1 established has to survive into follow-ups.
    assert "ご購入後" in prompt


def test_the_third_touch_is_written_as_a_close():
    prompt = followup_composer.followup_prompt_for({"messages": [], "followups_sent": 2})
    assert "最後の連絡" in prompt


def test_missing_state_reads_conservatively():
    # Unknown count means first touch; unknown silence means zero, not "long enough".
    prompt = followup_composer.followup_prompt_for({"messages": []})
    assert "0 回" in prompt


def test_a_promise_of_free_work_is_refused_after_the_model_answers():
    # A prompt is a request, and this exact request already failed once: kiki_1115 was
    # promised the deliverable free, 本日中, and stopped answering.
    with pytest.raises(followup_composer.FollowupRefused) as caught:
        followup_composer.check_composed(OPEN_THREAD, "本日中に構成案をお送りします。")
    assert caught.value.reason == "draft_violation"
    assert "unpaid_delivery_promise" in caught.value.evidence


def test_a_clean_body_passes_through_stripped():
    body = "  その後いかがでしょうか。ご購入後、当日中に初稿をご提出します。  "
    assert followup_composer.check_composed(OPEN_THREAD, body) == body.strip()


def test_guarded_applies_the_gate_to_whatever_the_composer_returns():
    composer = followup_composer.guarded(lambda context: "詳細は https://example.com へ")
    with pytest.raises(followup_composer.FollowupRefused) as caught:
        composer(OPEN_THREAD)
    assert "external_link" in caught.value.evidence


def test_guarded_lets_a_clean_body_through():
    composer = followup_composer.guarded(lambda context: "その後いかがでしょうか。")
    assert composer(OPEN_THREAD) == "その後いかがでしょうか。"


def test_a_refusal_before_the_model_gives_the_slot_back():
    """One refused thread must not starve the pass's other buyers."""
    try:
        followup_composer.followup_prompt_for(REFUSED_THREAD)
    except followup_composer.FollowupRefused as refused:
        assert refused.spent_model_call is False
    else:
        raise AssertionError("expected a refusal")


def test_a_refusal_after_the_model_does_not():
    """A call was spent; pretending otherwise lets a broken lane loop unbounded."""
    try:
        followup_composer.check_composed(OPEN_THREAD, "本日中に構成案をお送りします。")
    except followup_composer.FollowupRefused as refused:
        assert refused.spent_model_call is True
    else:
        raise AssertionError("expected a refusal")


def test_the_lane_recognises_a_refusal_without_importing_it():
    """reply_lane loads this module dynamically, so isinstance would never match."""
    import reply_lane

    refused = followup_composer.FollowupRefused("stopped:other_seller", "他の方")
    assert reply_lane._followup_refusal(refused) is refused
    assert reply_lane._followup_refusal(ValueError("unrelated")) is None


def test_the_queues_history_reaches_the_composer():
    """Without this the prompt says "0 日 / 0 回" on every thread and never closes."""
    import reply_lane

    class Browser:
        def read_before(self):
            return {"messages": [{"sender": "buyer", "text": "検討します"}]}, {"x": 1}

        def fill(self, body):
            self.body = body

    wrapped = reply_lane._FollowupContext(
        Browser(), {"followups_sent": 2, "silent_days": 11.0})
    context, before = wrapped.read_before()
    assert context["followups_sent"] == 2
    assert context["silent_days"] == 11.0
    assert before == {"x": 1}
    prompt = followup_composer.followup_prompt_for(context)
    assert "11 日" in prompt and "2 回" in prompt
    assert "最後の連絡" in prompt


def test_what_the_page_observed_wins_over_the_queue():
    import reply_lane

    class Browser:
        def read_before(self):
            return {"messages": [], "silent_days": 3.0}, {}

    context, _ = reply_lane._FollowupContext(
        Browser(), {"silent_days": 99.0}).read_before()
    assert context["silent_days"] == 3.0


def test_everything_else_still_reaches_the_real_browser():
    import reply_lane

    class Browser:
        def read_before(self):
            return {}, {}

        def click(self):
            return "clicked"

    assert reply_lane._FollowupContext(Browser(), {}).click() == "clicked"


def test_the_wrapper_can_be_opened_as_a_context_manager():
    """The lane opens the browser with a `with` block.

    __getattr__ cannot serve __enter__/__exit__ -- Python looks up dunder methods on the
    type, never the instance -- so the first real question to a paying buyer died with
    TypeError: object does not support the context manager protocol.
    """
    import reply_lane

    class Browser:
        entered = False
        exited = False

        def __enter__(self):
            self.entered = True
            return self

        def __exit__(self, *exc_info):
            self.exited = True
            return False

        def read_before(self):
            return {"messages": []}, {}

    browser = Browser()
    wrapped = reply_lane._FollowupContext(browser, {"silent_days": 4.0})
    with wrapped as opened:
        assert browser.entered is True
        # The wrapper, not the raw browser: the merged context is why it exists.
        assert opened is wrapped
        assert opened.read_before()[0]["silent_days"] == 4.0
    assert browser.exited is True
