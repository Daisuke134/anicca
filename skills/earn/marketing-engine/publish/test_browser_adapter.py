import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from browser_adapter import BrowserAdapter, unique_native_match
from intent_store import IntentStore
from test_intent_store import fixture_intent


class FakeDriver:
    def __init__(self, *, snapshot=None, submit_result=None, submit_error=None):
        self.snapshot_result = snapshot or {
            "native_handle": "anicca.en", "logged_in": True,
            "profile_url": "https://www.instagram.com/anicca.en/", "recent_items": []
        }
        self.submit_result = submit_result or {
            "native_handle": "anicca.en", "native_post_id": "native-123",
            "native_post_url": "https://www.instagram.com/reel/native-123/"
        }
        self.submit_error = submit_error
        self.snapshot_calls = 0
        self.submit_calls = 0

    def snapshot(self, intent):
        self.snapshot_calls += 1
        return self.snapshot_result

    def submit(self, intent):
        self.submit_calls += 1
        if self.submit_error:
            raise self.submit_error
        return self.submit_result


def setup(tmp_path):
    store = IntentStore(tmp_path / "jobs.sqlite3")
    intent = store.register(fixture_intent(tmp_path))["intent"]
    lease = store.acquire(intent["publish_key"], owner="browser-worker",
                          now="2026-08-01T00:00:00Z", ttl_seconds=300)
    return store, intent, lease


def test_submit_requires_durable_preflight_snapshot(tmp_path):
    store, intent, lease = setup(tmp_path)
    adapter = BrowserAdapter(store, FakeDriver())
    with pytest.raises(ValueError, match="browser preflight snapshot missing"):
        adapter.submit(intent["publish_key"], "browser-worker", lease["fence"],
                       now="2026-08-01T00:00:01Z")


def test_wrong_native_handle_fails_before_submit(tmp_path):
    store, intent, lease = setup(tmp_path)
    driver = FakeDriver(snapshot={
        "native_handle": "wrong.account", "logged_in": True,
        "profile_url": "https://www.instagram.com/wrong.account/", "recent_items": []
    })
    adapter = BrowserAdapter(store, driver)
    with pytest.raises(ValueError, match="browser native handle mismatch"):
        adapter.preflight(intent["publish_key"], "browser-worker", lease["fence"],
                          expected_handle="anicca.en", now="2026-08-01T00:00:01Z")
    assert driver.submit_calls == 0


def test_preflight_and_submit_are_idempotent_and_store_native_receipt(tmp_path):
    store, intent, lease = setup(tmp_path)
    driver = FakeDriver()
    adapter = BrowserAdapter(store, driver)
    first_snapshot = adapter.preflight(
        intent["publish_key"], "browser-worker", lease["fence"],
        expected_handle="anicca.en", now="2026-08-01T00:00:01Z")
    second_snapshot = adapter.preflight(
        intent["publish_key"], "browser-worker", lease["fence"],
        expected_handle="anicca.en", now="2026-08-01T00:00:02Z")
    assert first_snapshot == second_snapshot
    assert driver.snapshot_calls == 1
    first = adapter.submit(intent["publish_key"], "browser-worker", lease["fence"],
                           now="2026-08-01T00:00:03Z")
    second = adapter.submit(intent["publish_key"], "browser-worker", lease["fence"],
                            now="2026-08-01T00:00:04Z")
    assert first["state"] == second["state"] == "accepted"
    assert driver.submit_calls == 1
    current = store.get(intent["publish_key"])
    assert current["state"] == "published"
    assert current["native_post_id"] == "native-123"
    assert current["native_post_url"] == "https://www.instagram.com/reel/native-123/"


def test_browser_timeout_is_uncertain_and_never_reclicked(tmp_path):
    store, intent, lease = setup(tmp_path)
    driver = FakeDriver(submit_error=TimeoutError("submit response lost"))
    adapter = BrowserAdapter(store, driver)
    adapter.preflight(intent["publish_key"], "browser-worker", lease["fence"],
                      expected_handle="anicca.en", now="2026-08-01T00:00:01Z")
    first = adapter.submit(intent["publish_key"], "browser-worker", lease["fence"],
                           now="2026-08-01T00:00:02Z")
    second = adapter.submit(intent["publish_key"], "browser-worker", lease["fence"],
                            now="2026-08-01T00:00:03Z")
    assert first["state"] == second["state"] == "uncertain"
    assert driver.submit_calls == 1


def test_malformed_browser_response_is_durably_rejected(tmp_path):
    store, intent, lease = setup(tmp_path)
    driver = FakeDriver(submit_result={
        "native_handle": "wrong.account", "native_post_id": "native-123",
        "native_post_url": "https://www.instagram.com/reel/native-123/"})
    adapter = BrowserAdapter(store, driver)
    adapter.preflight(intent["publish_key"], "browser-worker", lease["fence"],
                      expected_handle="anicca.en", now="2026-08-01T00:00:01Z")
    with pytest.raises(ValueError, match="browser response handle mismatch"):
        adapter.submit(intent["publish_key"], "browser-worker", lease["fence"],
                       now="2026-08-01T00:00:02Z")
    current = store.get(intent["publish_key"])
    assert current["state"] == "browser_rejected"
    assert "handle mismatch" in current["last_error"]


def test_native_reconciliation_requires_one_account_token_time_match(tmp_path):
    intent = fixture_intent(tmp_path)
    exact = {
        "native_handle": "anicca.en", "native_post_id": "native-123",
        "native_post_url": "https://www.instagram.com/reel/native-123/",
        "caption": intent["caption"], "published_at": intent["scheduled_at"],
    }
    assert unique_native_match(intent, [exact], expected_handle="anicca.en")["native_post_id"] == "native-123"
    assert unique_native_match(intent, [], expected_handle="anicca.en") is None
    assert unique_native_match(intent, [exact | {"native_handle": "wrong"}],
                               expected_handle="anicca.en") is None
    with pytest.raises(ValueError, match="multiple native candidates"):
        unique_native_match(intent, [exact, exact | {"native_post_id": "native-456",
            "native_post_url": "https://www.instagram.com/reel/native-456/"}],
            expected_handle="anicca.en")
