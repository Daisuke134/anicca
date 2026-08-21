from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "publication_guard_x_missing_media", SCRIPTS / "publication-guard.py"
)
GUARD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(GUARD)


class FakeStore:
    def __init__(self) -> None:
        self.state = {
            "destination_identities": {"x-article/ja": "diceai0"},
            "pairs": {
                "x-article/ja": {
                    "status": "intent",
                    "target_kind": "x-draft-url",
                    "target": "https://x.com/compose/articles/edit/12345678",
                }
            },
        }
        self.marked: tuple[str, str] | None = None

    def read(self) -> dict:
        return self.state

    def mark_unavailable(self, pair: str, reason: str) -> dict:
        self.marked = (pair, reason)
        entry = self.state["pairs"][pair]
        entry["status"] = "unavailable"
        entry["error"] = reason
        return entry

    def quarantine_missing_media(
        self, pair: str, target: str, reason: str, remote: dict
    ) -> dict:
        entry = self.state["pairs"][pair]
        if entry.get("status") != "intent" or entry.get("target") != target:
            raise GUARD.InvariantError("missing-media quarantine state changed before the atomic write")
        if not (
            remote.get("status") == "not-live"
            and remote.get("verified") is True
            and remote.get("destination_identity") == "diceai0"
            and remote.get("identity_verified") is True
            and remote.get("identity_source") == "x-authenticated-edit-url"
            and remote.get("source") == "x-cdp-saved-article-editor"
        ):
            raise GUARD.InvariantError(
                "missing-media quarantine requires an authenticated exact-editor not-live proof"
            )
        proof = json.dumps(remote, sort_keys=True, separators=(",", ":"))
        return self.mark_unavailable(
            pair,
            f"{reason}; authenticated exact-editor not-live proof={proof}",
        )


def _wire(monkeypatch: pytest.MonkeyPatch, store: FakeStore, remote: dict) -> None:
    monkeypatch.setenv("ARTICLE_RUN_DIR", "/tmp/run")
    monkeypatch.setenv("ARTICLE_PUBLICATION_STATE", "/tmp/state.json")
    monkeypatch.setenv("ARTICLE_LEDGER", "/tmp/ledger.jsonl")
    monkeypatch.setattr(GUARD, "store_from_env", lambda: store)
    monkeypatch.setattr(GUARD, "probe", lambda *args, **kwargs: remote)
    monkeypatch.setattr(GUARD, "x_post_effect_uncertain", lambda state: False)


def test_missing_media_quarantine_requires_exact_authenticated_not_live_proof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FakeStore()
    remote = {
        "status": "not-live",
        "verified": True,
        "destination_identity": "diceai0",
        "identity_verified": True,
        "identity_source": "x-authenticated-edit-url",
        "source": "x-cdp-saved-article-editor",
    }
    _wire(monkeypatch, store, remote)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "publication-guard.py",
            "quarantine-missing-media",
            "--pair",
            "x-article/ja",
            "--reason",
            "x-article immutable media unavailable: immutable headline image is missing or changed",
        ],
    )

    assert GUARD.main() == 0
    assert store.marked is not None
    assert store.marked[0] == "x-article/ja"
    assert "authenticated exact-editor not-live proof" in store.marked[1]
    assert store.state["pairs"]["x-article/ja"]["status"] == "unavailable"


def test_missing_media_quarantine_keeps_intent_when_remote_is_uncertain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FakeStore()
    _wire(
        monkeypatch,
        store,
        {"status": "unknown", "reason": "remote-probe-error"},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "publication-guard.py",
            "quarantine-missing-media",
            "--pair",
            "x-article/ja",
            "--reason",
            "missing media",
        ],
    )

    with pytest.raises(GUARD.InvariantError, match="authenticated exact-editor"):
        GUARD.main()
    assert store.marked is None
    assert store.state["pairs"]["x-article/ja"]["status"] == "intent"


def test_missing_media_quarantine_rechecks_state_after_remote_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FakeStore()

    def probe_then_publish(*args, **kwargs):
        store.state["pairs"]["x-article/ja"]["status"] = "live"
        return {
            "status": "not-live",
            "verified": True,
            "destination_identity": "diceai0",
            "identity_verified": True,
            "identity_source": "x-authenticated-edit-url",
            "source": "x-cdp-saved-article-editor",
        }

    _wire(monkeypatch, store, {})
    monkeypatch.setattr(GUARD, "probe", probe_then_publish)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "publication-guard.py",
            "quarantine-missing-media",
            "--pair",
            "x-article/ja",
            "--reason",
            "missing media",
        ],
    )

    with pytest.raises(GUARD.InvariantError, match="state changed"):
        GUARD.main()
    assert store.marked is None
