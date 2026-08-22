from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from project_workspace import WorkspaceError, create_workspace  # noqa: E402


def _contract(contract_id="contract-1", **changes):
    value = {
        "version": 1, "provider": "upwork", "contract_id": contract_id,
        "offer_id": "offer-1", "scope": "Integrate one documented REST API endpoint.",
        "deadline": "2026-09-01", "terms_sha256": "a" * 64,
        "contract_readback_sha256": "b" * 64,
    }
    value.update(changes)
    return value


WORKFLOW = {"skill_id": "python-rest-api", "version": "1.0.0", "bundle_sha256": "c" * 64}


def test_workspace_is_private_content_addressed_and_append_only(tmp_path):
    first = create_workspace(tmp_path / "projects", _contract(), WORKFLOW)
    replay = create_workspace(tmp_path / "projects", _contract(), WORKFLOW)
    revised = create_workspace(
        tmp_path / "projects", _contract(scope="Integrate two documented REST API endpoints."), WORKFLOW,
    )

    root = Path(first["workspace"])
    assert replay == first
    assert revised["revision_sha256"] != first["revision_sha256"]
    assert len(list((root / "requirements" / "revisions").glob("*.json"))) == 2
    assert len((root / "events.jsonl").read_text().splitlines()) == 3
    assert json.loads(Path(first["artifact_manifest"]).read_text())["artifacts"] == []
    for path in [root, *root.rglob("*")]:
        assert not path.is_symlink()
        want = 0o700 if path.is_dir() else 0o600
        assert stat.S_IMODE(path.stat().st_mode) == want


@pytest.mark.parametrize("contract", [
    _contract("../shared"),
    _contract(scope=""),
    {**_contract(), "api_token": "must-not-be-copied"},
])
def test_invalid_or_secret_bearing_contract_creates_nothing(tmp_path, contract):
    base = tmp_path / "projects"
    with pytest.raises(WorkspaceError):
        create_workspace(base, contract, WORKFLOW)
    assert not base.exists()


def test_contracts_never_share_a_client_directory(tmp_path):
    one = create_workspace(tmp_path / "projects", _contract("contract-1"), WORKFLOW)
    two = create_workspace(tmp_path / "projects", _contract("contract-2"), WORKFLOW)
    assert Path(one["workspace"]) != Path(two["workspace"])
    assert Path(one["workspace"]).parent == Path(two["workspace"]).parent


def test_provider_symlink_cannot_escape_workspace_root(tmp_path):
    base, outside = tmp_path / "projects", tmp_path / "outside"
    base.mkdir(mode=0o700)
    outside.mkdir(mode=0o700)
    (base / "upwork").symlink_to(outside, target_is_directory=True)
    with pytest.raises(WorkspaceError, match="symlink"):
        create_workspace(base, _contract(), WORKFLOW)
    assert list(outside.iterdir()) == []


def test_nested_symlink_is_rejected_before_revision_write(tmp_path):
    base, outside = tmp_path / "projects", tmp_path / "outside"
    receipt = create_workspace(base, _contract(), WORKFLOW)
    revisions = Path(receipt["workspace"]) / "requirements" / "revisions"
    revisions.rename(revisions.with_name("real-revisions"))
    outside.mkdir(mode=0o700)
    revisions.symlink_to(outside, target_is_directory=True)
    with pytest.raises(WorkspaceError, match="symlink"):
        create_workspace(base, _contract(scope="A changed private client scope."), WORKFLOW)
    assert list(outside.iterdir()) == []
