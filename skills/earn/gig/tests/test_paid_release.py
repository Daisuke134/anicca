from __future__ import annotations

import importlib.util
import tarfile
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "paid_release.py"


def load():
    spec = importlib.util.spec_from_file_location("paid_release_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_filter_accepts_internal_relative_symlink(tmp_path):
    release = load()
    member = tarfile.TarInfo("skills/goal-setter")
    member.type = tarfile.SYMTYPE
    member.linkname = "../.agents/skills/goal-setter"

    assert release._release_filter(member, str(tmp_path)) is member


def test_release_filter_rejects_symlink_outside_release(tmp_path):
    release = load()
    member = tarfile.TarInfo("skills/escape")
    member.type = tarfile.SYMTYPE
    member.linkname = "../../outside"

    with pytest.raises(release.ReleaseError, match="symlink escapes root"):
        release._release_filter(member, str(tmp_path))


def test_default_repo_is_repository_root():
    release = load()

    assert release.DEFAULT_REPO == SCRIPT.parents[4]
    assert (release.DEFAULT_REPO / release.ENTRYPOINT).is_file()
