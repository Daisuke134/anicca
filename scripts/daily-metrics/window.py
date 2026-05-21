"""Shared reporting window helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class ReportingWindow:
    """Closed window [start_date, end_date] in calendar days."""

    start_date: date
    end_date: date


def default_reporting_window() -> ReportingWindow:
    """Backward-compatible alias of behavior_reporting_window()."""
    return behavior_reporting_window()


def behavior_reporting_window() -> ReportingWindow:
    """Return behavior 7-day window: yesterday-6 days through yesterday."""
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=6)
    return ReportingWindow(start_date=start_date, end_date=end_date)


def asc_reporting_window() -> ReportingWindow:
    """Return ASC-safe 7-day window: (today-8) through (today-2)."""
    end_date = date.today() - timedelta(days=2)
    start_date = end_date - timedelta(days=6)
    return ReportingWindow(start_date=start_date, end_date=end_date)
