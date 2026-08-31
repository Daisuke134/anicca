from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "publication-guard.py"
FLOOR_BYTES = 524_288 * 1024
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("publication_guard_disk", SCRIPT)
GUARD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(GUARD)


def test_publication_guard_refuses_below_coconala_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARTICLE_PUBLICATION_STATE", "/var/lib/mr-bot/writer/state.json")
    monkeypatch.setattr(GUARD.shutil, "disk_usage", lambda _path: SimpleNamespace(free=FLOOR_BYTES - 1))
    with pytest.raises(GUARD.InvariantError, match="disk_headroom_low"):
        GUARD.assert_disk_headroom()


def test_publication_guard_allows_at_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARTICLE_PUBLICATION_STATE", "/var/lib/mr-bot/writer/state.json")
    monkeypatch.setattr(GUARD.shutil, "disk_usage", lambda _path: SimpleNamespace(free=FLOOR_BYTES))
    GUARD.assert_disk_headroom()


def test_capacity_receipt_raises_host_floor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    receipt = tmp_path / "capacity" / "article-run-floor.json"
    receipt.parent.mkdir()
    receipt.write_text(json.dumps({
        "schema": "writer.capacity-receipt",
        "version": 1,
        "observed_consumption_kib": 604_404,
        "atomic_reserve_kib": 524_288,
        "required_free_kib": 1_128_692,
    }), encoding="utf-8")
    monkeypatch.delenv("ARTICLE_DISK_MIN_FREE_BYTES", raising=False)
    assert GUARD.resolve_disk_floor_bytes(tmp_path) == 1_128_692 * 1024


def test_capacity_receipt_rejects_unbound_arithmetic(tmp_path: Path) -> None:
    receipt = tmp_path / "capacity" / "article-run-floor.json"
    receipt.parent.mkdir()
    receipt.write_text(json.dumps({
        "schema": "writer.capacity-receipt",
        "version": 1,
        "observed_consumption_kib": 604_404,
        "atomic_reserve_kib": 524_288,
        "required_free_kib": 524_288,
    }), encoding="utf-8")
    with pytest.raises(GUARD.CapacityFloorError, match="capacity_receipt_invalid"):
        GUARD.resolve_disk_floor_bytes(tmp_path)


def test_publication_guard_checks_publication_state_filesystem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[Path] = []
    monkeypatch.setenv(
        "ARTICLE_PUBLICATION_STATE",
        "/var/lib/mr-bot/writer/runs/active/gates/publication-state.json",
    )
    monkeypatch.delenv("ARTICLE_STATE_DIR", raising=False)
    monkeypatch.setattr(
        GUARD.shutil,
        "disk_usage",
        lambda path: seen.append(Path(path)) or SimpleNamespace(free=1_073_741_824),
    )

    GUARD.assert_disk_headroom()

    assert seen == [Path("/var/lib/mr-bot/writer/runs/active/gates")]


def test_publication_guard_requires_managed_state_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARTICLE_PUBLICATION_STATE", raising=False)
    monkeypatch.delenv("ARTICLE_STATE_DIR", raising=False)
    with pytest.raises(GUARD.InvariantError, match="managed_publication_state_required"):
        GUARD.assert_disk_headroom()


@pytest.mark.parametrize("value", ["0", "1", "536870911", "-1", "not-a-number"])
def test_publication_guard_rejects_floor_below_canonical_or_invalid(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("ARTICLE_PUBLICATION_STATE", "/var/lib/mr-bot/writer/state.json")
    monkeypatch.setenv("ARTICLE_DISK_MIN_FREE_BYTES", value)
    monkeypatch.setattr(GUARD.shutil, "disk_usage", lambda _path: SimpleNamespace(free=10**12))
    with pytest.raises(GUARD.InvariantError, match="disk_headroom_configuration_invalid"):
        GUARD.assert_disk_headroom()


@pytest.mark.parametrize("value", ["1", "524287"])
def test_publication_guard_rejects_gig_floor_below_canonical(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("ARTICLE_PUBLICATION_STATE", "/var/lib/mr-bot/writer/state.json")
    monkeypatch.delenv("ARTICLE_DISK_MIN_FREE_BYTES", raising=False)
    monkeypatch.setenv("GIG_DISK_HEADROOM_KIB", value)
    monkeypatch.setattr(GUARD.shutil, "disk_usage", lambda _path: SimpleNamespace(free=10**12))
    with pytest.raises(GUARD.InvariantError, match="disk_headroom_configuration_invalid"):
        GUARD.assert_disk_headroom()


def test_preflight_disk_gate_runs_before_store_creation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARTICLE_AUTOPUBLISH", "1")
    monkeypatch.setenv("ARTICLE_PUBLICATION_STATE", "/var/lib/mr-bot/writer/state.json")
    monkeypatch.setattr(GUARD.shutil, "disk_usage", lambda _path: SimpleNamespace(free=FLOOR_BYTES - 1))
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
