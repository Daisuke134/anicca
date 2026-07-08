#!/usr/bin/env python3
"""guardrails.py — Loop Scaling (fleet increase) guardrail pure functions (REQ-LV-130/132-135).
Deliberately a NEW namespace, separate from skills/self/spawn/lib/ (the existing Anicca-colony
CITIZEN spawn system — spawns whole new Anicca instances, a different concern from scaling an
EXISTING earn loop's own account fleet)."""


def scale_eligible(streak, weekly_score, weekly_score_threshold, disk_free_gb):
    """3-condition AND (REQ-LV-130): streak>=7, weekly_score strictly > threshold, disk_free_gb>=5."""
    return streak >= 7 and weekly_score > weekly_score_threshold and disk_free_gb >= 5


def cooldown_ok(last_spawn_ts, now_ts, min_interval_days):
    """REQ-LV-133: no prior spawn (None) -> always ok. Otherwise elapsed time must clear the
    minimum interval."""
    if last_spawn_ts is None:
        return True
    return (now_ts - last_spawn_ts) >= min_interval_days * 86400


def fleet_at_capacity(current_count, max_count):
    """REQ-LV-134: fail-closed — current_count reaching or exceeding max_count is "at capacity"."""
    return current_count >= max_count


def is_ban_suspected(consecutive_failures, threshold):
    """REQ-LV-135: reaching or exceeding the configured threshold trips ban suspicion."""
    return consecutive_failures >= threshold
