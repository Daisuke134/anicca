"""W1 (26-gig-loop-asis-tobe-plan.md §FL'): planner_prompt() carries the measured
proposal-feedback fragment when GIG_APPLIED_LEDGER etc. point at real signal, and is
byte-for-byte unchanged (fail-open) when they point at nothing -- a fresh install with
no gig history yet must not see a different prompt. Synthetic ids only (99xxxxxx).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "application_planner.py"


def load_module():
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("application_planner", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _envelope() -> dict:
    return {
        "request_details": [
            {"request_id": "99700001", "category": "コード", "budget_min_jpy": None, "budget_max_jpy": None}
        ]
    }


def test_prompt_unchanged_when_no_gig_state_present(tmp_path, monkeypatch):
    monkeypatch.setenv("GIG_APPLIED_LEDGER", str(tmp_path / "no-applied.jsonl"))
    monkeypatch.setenv("GIG_PROJECTS_ROOT", str(tmp_path / "no-projects"))
    monkeypatch.setenv("GIG_EVIDENCE_ROOT", str(tmp_path / "no-evidence"))
    monkeypatch.setenv("ANICCA_JOB_PROFILE", str(tmp_path / "no-profile.json"))
    m = load_module()
    prompt = m.planner_prompt(_envelope())
    assert "個別化" not in prompt


def test_prompt_carries_measured_band_guidance_when_applied_ledger_has_signal(tmp_path, monkeypatch):
    applied_path = tmp_path / "applied.jsonl"
    with applied_path.open("w", encoding="utf-8") as handle:
        for i in range(3):
            handle.write(json.dumps({"requestId": f"99710{i}", "status": "applied", "applicants_at_bid": 0}) + "\n")
        for i in range(2):
            handle.write(json.dumps({"requestId": f"99720{i}", "status": "replied", "applicants_at_bid": 0}) + "\n")
    monkeypatch.setenv("GIG_APPLIED_LEDGER", str(applied_path))
    monkeypatch.setenv("GIG_PROJECTS_ROOT", str(tmp_path / "no-projects"))
    monkeypatch.setenv("GIG_EVIDENCE_ROOT", str(tmp_path / "no-evidence"))
    monkeypatch.setenv("ANICCA_JOB_PROFILE", str(tmp_path / "no-profile.json"))
    m = load_module()
    prompt = m.planner_prompt(_envelope())
    assert "応募者0" in prompt
    assert "個別化" in prompt


def test_prompt_carries_verified_fact_and_explicit_nonfabrication_contract(tmp_path, monkeypatch):
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({"facts": [{
        "id": "life_manager",
        "claim": "Built a verified local agent system.",
        "evidence": "user_statement",
    }]}), encoding="utf-8")
    monkeypatch.setenv("GIG_APPLIED_LEDGER", str(tmp_path / "no-applied.jsonl"))
    monkeypatch.setenv("GIG_PROJECTS_ROOT", str(tmp_path / "no-projects"))
    monkeypatch.setenv("GIG_EVIDENCE_ROOT", str(tmp_path / "no-evidence"))
    monkeypatch.setenv("ANICCA_JOB_PROFILE", str(profile))

    prompt = load_module().planner_prompt(_envelope())

    assert "Built a verified local agent system." in prompt
    assert "Never invent or inflate qualifications" in prompt
    assert "未作成物を作成済みとは書かない" in prompt
    assert "Never volunteer or promise a live call" in prompt
    assert "Coconala messages" in prompt
