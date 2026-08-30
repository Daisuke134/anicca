from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "extract_cp2_review_url.py"
SPEC = importlib.util.spec_from_file_location("extract_cp2_review_url", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_extracts_configure_response_cp2_short_url() -> None:
    assert MODULE.extract(
        {"ok": True, "status": "configured", "review_url": "https://api.capafy.ai/C123456"}
    ) == "https://api.capafy.ai/C123456"


@pytest.mark.parametrize(
    "payload",
    [
        {"ok": True, "status": "configured", "review_url": "https://api.capafy.ai/R123456"},
        {"ok": True, "status": "pending_config_confirmation", "review_url": "https://api.capafy.ai/C123456"},
        {"ok": True, "status": "configured", "review_url": ""},
    ],
)
def test_rejects_non_cp2_or_nonconfigured_response(payload: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        MODULE.extract(payload)
