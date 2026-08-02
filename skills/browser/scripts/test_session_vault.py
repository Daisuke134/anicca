"""Unit tests for session_vault's logged_out detection.

Bug fixed: keepalive/logged_out previously judged purely by whether the final URL redirected to
/login or /signin (session_vault.py:210, pre-fix). Instagram does NOT redirect to /login for a
half-dead session — ds_user_id survives after sessionid expires, and IG just serves the feed as
if nothing happened. So the old logic returned logged_out:false forever even though the session
was dead ("session was dead for 3 days and nobody noticed"). The negative test below reproduces
exactly that: an instagram.com page, no redirect, sessionid cookie absent -> must report
logged_out:true. Non-instagram domains (coconala etc) must keep the old URL-only behavior.

Run: python3 -m pytest test_session_vault.py -v
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import session_vault as sv  # noqa: E402


def _cookie(name, domain):
    return {"name": name, "domain": domain, "value": "x"}


def test_instagram_no_sessionid_no_redirect_is_logged_out():
    """THE false-positive bug: IG keeps ds_user_id after sessionid dies, never redirects to /login."""
    url = "https://www.instagram.com/"
    final = "https://www.instagram.com/"  # no redirect at all
    cookies = [_cookie("ds_user_id", ".instagram.com"), _cookie("csrftoken", ".instagram.com")]
    assert sv._logged_out_for(url, final, cookies) is True


def test_instagram_with_sessionid_no_redirect_is_logged_in():
    url = "https://www.instagram.com/"
    final = "https://www.instagram.com/"
    cookies = [_cookie("sessionid", ".instagram.com"), _cookie("ds_user_id", ".instagram.com")]
    assert sv._logged_out_for(url, final, cookies) is False


def test_instagram_redirected_to_login_is_logged_out_even_without_cookie_check():
    url = "https://www.instagram.com/"
    final = "https://www.instagram.com/accounts/login/"
    cookies = [_cookie("sessionid", ".instagram.com")]  # even a live-looking cookie can't save it
    assert sv._logged_out_for(url, final, cookies) is True


def test_non_instagram_domain_uses_url_redirect_only_sessionid_irrelevant():
    """coconala etc keep the old behavior: sessionid check must not fire off-instagram."""
    url = "https://coconala.com/mypage"
    final = "https://coconala.com/mypage"
    cookies = []  # no sessionid cookie anywhere -- must not matter off-instagram
    assert sv._logged_out_for(url, final, cookies) is False


def test_non_instagram_domain_redirected_to_login_is_logged_out():
    url = "https://coconala.com/mypage"
    final = "https://coconala.com/login"
    cookies = [_cookie("sessionid", ".instagram.com")]  # unrelated cookie present, irrelevant
    assert sv._logged_out_for(url, final, cookies) is True


def test_instagram_sessionid_on_wrong_domain_does_not_count():
    """A sessionid cookie scoped to a different domain must not satisfy the instagram check."""
    url = "https://www.instagram.com/"
    final = "https://www.instagram.com/"
    cookies = [_cookie("sessionid", ".some-other-site.com")]
    assert sv._logged_out_for(url, final, cookies) is True


def test_read_only_targets_are_hidden_and_backgrounded():
    """Scheduled dump/keepalive must never flash a user-visible browser tab."""
    url = "https://coconala.com/mypage/dashboard"
    assert sv._read_only_target_params(url) == {
        "url": url,
        "hidden": True,
        "background": True,
    }


def test_degraded_coconala_dump_preserves_prior_authenticated_cookies(tmp_path, monkeypatch):
    """A restarted browser must not replace Coconala auth with analytics-only cookies."""
    vault = tmp_path / "auth-state.json"
    vault.write_text(json.dumps({"cookies": [
        _cookie("_coconala_session", ".coconala.com"),
        _cookie("_coconala_session_private", ".coconala.com"),
        _cookie("other", ".example.com"),
    ]}))
    monkeypatch.setattr(sv, "VAULT", str(vault))

    guarded, degraded = sv._guard_degraded_site_cookies([
        _cookie("_ga", ".coconala.com"),
        _cookie("fresh", ".example.net"),
    ])

    assert degraded == ["coconala.com"]
    assert {(c["name"], c["domain"]) for c in guarded} == {
        ("_coconala_session", ".coconala.com"),
        ("_coconala_session_private", ".coconala.com"),
        ("fresh", ".example.net"),
    }


def test_degraded_instagram_dump_preserves_prior_sessionid(tmp_path, monkeypatch):
    """A restarted browser must not bank an Instagram snapshot without sessionid."""
    vault = tmp_path / "auth-state.json"
    vault.write_text(json.dumps({"cookies": [
        _cookie("sessionid", ".instagram.com"),
        _cookie("csrftoken", ".instagram.com"),
    ]}))
    monkeypatch.setattr(sv, "VAULT", str(vault))

    guarded, degraded = sv._guard_degraded_site_cookies([
        _cookie("csrftoken", ".instagram.com"),
    ])

    assert degraded == ["instagram.com"]
    assert {c["name"] for c in guarded} == {"sessionid", "csrftoken"}


def test_latest_healthy_snapshot_skips_newer_degraded_files(tmp_path):
    """Recovery selects the newest complete site snapshot, not merely the newest backup."""
    healthy = tmp_path / "auth-state.100.json"
    degraded = tmp_path / "auth-state.200.json"
    healthy.write_text(json.dumps({"cookies": [
        _cookie("_coconala_session", ".coconala.com"),
        _cookie("_coconala_session_private", ".coconala.com"),
    ]}))
    degraded.write_text(json.dumps({"cookies": [_cookie("_ga", ".coconala.com")]}))
    os.utime(healthy, (100, 100))
    os.utime(degraded, (200, 200))

    selected = sv._latest_healthy_snapshot("coconala.com", [str(healthy), str(degraded)])

    assert selected == str(healthy)


def test_recover_reports_coconala_success_independently_of_instagram_failure(monkeypatch):
    """An unrelated Instagram failure must not hide a recovered Coconala revenue session."""
    calls = []
    keepalive_results = iter([
        {"ok": False, "logged_out": True, "pages": [
            {"url": "https://coconala.com/mypage/dashboard", "final": "https://coconala.com/login", "logged_out": True},
            {"url": "https://www.instagram.com/", "final": "https://www.instagram.com/", "logged_out": True},
        ]},
        {"ok": False, "logged_out": True, "pages": [
            {"url": "https://coconala.com/mypage/dashboard", "final": "https://coconala.com/mypage/dashboard", "logged_out": False},
            {"url": "https://www.instagram.com/", "final": "https://www.instagram.com/", "logged_out": True},
        ]},
    ])
    monkeypatch.setattr(sv, "keepalive", lambda urls: next(keepalive_results))
    monkeypatch.setattr(sv, "restore_site", lambda site: calls.append(site) or {"ok": True, "site": site})

    result = sv.recover([
        "https://coconala.com/mypage/dashboard",
        "https://www.instagram.com/",
    ])

    assert calls == ["coconala.com", "instagram.com"]
    assert result["sites"]["coconala.com"]["recovered"] is True
    assert result["sites"]["instagram.com"]["recovered"] is False
    assert result["revenue_ready"] is True
