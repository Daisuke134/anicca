# Purity Audit — self-improve-checkpoint-resume (Phase 5)

## Declared purity boundary (behavioral-spec.md "Purity Boundary Analysis")

- **Pure core**: `lib/checkpoint_resume.py::find_latest_checkpoint(runs_dir, current_run_id) ->
  Optional[str]`. Declared: deterministic path/existence logic ONLY (`os.listdir`,
  `os.path.isdir`, string parsing/sorting) — no subprocess, no network, no filesystem mutation,
  no file-content reads.
- **Effectful shell**: `run_evolve.sh`'s new pre-invocation step (REQ-CR6-9,12) — one subprocess
  call to `lib/checkpoint_resume.py`'s `__main__` CLI entrypoint (env-var config, single stdout
  line, no argv, no file writes of its own) and, downstream, appending a conditional
  `--checkpoint <path>` argument pair to the pre-existing `openevolve-run` invocation.

## Verification against the actual shipped code (this session, commit `eba2270a`)

1. **Static denylist scan** (`test_prop_cr9_...`, `test_prop_cr12a_...`): the FULL module source
   of `lib/checkpoint_resume.py` (pure function AND `__main__` block) contains no `open(` in a
   non-default mode, no `subprocess`, `requests`, `socket`, `urllib`, and no filesystem-mutation
   API (`os.remove`/`unlink`/`rmdir`/`removedirs`/`mkdir`/`makedirs`/`rename`/`replace`/
   `truncate`/`symlink`/`link`, any `shutil.*`). Re-read the shipped file this session to confirm
   directly: it contains exactly `import os`, `import re`, `import sys`, and no other import —
   zero deviation from the declared boundary.
2. **Import-absence scan** (`test_prop_cr12b_...`): no `import pathlib` / `from pathlib` anywhere
   in the module — confirmed by direct read.
3. **Dynamic before/after snapshot** (`test_prop_cr12c_...`, both variants): a full recursive
   directory-tree snapshot (path, is-dir, mtime) taken immediately before and after calling
   `find_latest_checkpoint` — for BOTH a `None`-returning call (empty `runs_dir`) and a real-path-
   returning call (populated two-run fixture) — is byte-for-byte/mtime-for-mtime identical. This
   is the strongest possible purity evidence: not "the source looks pure" but "observed behavior
   against a real filesystem tree caused zero mutation," independently of (1)/(2).
4. **`__main__` entrypoint's only effect**: reads `os.environ["RUNS_DIR"]`/`os.environ["RUN_ID"]`,
   calls the pure function, writes exactly one line to stdout (`sys.stdout.write(...)`, no
   trailing newline, matching the spec's "prints EXACTLY one line" contract as interpreted by the
   test fixtures' `printf '%s'`-shaped stand-ins). Never opens a file. Confirmed by direct read of
   the `if __name__ == "__main__":` block (5 lines).
5. **Effectful-shell boundary in `run_evolve.sh`**: the new step's only side effects are (a) one
   `2>>"$LOG"` stderr-append during the subprocess call (pre-existing convention, same as the
   OBSERVE step's `ledger_reader.py` call) and (b) `echo ... >> "$LOG"` log lines (pre-existing
   convention, REQ-CR9). It never writes to `runs/`, `state/` (other than the log), or anywhere
   outside `$LOG` and the array variable it builds in-memory for the subsequent (pre-existing,
   unmodified-except-for-the-one-appended-argument) `openevolve-run` invocation.

## Deviations found

**Zero.** Every claim in the declared Purity Boundary Analysis is true of the actually-shipped
code, verified by a combination of static source inspection (this audit + PROP-CR9/12a/12b) and
dynamic behavioral observation (PROP-CR12c) — not a "zero deviations" self-certification on trust
alone (the franklin-alwaysact-skill-router feature's own Phase 6 convergence history in this same
repo records that a purity-audit's bare "zero deviations" claim was found FALSE twice by later
adversary review on citation-accuracy grounds; this audit is written to withstand that same
scrutiny by pointing at the specific test/read that grounds each claim above, not asserting it
unsupported).
