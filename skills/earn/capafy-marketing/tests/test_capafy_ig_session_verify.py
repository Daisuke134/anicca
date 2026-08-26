import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "capafy_ig_session_verify.py"
HANDLE = "capafy.skills25042"
OWNER = {"origin": "https://www.instagram.com", "hostname": "www.instagram.com", "path": "/accounts/edit/", "username": HANDLE}
PAGE = {"id": "target", "type": "page", "url": "about:blank"}
SEAM = """#!/usr/bin/env python3
import json,os,sys
fixture=json.loads(os.environ["FIXTURE"]); request=json.load(sys.stdin); operation=request["operation"]
value=fixture["pages"] if operation=="pages" else fixture["created"] if operation=="create" else fixture["evidence"] if operation=="evidence" else {} if operation=="navigate" else None
if value is None: raise SystemExit(2)
with open(os.environ["CAPAFY_TEST_CDP_LOG"],"a") as stream: stream.write(operation+"\\n")
print(json.dumps(value))
"""


def run_verify(tmp_path, *, pages, evidence=OWNER, current=True, registry_port=9555, live_port=9555, credential=HANDLE, created="created-target", target_id=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    seam, accounts, secret, log = (tmp_path / name for name in ("cdp.py", "accounts.json", "credential.json", "calls"))
    seam.write_text(SEAM); seam.chmod(0o755)
    accounts.write_text(json.dumps([{"handle": HANDLE, "status": "warming", "session_owner": "browser", "port": registry_port}]))
    secret.write_text(json.dumps({"username": credential, "pw": "fixture"}))
    command = [sys.executable, str(SCRIPT), "--accounts", str(accounts), "--handle", HANDLE, "--port", str(live_port)]
    command += ["--current-session"] if current else ["--credential", str(secret)]
    if target_id is not None: command += ["--target-id", target_id]
    env = {**os.environ, "CAPAFY_IG_CDP_COMMAND": str(seam), "CAPAFY_IG_SESSION_VERIFY_TEST_SEAM": "1", "CAPAFY_TEST_CDP_LOG": str(log), "FIXTURE": json.dumps({"pages": pages, "evidence": evidence, "created": created})}
    result = subprocess.run(command, text=True, capture_output=True, env=env, check=False)
    return result, log.read_text().splitlines() if log.exists() else []


def test_current_session_reuses_existing_target_and_proves_exact_owner(tmp_path):
    result, calls = run_verify(tmp_path, pages=[{**PAGE, "id": "existing", "url": f"https://www.instagram.com/{HANDLE}/"}])
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["target_id"] == "existing"
    assert calls == ["pages", "navigate", "evidence"]


def test_current_session_accepts_current_edit_page_profile_link_owner_proof(tmp_path):
    evidence = {
        "origin": "https://www.instagram.com",
        "hostname": "www.instagram.com",
        "path": "/accounts/edit/",
        "username": None,
        "profile_hrefs": [f"/{HANDLE}/"],
    }
    result, _ = run_verify(tmp_path, pages=[PAGE], evidence=evidence)
    assert result.returncode == 0, result.stderr


def test_current_session_creates_one_target_when_none_is_reusable(tmp_path):
    result, calls = run_verify(tmp_path, pages=[{**PAGE, "id": "foreign", "url": "https://example.test/"}])
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["target_id"] == "created-target"
    assert calls == ["pages", "create", "navigate", "evidence"]


@pytest.mark.parametrize("evidence", [
    {**OWNER, "path": "/accounts/login/"},
    {**OWNER, "path": "/challenge/ABC/"},
    {**OWNER, "username": "capafy.someone_else", "profile_hrefs": [f"/{HANDLE}/"]},
    {**OWNER, "path": ["malformed"]},
    {**OWNER, "username": ""},
    {**OWNER, "origin": "https://evil.example", "hostname": "evil.example"},
    {**OWNER, "path": f"/{HANDLE}/"},
])
def test_current_session_rejects_untrusted_owner_evidence(tmp_path, evidence):
    result, _ = run_verify(tmp_path, pages=[PAGE], evidence=evidence)
    assert result.returncode != 0 and not result.stdout


def test_current_session_rejects_malformed_cdp_and_ignores_stale_registry_port(tmp_path):
    bad, _ = run_verify(tmp_path / "bad", pages=[{**PAGE, "url": None}])
    live, _ = run_verify(tmp_path / "live", pages=[PAGE], registry_port=9554)
    assert bad.returncode != 0 and not bad.stdout
    assert live.returncode == 0, live.stderr


@pytest.mark.parametrize("invalid", ["", "123"])
def test_current_session_rejects_blank_or_numeric_existing_created_and_injected_targets(tmp_path, invalid):
    existing, _ = run_verify(tmp_path / "existing", pages=[{**PAGE, "id": invalid}])
    created, _ = run_verify(tmp_path / "created", pages=[], created=invalid)
    injected, _ = run_verify(tmp_path / "injected", pages=[PAGE], target_id=invalid)
    assert existing.returncode != 0 and created.returncode != 0 and injected.returncode != 0


def test_new_account_keeps_exact_port_credential_and_owner_requirements(tmp_path):
    stale, _ = run_verify(tmp_path / "stale", pages=[PAGE], current=False, registry_port=9554)
    wrong, _ = run_verify(tmp_path / "wrong", pages=[PAGE], current=False, credential="capafy.someone_else")
    valid, _ = run_verify(tmp_path / "valid", pages=[PAGE], current=False)
    assert stale.returncode != 0 and wrong.returncode != 0
    assert valid.returncode == 0, valid.stderr
