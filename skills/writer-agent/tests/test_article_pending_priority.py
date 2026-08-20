import importlib.util
import sys
from datetime import datetime
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "article_pending.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("article_pending_priority", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
article_pending = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(article_pending)


def test_latest_active_six_run_precedes_old_legacy_backlog_after_midnight() -> None:
    now = datetime.fromisoformat("2026-08-07T00:30:00+09:00")
    states = [
        {
            "run_id": "daily-2026-07-24",
            "created_at": "2026-07-24T06:00:00+09:00",
            "publication_contract": "legacy-exact8",
        },
        {
            "run_id": "20260802-000152",
            "created_at": "2026-08-02T00:01:52+09:00",
            "publication_contract": "active-six",
        },
        {
            "run_id": "20260806-084924",
            "created_at": "2026-08-06T08:49:24+09:00",
            "publication_contract": "active-six",
        },
    ]

    ordered = sorted(states, key=lambda state: article_pending.run_priority(state, now))

    assert [state["run_id"] for state in ordered] == [
        "20260806-084924",
        "20260802-000152",
        "daily-2026-07-24",
    ]
