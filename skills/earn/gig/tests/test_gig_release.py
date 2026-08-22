import importlib.util
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).parents[1] / "scripts" / "gig_release.py"
SPEC = importlib.util.spec_from_file_location("gig_release_gc_test", SCRIPT)
gig_release = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gig_release)


def test_gc_preserves_release_referenced_by_loaded_launchd_job(tmp_path, monkeypatch):
    current_sha = "a" * 40
    loaded_sha = "b" * 40
    rollback_sha = "c" * 40
    stale_sha = "d" * 40
    for sha in (current_sha, loaded_sha, rollback_sha, stale_sha):
        release = tmp_path / sha
        release.mkdir()
        (release / "marker").write_text(sha, encoding="utf-8")
    (tmp_path / "current").symlink_to(current_sha)

    monkeypatch.setattr(gig_release, "RELEASE_ROOT", tmp_path)
    monkeypatch.setattr(gig_release, "CURRENT_RELEASE", tmp_path / "current")
    monkeypatch.setattr(
        gig_release,
        "loaded_program",
        lambda label: ["/bin/bash", str(tmp_path / loaded_sha / "browser.sh")],
    )
    monkeypatch.setattr(
        gig_release.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=""),
    )

    removed = gig_release.collect_old_releases()

    assert loaded_sha not in removed
    assert (tmp_path / loaded_sha).is_dir()


def test_gc_preserves_release_pinned_by_live_wrapper(tmp_path, monkeypatch):
    current_sha = "a" * 40
    pinned_sha = "b" * 40
    rollback_sha = "c" * 40
    stale_sha = "d" * 40
    for sha in (current_sha, pinned_sha, rollback_sha, stale_sha):
        release = tmp_path / sha
        release.mkdir()
        (release / "marker").write_text(sha, encoding="utf-8")
    (tmp_path / "current").symlink_to(current_sha)
    parent = tmp_path / pinned_sha / "skills" / "earn" / "gig" / "scripts" / "application_parent.py"
    parent.parent.mkdir(parents=True)
    parent.touch()

    monkeypatch.setattr(gig_release, "RELEASE_ROOT", tmp_path)
    monkeypatch.setattr(gig_release, "CURRENT_RELEASE", tmp_path / "current")
    monkeypatch.setattr(gig_release, "loaded_program", lambda _label: [])
    monkeypatch.setattr(gig_release.os, "getpid", lambda: 4242)
    monkeypatch.setattr(gig_release.os, "kill", lambda pid, signal: None)
    monkeypatch.setattr(
        gig_release.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=""),
    )

    marker = gig_release.pin_release_for_process(parent)
    removed = gig_release.collect_old_releases()

    assert marker == tmp_path / ".pins" / f"4242-{pinned_sha}"
    assert pinned_sha not in removed
    assert (tmp_path / pinned_sha).is_dir()
