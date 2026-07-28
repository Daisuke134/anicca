from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[3]
CONTROL = Path(__file__).parents[1] / "cleanup_control.py"
MANIFEST = Path(__file__).parents[1] / "artifact-lifecycle.json"


def load_control():
    spec = importlib.util.spec_from_file_location("cleanup_control_wiring", CONTROL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_production_guard_has_one_cleanup_authority() -> None:
    guard = (ROOT / "scripts" / "emergency-disk-guard.sh").read_text(encoding="utf-8")
    assert 'if [ "$TEST_MODE" -eq 0 ]; then' in guard
    assert 'python3 "$CLEANUP_CONTROL" sweep' in guard
    assert (
        'if [ "$TEST_MODE" -eq 1 ] && [ "${EMERGENCY_GUARD_TEST_ENABLE_RECLAIM:-0}" = 1 ]; then'
        in guard
    )
    assert 'if [ "$TEST_MODE" -eq 0 ] ||' not in guard


def test_production_manifest_is_valid_and_protects_known_incident_roots() -> None:
    _, _, entries = load_control().load_manifest(MANIFEST)
    by_id = {entry["id"]: entry for entry in entries}
    assert by_id["work-clones"]["class"] == "source"
    assert by_id["reelclaw-assets"]["class"] == "deliverable"
    assert by_id["anicca-source"]["class"] == "source"
    assert by_id["anicca-project-source"]["class"] == "source"
    assert by_id["anicca-project-worktrees"]["class"] == "git_worktree_collection"
    assert by_id["anicca-project-worktrees"]["finalizer"]["kind"] == "remote_recoverable_remove"
    assert by_id["kickama-cargo-target"]["class"] == "regenerable_output"
    assert by_id["kickama-cargo-target"]["finalizer"]["kind"] == "verified_regenerable_remove"
    assert by_id["playwright-browser-cache"]["class"] == "regenerable_output"
    assert (
        by_id["playwright-browser-cache"]["finalizer"]["proof_path"]
        == str(Path.home() / ".openclaw/skills/roundcube-webmail-skill/package.json")
    )
    assert by_id["playwright-browser-cache"]["lease"] == {
        "path": str(Path.home() / ".openclaw/state/playwright.lease"),
        "max_age_seconds": 300,
    }
    assert by_id["claude-vm-bundle"]["path"] == str(
        Path.home() / "Library/Application Support/Claude/vm_bundles/claudevm.bundle"
    )
    assert by_id["claude-vm-bundle"]["class"] == "regenerable_output"
    assert by_id["claude-vm-bundle"]["finalizer"] == {
        "kind": "verified_regenerable_remove",
        "proof_path": "/Applications/Claude.app/Contents/Resources/app.asar",
    }
    assert by_id["life-manager-main-worktrees"]["class"] == "git_worktree_collection"
    assert by_id["life-manager-main-worktrees"]["finalizer"] == {
        "kind": "remote_recoverable_remove"
    }
    assert by_id["life-manager-external-worktrees"]["finalizer"] == {
        "kind": "remote_recoverable_remove",
        "repository_path": str(Path.home() / "Projects/life-manager-main"),
    }
    assert by_id["life-manager-main-node-modules"]["class"] == "regenerable_output"
    assert by_id["life-manager-main-node-modules"]["finalizer"] == {
        "kind": "verified_regenerable_remove",
        "proof_path": str(Path.home() / "Projects/life-manager-main/package-lock.json"),
    }
    assert by_id["camoufox-browser-cache"]["class"] == "regenerable_output"
    assert by_id["camoufox-browser-cache"]["finalizer"] == {
        "kind": "verified_regenerable_remove",
        "proof_path": str(Path.home() / ".local/pipx/venvs/camoufox/bin/camoufox"),
    }
    assert by_id["orca-codex-marketplace-staging"] == {
        "id": "orca-codex-marketplace-staging",
        "path": str(
            Path.home()
            / "Library/Application Support/orca/codex-runtime-home/home/.tmp/marketplaces/.staging"
        ),
        "owner": "codex-marketplace-runtime",
        "class": "regenerable_output",
        "ttl_seconds": None,
        "quota_bytes": 0,
        "lease": None,
        "finalizer": {
            "kind": "verified_regenerable_remove",
            "proof_path": "/Applications/Codex.app/Contents/Resources/codex",
        },
    }
    camoufox_proof = Path(by_id["camoufox-browser-cache"]["finalizer"]["proof_path"])
    assert camoufox_proof.is_file()
    assert not camoufox_proof.is_symlink()
    assert all(set(entry) >= {"owner", "class", "ttl_seconds", "quota_bytes", "lease", "finalizer"} for entry in entries)
