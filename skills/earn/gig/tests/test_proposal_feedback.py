"""W1 (26-gig-loop-asis-tobe-plan.md §FH'/§FI'/§FL'): measured reply-rate bands and a won
proposal exemplar, fed back into the application planner's prompt so proposals get
individualized by evidence instead of vibes. All fixtures use synthetic ids (99xxxxxx) --
no real customer text ever appears in this file or in git.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("proposal_feedback", SCRIPTS / "proposal_feedback.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _write_applied(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _row(request_id: str, status: str, *, applicants: int | None = None, order_rate: int | None = None) -> dict:
    return {
        "requestId": request_id,
        "status": status,
        "applicants_at_bid": applicants,
        "client_order_rate": order_rate,
    }


# ---------- band_guidance ----------

def test_missing_applied_ledger_yields_empty_bands(tmp_path):
    assert MODULE.band_guidance(tmp_path / "no-such.jsonl") == ""


def test_band_below_min_samples_is_excluded(tmp_path):
    path = tmp_path / "applied.jsonl"
    # Only 3 rows in the applicants=0 band -- below MIN_BAND_SAMPLES(5), must not appear.
    rows = [_row(f"990000{i}", "applied", applicants=0, order_rate=None) for i in range(3)]
    _write_applied(path, rows)
    assert MODULE.band_guidance(path) == ""


def test_band_at_min_samples_reports_measured_reply_rate(tmp_path):
    path = tmp_path / "applied.jsonl"
    # 5 rows, applicants=0 band, 2 replied -> 40.0%. Exact count and rate must appear.
    rows = [_row(f"990010{i}", "applied", applicants=0) for i in range(3)]
    rows += [_row(f"990020{i}", "replied", applicants=0) for i in range(2)]
    _write_applied(path, rows)
    out = MODULE.band_guidance(path)
    assert "応募者0" in out
    assert "2/5" in out
    assert "40.0%" in out


def test_crowded_band_and_order_rate_band_both_render(tmp_path):
    path = tmp_path / "applied.jsonl"
    rows = [_row(f"990030{i}", "applied", applicants=12) for i in range(6)]  # 8+ band, 0 replies
    rows += [_row(f"990040{i}", "delivered", order_rate=80) for i in range(5)]  # 50%+ band, all replied
    _write_applied(path, rows)
    out = MODULE.band_guidance(path)
    assert "応募者8+" in out and "0/6" in out
    assert "発注率50%+" in out and "5/5" in out


def test_rows_missing_band_key_or_status_are_skipped_not_fatal(tmp_path):
    path = tmp_path / "applied.jsonl"
    rows = [{"requestId": "9905000", "status": "applied"}]  # no applicants_at_bid/client_order_rate
    rows += [{"requestId": "9905001", "applicants_at_bid": 1}]  # no status
    rows += [_row(f"990500{i}", "applied", applicants=1) for i in range(2, 7)]
    _write_applied(path, rows)
    out = MODULE.band_guidance(path)
    assert "応募者1-3" in out
    assert "0/5" in out


# ---------- win_exemplar ----------

def test_no_project_dirs_yields_no_exemplar(tmp_path):
    out = MODULE.win_exemplar(tmp_path / "projects", tmp_path / "evidence")
    assert out == ""


def test_exemplar_found_in_recent_evidence_for_a_won_request(tmp_path):
    projects_root = tmp_path / "projects"
    (projects_root / "9910000").mkdir(parents=True)
    evidence_root = tmp_path / "evidence"
    pass_dir = evidence_root / "gig-pass-1" / "agent-B2"
    pass_dir.mkdir(parents=True)
    (pass_dir / "application-decisions.json").write_text(
        json.dumps({
            "decisions": [
                {"request_id": "9910000", "eligibility": "eligible", "proposal_text": "synthetic won proposal text"},
                {"request_id": "9910099", "eligibility": "eligible", "proposal_text": "not the winner"},
            ]
        }),
        encoding="utf-8",
    )
    out = MODULE.win_exemplar(projects_root, evidence_root)
    assert "9910000" in out
    assert "synthetic won proposal text" in out
    assert "not the winner" not in out


def test_exemplar_ignores_ineligible_decision_for_won_id(tmp_path):
    projects_root = tmp_path / "projects"
    (projects_root / "9920000").mkdir(parents=True)
    evidence_root = tmp_path / "evidence"
    pass_dir = evidence_root / "gig-pass-1" / "agent-B2"
    pass_dir.mkdir(parents=True)
    (pass_dir / "application-decisions.json").write_text(
        json.dumps({"decisions": [
            {"request_id": "9920000", "eligibility": "ineligible", "proposal_text": None},
        ]}),
        encoding="utf-8",
    )
    assert MODULE.win_exemplar(projects_root, evidence_root) == ""


def test_malformed_decisions_file_is_skipped_not_fatal(tmp_path):
    projects_root = tmp_path / "projects"
    (projects_root / "9930000").mkdir(parents=True)
    evidence_root = tmp_path / "evidence"
    pass_dir = evidence_root / "gig-pass-1" / "agent-B2"
    pass_dir.mkdir(parents=True)
    (pass_dir / "application-decisions.json").write_text("{not json", encoding="utf-8")
    assert MODULE.win_exemplar(projects_root, evidence_root) == ""


# ---------- fragment (top-level, fail-open) ----------

def test_fragment_is_empty_when_state_dir_has_nothing(tmp_path):
    out = MODULE.fragment(
        applied_path=tmp_path / "applied.jsonl",
        projects_root=tmp_path / "projects",
        evidence_root=tmp_path / "evidence",
        profile_path=tmp_path / "profile.json",
    )
    assert out == ""


def test_fragment_includes_bands_and_individualization_instruction_when_data_exists(tmp_path):
    applied_path = tmp_path / "applied.jsonl"
    rows = [_row(f"994000{i}", "applied", applicants=0) for i in range(3)]
    rows += [_row(f"994010{i}", "replied", applicants=0) for i in range(2)]
    _write_applied(applied_path, rows)
    out = MODULE.fragment(
        applied_path=applied_path,
        projects_root=tmp_path / "projects",
        evidence_root=tmp_path / "evidence",
        profile_path=tmp_path / "profile.json",
    )
    assert out != ""
    assert "応募者0" in out
    assert "個別化" in out


def test_verified_profile_exposes_only_allowlisted_evidenced_professional_facts(tmp_path):
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({"facts": [
        {"id": "life_manager", "claim": "Built a verified agent system.", "evidence": "user_statement"},
        {"id": "profile.mailing_address", "claim": "private address", "evidence": "private"},
        {"id": "muit_agent_crm", "claim": "unsupported without evidence", "evidence": ""},
    ]}), encoding="utf-8")

    out = MODULE.verified_fact_guidance(profile)

    assert "Built a verified agent system." in out
    assert "private address" not in out
    assert "unsupported without evidence" not in out
    assert "未作成物を作成済みとは書かない" in out


if __name__ == "__main__":
    import inspect
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and inspect.isfunction(fn):
            import tempfile
            tmp = Path(tempfile.mkdtemp())
            try:
                fn(tmp)
                print(f"PASS {name}")
            except Exception as exc:  # noqa: BLE001
                failures.append(name)
                print(f"FAIL {name}: {exc}")
    if failures:
        raise SystemExit(f"{len(failures)} failed: {failures}")
    print("ALL PASS")
