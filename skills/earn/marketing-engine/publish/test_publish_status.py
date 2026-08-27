import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from intent_store import IntentStore
from publish_cli import run_status
from test_intent_store import fixture_intent


def test_status_is_sanitized_and_reports_attempt_states(tmp_path):
    store = IntentStore(tmp_path / "jobs.sqlite3")
    intent = store.register(fixture_intent(tmp_path))["intent"]
    lease = store.acquire(intent["publish_key"], owner="worker",
                          now="2026-08-02T00:00:00Z", ttl_seconds=60)
    attempt = store.begin_dispatch(
        intent["publish_key"], owner="worker", fence=lease["fence"],
        operation="upload_media", request={"asset_sha256": intent["asset_sha256"]},
        now="2026-08-02T00:00:01Z")
    store.mark_uncertain(attempt["attempt_id"], "timeout after dispatch",
                         now="2026-08-02T00:00:02Z")
    result = run_status(db_path=store.path, publish_key=intent["publish_key"])
    assert result["state"] == "uncertain"
    assert result["account_id"] == "instagram.anicca_en"
    assert result["native_handle"] == "anicca.en"
    assert result["attempts"] == [{"operation": "upload_media", "state": "uncertain",
                                    "started_at": "2026-08-02T00:00:01Z",
                                    "finished_at": "2026-08-02T00:00:02Z"}]
    assert "caption" not in result
    assert "asset_path" not in result
