from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_status


def test_classifies_only_explicit_provider_states():
    assert review_status.classify_dashboard("Application submitted: In review") == "in_review"
    assert review_status.classify_dashboard("Action required to finish your application") == "action_required"
    assert review_status.classify_dashboard("Application rejected") == "rejected"
    assert review_status.classify_dashboard("Life Manager\nLive - ABC12345") == "active"
    assert review_status.classify_dashboard("Welcome to Alpaca") is None


def test_dashboard_shell_is_not_ready_before_provider_state_renders():
    url = "https://app.alpaca.markets/dashboard/overview"
    assert not review_status.dashboard_ready(url, "Home Account API Community Support")
    assert review_status.dashboard_ready(url, "Life Manager\nPaper - PA123456")
    assert review_status.dashboard_ready(url, "Application submitted: In review")
    assert review_status.dashboard_ready("https://app.alpaca.markets/login", "")


def test_due_uses_last_provider_observation():
    now = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
    assert review_status.due({}, now=now)
    assert not review_status.due(
        {"observed_at": "2026-09-05T11:45:00Z"}, now=now, interval_seconds=1800
    )
    assert review_status.due(
        {"observed_at": "2026-09-05T11:29:59Z"}, now=now, interval_seconds=1800
    )
