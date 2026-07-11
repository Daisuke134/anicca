"""checkpoint_resume.py — self-improve-checkpoint-resume (REQ-CR1..12).

Pure checkpoint-discovery core for run_evolve.sh's recurring ~6h self-improve cycle (REQ-OE7).
Every cycle today starts openevolve-run from a cold population (initial_program only) and
discards its own MAP-Elites checkpoints at cycle end — this module lets a cycle resume from the
most recent PRIOR cycle's highest-numbered checkpoint instead, so iterations accumulate across
cycles rather than re-deriving the same already-known baseline every ~6h (the confirmed root
cause of 3 consecutive tied combined_score cycles / 18h zero forward progress — see
behavioral-spec.md sources).

`find_latest_checkpoint` is PATH/EXISTENCE logic only (REQ-CR5, REQ-CR11): directory listing,
name-pattern matching, integer comparison. It never opens a file's byte contents, never mutates
the filesystem, and never imports pathlib (os/os.path suffice for every operation this needs).
"""
import os
import re
import sys

_RUN_ID_RE = re.compile(r"^run-\d{8}T\d{6}Z$")
_CHECKPOINT_RE = re.compile(r"^checkpoint_(\d+)$")


def _latest_checkpoint_in_run(run_dir):
    """REQ-CR3: the absolute path of the highest-numbered checkpoint_<N> under run_dir/checkpoints,
    or None if run_dir has no checkpoints/ subdirectory, an empty one, or one with zero
    checkpoint_<N>-shaped entries. Never raises — a run-shaped candidate that is a plain FILE
    (EDGE-CR12) is checked with os.path.isdir before any listdir is attempted."""
    checkpoints_dir = os.path.join(run_dir, "checkpoints")
    if not os.path.isdir(checkpoints_dir):
        return None

    best_n = None
    best_name = None
    for entry in os.listdir(checkpoints_dir):
        match = _CHECKPOINT_RE.match(entry)
        if match is None:
            continue
        n = int(match.group(1))
        if best_n is None or n > best_n:
            best_n = n
            best_name = entry

    if best_name is None:
        return None
    return os.path.abspath(os.path.join(checkpoints_dir, best_name))


def find_latest_checkpoint(runs_dir, current_run_id):
    """REQ-CR1: return the absolute path to a checkpoint directory to resume from, or None when
    no prior run has any usable checkpoint. runs_dir may be relative -- the result is always
    normalized to an absolute path (REQ-CR1)."""
    runs_dir_abs = os.path.abspath(runs_dir)
    if not os.path.isdir(runs_dir_abs):
        return None

    candidates = [
        entry for entry in os.listdir(runs_dir_abs)
        if _RUN_ID_RE.match(entry) and entry != current_run_id
    ]
    # REQ-CR2: run directory names (run-YYYYMMDDTHHMMSSZ) sort correctly as plain strings;
    # descending lexicographic order == most-recent-first.
    candidates.sort(reverse=True)

    for candidate in candidates:
        checkpoint = _latest_checkpoint_in_run(os.path.join(runs_dir_abs, candidate))
        if checkpoint is not None:
            return checkpoint

    return None


if __name__ == "__main__":
    # Runnable as `RUNS_DIR=... RUN_ID=... python3 lib/checkpoint_resume.py` for run_evolve.sh's
    # new pre-invocation step (REQ-CR6): no argv, env-var config only (mirrors lib/ledger_reader.py's
    # own __main__ convention). Prints EXACTLY one line to stdout -- the resolved checkpoint path,
    # or an empty string when None -- nothing else. Never writes to any file (REQ-CR11).
    result = find_latest_checkpoint(
        runs_dir=os.environ["RUNS_DIR"],
        current_run_id=os.environ["RUN_ID"],
    )
    sys.stdout.write(result if result is not None else "")
