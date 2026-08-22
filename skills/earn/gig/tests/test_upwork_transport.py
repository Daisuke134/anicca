"""Selection tests for Upwork API-first, authorization-bound transports."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


GIG_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = GIG_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
MODULE = SCRIPTS / "providers" / "upwork_transport.py"


def _load_module():
    name = "gig_upwork_transport_test"
    spec = importlib.util.spec_from_file_location(name, MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


transport = _load_module()
NOW = datetime(2026, 8, 23, tzinfo=timezone.utc)
ACCOUNT = "upwork-owner:v1:" + "1" * 64


def _receipt(action: str, mode: str, *, expired: bool = False) -> dict[str, object]:
    state = "approved_api" if mode == "official_api" else "approved_browser"
    return {
        "provider": "upwork", "account": ACCOUNT, "action": action,
        "transport": mode, "state": state, "jurisdiction": "JP",
        "terms_version": "special-approval-v1", "evidence_hash": "a" * 64,
        "issued_at": "2026-08-01T00:00:00+00:00",
        "expires_at": "2026-08-22T00:00:00+00:00" if expired else "2026-09-22T00:00:00+00:00",
    }


def _authorization_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipts: list[dict[str, object]],
) -> Path:
    path = tmp_path / "authorizations.json"
    path.write_text(json.dumps({"version": 1, "receipts": receipts}), encoding="utf-8")
    path.chmod(0o600)
    monkeypatch.setenv("GIG_AUTHORIZATION_PATH", str(path))
    return path


def _oauth(path: Path, *, expired: bool = False) -> None:
    path.write_text(json.dumps({
        "version": 1,
        "access_token": "upwork-access-token-must-never-appear",
        "refresh_token": "upwork-refresh-token-must-never-appear",
        "token_type": "Bearer",
        "scopes": ["graphql"],
        "expires_at": "2026-08-22T00:00:00+00:00" if expired else "2026-08-24T00:00:00+00:00",
    }), encoding="utf-8")
    path.chmod(0o600)


def _profile(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "profiles"
    path = root / "gig-upwork"
    path.mkdir(parents=True)
    root.chmod(0o700)
    path.chmod(0o700)
    return root, path


def _selector(tmp_path: Path, **overrides: object):
    root, profile = _profile(tmp_path)
    values = {
        "account": ACCOUNT,
        "now": NOW,
        "oauth_path": tmp_path / "upwork-oauth2.json",
        "profiles_root": root,
        "browser_profile": profile,
        "matrix_path": GIG_ROOT / "config" / "upwork-actions.public.json",
    }
    values.update(overrides)
    return transport.UpworkTransport(**values)


def test_approved_api_with_live_token_is_preferred_over_approved_browser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    _authorization_store(
        tmp_path, monkeypatch,
        [_receipt("search", "official_api"), _receipt("search", "cloak_browser")],
    )
    oauth_path = tmp_path / "upwork-oauth2.json"
    _oauth(oauth_path)

    selected = _selector(tmp_path, oauth_path=oauth_path).for_action("search")

    assert selected is not None
    assert selected.mode == "official_api"
    assert selected.credential_path == oauth_path
    assert "access-token" not in repr(selected)


def test_approved_browser_is_used_when_api_is_not_authorized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    _authorization_store(
        tmp_path, monkeypatch, [_receipt("propose", "cloak_browser")]
    )
    root, profile = _profile(tmp_path)
    selected = transport.UpworkTransport(
        account=ACCOUNT, now=NOW, oauth_path=tmp_path / "missing-oauth.json",
        profiles_root=root, browser_profile=profile,
        matrix_path=GIG_ROOT / "config" / "upwork-actions.public.json",
    ).for_action("propose")

    assert selected is not None
    assert selected.mode == "cloak_browser"
    assert selected.credential_path == profile


def test_expired_authorization_and_expired_token_produce_zero_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    _authorization_store(
        tmp_path, monkeypatch,
        [_receipt("message", "official_api"), _receipt("message", "cloak_browser", expired=True)],
    )
    oauth_path = tmp_path / "upwork-oauth2.json"
    _oauth(oauth_path, expired=True)

    assert _selector(tmp_path, oauth_path=oauth_path).for_action("message") is None


def test_missing_authorization_and_unlisted_action_produce_zero_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    _authorization_store(tmp_path, monkeypatch, [])
    selector = _selector(tmp_path)

    assert selector.for_action("search") is None
    assert selector.for_action("delete_account") is None


def test_oauth_loader_is_bounded_private_and_redacted(tmp_path: Path):
    oauth_path = tmp_path / "upwork-oauth2.json"
    _oauth(oauth_path)

    token = transport.load_oauth2_token(oauth_path, NOW)

    assert token is not None
    assert token.access_token == "upwork-access-token-must-never-appear"
    assert "must-never-appear" not in repr(token)
    oauth_path.chmod(0o644)
    with pytest.raises(transport.TransportConfigurationError, match="mode_600"):
        transport.load_oauth2_token(oauth_path, NOW)
    oauth_path.write_bytes(b"x" * 32_769)
    oauth_path.chmod(0o600)
    with pytest.raises(transport.TransportConfigurationError, match="too_large"):
        transport.load_oauth2_token(oauth_path, NOW)


def test_api_and_browser_share_one_logical_effect_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    oauth_path = tmp_path / "upwork-oauth2.json"
    _oauth(oauth_path)
    _authorization_store(
        tmp_path, monkeypatch, [_receipt("propose", "official_api")]
    )
    selector = _selector(tmp_path, oauth_path=oauth_path)
    api = selector.for_action("propose")
    assert api is not None
    api_intent = selector.effect_intent(
        api, resource_id="job-123", payload_hash="b" * 64,
    )

    _authorization_store(
        tmp_path, monkeypatch, [_receipt("propose", "cloak_browser")]
    )
    browser = selector.for_action("propose")
    assert browser is not None
    browser_intent = selector.effect_intent(
        browser, resource_id="job-123", payload_hash="b" * 64,
    )

    assert api_intent.effect_key == browser_intent.effect_key
    assert api_intent.authorization_hash != browser_intent.authorization_hash
