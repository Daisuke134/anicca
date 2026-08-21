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
    monkeypatch.setenv("ARTICLE_PUBLICATION_STATE", "/var/lib/life-manager/writer/state.json")
    monkeypatch.setattr(GUARD.shutil, "disk_usage", lambda _path: SimpleNamespace(free=1_073_741_823))
    with pytest.raises(GUARD.InvariantError, match="disk_headroom_low"):
        GUARD.assert_disk_headroom()


def test_publication_guard_allows_at_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARTICLE_PUBLICATION_STATE", "/var/lib/life-manager/writer/state.json")
    monkeypatch.setattr(GUARD.shutil, "disk_usage", lambda _path: SimpleNamespace(free=1_073_741_824))
    GUARD.assert_disk_headroom()


def test_publication_guard_checks_publication_state_filesystem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[Path] = []
    monkeypatch.setenv(
        "ARTICLE_PUBLICATION_STATE",
        "/var/lib/life-manager/writer/runs/active/gates/publication-state.json",
    )
    monkeypatch.delenv("ARTICLE_STATE_DIR", raising=False)
    monkeypatch.setattr(
        GUARD.shutil,
        "disk_usage",
        lambda path: seen.append(Path(path)) or SimpleNamespace(free=1_073_741_824),
    )

    GUARD.assert_disk_headroom()

    assert seen == [Path("/var/lib/life-manager/writer/runs/active/gates")]


def test_publication_guard_requires_managed_state_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARTICLE_PUBLICATION_STATE", raising=False)
    monkeypatch.delenv("ARTICLE_STATE_DIR", raising=False)
    with pytest.raises(GUARD.InvariantError, match="managed_publication_state_required"):
        GUARD.assert_disk_headroom()


def test_preflight_disk_gate_runs_before_store_creation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARTICLE_AUTOPUBLISH", "1")
    monkeypatch.setenv("ARTICLE_PUBLICATION_STATE", "/var/lib/life-manager/writer/state.json")
    monkeypatch.setattr(GUARD.shutil, "disk_usage", lambda _path: SimpleNamespace(free=1_073_741_823))
    store_created = False

    def fail_if_store_created(*_args: object, **_kwargs: object) -> object:
        nonlocal store_created
        store_created = True
        raise AssertionError("PublicationStore must not be created before disk gate")

    monkeypatch.setattr(GUARD, "store_from_env", fail_if_store_created)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "preflight",
            "--pair",
            "note/ja",
            "--target-kind",
            "note-key",
            "--target",
            "example",
        ],
    )

    with pytest.raises(GUARD.InvariantError, match="disk_headroom_low"):
        GUARD.main()
    assert store_created is False
