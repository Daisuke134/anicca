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
    assert all(set(entry) >= {"owner", "class", "ttl_seconds", "quota_bytes", "lease", "finalizer"} for entry in entries)

