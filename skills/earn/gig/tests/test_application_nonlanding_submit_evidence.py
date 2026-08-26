from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "application_parent_nonlanding_evidence", SCRIPTS / "application_parent.py"
)
assert SPEC and SPEC.loader
application_parent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(application_parent)


ORIGIN_PASS_ID = "gig-apply-direct-1787441285494444000-76896"
REQUEST_ID = "5227400"


def _effects(tmp_path: Path) -> application_parent.CdpParentEffects:
    return application_parent.CdpParentEffects(
        ws_url="ws://example.invalid/devtools/page/1",
        evidence_dir=tmp_path / "apply" / "current-pass" / "refresh-evidence",
        ledger_path=tmp_path / "apply" / "applied.jsonl",
        pass_id="current-pass",
    )


def _intent() -> dict[str, object]:
    return {"lease_fence": {"task": ORIGIN_PASS_ID}}


def test_saved_nonlanding_submit_evidence_accepts_multiple_nonempty_phase_proofs(tmp_path) -> None:
    effects = _effects(tmp_path)
    apply_root = tmp_path / "apply"
    origin = apply_root / ORIGIN_PASS_ID
    filename = f"gig-{ORIGIN_PASS_ID}-B2-{REQUEST_ID}-submit-attempt.png"
    for phase in ("refresh-evidence", "refresh-reconcile-evidence"):
        path = origin / phase / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"png")

    assert effects.saved_nonlanding_submit_evidence(REQUEST_ID, _intent()) is True


def test_saved_nonlanding_submit_evidence_rejects_missing_or_empty_matching_proof(tmp_path) -> None:
    effects = _effects(tmp_path)
    apply_root = tmp_path / "apply"
    origin = apply_root / ORIGIN_PASS_ID
    filename = f"gig-{ORIGIN_PASS_ID}-B2-{REQUEST_ID}-submit-attempt.png"

    assert effects.saved_nonlanding_submit_evidence(REQUEST_ID, _intent()) is False

    empty_path = origin / "refresh-evidence" / filename
    nonempty_path = origin / "refresh-reconcile-evidence" / filename
    empty_path.parent.mkdir(parents=True, exist_ok=True)
    nonempty_path.parent.mkdir(parents=True, exist_ok=True)
    empty_path.write_bytes(b"")
    nonempty_path.write_bytes(b"png")

    assert effects.saved_nonlanding_submit_evidence(REQUEST_ID, _intent()) is False
