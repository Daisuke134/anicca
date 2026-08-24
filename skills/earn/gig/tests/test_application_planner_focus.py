from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_planner():
    path = Path(__file__).resolve().parents[1] / "scripts" / "application_planner.py"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("application_planner_focus_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prompt_prioritizes_async_strengths_and_rejects_operational_labor():
    planner = load_planner()

    prompt = planner.planner_prompt({"request_details": []})

    assert "software / landing_page / article / strategy" in prompt
    assert "outreach_or_account_operations" in prompt
    assert "mandatory_desktop_or_browser_operations" in prompt
    assert "定期購入・保守・運用のように毎月続くもの" not in prompt
