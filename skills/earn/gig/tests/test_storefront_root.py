"""Fail-closed binding of an optional private Storefront bundle root."""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import kpi_readback_audit as kpi  # noqa: E402
import storefront_direct as storefront  # noqa: E402


@pytest.fixture(autouse=True)
def _synthetic_service_ids(monkeypatch):
    """Give explicit-bundle preflight a non-private contract boundary."""
    for name, value in {
        "GIG_STOREFRONT_TARGET_SERVICE_ID": "90000001",
        "GIG_STOREFRONT_GALLERY_SERVICE_ID": "90000002",
        "GIG_STOREFRONT_PRESENTATION_SERVICE_ID": "90000004",
        "GIG_STOREFRONT_SCOPE_SERVICE_ID": "90000005",
    }.items():
        monkeypatch.setenv(name, value)


def _bundle(
    root: Path, *, hero_image_contract: str = "../assets/hero.json", image_asset: str = "hero.png",
) -> None:
    (root / "contracts" / "listings").mkdir(parents=True)
    (root / "contracts" / "mutations").mkdir()
    (root / "assets").mkdir()
    (root / "scorecard.json").write_text(json.dumps({
        "portfolio_policy": {
            "version": 1, "slot_limit": 1, "minimum_views_for_retirement": 1,
            "short_term_zero_sales_can_retire": False,
            "retirement_mode": "recoverable_unpublish_before_delete", "replacement_candidates": [],
        }, "services": [], "priority_backlog": [],
    }), encoding="utf-8")
    (root / "families.json").write_text(json.dumps({}), encoding="utf-8")
    (root / "contracts" / "new-listing.json").write_text(
        json.dumps({"hero_image_contract": hero_image_contract}), encoding="utf-8"
    )
    for field in ("title", "body", "scope", "package", "faq", "price"):
        (root / "contracts" / "mutations" / f"{field}.json").write_text("{}", encoding="utf-8")
    (root / "assets" / "hero.json").write_text(json.dumps({"asset": "hero.png"}), encoding="utf-8")
    (root / "assets" / "hero.png").write_bytes(b"asset")
    (root / "assets" / "image-contract.json").write_text(
        json.dumps({"asset": image_asset}), encoding="utf-8"
    )
    (root / "assets" / "gallery-contract.json").write_text(
        json.dumps({"asset": "gallery.png"}), encoding="utf-8"
    )
    (root / "assets" / "gallery.png").write_bytes(b"asset")


def _run_args(root: Path, tmp_path: Path):
    args = storefront.build_parser().parse_args([])
    args.pass_id = "storefront-root-preflight"
    args.state_dir = tmp_path / "state"
    args.output = None
    args.operator_brake = tmp_path / "brake"
    args.ensure_browser_script = tmp_path / "ensure-browser.sh"
    args.lease_script = tmp_path / "lease.py"
    args.telegram_database = tmp_path / "outbox.sqlite3"
    args.telegram_receipt_dir = tmp_path / "receipts"
    args.telegram_target = ""
    return args


def _png() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + struct.pack(">II", 1220, 1016)


def _valid_image_assets(root: Path) -> None:
    image = _png()
    image_digest = hashlib.sha256(image).hexdigest()
    (root / "assets" / "image.png").write_bytes(image)
    (root / "assets" / "image-contract.json").write_text(json.dumps({
        "version": 1, "service_id": storefront.TARGET_SERVICE_ID, "field": "image",
        "asset": "image.png", "asset_sha256": image_digest, "width": 1220, "height": 1016,
        "mime_type": "image/png", "claims": ["test"], "claim_source": "test",
        "platform_requirement_source": "test",
    }), encoding="utf-8")
    before = [f"image-{number}.png" for number in range(1, 7)]
    replacements = []
    for number in range(3, 7):
        path = root / "assets" / f"gallery-{number}.png"
        path.write_bytes(image)
        replacements.append({"replace_image_id": before[number - 1], "asset": path.name,
                             "asset_sha256": image_digest, "width": 1220, "height": 1016,
                             "mime_type": "image/png"})
    (root / "assets" / "gallery-contract.json").write_text(json.dumps({
        "version": 1, "service_id": storefront.GALLERY_SERVICE_ID, "field": "image",
        "before_image_ids": before, "kept_image_ids": before[:2], "replacements": replacements,
        "claims": ["test"], "claim_source": "test", "platform_requirement_source": "test",
    }), encoding="utf-8")


def _assert_no_browser_run(monkeypatch, calls: list[str]) -> None:
    def run(argv, **_kwargs):
        if argv[:1] == ["/bin/bash"]:
            calls.append("browser")
        return storefront.subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(storefront.subprocess, "run", run)
    monkeypatch.setattr(storefront, "_lease", lambda *_args, **_kwargs: calls.append("lease"))


def test_explicit_root_binds_both_storefront_consumers_to_same_scorecard(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    _bundle(root)
    monkeypatch.setenv("GIG_STOREFRONT_ROOT", str(root))

    paths = storefront._storefront_paths()

    assert paths["scorecard"] == root / "scorecard.json"
    assert storefront.build_parser().parse_args([]).scorecard == paths["scorecard"]
    assert paths["image"] == root / "assets" / "image-contract.json"
    assert paths["gallery"] == root / "assets" / "gallery-contract.json"
    assert storefront.build_parser().parse_args([]).image_contract == paths["image"]
    assert storefront.build_parser().parse_args([]).gallery_contract == paths["gallery"]
    assert kpi._storefront_contract_path() == paths["scorecard"]


@pytest.mark.parametrize("root", ("missing", "file", "empty"))
def test_explicit_missing_or_non_directory_root_is_rejected_before_runtime(tmp_path, monkeypatch, root):
    value = tmp_path / root
    if root == "file":
        value.write_text("not a bundle", encoding="utf-8")
    elif root == "empty":
        value.mkdir()
    monkeypatch.setenv("GIG_STOREFRONT_ROOT", str(value))

    with pytest.raises(RuntimeError, match="storefront_root_invalid"):
        storefront.build_parser()


def test_explicit_root_rejects_asset_reference_escaping_bundle(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    _bundle(root, hero_image_contract="../../../outside.json")
    monkeypatch.setenv("GIG_STOREFRONT_ROOT", str(root))

    with pytest.raises(RuntimeError, match="storefront_root_asset_invalid"):
        storefront.build_parser()


def test_explicit_root_rejects_image_contract_asset_escaping_bundle(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    _bundle(root, image_asset="../../outside.png")
    monkeypatch.setenv("GIG_STOREFRONT_ROOT", str(root))

    with pytest.raises(RuntimeError, match="storefront_root_asset_invalid"):
        storefront.build_parser()


def test_invalid_explicit_image_contract_fails_before_browser_or_lease(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    _bundle(root)
    monkeypatch.setenv("GIG_STOREFRONT_ROOT", str(root))
    args = _run_args(root, tmp_path)
    browser_calls = []
    def run(argv, **_kwargs):
        if argv[:1] == ["/bin/bash"]:
            browser_calls.append("browser")
        return storefront.subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(storefront.subprocess, "run", run)
    monkeypatch.setattr(storefront, "_lease", lambda *_args, **_kwargs: browser_calls.append("lease"))

    code, row = storefront.run_once(args)

    assert code == 1 and row["reason"] == "storefront_image_contract_fields_invalid"
    assert browser_calls == []


def test_preflight_rejects_static_scorecard_and_listing_schema_before_browser(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    _bundle(root)
    root.joinpath("scorecard.json").write_text(json.dumps({"services": []}), encoding="utf-8")
    monkeypatch.setenv("GIG_STOREFRONT_ROOT", str(root))
    calls: list[str] = []
    _assert_no_browser_run(monkeypatch, calls)

    code, row = storefront.run_once(_run_args(root, tmp_path))

    assert code == 1 and row["reason"] == "storefront_portfolio_policy_invalid"
    assert calls == []

    root.joinpath("scorecard.json").write_text(json.dumps({
        "portfolio_policy": {
            "version": 1, "slot_limit": 1, "minimum_views_for_retirement": 1,
            "short_term_zero_sales_can_retire": False,
            "retirement_mode": "recoverable_unpublish_before_delete", "replacement_candidates": [],
        }, "services": [], "priority_backlog": [],
    }), encoding="utf-8")
    root.joinpath("contracts/listings/bad.json").write_text("{}", encoding="utf-8")
    code, row = storefront.run_once(_run_args(root, tmp_path))

    assert code == 1 and row["reason"] == "listing_contract_static_invalid"
    assert calls == []


def test_preflight_rejects_external_fixed_input_symlink(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    _bundle(root)
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    (root / "contracts" / "mutations" / "title.json").unlink()
    (root / "contracts" / "mutations" / "title.json").symlink_to(outside)
    monkeypatch.setenv("GIG_STOREFRONT_ROOT", str(root))

    with pytest.raises(RuntimeError, match="storefront_root_invalid"):
        storefront.build_parser()


def test_preflight_rejects_unbound_private_image_family_before_browser(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    _bundle(root)
    _valid_image_assets(root)
    root.joinpath("families.json").write_text(json.dumps({
        "version": 1,
        "service_families": {storefront.GALLERY_SERVICE_ID: "bound"},
        "families": {"bound": {}},
    }), encoding="utf-8")
    monkeypatch.setenv("GIG_STOREFRONT_ROOT", str(root))
    calls: list[str] = []
    _assert_no_browser_run(monkeypatch, calls)

    code, row = storefront.run_once(_run_args(root, tmp_path))

    assert code == 1 and row["reason"] == "storefront_image_family_unbound"
    assert calls == []


def test_preflight_rejects_text_mutation_family_mismatch_before_browser(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    _bundle(root)
    _valid_image_assets(root)
    root.joinpath("families.json").write_text(json.dumps({
        "version": 1,
        "service_families": {storefront.TARGET_SERVICE_ID: "bound",
                               storefront.GALLERY_SERVICE_ID: "bound"},
        "families": {"bound": {}, "wrong": {}},
    }), encoding="utf-8")
    (root / "contracts" / "mutations" / "title.json").write_text(json.dumps({
        "version": 1, "platform": "coconala", "service_id": storefront.TARGET_SERVICE_ID,
        "capability_family": "wrong", "changed_field": "title", "form_field": "data[Service][overview]",
        "before_value": "before", "proposed_value": "after", "rollback_value": "before",
        "official_readback": {}, "success_metric": "views_to_inquiry",
        "observation_window_days": 7, "evidence": ["test"],
    }), encoding="utf-8")
    monkeypatch.setenv("GIG_STOREFRONT_ROOT", str(root))
    calls: list[str] = []
    _assert_no_browser_run(monkeypatch, calls)

    code, row = storefront.run_once(_run_args(root, tmp_path))

    assert code == 1 and row["reason"] == "storefront_text_mutation_family_unbound"
    assert calls == []


def test_image_mutation_keeps_an_external_bundle_asset_inside_its_fence(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    _bundle(root)
    asset_path = root / "assets" / "hero.png"
    asset = b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + struct.pack(">II", 1220, 1016)
    asset_path.write_bytes(asset)
    monkeypatch.setenv("GIG_STOREFRONT_ROOT", str(root))
    monkeypatch.setattr(
        storefront, "_load_capability_families", lambda _path: ({storefront.TARGET_SERVICE_ID: "vision"}, {}),
    )

    contract = storefront._image_mutation_contract(
        {"service_id": storefront.TARGET_SERVICE_ID, "field": "image", "before": 0,
         "executable": True, "success_metric": "views_to_inquiry"},
        {"listing_version_sha256": "a" * 64, "service_image_count": 0, "service_image_ids": []},
        {"asset_path": str(asset_path), "asset_sha256": hashlib.sha256(asset).hexdigest(),
         "claim_source": "test", "platform_requirement_source": "test"},
        {storefront.TARGET_SERVICE_ID: "vision"},
    )

    assert contract["proposed_value"]["asset_path"] == str(asset_path)
    storefront._validate_image_mutation_contract(contract, root / "families.json")


def test_image_mutation_validation_uses_private_families_by_default(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    _bundle(root)
    root.joinpath("families.json").write_text(json.dumps({
        "version": 1,
        "service_families": {storefront.TARGET_SERVICE_ID: "private_vision"},
        "families": {"private_vision": {}},
    }), encoding="utf-8")
    asset_path = root / "assets" / "hero.png"
    asset = b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + struct.pack(">II", 1220, 1016)
    asset_path.write_bytes(asset)
    monkeypatch.setenv("GIG_STOREFRONT_ROOT", str(root))
    contract = storefront._image_mutation_contract(
        {"service_id": storefront.TARGET_SERVICE_ID, "field": "image", "before": 0,
         "executable": True, "success_metric": "views_to_inquiry"},
        {"listing_version_sha256": "a" * 64, "service_image_count": 0, "service_image_ids": []},
        {"asset_path": str(asset_path), "asset_sha256": hashlib.sha256(asset).hexdigest(),
         "claim_source": "test", "platform_requirement_source": "test"},
        {storefront.TARGET_SERVICE_ID: "private_vision"},
    )

    storefront._validate_image_mutation_contract(contract)


def test_image_effect_uses_immutable_runtime_snapshot_not_mutable_bundle_source(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    _bundle(root)
    _valid_image_assets(root)
    root.joinpath("families.json").write_text(json.dumps({
        "version": 1,
        "service_families": {storefront.TARGET_SERVICE_ID: "bound",
                               storefront.GALLERY_SERVICE_ID: "bound"},
        "families": {"bound": {}},
    }), encoding="utf-8")
    monkeypatch.setenv("GIG_STOREFRONT_ROOT", str(root))
    default_state = tmp_path / "default-runtime" / "storefront-direct"
    state_dir = tmp_path / "pass-runtime" / "storefront-direct"
    monkeypatch.setattr(storefront, "DEFAULT_STATE", default_state)
    source = root / "assets" / "image.png"
    original = source.read_bytes()
    contract = storefront._image_mutation_contract(
        {"service_id": storefront.TARGET_SERVICE_ID, "field": "image", "before": 0,
         "executable": True, "success_metric": "views_to_inquiry"},
        {"listing_version_sha256": "a" * 64, "service_image_count": 0, "service_image_ids": []},
        {"asset_path": str(source), "asset_sha256": hashlib.sha256(original).hexdigest(),
         "claim_source": "test", "platform_requirement_source": "test"},
        {storefront.TARGET_SERVICE_ID: "bound"},
    )

    outside_snapshots = tmp_path / "outside-snapshots"
    outside_snapshots.mkdir()
    state_dir.mkdir(parents=True)
    snapshots_dir = state_dir / "asset-snapshots"
    snapshots_dir.symlink_to(outside_snapshots, target_is_directory=True)
    with pytest.raises(RuntimeError, match="storefront_image_snapshot_invalid"):
        storefront._snapshot_image_contract_assets(contract, state_dir=state_dir)
    assert list(outside_snapshots.iterdir()) == []
    snapshots_dir.unlink()

    snapshotted = storefront._snapshot_image_contract_assets(contract, state_dir=state_dir)
    source.write_bytes(b"changed-after-validation")
    snapshot = Path(snapshotted["proposed_value"]["asset_path"])

    assert snapshot != source and snapshot.read_bytes() == original
    assert snapshot.is_relative_to(state_dir)
    assert not default_state.exists()
    assert contract["proposed_value"]["asset_path"] == str(snapshot)
    storefront._validate_image_mutation_contract(snapshotted, state_dir=state_dir)
    with pytest.raises(RuntimeError, match="storefront_image_asset_invalid"):
        storefront._validate_image_mutation_contract(snapshotted, state_dir=default_state)


def test_verified_snapshot_upload_path_rejects_tampering_before_upload(tmp_path):
    state_dir = tmp_path / "runtime"
    snapshots_dir = state_dir / "asset-snapshots"
    snapshots_dir.mkdir(parents=True)
    snapshot = snapshots_dir / "asset.png"
    snapshot.write_bytes(_png())
    digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()

    assert storefront._verified_snapshot_upload_path(snapshot, digest, state_dir=state_dir) == str(snapshot)
    snapshot.write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="storefront_image_snapshot_identity_invalid"):
        storefront._verified_snapshot_upload_path(snapshot, digest, state_dir=state_dir)
    outside = tmp_path / "identical-external.png"
    outside.write_bytes(_png())
    snapshot.unlink()
    snapshot.symlink_to(outside)
    upload_calls = []
    with pytest.raises(RuntimeError, match="storefront_image_snapshot_invalid"):
        upload_calls.append(storefront._verified_snapshot_upload_path(
            snapshot, digest, state_dir=state_dir,
        ))
    assert upload_calls == []


def test_gallery_mutation_allows_only_hashed_assets_inside_external_bundle(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    _bundle(root)
    before = [f"image-{number}.png" for number in range(1, 7)]
    kept = before[:2]
    replacements = []
    for number in range(3, 7):
        asset_path = root / "assets" / f"gallery-{number}.png"
        content = f"gallery-{number}".encode()
        asset_path.write_bytes(content)
        replacements.append({
            "replace_image_id": before[number - 1], "asset": asset_path.name,
            "asset_sha256": hashlib.sha256(content).hexdigest(),
        })
    (root / "assets" / "gallery-contract.json").write_text(json.dumps({
        "before_image_ids": before, "kept_image_ids": kept, "replacements": replacements,
    }), encoding="utf-8")
    monkeypatch.setenv("GIG_STOREFRONT_ROOT", str(root))
    mappings = {storefront.GALLERY_SERVICE_ID: "vision"}
    monkeypatch.setattr(storefront, "_load_capability_families", lambda _path: (mappings, {}))
    asset_contract = {
        "before_image_ids": before, "kept_image_ids": kept,
        "claim_source": "test", "platform_requirement_source": "test",
        "replacements": [{**row, "asset_path": str(root / "assets" / row["asset"])} for row in replacements],
    }
    contract = storefront._render_gallery_mutation(
        {"service_id": storefront.GALLERY_SERVICE_ID, "service_image_ids": before},
        "a" * 64, asset_contract, mappings,
    )["contract"]

    storefront._validate_image_mutation_contract(contract, root / "families.json")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside")
    invalid = json.loads(json.dumps(contract))
    invalid["proposed_value"]["replacement_assets"][0]["asset_path"] = str(outside)
    invalid = storefront._seal_mutation_contract(
        {key: value for key, value in invalid.items() if key != "contract_sha256"}, mappings,
    )

    with pytest.raises(RuntimeError, match="storefront_gallery_asset_invalid"):
        storefront._validate_image_mutation_contract(invalid, root / "families.json")
    mismatched = json.loads(json.dumps(contract))
    mismatched["proposed_value"]["replacement_assets"][0]["asset_sha256"] = "0" * 64
    mismatched = storefront._seal_mutation_contract(
        {key: value for key, value in mismatched.items() if key != "contract_sha256"}, mappings,
    )

    with pytest.raises(RuntimeError, match="storefront_gallery_asset_identity_invalid"):
        storefront._validate_image_mutation_contract(mismatched, root / "families.json")


def test_confirmed_gallery_survives_gc_of_transient_before_evidence(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    _bundle(root)
    before = [f"image-{number}.png" for number in range(1, 7)]
    kept = [before[2], before[4]]
    replacements = []
    for number in (1, 2, 4, 6):
        asset_path = root / "assets" / f"gallery-{number}.png"
        content = f"gallery-{number}".encode()
        asset_path.write_bytes(content)
        replacements.append({
            "replace_image_id": before[number - 1], "asset_path": str(asset_path),
            "asset_sha256": hashlib.sha256(content).hexdigest(),
        })
    mappings = {storefront.GALLERY_SERVICE_ID: "vision"}
    monkeypatch.setenv("GIG_STOREFRONT_ROOT", str(root))
    monkeypatch.setattr(storefront, "_load_capability_families", lambda _path: (mappings, {}))
    contract = storefront._render_gallery_mutation(
        {"service_id": storefront.GALLERY_SERVICE_ID, "service_image_ids": before},
        "a" * 64,
        {"before_image_ids": before, "kept_image_ids": kept,
         "claim_source": "test", "platform_requirement_source": "test",
         "replacements": replacements},
        mappings,
    )["contract"]
    intents = tmp_path / "runtime" / "effect-intents"
    intents.mkdir(parents=True)
    (intents / "confirmed.json").write_text(json.dumps({
        "status": "confirmed", "effect_ledger_appended": True,
        "service_id": storefront.GALLERY_SERVICE_ID, "changed_field": "image",
        "public_before_path": str(tmp_path / "gc-removed.json"),
        "mutation_contract": contract,
    }), encoding="utf-8")

    rendered = storefront._render_published_gallery_mutation(
        tmp_path / "runtime",
        {"service_id": storefront.GALLERY_SERVICE_ID,
         "url": f"https://coconala.com/services/{storefront.GALLERY_SERVICE_ID}",
         "service_image_count": 6,
         "service_image_ids": ["new-1.png", "new-2.png", kept[0],
                               "new-4.png", kept[1], "new-6.png"]},
    )

    assert rendered["published"] is True
    assert rendered["contract"]["contract_sha256"] == contract["contract_sha256"]


def test_storefront_launchd_job_renders_optional_root_from_install_override(tmp_path, monkeypatch):
    import gig_release

    override = tmp_path / "install.json"
    override.write_text(json.dumps({"GIG_STOREFRONT_ROOT": "/private/storefront-bundle"}))
    monkeypatch.setattr(gig_release, "OVERRIDES", override)
    manifest, table = gig_release.settings(Path("/release"))
    job = next(row for row in manifest["jobs"] if row["label"] == "ai.anicca.hf-gig-storefront-direct")

    assert gig_release.plist_for(job, table)["EnvironmentVariables"]["GIG_STOREFRONT_ROOT"] == (
        "/private/storefront-bundle"
    )
