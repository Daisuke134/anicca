import json
import os
import stat
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/paid_release.py"


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def repository(tmp_path):
    remote, repo = tmp_path / "remote.git", tmp_path / "repo"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "clone", str(remote), str(repo)], check=True, capture_output=True)
    git(repo, "config", "user.name", "Paid Test")
    git(repo, "config", "user.email", "paid@example.test")
    entrypoint = repo / "skills/earn/gig/scripts/paid_direct.py"
    entrypoint.parent.mkdir(parents=True)
    entrypoint.write_text("import helper\nprint(helper.VALUE)\n", encoding="utf-8")
    (entrypoint.parent / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(repo, "add", "."); git(repo, "commit", "-m", "first"); git(repo, "push", "-u", "origin", "HEAD")
    return repo, entrypoint


def test_build_is_idempotent_and_tamper_is_rejected(tmp_path):
    repo, entrypoint = repository(tmp_path)
    releases = tmp_path / "releases"
    first = run("--repo", repo, "--release-root", releases, "build", "HEAD")
    assert first.returncode == 0, first.stdout + first.stderr
    commit = git(repo, "rev-parse", "HEAD")
    release = releases / commit
    manifest = json.loads((release / "RELEASE-MANIFEST.json").read_text())
    assert manifest["git_commit"] == commit and manifest["entrypoint"].endswith("paid_direct.py")
    second = run("--repo", repo, "--release-root", releases, "build", commit)
    assert second.returncode == 0 and json.loads(second.stdout)["status"] == "existing"
    released_entrypoint = release / "skills/earn/gig/scripts/paid_direct.py"
    released_entrypoint.chmod(released_entrypoint.stat().st_mode | stat.S_IWUSR)
    released_entrypoint.write_text("tampered\n", encoding="utf-8")
    checked = run("--repo", repo, "--release-root", releases, "verify", release)
    assert checked.returncode == 1 and json.loads(checked.stdout)["status"] == "failed"


def test_build_rejects_dirty_and_unpushed_repository(tmp_path):
    repo, entrypoint = repository(tmp_path)
    releases = tmp_path / "releases"
    entrypoint.write_text("dirty\n", encoding="utf-8")
    dirty = run("--repo", repo, "--release-root", releases, "build", "HEAD")
    assert dirty.returncode == 1 and "dirty" in json.loads(dirty.stdout)["error"]
    git(repo, "add", "."); git(repo, "commit", "-m", "unpushed")
    unpushed = run("--repo", repo, "--release-root", releases, "build", "HEAD")
    assert unpushed.returncode == 1 and "unpushed" in json.loads(unpushed.stdout)["error"]


def test_promote_pins_current_and_previous_release(tmp_path):
    repo, entrypoint = repository(tmp_path)
    releases = tmp_path / "releases"
    first_commit = git(repo, "rev-parse", "HEAD")
    assert run("--repo", repo, "--release-root", releases, "build", first_commit).returncode == 0
    assert run("--repo", repo, "--release-root", releases, "promote", releases / first_commit).returncode == 0
    entrypoint.write_text("import helper\nprint('second', helper.VALUE)\n", encoding="utf-8")
    git(repo, "add", "."); git(repo, "commit", "-m", "second"); git(repo, "push")
    second_commit = git(repo, "rev-parse", "HEAD")
    assert run("--repo", repo, "--release-root", releases, "build", second_commit).returncode == 0
    promoted = run("--repo", repo, "--release-root", releases, "promote", releases / second_commit)
    assert promoted.returncode == 0, promoted.stdout + promoted.stderr
    observed = run("--repo", repo, "--release-root", releases, "status")
    payload = json.loads(observed.stdout)
    assert payload["current"].endswith(second_commit)
    assert payload["previous"].endswith(first_commit)
    assert payload["pinned"] == [str(releases / second_commit), str(releases / first_commit)]

    entrypoint.write_text("import helper\nprint('third', helper.VALUE)\n", encoding="utf-8")
    git(repo, "add", "."); git(repo, "commit", "-m", "third"); git(repo, "push")
    third_commit = git(repo, "rev-parse", "HEAD")
    assert run("--repo", repo, "--release-root", releases, "build", third_commit).returncode == 0
    assert run("--repo", repo, "--release-root", releases, "promote", releases / third_commit).returncode == 0

    collected = run("--repo", repo, "--release-root", releases, "gc")
    gc_payload = json.loads(collected.stdout)
    assert collected.returncode == 0 and gc_payload["status"] == "collected"
    assert not (releases / first_commit).exists()
    assert (releases / second_commit).exists() and (releases / third_commit).exists()
