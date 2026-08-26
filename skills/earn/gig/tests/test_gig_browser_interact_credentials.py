import json

from skills.earn.gig.scripts import gig_browser_interact


def test_credential_value_resolves_ref_without_cli_secret(tmp_path, monkeypatch):
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"credentials": [{"passcode": "private-value"}]}))
    monkeypatch.setattr(gig_browser_interact, "CREDENTIALS", path)

    assert gig_browser_interact.credential_value("credentials:0", "passcode") == "private-value"
