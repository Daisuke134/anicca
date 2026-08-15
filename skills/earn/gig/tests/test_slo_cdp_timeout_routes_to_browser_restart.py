from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


# The last missing link in a chain that was otherwise complete.
#
# gig_healer already knows how to fix a wedged browser: repair_class browser_restart
# kickstarts ai.anicca.hf-gig-browser with -k. gig_slo already raises that repair, but only
# for reasons browser_cdp_unavailable and live_queue_snapshot_failed.
#
# The failure the loop actually produces is b2_parent_boundary_failed, and after 2026-08-05
# it carries a precise cause: cdp_Page.enable_timeout_after_30s — the first CDP call on a
# fresh connection never answered, which means the target is dead. That is exactly the
# condition browser_restart exists for, and nothing routed it there. The browser stayed
# wedged, B2 failed every hour, and the repair that would have fixed it was never asked.
#
# Page.enable is the tell. It is the first call after connecting, so a timeout on it is not
# a slow page — it is a target that cannot answer at all.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "gig_slo.py"


def load_module():
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("gig_slo", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parent_error(evidence_dir: Path, error: str) -> Path:
    d = evidence_dir / "agent-B2"
    d.mkdir(parents=True, exist_ok=True)
    path = d / "parent-error.json"
    path.write_text(json.dumps({"ok": False, "error": error}), encoding="utf-8")
    return path


def test_a_cdp_timeout_asks_for_a_browser_restart(tmp_path) -> None:
    m = load_module()
    parent_error(tmp_path, "cdp_Page.enable_timeout_after_30s")
    assert m.browser_repair_for_parent_failure(tmp_path) is True


def test_any_cdp_call_timing_out_counts(tmp_path) -> None:
    # Page.enable is the clearest tell, but a navigate or evaluate that never answers means
    # the same thing: the target stopped talking.
    m = load_module()
    parent_error(tmp_path, "cdp_Page.navigate_timeout_after_30s")
    assert m.browser_repair_for_parent_failure(tmp_path) is True


def test_a_contract_violation_is_not_a_browser_fault(tmp_path) -> None:
    # Restarting the browser because the planner returned the wrong ids would hide a real
    # defect behind an infrastructure remedy, and cost a browser session each hour.
    m = load_module()
    parent_error(tmp_path, "decision_request_ids_not_one_to_one: missing=[111] unexpected=[]")
    assert m.browser_repair_for_parent_failure(tmp_path) is False


def test_a_quota_failure_is_not_a_browser_fault(tmp_path) -> None:
    m = load_module()
    parent_error(tmp_path, "application_intent_planner_failed: rc=1 transient_quota")
    assert m.browser_repair_for_parent_failure(tmp_path) is False


def test_no_recorded_error_does_not_restart_anything(tmp_path) -> None:
    # Absence is not evidence of a wedged browser. Guessing here would restart the shared
    # browser on every unexplained B2 failure.
    m = load_module()
    assert m.browser_repair_for_parent_failure(tmp_path) is False


def test_unreadable_evidence_does_not_restart_anything(tmp_path) -> None:
    m = load_module()
    d = tmp_path / "agent-B2"
    d.mkdir(parents=True)
    (d / "parent-error.json").write_text("{not json", encoding="utf-8")
    assert m.browser_repair_for_parent_failure(tmp_path) is False
