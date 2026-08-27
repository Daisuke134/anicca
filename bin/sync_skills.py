#!/usr/bin/env python3
"""sync_skills.py — REQ-VENDOR-002 backend for bin/sync-skills.sh. For each skills.lock entry,
materializes <source_path> at <source_commit> from <source_repo>'s local git clone into this
repo's vendor destination, via `git archive` into a staging dir first (so a failure -- e.g. the
source path is absent at the pinned commit -- never leaves a partial vendor tree behind).

Destination layout (a fixed, name-keyed lookup -- not a judgment call):
  - The Life Manager skill directories (Phase A action skills plus the planning-only
    `dig` skill) land at
    <VENDOR_ROOT>/skills/life-manager/vendor/<name>/ (directory copy).
  - Every other entry (single-file sources, e.g. ytdlp-parse-shared-lib, or a test fixture skill)
    lands at <VENDOR_ROOT>/lib/vendor/<name>/<basename(source_path)> (file copy).

Env overrides (test isolation, tests/vendor/test_sync_skills.sh):
  SKILLS_LOCK_FILE        default <repo_root>/skills.lock
  VENDOR_ROOT             default <repo_root>
  SOURCE_REPO_ROOT_<REPO> local git clone root for that skills.lock entry's `source_repo`
                          (e.g. SOURCE_REPO_ROOT_OPENCLAW, SOURCE_REPO_ROOT_ANICCA)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LIB_DIR = os.path.join(_REPO_ROOT, "lib")
sys.path.insert(0, _LIB_DIR)
from vendor_hash import hash_path  # noqa: E402
from vendor_layout import artifact_path as _artifact_path  # noqa: E402


def _repo_root():
    return _REPO_ROOT


def _lock_path():
    return os.environ.get("SKILLS_LOCK_FILE") or os.path.join(_repo_root(), "skills.lock")


def _vendor_root():
    return os.environ.get("VENDOR_ROOT") or _repo_root()


def _source_repo_root_env_name(source_repo):
    return "SOURCE_REPO_ROOT_" + "".join(c if c.isalnum() else "_" for c in source_repo.upper())


def _write_lock(lock_path, entries):
    directory = os.path.dirname(lock_path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".skills-lock-", suffix=".json.tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp_path, lock_path)


def _git(args, cwd):
    return subprocess.run(["git", "-C", cwd] + args, capture_output=True, text=True)


def _update_one(entry, vendor_root, errors):
    name = entry["name"]
    source_repo = entry["source_repo"]
    source_path = entry["source_path"]
    commit = entry["source_commit"]

    src_root = os.environ.get(_source_repo_root_env_name(source_repo))
    if not src_root or not os.path.isdir(src_root):
        errors.append(f"{name}: no SOURCE_REPO_ROOT for source_repo={source_repo!r} (checked ${_source_repo_root_env_name(source_repo)})")
        return

    resolve = _git(["cat-file", "-e", commit], src_root)
    if resolve.returncode != 0:
        errors.append(f"{name}: source_commit {commit!r} does not resolve in {source_repo!r} ({resolve.stderr.strip()})")
        return

    exists = _git(["cat-file", "-e", f"{commit}:{source_path}"], src_root)
    if exists.returncode != 0:
        errors.append(f"{name}: source_path {source_path!r} absent at commit {commit} in {source_repo!r}")
        return

    staging = tempfile.mkdtemp(prefix="sync-skills-staging-")
    try:
        archive = subprocess.Popen(["git", "-C", src_root, "archive", commit, "--", source_path],
                                    stdout=subprocess.PIPE)
        tar = subprocess.Popen(["tar", "-x", "-C", staging], stdin=archive.stdout)
        archive.stdout.close()
        tar.communicate()
        archive.wait()
        if archive.returncode != 0 or tar.returncode != 0:
            errors.append(f"{name}: git archive/tar extraction failed for {source_path}@{commit}")
            return

        extracted = os.path.join(staging, source_path)
        if not os.path.exists(extracted):
            errors.append(f"{name}: extraction produced no content at {source_path!r}")
            return

        artifact = _artifact_path(vendor_root, name, source_path)
        artifact_dir = os.path.dirname(artifact)
        os.makedirs(artifact_dir, exist_ok=True)
        if os.path.isdir(artifact):
            shutil.rmtree(artifact)
        elif os.path.isfile(artifact):
            os.remove(artifact)
        shutil.move(extracted, artifact)

        entry["sha256"] = hash_path(artifact)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _verify_one(entry, vendor_root, errors):
    name = entry["name"]
    source_path = entry["source_path"]
    artifact = _artifact_path(vendor_root, name, source_path)
    if not os.path.exists(artifact):
        errors.append(f"{name}: DRIFT (missing) -- vendored path {artifact} does not exist")
        return
    current = hash_path(artifact)
    recorded = entry.get("sha256")
    if current != recorded:
        errors.append(f"{name}: DRIFT (checksum mismatch) -- recorded={recorded} current={current}")


def main():
    update = "--update" in sys.argv[1:]
    lock_path = _lock_path()
    vendor_root = _vendor_root()

    try:
        with open(lock_path) as f:
            entries = json.load(f)
    except Exception as e:
        print(f"sync-skills: cannot read skills.lock at {lock_path} ({e})", file=sys.stderr)
        return 1

    errors = []
    for entry in entries:
        if update:
            _update_one(entry, vendor_root, errors)
        else:
            _verify_one(entry, vendor_root, errors)

    if update:
        _write_lock(lock_path, entries)

    if errors:
        for e in errors:
            print(f"sync-skills: {e}", file=sys.stderr)
        return 1

    if update:
        print("sync-skills: --update complete, all entries vendored + skills.lock updated")
    else:
        print("sync-skills: clean -- all vendored checksums match skills.lock")
    return 0


if __name__ == "__main__":
    sys.exit(main())
