from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[4]
PATH = ROOT / "skills/earn/crowdworks/scripts/paid_adapter.py"
OWNER = ROOT / "skills/earn/crowdworks/scripts/paid-owner"


def load():
    spec = importlib.util.spec_from_file_location("crowdworks_paid_adapter_test", PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_zero_inventory_is_complete_without_effect():
    module = load()
    adapter = module.CrowdWorksPaidAdapter(
        account_id="daisuke",
        inventory_reader=lambda: {"ok": True, "source_complete": True, "contract_candidates": []},
    )
    assert adapter.observe_active() == []


def test_positive_inventory_stays_visible_as_resumable_provider_wait():
    module = load()
    adapter = module.CrowdWorksPaidAdapter(
        account_id="daisuke",
        inventory_reader=lambda: {
            "ok": True,
            "source_complete": True,
            "contract_candidates": [{"provider_id": "1"}],
        },
    )
    with pytest.raises(module.CrowdWorksPaidWait) as caught:
        adapter.observe_active()
    assert caught.value.paid_wait_reason == "official_contract_detail_required"
    assert caught.value.paid_remaining_work


def test_owner_uses_shared_kernel_and_provider_adapter():
    source = OWNER.read_text(encoding="utf-8")
    assert "skills/_shared/marketplace-core/scripts/paid_kernel.py" in source
    assert "skills/earn/crowdworks/scripts/paid_adapter.py" in source
    assert '--state-root "$STATE_ROOT/paid"' in source
