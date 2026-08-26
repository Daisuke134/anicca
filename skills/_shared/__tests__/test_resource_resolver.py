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
