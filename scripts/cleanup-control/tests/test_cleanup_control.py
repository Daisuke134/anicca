from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock

import pytest


MODULE_PATH = Path(__file__).parents[1] / "cleanup_control.py"
SPEC = importlib.util.spec_from_file_location("cleanup_control", MODULE_PATH)
assert SPEC and SPEC.loader
cleanup_control = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cleanup_control)


def test_path_open_state_treats_nonempty_lsof_output_as_open() -> None:
    result = subprocess.CompletedProcess(
        args=["lsof"],
        returncode=1,
        stdout="COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME\nCodexBar 1 user 4u REG 1,1 1 1 /tmp/cache/db\n",
        stderr="",
    )

    with mock.patch.object(cleanup_control, "_command", return_value=result):
        assert cleanup_control.path_open_state(Path("/tmp/cache")) == "open"


def entry(
    path: Path,
    *,
    artifact_class: str = "ephemeral",
    ttl_seconds: int | None = 60,
    quota_bytes: int = 0,
    lease: dict[str, object] | None = None,
    finalizer: str | None = None,
) -> dict[str, object]:
    return {
        "id": path.name.replace(".", "dot-") or "root",
        "path": str(path),
        "owner": "test-owner",
        "class": artifact_class,
        "ttl_seconds": ttl_seconds,
        "quota_bytes": quota_bytes,
        "lease": lease,
        "finalizer": {
            "kind": finalizer
            or ("off_volume_quarantine" if artifact_class == "ephemeral" else "preserve")
        },
    }


def write_manifest(path: Path, entries: list[dict[str, object]]) -> Path:
    path.write_text(
        json.dumps({"policy_version": "cleanup-v1", "artifacts": entries}),
        encoding="utf-8",
    )
    return path


def make_old(path: Path, now: int, age_seconds: int = 120) -> None:
    stamp = now - age_seconds
    for child in sorted(path.rglob("*"), reverse=True):
        os.utime(child, (stamp, stamp), follow_symlinks=False)
    os.utime(path, (stamp, stamp), follow_symlinks=False)


def run(
    manifest: Path,
    quarantine: Path,
    ledger: Path,
    *,
    now: int,
    candidates: list[Path] | None = None,
    cross_device: bool = True,
    create_quarantine: bool = True,
    pressure_override: bool = False,
    reclaim_target_bytes: int = 0,
):
    if create_quarantine:
        quarantine.mkdir(parents=True, exist_ok=True)

    def fake_device(path: Path) -> int:
        resolved = Path(path).resolve()
        if cross_device and (resolved == quarantine.resolve() or quarantine.resolve() in resolved.parents):
            return 22
        return 11

    with mock.patch.object(cleanup_control, "device_id", side_effect=fake_device):
        return cleanup_control.sweep(
            manifest_path=manifest,
            quarantine_root=quarantine,
            ledger_path=ledger,
            now=now,
            candidates=candidates,
            pressure_override=pressure_override,
            reclaim_target_bytes=reclaim_target_bytes,
        )


def test_runtime_manifest_discovers_only_ignored_proven_regenerable_outputs(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(
        ["git", "init", "-q", str(repository)],
        check=True,
        text=True,
        capture_output=True,
    )
    (repository / ".gitignore").write_text(
        "node_modules/\n.venv/\n!unignored/\n!unignored/node_modules/\n",
        encoding="utf-8",
    )
    (repository / "package-lock.json").write_text('{"lockfileVersion":3}\n', encoding="utf-8")
    eligible = repository / "node_modules"
    eligible.mkdir()
    (eligible / "payload").write_bytes(b"x" * 128)

    no_proof = repository / "work" / "node_modules"
    no_proof.mkdir(parents=True)
    (no_proof / "payload").write_bytes(b"keep")

    unignored = repository / "unignored" / "node_modules"
    unignored.mkdir(parents=True)
    (unignored.parent / "package-lock.json").write_text(
        '{"lockfileVersion":3}\n',
        encoding="utf-8",
    )
    (unignored / "payload").write_bytes(b"keep")

    protected = repository / ".claude" / "private" / "node_modules"
    protected.mkdir(parents=True)
    (protected.parent / "package-lock.json").write_text(
        '{"lockfileVersion":3}\n',
        encoding="utf-8",
    )
    (protected / "payload").write_bytes(b"keep")

    base = write_manifest(tmp_path / "base.json", [])
    before = base.read_bytes()
    runtime = tmp_path / "runtime.json"
    cache_root = tmp_path / "Caches"
    pnpm_cache = cache_root / "pnpm"
    pnpm_cache.mkdir(parents=True)
    (pnpm_cache / "payload").write_bytes(b"x" * 128)
    browser_cache = cache_root / "camoufox"
    browser_cache.mkdir()
    (browser_cache / "payload").write_bytes(b"keep")
    command = [
        sys.executable,
        str(MODULE_PATH),
        "runtime-manifest",
        "--manifest",
        str(base),
        "--output",
        str(runtime),
        "--root",
        str(repository),
        "--cache-root",
        str(cache_root),
        "--min-cache-bytes",
        "1",
    ]

    first = subprocess.run(command, text=True, capture_output=True, check=False)
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout) == {
        "discovered": 2,
        "output": str(runtime),
        "status": "ok",
    }
    assert base.read_bytes() == before

    generated = json.loads(runtime.read_text(encoding="utf-8"))
    build_outputs = [
        item
        for item in generated["artifacts"]
        if item["owner"] == "cleanup-discovery"
        and item["class"] == "regenerable_output"
    ]
    assert build_outputs == [
        {
            "class": "regenerable_output",
            "finalizer": {
                "kind": "verified_regenerable_remove",
                "proof_path": str(repository / "package-lock.json"),
            },
            "id": build_outputs[0]["id"],
            "lease": None,
            "owner": "cleanup-discovery",
            "path": str(eligible),
            "quota_bytes": 0,
            "ttl_seconds": None,
        }
    ]
    cache_outputs = [
        item
        for item in generated["artifacts"]
        if item["owner"] == "cleanup-discovery" and item["class"] == "ephemeral"
    ]
    assert cache_outputs == [
        {
            "class": "ephemeral",
            "finalizer": {"kind": "off_volume_quarantine"},
            "id": cache_outputs[0]["id"],
            "lease": None,
            "owner": "cleanup-discovery",
            "path": str(pnpm_cache),
            "quota_bytes": 0,
            "ttl_seconds": 604800,
        }
    ]
    assert str(browser_cache) not in {item["path"] for item in generated["artifacts"]}
    assert str(no_proof) not in {item["path"] for item in generated["artifacts"]}
    assert str(unignored) not in {item["path"] for item in generated["artifacts"]}
    assert str(protected) not in {item["path"] for item in generated["artifacts"]}

    second = subprocess.run(command, text=True, capture_output=True, check=False)
    assert second.returncode == 0, second.stderr
    assert runtime.read_text(encoding="utf-8") == json.dumps(
        generated,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def test_runtime_manifest_discovers_exact_chrome_code_sign_clone_children(
    tmp_path: Path,
) -> None:
    scan_root = tmp_path / "empty-root"
    scan_root.mkdir()
    code_sign_root = tmp_path / "X"
    clone_collection = code_sign_root / "com.google.Chrome.code_sign_clone"
    active = clone_collection / "code_sign_clone.active"
    stale = clone_collection / "code_sign_clone.stale"
    unrelated = clone_collection / "not-a-code-sign-clone"
    for candidate in (active, stale, unrelated):
        candidate.mkdir(parents=True)
        (candidate / "payload").write_bytes(b"x" * 128)
    symlinked = clone_collection / "code_sign_clone.symlink"
    symlinked.symlink_to(stale, target_is_directory=True)

    chrome_proof = tmp_path / "Google Chrome"
    chrome_proof.write_bytes(b"executable")
    base = write_manifest(tmp_path / "base.json", [])
    runtime = tmp_path / "runtime.json"
    command = [
        sys.executable,
        str(MODULE_PATH),
        "runtime-manifest",
        "--manifest",
        str(base),
        "--output",
        str(runtime),
        "--root",
        str(scan_root),
        "--code-sign-clone-root",
        str(code_sign_root),
        "--chrome-code-sign-proof",
        str(chrome_proof),
    ]

    result = subprocess.run(command, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["discovered"] == 2
    artifacts = json.loads(runtime.read_text(encoding="utf-8"))["artifacts"]
    assert [artifact["path"] for artifact in artifacts] == [str(active), str(stale)]
    assert {artifact["owner"] for artifact in artifacts} == {"macos-code-sign-clone"}
    assert {artifact["class"] for artifact in artifacts} == {"regenerable_output"}
    assert {
        artifact["finalizer"]["proof_path"]
        for artifact in artifacts
    } == {str(chrome_proof)}
    assert str(unrelated) not in {artifact["path"] for artifact in artifacts}
    assert str(symlinked) not in {artifact["path"] for artifact in artifacts}


def test_runtime_manifest_discovers_exact_pnpm_store_versions(tmp_path: Path) -> None:
    scan_root = tmp_path / "empty-root"
    scan_root.mkdir()
    store_root = tmp_path / "pnpm" / "store"
    current = store_root / "v10"
    previous = store_root / "v9"
    unrelated = store_root / "metadata"
    for candidate in (current, previous, unrelated):
        candidate.mkdir(parents=True)
        (candidate / "payload").write_bytes(b"x" * 128)
    symlinked = store_root / "v11"
    symlinked.symlink_to(current, target_is_directory=True)

    pnpm_proof = tmp_path / "pnpm.cjs"
    pnpm_proof.write_bytes(b"executable")
    base = write_manifest(tmp_path / "base.json", [])
    runtime = tmp_path / "runtime.json"
    command = [
        sys.executable,
        str(MODULE_PATH),
        "runtime-manifest",
        "--manifest",
        str(base),
        "--output",
        str(runtime),
        "--root",
        str(scan_root),
        "--pnpm-store-root",
        str(store_root),
        "--pnpm-proof",
        str(pnpm_proof),
    ]

    result = subprocess.run(command, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["discovered"] == 2
    artifacts = json.loads(runtime.read_text(encoding="utf-8"))["artifacts"]
    assert [artifact["path"] for artifact in artifacts] == [str(current), str(previous)]
    assert {artifact["owner"] for artifact in artifacts} == {"pnpm-store"}
    assert {artifact["class"] for artifact in artifacts} == {"regenerable_output"}
    assert {
        artifact["finalizer"]["proof_path"]
        for artifact in artifacts
    } == {str(pnpm_proof)}
    assert str(unrelated) not in {artifact["path"] for artifact in artifacts}
    assert str(symlinked) not in {artifact["path"] for artifact in artifacts}


def test_runtime_manifest_discovers_only_verified_published_runs(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    runs = tmp_path / "runs"
    runs.mkdir()

    published = runs / "published"
    published.mkdir()
    proof = published / "reel-meta.json"
    proof.write_text(
        json.dumps(
            {
                "postId": "post-123",
                "postedAt": "2026-07-19T11:05:22.000Z",
                "integration": "integration-456",
                "method": "DIRECT_POST",
            }
        ),
        encoding="utf-8",
    )
    (published / "reel-final.mp4").write_bytes(b"published-video")

    malformed = runs / "malformed"
    malformed.mkdir()
    (malformed / "reel-meta.json").write_text('{"postId":""}', encoding="utf-8")
    (malformed / "reel-final.mp4").write_bytes(b"keep")

    symlinked_proof = runs / "symlinked-proof"
    symlinked_proof.mkdir()
    (symlinked_proof / "reel-meta.json").symlink_to(proof)
    (symlinked_proof / "reel-final.mp4").write_bytes(b"keep")

    missing_output = runs / "missing-output"
    missing_output.mkdir()
    (missing_output / "reel-meta.json").write_text(proof.read_text(encoding="utf-8"), encoding="utf-8")

    empty_output = runs / "empty-output"
    empty_output.mkdir()
    (empty_output / "reel-meta.json").write_text(proof.read_text(encoding="utf-8"), encoding="utf-8")
    (empty_output / "reel-final.mp4").touch()

    base = write_manifest(tmp_path / "base.json", [])
    runtime = tmp_path / "runtime.json"
    command = [
        sys.executable,
        str(MODULE_PATH),
        "runtime-manifest",
        "--manifest",
        str(base),
        "--output",
        str(runtime),
        "--root",
        str(repository),
        "--published-run-root",
        str(runs),
    ]

    result = subprocess.run(command, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["discovered"] == 1

    generated = json.loads(runtime.read_text(encoding="utf-8"))
    assert generated["artifacts"] == [
        {
            "class": "regenerable_output",
            "finalizer": {
                "kind": "verified_regenerable_remove",
                "proof_path": str(proof),
            },
            "id": generated["artifacts"][0]["id"],
            "lease": None,
            "owner": "reelclaw",
            "path": str(published),
            "quota_bytes": 0,
            "ttl_seconds": None,
        }
    ]


@pytest.mark.parametrize("mode", ["missing", "corrupt", "missing-field"])
def test_manifest_failure_is_fail_closed(tmp_path: Path, mode: str) -> None:
    source = tmp_path / "cache"
    source.mkdir()
    (source / "payload").write_text("keep", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    if mode == "corrupt":
        manifest.write_text("{not json", encoding="utf-8")
    elif mode == "missing-field":
        bad = entry(source)
        del bad["owner"]
        write_manifest(manifest, [bad])

    result = run(manifest, tmp_path / "q", tmp_path / "ledger.jsonl", now=1_000)

    assert result["status"] == "manifest_error"
    assert source.exists()
    assert result["quarantined"] == 0


def test_unknown_candidate_is_reported_and_preserved(tmp_path: Path) -> None:
    known = tmp_path / "known"
    unknown = tmp_path / "unknown"
    known.mkdir()
    unknown.mkdir()
    (unknown / "payload").write_text("keep", encoding="utf-8")
    manifest = write_manifest(tmp_path / "manifest.json", [entry(known)])
    ledger = tmp_path / "ledger.jsonl"

    result = run(
        manifest,
        tmp_path / "q",
        ledger,
        now=1_000,
        candidates=[unknown],
    )

    assert result == {
        "status": "ok",
        "evaluated": 1,
        "quarantined": 0,
        "preserved": 1,
        "errors": 0,
        "bytes_quarantined": 0,
    }
    assert unknown.exists()
    event = json.loads(ledger.read_text(encoding="utf-8").splitlines()[-1])
    assert (event["event"], event["reason"]) == ("preserved", "unknown_artifact")


def test_active_lease_and_deliverable_are_preserved(tmp_path: Path) -> None:
    now = 10_000
    active = tmp_path / "active-cache"
    deliverable = tmp_path / "delivery.zip"
    lease = tmp_path / "active.lease"
    active.mkdir()
    (active / "payload").write_text("keep", encoding="utf-8")
    deliverable.write_text("customer work", encoding="utf-8")
    lease.write_text("owner=worker", encoding="utf-8")
    make_old(active, now)
    make_old(deliverable, now)
    os.utime(lease, (now - 5, now - 5))
    entries = [
        entry(
            active,
            lease={"path": str(lease), "max_age_seconds": 30},
        ),
        entry(
            deliverable,
            artifact_class="deliverable",
            ttl_seconds=None,
            finalizer="preserve",
        ),
    ]
    ledger = tmp_path / "ledger.jsonl"

    result = run(
        write_manifest(tmp_path / "manifest.json", entries),
        tmp_path / "q",
        ledger,
        now=now,
    )

    assert result["quarantined"] == 0
    assert result["preserved"] == 2
    assert active.exists() and deliverable.exists()
    reasons = {json.loads(line)["reason"] for line in ledger.read_text().splitlines()}
    assert reasons == {"active_lease", "protected_class"}


def test_only_expired_over_quota_ephemeral_is_quarantined(tmp_path: Path) -> None:
    now = 10_000
    expired = tmp_path / "expired"
    fresh = tmp_path / "fresh"
    under_quota = tmp_path / "under-quota"
    for path in (expired, fresh, under_quota):
        path.mkdir()
        (path / "payload").write_bytes(path.name.encode() * 20)
    make_old(expired, now)
    make_old(under_quota, now)
    entries = [entry(expired), entry(fresh), entry(under_quota, quota_bytes=10_000)]
    quarantine = tmp_path / "q"
    ledger = tmp_path / "ledger.jsonl"

    result = run(
        write_manifest(tmp_path / "manifest.json", entries),
        quarantine,
        ledger,
        now=now,
    )

    assert result["quarantined"] == 1
    assert not expired.exists()
    assert fresh.exists() and under_quota.exists()
    quarantined = [json.loads(line) for line in ledger.read_text().splitlines() if json.loads(line)["event"] == "quarantined"]
    assert len(quarantined) == 1
    assert quarantined[0]["path"] == str(expired)
    assert Path(quarantined[0]["quarantine_path"]).exists()
    assert quarantined[0]["manifest_sha256"]


def test_pressure_override_reclaims_fresh_closed_ephemeral_until_target(
    tmp_path: Path,
) -> None:
    now = 10_000
    first = tmp_path / "first-cache"
    second = tmp_path / "second-cache"
    for path in (first, second):
        path.mkdir()
        (path / "payload").write_bytes(b"x" * 128)
    ledger = tmp_path / "ledger.jsonl"

    with mock.patch.object(cleanup_control, "path_open_state", return_value="confirmed-closed"):
        result = run(
            write_manifest(tmp_path / "manifest.json", [entry(first), entry(second)]),
            tmp_path / "q",
            ledger,
            now=now,
            pressure_override=True,
            reclaim_target_bytes=1,
        )

    assert result["quarantined"] == 1
    assert not first.exists()
    assert second.exists()
    events = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert any(
        event["path"] == str(second) and event["reason"] == "pressure_target_met"
        for event in events
    )


@pytest.mark.parametrize(
    ("open_state", "expected_reason"),
    [("open", "open_path"), ("unknown", "lsof_error")],
)
def test_pressure_override_preserves_fresh_ephemeral_unless_confirmed_closed(
    tmp_path: Path,
    open_state: str,
    expected_reason: str,
) -> None:
    now = 10_000
    source = tmp_path / "fresh-cache"
    source.mkdir()
    (source / "payload").write_bytes(b"x" * 128)
    ledger = tmp_path / "ledger.jsonl"

    with mock.patch.object(cleanup_control, "path_open_state", return_value=open_state):
        result = run(
            write_manifest(tmp_path / "manifest.json", [entry(source)]),
            tmp_path / "q",
            ledger,
            now=now,
            pressure_override=True,
            reclaim_target_bytes=1,
        )

    assert result["quarantined"] == 0
    assert source.exists()
    assert json.loads(ledger.read_text().splitlines()[-1])["reason"] == expected_reason


def test_same_volume_quarantine_is_fail_closed(tmp_path: Path) -> None:
    now = 10_000
    source = tmp_path / "expired"
    source.mkdir()
    (source / "payload").write_text("keep", encoding="utf-8")
    make_old(source, now)
    ledger = tmp_path / "ledger.jsonl"

    result = run(
        write_manifest(tmp_path / "manifest.json", [entry(source)]),
        tmp_path / "q",
        ledger,
        now=now,
        cross_device=False,
    )

    assert result["quarantined"] == 0
    assert result["errors"] == 1
    assert source.exists()
    assert json.loads(ledger.read_text().splitlines()[-1])["reason"] == "quarantine_not_off_volume"


@pytest.mark.parametrize("incident_name", [".venv", "wip-clone", "dist", "reelclaw-assets"])
def test_past_incident_artifacts_are_preserved(tmp_path: Path, incident_name: str) -> None:
    now = 10_000
    source = tmp_path / incident_name
    source.mkdir()
    (source / "important").write_text("must survive", encoding="utf-8")
    make_old(source, now, age_seconds=10_000)
    manifest = write_manifest(tmp_path / "manifest.json", [])

    result = run(
        manifest,
        tmp_path / "q",
        tmp_path / "ledger.jsonl",
        now=now,
        candidates=[source],
    )

    assert result["quarantined"] == 0
    assert (source / "important").read_text() == "must survive"


def test_restore_round_trip_and_conflict_fail_closed(tmp_path: Path) -> None:
    now = int(time.time())
    source = tmp_path / "expired"
    source.mkdir()
    (source / "nested").mkdir()
    (source / "nested" / "payload.bin").write_bytes(b"irrecoverable-customer-evidence")
    make_old(source, now)
    quarantine = tmp_path / "q"
    ledger = tmp_path / "ledger.jsonl"
    manifest = write_manifest(tmp_path / "manifest.json", [entry(source)])
    result = run(manifest, quarantine, ledger, now=now)
    assert result["quarantined"] == 1
    q_event = next(
        json.loads(line)
        for line in ledger.read_text().splitlines()
        if json.loads(line)["event"] == "quarantined"
    )

    restore = cleanup_control.restore(
        transaction_id=q_event["transaction_id"],
        quarantine_root=quarantine,
        ledger_path=ledger,
    )

    assert restore["status"] == "restored"
    assert (source / "nested" / "payload.bin").read_bytes() == b"irrecoverable-customer-evidence"
    assert json.loads(ledger.read_text().splitlines()[-1])["event"] == "restored"

    conflict_source = tmp_path / "conflict"
    conflict_source.write_text("original", encoding="utf-8")
    old = tmp_path / "old-conflict"
    old.write_text("quarantine me", encoding="utf-8")
    os.utime(old, (now - 120, now - 120))
    result = run(
        write_manifest(tmp_path / "manifest-2.json", [entry(old)]),
        quarantine,
        ledger,
        now=now,
    )
    event = [json.loads(line) for line in ledger.read_text().splitlines() if json.loads(line)["event"] == "quarantined"][-1]
    record = Path(event["quarantine_path"]).parent / "record.json"
    data = json.loads(record.read_text())
    data["original_path"] = str(conflict_source)
    record.write_text(json.dumps(data), encoding="utf-8")

    refused = cleanup_control.restore(
        transaction_id=event["transaction_id"],
        quarantine_root=quarantine,
        ledger_path=ledger,
    )

    assert refused["status"] == "conflict"
    assert conflict_source.read_text() == "original"


def test_regenerable_output_requires_lockfile_proof_and_closed_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "object.o").write_bytes(b"x" * 1024)
    proof = tmp_path / "Cargo.lock"
    proof.write_text("[[package]]\n", encoding="utf-8")
    entry = {
        "id": "cargo-target",
        "path": str(target),
        "owner": "cargo",
        "class": "regenerable_output",
        "ttl_seconds": None,
        "quota_bytes": 0,
        "lease": None,
        "finalizer": {
            "kind": "verified_regenerable_remove",
            "proof_path": str(proof),
        },
    }
    manifest = write_manifest(tmp_path / "manifest.json", [entry])
    monkeypatch.setattr(cleanup_control, "path_open_state", lambda _: "confirmed-closed")

    result = run(manifest, tmp_path / "q", tmp_path / "ledger.jsonl", now=1_000)

    assert result["quarantined"] == 1
    assert result["bytes_quarantined"] >= 1024
    assert not target.exists()

    missing_proof_target = tmp_path / "missing-proof-target"
    missing_proof_target.mkdir()
    entry["path"] = str(missing_proof_target)
    entry["finalizer"]["proof_path"] = str(tmp_path / "missing.lock")
    missing_manifest = write_manifest(tmp_path / "missing.json", [entry])
    preserved = run(
        missing_manifest, tmp_path / "q", tmp_path / "missing-ledger.jsonl", now=1_000
    )
    assert preserved["quarantined"] == 0
    assert missing_proof_target.exists()

    open_target = tmp_path / "open-target"
    open_target.mkdir()
    entry["path"] = str(open_target)
    entry["finalizer"]["proof_path"] = str(proof)
    open_manifest = write_manifest(tmp_path / "open.json", [entry])
    monkeypatch.setattr(cleanup_control, "path_open_state", lambda _: "open")
    open_result = run(
        open_manifest, tmp_path / "q", tmp_path / "open-ledger.jsonl", now=1_000
    )
    assert open_result["quarantined"] == 0
    assert open_target.exists()


def test_expired_ephemeral_is_removed_when_quarantine_volume_is_absent(
    tmp_path: Path,
) -> None:
    # Measured 2026-07-26: /Volumes/AniccaQuarantine does not exist, so every
    # ephemeral candidate returned quarantine_unavailable and the guard idled
    # at "no-eligible-reclaim" through a real ENOSPC. An expired ephemeral
    # artifact is regenerable by definition — when the off-volume store is
    # absent it is removed directly, and the ledger records why.
    now = 10_000
    expired = tmp_path / "expired"
    expired.mkdir()
    (expired / "payload").write_bytes(b"cache" * 20)
    make_old(expired, now)
    ledger = tmp_path / "ledger.jsonl"

    absent = tmp_path / "absent-quarantine"
    result = run(
        write_manifest(tmp_path / "manifest.json", [entry(expired)]),
        absent,
        ledger,
        now=now,
        create_quarantine=False,
    )

    assert result["quarantined"] == 1
    assert not expired.exists()
    assert not absent.exists()
    events = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert any(
        e["reason"] == "quarantine_unavailable_direct_remove" for e in events
    ), "the ledger must record why the artifact was removed in place"
