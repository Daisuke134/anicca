"""RED phase — self-improve-checkpoint-resume, Group CR-FIND (pure checkpoint discovery).

Traces to behavioral-spec.md REQ-CR1-5, REQ-CR10, REQ-CR11, EDGE-CR1-12; verification-
architecture.md PROP-CR1, PROP-CR1b, PROP-CR2-12, PROP-CR14.

`lib/checkpoint_resume.py` does not exist yet — every test below is EXPECTED TO FAIL at RED-phase
time (a collection-time `ModuleNotFoundError`/`ImportError` for `lib.checkpoint_resume`, or a
`FileNotFoundError` in the source-text-scan tests that open the not-yet-created file directly).

EDGE-CR1: `runs/` is gitignored in this worktree (`skills/earn/self-improve/.gitignore` contains
`runs/`) — every fixture below builds its own synthetic `runs_dir` tree under pytest's `tmp_path`.
No test here ever reads, symlinks, or copies this worktree's own (nonexistent) `runs/` directory.
"""
import os
import re

import pytest

from lib import checkpoint_resume

SELF_IMPROVE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKPOINT_RESUME_SOURCE_PATH = os.path.join(SELF_IMPROVE_DIR, "lib", "checkpoint_resume.py")

# A fixed, always-valid current_run_id used by tests that don't care about its exact value (it
# just needs to match REQ-CR10's run-directory-name shape so it is a real candidate that gets
# correctly excluded per REQ-CR2/EDGE-CR9, not accidentally treated as non-run-shaped noise).
CURRENT_RUN_ID = "run-20260103T000000Z"


def _mkrun(runs_dir, run_id):
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _mkcheckpoint(run_dir, n):
    checkpoint_dir = run_dir / "checkpoints" / f"checkpoint_{n}"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return checkpoint_dir


# --- PROP-CR1: nonexistent runs_dir -> None (REQ-CR4, EDGE-CR2) ---


def test_prop_cr1_returns_none_for_nonexistent_runs_dir(tmp_path):
    missing_runs_dir = tmp_path / "does-not-exist"
    result = checkpoint_resume.find_latest_checkpoint(str(missing_runs_dir), CURRENT_RUN_ID)
    assert result is None


# --- PROP-CR1b: relative runs_dir still returns an ABSOLUTE path (REQ-CR1) ---


def test_prop_cr1b_relative_runs_dir_returns_absolute_path(tmp_path, monkeypatch):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    older = _mkrun(runs_dir, "run-20260101T000000Z")
    expected_checkpoint = _mkcheckpoint(older, 5)
    monkeypatch.chdir(tmp_path)

    result = checkpoint_resume.find_latest_checkpoint("runs", CURRENT_RUN_ID)

    assert result is not None
    assert os.path.isabs(result) is True
    assert result == os.path.abspath(str(expected_checkpoint))


# --- PROP-CR2: empty runs_dir, or runs_dir containing ONLY current_run_id -> None
#     (REQ-CR4, EDGE-CR3, EDGE-CR9) ---


def test_prop_cr2_empty_runs_dir_returns_none(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    assert checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID) is None


def test_prop_cr2_runs_dir_with_only_current_run_id_returns_none(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _mkrun(runs_dir, CURRENT_RUN_ID)  # its own freshly-created, empty directory

    assert checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID) is None


# --- PROP-CR3: most recent run (by name) selected, never the older one, even when the older
#     one has a higher checkpoint number (REQ-CR2, EDGE-CR7) ---


def test_prop_cr3_selects_most_recent_run_by_name_not_highest_checkpoint_number(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    older = _mkrun(runs_dir, "run-20260101T000000Z")
    _mkcheckpoint(older, 100)
    newer = _mkrun(runs_dir, "run-20260102T000000Z")
    expected = _mkcheckpoint(newer, 10)

    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)

    assert result == os.path.abspath(str(expected))


# --- PROP-CR4: within the selected run, checkpoint_100 beats checkpoint_20 (integer, not
#     lexicographic, comparison) (REQ-CR3) ---


def test_prop_cr4_integer_comparison_not_lexicographic(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    run = _mkrun(runs_dir, "run-20260101T000000Z")
    _mkcheckpoint(run, 20)
    expected = _mkcheckpoint(run, 100)

    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)

    assert result == os.path.abspath(str(expected))


# --- PROP-CR5: a prior run with no checkpoints/ subdir at all, or a literally empty one, is
#     skipped in favor of the next-most-recent qualifying run (REQ-CR2, EDGE-CR4, EDGE-CR5) ---


def test_prop_cr5_run_without_checkpoints_subdirectory_is_skipped(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _mkrun(runs_dir, "run-20260102T000000Z")  # newer, but NO checkpoints/ dir at all
    older = _mkrun(runs_dir, "run-20260101T000000Z")
    expected = _mkcheckpoint(older, 5)

    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)

    assert result == os.path.abspath(str(expected))


def test_prop_cr5_run_with_literally_empty_checkpoints_subdirectory_is_skipped(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    newer = _mkrun(runs_dir, "run-20260102T000000Z")
    (newer / "checkpoints").mkdir(parents=True)  # exists, zero entries of any kind
    older = _mkrun(runs_dir, "run-20260101T000000Z")
    expected = _mkcheckpoint(older, 5)

    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)

    assert result == os.path.abspath(str(expected))


# --- PROP-CR6: non-checkpoint_<N>-shaped entries interleaved with a valid one are ignored,
#     never raise (REQ-CR3, EDGE-CR6) ---


def test_prop_cr6_ignores_non_matching_entries_interleaved_with_a_valid_one(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    run = _mkrun(runs_dir, "run-20260101T000000Z")
    checkpoints_dir = run / "checkpoints"
    checkpoints_dir.mkdir(parents=True)
    (checkpoints_dir / ".DS_Store").write_text("junk")
    (checkpoints_dir / "checkpoint_abc").mkdir()  # non-numeric suffix: invalid shape
    (checkpoints_dir / "not_a_checkpoint_dir").mkdir()
    expected = _mkcheckpoint(run, 7)

    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)

    assert result == os.path.abspath(str(expected))


# --- PROP-CR7: current_run_id is always excluded, even when its own (empty, or adversarially
#     non-empty) directory already exists under runs_dir at scan time (REQ-CR2, EDGE-CR9) ---


def test_prop_cr7_current_run_id_excluded_even_with_its_own_checkpoints(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    current_dir = _mkrun(runs_dir, CURRENT_RUN_ID)
    _mkcheckpoint(current_dir, 999)  # adversarial: current run "somehow" already has one
    older = _mkrun(runs_dir, "run-20260101T000000Z")
    expected = _mkcheckpoint(older, 1)

    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)

    assert result == os.path.abspath(str(expected))


# --- PROP-CR8: selection is purely name/existence-based — a checkpoint dir with zero internal
#     files, or arbitrary garbage file contents, is still selected (REQ-CR5, EDGE-CR8) ---


def test_prop_cr8_selected_purely_by_name_empty_checkpoint_dir_never_inspected(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    run = _mkrun(runs_dir, "run-20260101T000000Z")
    expected = _mkcheckpoint(run, 3)  # completely empty — no internal openevolve state files

    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)

    assert result == os.path.abspath(str(expected))


def test_prop_cr8_selected_purely_by_name_garbage_content_never_inspected(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    run = _mkrun(runs_dir, "run-20260101T000000Z")
    checkpoint_dir = _mkcheckpoint(run, 3)
    (checkpoint_dir / "not_real_openevolve_state.bin").write_bytes(b"\x00\x01garbage\xff")

    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)

    assert result == os.path.abspath(str(checkpoint_dir))


# --- PROP-CR9: static source-text check — the pure function's own source (excluding its
#     __main__ CLI-entrypoint block) references no open(/subprocess/requests/socket/urllib
#     (INV-CR1) ---


def _read_checkpoint_resume_source():
    with open(CHECKPOINT_RESUME_SOURCE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _source_before_main_block(source):
    """Everything strictly BEFORE the `if __name__ == "__main__":` guard — i.e. the pure-function
    portion of the module this PROP scopes to."""
    marker = re.search(r'^if __name__ == ["\']__main__["\']:', source, re.MULTILINE)
    return source if marker is None else source[: marker.start()]


def test_prop_cr9_pure_function_source_has_no_effectful_references_outside_main():
    source = _read_checkpoint_resume_source()
    pure_source = _source_before_main_block(source)

    for forbidden in ("open(", "subprocess", "requests", "socket", "urllib"):
        assert forbidden not in pure_source, (
            f"forbidden effectful reference {forbidden!r} found in the pure-function portion of "
            "lib/checkpoint_resume.py (PROP-CR9/INV-CR1)"
        )


# --- PROP-CR10: a runs_dir entry that does NOT match REQ-CR10's run-directory-name shape (e.g.
#     the real production `runs/db` sibling) is NEVER a candidate, even with its own adversarial
#     checkpoints/checkpoint_1/ subdirectory (REQ-CR10, EDGE-CR10) ---


def test_prop_cr10_non_run_shaped_db_sibling_alone_returns_none(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    db_dir = runs_dir / "db"
    (db_dir / "checkpoints" / "checkpoint_1").mkdir(parents=True)  # adversarial fixture

    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)

    assert result is None


def test_prop_cr10_non_run_shaped_db_sibling_ignored_when_a_real_run_also_present(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    db_dir = runs_dir / "db"
    (db_dir / "checkpoints" / "checkpoint_1").mkdir(parents=True)
    run = _mkrun(runs_dir, "run-20260101T000000Z")
    expected = _mkcheckpoint(run, 2)

    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)

    assert result == os.path.abspath(str(expected))


# --- PROP-CR11: checkpoints/ non-empty at the OS-listing level but ZERO checkpoint_<N>-shaped
#     entries (e.g. a stray .DS_Store only) falls through to the next-most-recent candidate
#     (REQ-CR2, REQ-CR3, EDGE-CR11) ---


def test_prop_cr11_stray_file_only_checkpoints_dir_falls_through_to_older_run(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    newer = _mkrun(runs_dir, "run-20260102T000000Z")
    newer_checkpoints_dir = newer / "checkpoints"
    newer_checkpoints_dir.mkdir(parents=True)
    (newer_checkpoints_dir / ".DS_Store").write_text("junk")  # non-empty listing, zero valid entries
    older = _mkrun(runs_dir, "run-20260101T000000Z")
    expected = _mkcheckpoint(older, 9)

    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)

    assert result == os.path.abspath(str(expected))


# --- PROP-CR14: a run-shaped entry that is a PLAIN FILE (not a directory) falls through without
#     raising NotADirectoryError/FileNotFoundError/any exception (REQ-CR2, REQ-CR3, EDGE-CR12) ---


def test_prop_cr14_run_shaped_plain_file_falls_through_without_raising(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    stray_file = runs_dir / "run-20260102T000000Z"
    stray_file.write_text("")  # zero-byte plain FILE, matches the run-shape by NAME only
    older = _mkrun(runs_dir, "run-20260101T000000Z")
    expected = _mkcheckpoint(older, 4)

    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)

    assert result == os.path.abspath(str(expected))


def test_prop_cr14_run_shaped_plain_file_only_returns_none(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    stray_file = runs_dir / "run-20260102T000000Z"
    stray_file.write_text("")

    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)

    assert result is None


# --- PROP-CR12(a): static denylist — no filesystem-mutation API reference anywhere in the FULL
#     module source (including __main__), except its legitimate os.environ read / stdout write
#     (REQ-CR11, INV-CR1) ---

FORBIDDEN_MUTATION_TOKENS = (
    "os.remove",
    "os.unlink",
    "os.rmdir",
    "os.removedirs",
    "os.mkdir",
    "os.makedirs",
    "os.rename",
    "os.replace",
    "os.truncate",
    "os.symlink",
    "os.link",
    "shutil.",
)


def test_prop_cr12a_full_module_source_has_no_filesystem_mutation_api_references():
    source = _read_checkpoint_resume_source()

    found = [token for token in FORBIDDEN_MUTATION_TOKENS if token in source]
    assert found == [], (
        f"forbidden filesystem-mutation API reference(s) {found} found in lib/checkpoint_resume.py "
        "(PROP-CR12a/REQ-CR11)"
    )

    non_default_open_modes = re.findall(
        r"""open\([^)]*['"](?:w\+?|a\+?|x\+?)['"]""", source
    )
    assert non_default_open_modes == [], (
        "lib/checkpoint_resume.py contains an open() call with a non-default (write/append/"
        "create) mode (PROP-CR12a/REQ-CR11)"
    )


# --- PROP-CR12(b): static import-absence scan — the module never imports pathlib (REQ-CR11) ---


def test_prop_cr12b_module_never_imports_pathlib():
    source = _read_checkpoint_resume_source()

    assert "import pathlib" not in source
    assert "from pathlib" not in source


# --- PROP-CR12(c): dynamic before/after directory-tree snapshot is byte-for-byte/mtime-for-mtime
#     identical across a None-returning call AND a real-path-returning call (REQ-CR11, INV-CR1) ---


def _snapshot(root_dir):
    entries = []
    for current_dir, dirnames, filenames in os.walk(str(root_dir)):
        for name in sorted(dirnames) + sorted(filenames):
            full_path = os.path.join(current_dir, name)
            entries.append(
                (os.path.relpath(full_path, str(root_dir)), os.path.isdir(full_path), os.stat(full_path).st_mtime)
            )
    return sorted(entries)


def test_prop_cr12c_no_mutation_across_a_none_returning_call(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    before = _snapshot(runs_dir)
    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)
    after = _snapshot(runs_dir)

    assert result is None
    assert after == before


def test_prop_cr12c_no_mutation_across_a_real_path_returning_call(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    run = _mkrun(runs_dir, "run-20260101T000000Z")
    _mkcheckpoint(run, 1)

    before = _snapshot(runs_dir)
    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)
    after = _snapshot(runs_dir)

    assert result is not None
    assert after == before


# --- REQ-CR4 (residual coverage): runs_dir containing only non-run-shaped entries (no run-* at
#     all) returns None (EDGE-CR3/EDGE-CR10 combined) ---


def test_req_cr4_runs_dir_with_only_non_run_shaped_entries_returns_none(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    (runs_dir / "db").mkdir()

    result = checkpoint_resume.find_latest_checkpoint(str(runs_dir), CURRENT_RUN_ID)

    assert result is None
