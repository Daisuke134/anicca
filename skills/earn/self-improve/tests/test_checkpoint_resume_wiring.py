"""RED phase — self-improve-checkpoint-resume, Group CR-WIRE (wiring into run_evolve.sh).

Traces to behavioral-spec.md REQ-CR6-9, REQ-CR12, EDGE-CR1; verification-architecture.md
PROP-CR-WIRE1, PROP-CR-WIRE2, PROP-CR-WIRE2b, PROP-CR-WIRE3, PROP-CR13, PROP-CR-LIVE1.

Test-shape rationale (there is no pre-existing shell-level test convention in this suite to
mirror — `grep -rl "run_evolve.sh" tests/ lib/` finds only `lib/ledger_reader.py`'s own docstring
reference, no prior `test_run_evolve*.py`/bash-test-runner file): this file uses (1) a plain
source-text/position check against the REAL `run_evolve.sh` for PROP-CR-WIRE1's pinned command
string (no execution needed — it is a static shape claim), and (2) a `subprocess`-driven
integration harness for the argument-list/log-content properties (PROP-CR-WIRE2/2b/3, PROP-CR13,
PROP-CR-LIVE1) that actually RUNS `run_evolve.sh` end-to-end via `bash`, with `PY_BIN`/
`OPENEVOLVE_BIN` swapped for tiny, fully deterministic stand-in scripts this file writes itself —
mirroring `tests/test_wiring.py`'s existing `subprocess.run([...], cwd=tmp_path, ...)` convention
in this same suite, extended here to drive a whole shell script rather than just `git`. This is
the `pytest`-based-inspection-plus-subprocess-integration shape the task description names as an
acceptable RED-phase choice when no shell-test convention already exists.

EDGE-CR1 / execution-locus note: every sandboxed run below copies `run_evolve.sh` into its own
`tmp_path`-rooted fake `$SKILL_DIR` and builds its own synthetic `runs/` tree there — this file
NEVER executes `run_evolve.sh` against this worktree's own real `$SKILL_DIR` (which would create
real `runs/`/`state/` side effects outside a test sandbox), and NEVER reads/symlinks/copies a real
production `runs/` directory.

At RED-phase time, `run_evolve.sh` has NOT been edited to add the REQ-CR6 pre-invocation step yet,
and `lib/checkpoint_resume.py` does not exist. Every test below is EXPECTED TO FAIL: PROP-CR-WIRE1
because the pinned command substring is absent from `run_evolve.sh`'s current source; the
integration tests because the log NEVER gains a `checkpoint_resume:`-prefixed line and the
`openevolve-run` argument list NEVER gains a `--checkpoint` flag (the whole new step simply does
not run yet) — clean `AssertionError`s, not broken-test artifacts.
"""
import os
import re
import shutil
import subprocess
import sys

SELF_IMPROVE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_EVOLVE_SH_PATH = os.path.join(SELF_IMPROVE_DIR, "run_evolve.sh")

# REQ-CR6's ONE committed invocation shape, pinned verbatim so two independent implementers
# cannot diverge on it — see behavioral-spec.md REQ-CR6 / verification-architecture.md
# PROP-CR-WIRE1.
PINNED_CHECKPOINT_RESUME_CALL = (
    'RUNS_DIR="$RUNS_DIR" RUN_ID="$RUN_ID" "$PY_BIN" "$SKILL_DIR/lib/checkpoint_resume.py"'
)

FAKE_PY_BIN_SCRIPT = """#!/bin/bash
# Deterministic stand-in for $PY_BIN, dispatching on the requested script's basename so it can
# serve BOTH run_evolve.sh's existing OBSERVE call (lib/ledger_reader.py) and this feature's new
# REQ-CR6 call (lib/checkpoint_resume.py) without needing either file to actually exist on disk.
case "$1" in
  */checkpoint_resume.py)
    if [ -n "${FAKE_CHECKPOINT_CRASH:-}" ]; then
      echo "simulated checkpoint_resume crash" >&2
      exit "${FAKE_CHECKPOINT_EXIT_CODE:-1}"
    fi
    printf '%s' "${FAKE_CHECKPOINT_PATH:-}"
    ;;
  *)
    echo '{}'
    ;;
esac
"""

FAKE_OPENEVOLVE_BIN_SCRIPT = """#!/bin/bash
# Deterministic stand-in for $OPENEVOLVE_BIN: captures its full argv (one token per line) to
# $FAKE_OPENEVOLVE_CAPTURE_FILE and exits 0 — never actually runs openevolve.
printf '%s\\n' "$@" > "$FAKE_OPENEVOLVE_CAPTURE_FILE"
exit 0
"""


def _write_executable(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    os.chmod(path, 0o755)
    return path


def _build_sandbox_skill_dir(tmp_path, copy_real_lib=False):
    """A fresh $SKILL_DIR under tmp_path containing a copy of the REAL run_evolve.sh (so tests
    exercise the actual production script text, not a hand-written stand-in), never the real
    worktree's own $SKILL_DIR (EDGE-CR1: never touch the real runs//state/ trees)."""
    skill_dir = tmp_path / "self-improve"
    skill_dir.mkdir()
    shutil.copy(RUN_EVOLVE_SH_PATH, skill_dir / "run_evolve.sh")
    os.chmod(skill_dir / "run_evolve.sh", 0o755)
    (skill_dir / "lib").mkdir()
    if copy_real_lib:
        real_lib_dir = os.path.join(SELF_IMPROVE_DIR, "lib")
        for name in os.listdir(real_lib_dir):
            src = os.path.join(real_lib_dir, name)
            if os.path.isfile(src):
                shutil.copy(src, skill_dir / "lib" / name)
    return skill_dir


def _run_sandboxed_run_evolve(skill_dir, tmp_path, py_bin, extra_env=None):
    capture_file = tmp_path / "openevolve_capture.txt"
    fake_openevolve_bin = _write_executable(
        tmp_path / "fake_openevolve_bin.sh", FAKE_OPENEVOLVE_BIN_SCRIPT
    )

    env = os.environ.copy()
    env["PY_BIN"] = str(py_bin)
    env["OPENEVOLVE_BIN"] = str(fake_openevolve_bin)
    env["FAKE_OPENEVOLVE_CAPTURE_FILE"] = str(capture_file)
    if extra_env:
        env.update(extra_env)

    result = subprocess.run(
        ["bash", str(skill_dir / "run_evolve.sh")],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    log_path = skill_dir.parent / "state" / "self-improve-evolve.log"
    log_content = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    capture_content = capture_file.read_text(encoding="utf-8") if capture_file.exists() else ""
    return result, log_content, capture_content


# --- PROP-CR-WIRE1: run_evolve.sh's source text contains the EXACT pinned call, positioned
#     BEFORE the "$OPENEVOLVE_BIN" invocation (REQ-CR6, REQ-CR7) ---


def test_prop_cr_wire1_pinned_checkpoint_resume_call_present_and_before_openevolve_invocation():
    with open(RUN_EVOLVE_SH_PATH, "r", encoding="utf-8") as f:
        source = f.read()

    assert PINNED_CHECKPOINT_RESUME_CALL in source, (
        "run_evolve.sh does not yet contain the REQ-CR6 pinned checkpoint_resume.py invocation "
        f"{PINNED_CHECKPOINT_RESUME_CALL!r}"
    )

    call_index = source.index(PINNED_CHECKPOINT_RESUME_CALL)
    openevolve_index = source.index('"$OPENEVOLVE_BIN"')
    assert call_index < openevolve_index, (
        "the REQ-CR6 checkpoint_resume.py call must appear BEFORE the existing "
        '"$OPENEVOLVE_BIN" invocation in run_evolve.sh'
    )


# --- PROP-CR-WIRE2: no checkpoint found -> openevolve-run's argument list is byte-for-byte
#     unchanged (no --checkpoint), AND the REQ-CR9 "no prior checkpoint found" log line is
#     actually written (proves the new step really ran, not merely that the fallback is a no-op
#     pre-feature) (REQ-CR8, REQ-CR9, INV-CR4) ---


def test_prop_cr_wire2_no_checkpoint_found_argument_list_unchanged_and_logged(tmp_path):
    skill_dir = _build_sandbox_skill_dir(tmp_path)
    fake_py_bin = _write_executable(tmp_path / "fake_py_bin.sh", FAKE_PY_BIN_SCRIPT)

    result, log_content, capture_content = _run_sandboxed_run_evolve(
        skill_dir, tmp_path, fake_py_bin, extra_env={"FAKE_CHECKPOINT_PATH": ""}
    )

    assert result.returncode == 0, f"run_evolve.sh failed: stderr={result.stderr!r}"
    assert "--checkpoint" not in capture_content, (
        "openevolve-run's argument list must NOT contain --checkpoint when no prior checkpoint "
        "was found (REQ-CR8/INV-CR4)"
    )
    # FIND-001/FIND-002 regression guard: REQ-CR8 requires the fallback argument list to be
    # BYTE-FOR-BYTE identical to pre-feature behavior — not merely "no --checkpoint substring
    # anywhere". A naive `"${CHECKPOINT_ARGS[@]:-}"` empty-array-expansion bug (bash <4.4/set -u)
    # appends ONE stray empty-string argument even when CHECKPOINT_ARGS is empty, which the old
    # substring-only assertion above could not detect (no literal "--checkpoint" text, but argv
    # grows by one anyway). Assert the exact argument COUNT (8: 2 positionals + 3 flag pairs) and
    # that no argument is an empty/stray string.
    capture_lines = capture_content.splitlines()
    assert len(capture_lines) == 8, (
        "openevolve-run's argument list must be BYTE-FOR-BYTE identical to pre-feature behavior "
        f"when no checkpoint is found (REQ-CR8/INV-CR4) — expected exactly 8 arguments (2 "
        f"positionals + 3 flag pairs), no stray trailing empty-string argument. got "
        f"{len(capture_lines)}: {capture_lines!r}"
    )
    assert "" not in capture_lines, (
        f"openevolve-run's argument list must never contain a stray empty-string argument "
        f"(REQ-CR8/INV-CR4). got: {capture_lines!r}"
    )
    assert capture_lines[2:7] == ["--config", str(skill_dir / "config.yaml"), "--iterations", "20", "--output"], (
        f"unexpected argument list shape: {capture_lines!r}"
    )
    assert "checkpoint_resume: no prior checkpoint found" in log_content, (
        "expected the REQ-CR9 'no prior checkpoint found' log line — proves the new REQ-CR6 step "
        "actually ran, not merely that today's unmodified fallback happens to match"
    )


# --- PROP-CR-WIRE2b: checkpoint found -> the EXISTING argument list is preserved with EXACTLY
#     ONE addition, --checkpoint "<path>", appended at the end (REQ-CR7) ---


def test_prop_cr_wire2b_checkpoint_found_appends_single_checkpoint_flag(tmp_path):
    skill_dir = _build_sandbox_skill_dir(tmp_path)
    fake_py_bin = _write_executable(tmp_path / "fake_py_bin.sh", FAKE_PY_BIN_SCRIPT)
    fake_checkpoint_path = str(tmp_path / "runs" / "run-20260101T000000Z" / "checkpoints" / "checkpoint_20")

    result, log_content, capture_content = _run_sandboxed_run_evolve(
        skill_dir, tmp_path, fake_py_bin, extra_env={"FAKE_CHECKPOINT_PATH": fake_checkpoint_path}
    )

    assert result.returncode == 0, f"run_evolve.sh failed: stderr={result.stderr!r}"
    capture_lines = capture_content.splitlines()

    assert "--checkpoint" in capture_lines, (
        "openevolve-run's argument list must gain --checkpoint when a prior checkpoint was found "
        "(REQ-CR7)"
    )
    checkpoint_flag_index = capture_lines.index("--checkpoint")
    assert checkpoint_flag_index == len(capture_lines) - 2, (
        "--checkpoint <path> must be appended at the END of the existing argument list (REQ-CR7), "
        f"got args={capture_lines!r}"
    )
    assert capture_lines[checkpoint_flag_index + 1] == fake_checkpoint_path

    # Every EXISTING argument (initial_program, evaluator, --config, --iterations, --output)
    # must still be present, unchanged, before the new --checkpoint pair (INV-CR4).
    existing_args = capture_lines[:checkpoint_flag_index]
    assert existing_args.count("--config") == 1
    assert existing_args.count("--iterations") == 1
    assert existing_args.count("--output") == 1
    assert any(arg.endswith("pm_backtest_strategy.py") for arg in existing_args)
    assert any(arg.endswith("evaluator.py") for arg in existing_args)

    assert "checkpoint_resume: resuming from checkpoint" in log_content
    assert fake_checkpoint_path in log_content


# --- PROP-CR-WIRE3: exactly one checkpoint_resume:-prefixed log line per branch, with the
#     REQ-CR9-pinned substring for that branch (never merely "some line got written") ---


def test_prop_cr_wire3_exactly_one_checkpoint_resume_log_line_not_found_branch(tmp_path):
    skill_dir = _build_sandbox_skill_dir(tmp_path)
    fake_py_bin = _write_executable(tmp_path / "fake_py_bin.sh", FAKE_PY_BIN_SCRIPT)

    _, log_content, _ = _run_sandboxed_run_evolve(
        skill_dir, tmp_path, fake_py_bin, extra_env={"FAKE_CHECKPOINT_PATH": ""}
    )

    matching_lines = [line for line in log_content.splitlines() if "checkpoint_resume:" in line]
    assert len(matching_lines) == 1, (
        f"expected exactly one checkpoint_resume: log line, got {matching_lines!r}"
    )
    assert "checkpoint_resume: no prior checkpoint found" in matching_lines[0]


def test_prop_cr_wire3_exactly_one_checkpoint_resume_log_line_found_branch(tmp_path):
    skill_dir = _build_sandbox_skill_dir(tmp_path)
    fake_py_bin = _write_executable(tmp_path / "fake_py_bin.sh", FAKE_PY_BIN_SCRIPT)
    fake_checkpoint_path = str(tmp_path / "runs" / "run-20260101T000000Z" / "checkpoints" / "checkpoint_20")

    _, log_content, _ = _run_sandboxed_run_evolve(
        skill_dir, tmp_path, fake_py_bin, extra_env={"FAKE_CHECKPOINT_PATH": fake_checkpoint_path}
    )

    matching_lines = [line for line in log_content.splitlines() if "checkpoint_resume:" in line]
    assert len(matching_lines) == 1, (
        f"expected exactly one checkpoint_resume: log line, got {matching_lines!r}"
    )
    assert "checkpoint_resume: resuming from checkpoint" in matching_lines[0]
    assert fake_checkpoint_path in matching_lines[0]


# --- PROP-CR13: the REQ-CR6 call itself crashing (non-zero exit) degrades to the REQ-CR8
#     fallback (no --checkpoint) AND logs the THIRD, distinct "resume-check crashed" wording with
#     the captured exit status (REQ-CR12) ---


def test_prop_cr13_resume_check_crash_falls_back_and_logs_distinct_message(tmp_path):
    skill_dir = _build_sandbox_skill_dir(tmp_path)
    fake_py_bin = _write_executable(tmp_path / "fake_py_bin.sh", FAKE_PY_BIN_SCRIPT)

    result, log_content, capture_content = _run_sandboxed_run_evolve(
        skill_dir,
        tmp_path,
        fake_py_bin,
        extra_env={"FAKE_CHECKPOINT_CRASH": "1", "FAKE_CHECKPOINT_EXIT_CODE": "7"},
    )

    assert result.returncode == 0, f"run_evolve.sh itself must not crash: stderr={result.stderr!r}"
    assert "--checkpoint" not in capture_content, (
        "a crashed resume-check must degrade to the REQ-CR8 fallback (no --checkpoint), never "
        "block the openevolve-run invocation (REQ-CR12)"
    )
    assert "checkpoint_resume: resume-check crashed" in log_content, (
        "expected the REQ-CR12 'resume-check crashed' log line, distinct from both the "
        "found/not-found wording"
    )
    assert "7" in log_content.split("checkpoint_resume: resume-check crashed", 1)[1].splitlines()[0], (
        "expected the captured non-zero exit status (7) to appear immediately after the "
        "'resume-check crashed' substring"
    )
    assert "checkpoint_resume: no prior checkpoint found" not in log_content, (
        "a crash must NEVER be logged with the ordinary not-found wording — REQ-CR12 requires a "
        "third, distinct branch"
    )


# --- PROP-CR-LIVE1: end-to-end — a hand-constructed two-run tmp_path tree fed through
#     run_evolve.sh's REAL new step (via the real python interpreter and, once it exists, the
#     real lib/checkpoint_resume.py — never a stand-in for the pure logic itself) selects and
#     logs checkpoint_20's path (REQ-CR6, REQ-CR9) ---


def test_prop_cr_live1_end_to_end_two_run_fixture_selects_and_logs_checkpoint_20(tmp_path):
    skill_dir = _build_sandbox_skill_dir(tmp_path, copy_real_lib=True)

    # Hand-constructed two-run fixture (per PROP-CR-LIVE1's own description): an older run with
    # checkpoint_10 AND checkpoint_20 (REQ-CR3: the higher-numbered one must win), pre-existing
    # BEFORE run_evolve.sh creates its own new (current) run directory.
    runs_dir = skill_dir / "runs"
    older_run = runs_dir / "run-20260101T000000Z"
    (older_run / "checkpoints" / "checkpoint_10").mkdir(parents=True)
    expected_checkpoint = older_run / "checkpoints" / "checkpoint_20"
    expected_checkpoint.mkdir(parents=True)

    result, log_content, capture_content = _run_sandboxed_run_evolve(
        skill_dir, tmp_path, py_bin=sys.executable
    )

    assert result.returncode == 0, f"run_evolve.sh failed: stderr={result.stderr!r}"
    assert "checkpoint_resume: resuming from checkpoint" in log_content, (
        "PROP-CR-LIVE1: expected the real (not stand-in) checkpoint_resume.py, invoked via the "
        "real python interpreter, to select and log the older run's checkpoint_20"
    )
    assert str(expected_checkpoint) in log_content or os.path.abspath(str(expected_checkpoint)) in log_content
    assert "--checkpoint" in capture_content


# --- Regression Table smoke check: run_evolve.sh remains valid bash after every edit ---


def test_regression_run_evolve_sh_remains_valid_bash_syntax():
    result = subprocess.run(
        ["bash", "-n", RUN_EVOLVE_SH_PATH], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"run_evolve.sh has a bash syntax error: {result.stderr}"
