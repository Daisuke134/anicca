#!/usr/bin/env python3
"""Opt-in uptake coverage checks on synthetic complete-turn transcripts only."""
import unittest
from validate_stage_dialogue import OPENING, SECOND, validate


def e(speaker, text, cue=None, kind=None):
    row = {"speaker": speaker, "text": text}
    if cue:
        row["cue"] = cue
    if kind:
        row["kind"] = kind
    return row


def complete_turns():
    return [
        e("dais", "痛い痛い、もしもし！", "start"),
        e("ai", OPENING),
        e("dais", "救急！痛い痛い！"),
        e("ai", SECOND),
        e("dais", "会いたい！"),
        e("ai", "会田アイタロウに連絡しました。式場の受付に到着しています。"),
        e("dais", "終演", "end"),
    ]


class TurnCoverageTests(unittest.TestCase):
    def reasons(self, events, strict=True):
        result = validate(events, require_turn_coverage=strict)
        return [item["reason"] for item in result["violations"]]

    def test_full_callback_chain_is_accepted(self):
        result = validate(complete_turns(), require_turn_coverage=True)
        self.assertEqual(result["gate"], "PASS")
        self.assertEqual(result["turn_coverage"], "CHECKED_COMPLETE_ANNOTATED_TURNS")

    def test_skipped_dais_adlib_is_detected(self):
        events = complete_turns()
        events.insert(5, e("dais", "聞いてる？"))
        self.assertIn("unanswered_dais_turn", self.reasons(events))

    def test_unanswered_dais_at_end_is_detected(self):
        events = complete_turns()
        events.pop(5)
        self.assertIn("unanswered_dais_before_end", self.reasons(events))

    def test_legacy_default_is_unchanged(self):
        events = complete_turns()
        events.insert(5, e("dais", "聞いてる？"))
        self.assertEqual(validate(events)["gate"], "PASS")
        self.assertEqual(validate(events)["turn_coverage"], "NOT_REQUESTED")

    def test_audience_laughter_is_not_an_extra_dais_turn(self):
        events = complete_turns()
        events.insert(5, e("audience", "笑い声", kind="laughter"))
        self.assertEqual(validate(events, require_turn_coverage=True)["gate"], "PASS")

    def test_empty_ai_event_does_not_count_as_answer(self):
        events = complete_turns()
        events[5]["text"] = ""
        self.assertIn("unanswered_dais_before_end", self.reasons(events))


if __name__ == "__main__":
    unittest.main()
