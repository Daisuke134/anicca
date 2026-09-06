import json

from skills._shared import resource_resolver


def test_credential_refs_advertise_passcode_without_exposing_value(tmp_path, monkeypatch):
    credentials = tmp_path / "credentials.json"
    credentials.write_text(json.dumps({"credentials": [{
        "service": "x.com",
        "username": "@seller",
        "passcode": "private-value",
    }]}))
    monkeypatch.setattr(resource_resolver, "CREDENTIALS", credentials)

    resolved = resource_resolver.credential_refs("x.com")

    assert resolved[0]["secret_fields"] == ["passcode"]
    assert "private-value" not in json.dumps(resolved)


def test_installed_skill_matches_hyphenated_capability_tokens(tmp_path, monkeypatch):
    skill = tmp_path / "skills/google-login/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: google-login\n"
        "description: Google Gmail login and receive OTP verification.\n---\n"
    )
    monkeypatch.setattr(resource_resolver, "REPO", tmp_path)
    monkeypatch.setattr(resource_resolver, "SKILLS_ROOT", tmp_path / "skills")

    resolved = resource_resolver.installed_skill_refs("gmail.com", "receive-otp")

    assert resolved[0]["skill"] == "google-login"
    assert resolved[0]["skill_path"] == "skills/google-login/SKILL.md"


def test_browser_skill_advertises_tiktok_login_readback():
    login = resource_resolver.installed_skill_refs("tiktok.com", "login")
    message = resource_resolver.installed_skill_refs("tiktok.com", "message")

    assert any(row["skill"] == "browser-foundation" for row in login)
    assert any(row["skill"] == "browser-foundation" for row in message)
