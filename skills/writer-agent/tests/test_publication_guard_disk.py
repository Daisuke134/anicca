from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "publication-guard.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("publication_guard_disk", SCRIPT)
GUARD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(GUARD)


def test_publication_guard_refuses_below_coconala_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(GUARD.shutil, "disk_usage", lambda _path: SimpleNamespace(free=1_073_741_823))
    with pytest.raises(GUARD.InvariantError, match="disk_headroom_low"):
        GUARD.assert_disk_headroom()


def test_publication_guard_allows_at_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(GUARD.shutil, "disk_usage", lambda _path: SimpleNamespace(free=1_073_741_824))
    GUARD.assert_disk_headroom()
