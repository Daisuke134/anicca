import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import application_parent  # noqa: E402


def test_parent_outlives_the_telegram_transport(tmp_path, monkeypatch):
    calls = []

    class Completed:
        returncode = 0

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return Completed()

    monkeypatch.setattr(application_parent.subprocess, "run", run)

    application_parent._publish_instant_work_events(
        tmp_path / "applied.jsonl", "pass-1",
    )

    reporter = next(call for call in calls if "apply_telegram_report.py" in str(call[0]))
    assert reporter[1]["timeout"] > 180
