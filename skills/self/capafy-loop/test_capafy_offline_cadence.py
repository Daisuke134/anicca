from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("capafy_offline_cadence.py")


def load_module():
    spec = importlib.util.spec_from_file_location("capafy_offline_cadence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_claim_allows_only_one_offline_build_per_calendar_day(tmp_path: Path) -> None:
    module = load_module()
    state = tmp_path / "cadence.json"

    assert module.claim(state, "2026-08-23", "run-a") is True
    assert module.claim(state, "2026-08-23", "run-b") is False
    assert module.claim(state, "2026-08-24", "run-c") is True

