#!/usr/bin/env python3
"""weekly_compare.py — beats_previous_week(this_week_score, last_week_score) -> bool (REQ-LV-111).
Pure, strict > only — a tie is NOT a beat (mirrors earn/self-improve's gate_math.py baseline-floor
"ties do not beat baseline" rule, applied here to the week-over-week comparison instead)."""


def beats_previous_week(this_week_score, last_week_score):
    return this_week_score > last_week_score
