---
feature: self-improve-checkpoint-resume
phase: 1b
mode: lean
sources:
  - behavioral-spec.md (this feature, same directory) — REQ-CR/INV-CR/EDGE-CR IDs referenced below
  - .vcsdd/features/self-improve-real-ledger/specs/verification-architecture.md (prior phase) —
    Purity Boundary Map / Proof Obligations table conventions, and its EDGE-RL5a-driven "live tier
    must run from the merged checkout, never a worktree" execution-locus note, whose EDGE-CR1
    equivalent this document restates for `runs/`
---

# Verification Architecture — self-improve-checkpoint-resume (Phase 1b)

## Purity Boundary Map

### Pure Core

| function | signature | why it is pure | REQ traced |
|---|---|---|---|
| `find_latest_checkpoint(runs_dir, current_run_id)` | `(str, str) -> Optional[str]` | deterministic directory-listing + name-shape filtering + string/integer comparison over an already-given path; no subprocess, no network, no file-content reads, no writes — same input tree yields same output every call | REQ-CR1, REQ-CR2, REQ-CR3, REQ-CR4, REQ-CR5, REQ-CR10, REQ-CR11 |

This is the feature's ENTIRE testable surface. There is no additional pure helper to extract — the
function is small and single-purpose by design (lean mode; do not add abstractions the spec does
not require).

### Effectful Shell

| module / function | primary I/O surface | REQ traced |
|---|---|---|
| `lib/checkpoint_resume.py`'s `if __name__ == "__main__":` CLI entrypoint (thin wrapper, same file as the pure core, but itself effectful) | reads `RUNS_DIR`/`RUN_ID` from `os.environ` (no argv), calls `find_latest_checkpoint`, prints exactly one line to stdout (the path, or empty string for `None`) — no other output; NEVER creates, deletes, renames, or writes bytes to any file or directory | REQ-CR6, REQ-CR11 |
| `run_evolve.sh` (EXTENDED, existing script) | invokes EXACTLY `RUNS_DIR="$RUNS_DIR" RUN_ID="$RUN_ID" "$PY_BIN" "$SKILL_DIR/lib/checkpoint_resume.py"` (mirroring `lib/ledger_reader.py:60`'s existing no-`-c`, no-argv call shape) against the REAL `runs_dir` (`$SKILL_DIR/runs`) and the real `$RUN_ID`; captures its stdout; appends a log line to `$LOG`; conditionally appends `--checkpoint "<path>"` to the existing `"$OPENEVOLVE_BIN"` invocation | REQ-CR6, REQ-CR7, REQ-CR8, REQ-CR9 |
| `openevolve-run` (external, unchanged binary, not part of this feature) | reads the checkpoint directory's own internal contents and resumes from it — entirely outside this feature's code; this feature only ever hands it a PATH | REQ-CR7 (downstream consumer only) |

The pure `find_latest_checkpoint` never itself invokes `openevolve-run`, writes to `$LOG`, or
touches `os.environ`/stdout — those are the CLI entrypoint's and `run_evolve.sh`'s own effectful
responsibilities, exactly mirroring how `lib/ledger_reader.py`'s pure predicates are called from,
but never call into, the `__main__` block / shell script that logs their results.

**One committed invocation shape (resolves the ambiguity a prior review round flagged):** there is
no `"$PY_BIN" -c` alternative left open anywhere in this feature. The ONLY call site is
`RUNS_DIR="$RUNS_DIR" RUN_ID="$RUN_ID" "$PY_BIN" "$SKILL_DIR/lib/checkpoint_resume.py"` — a full-
script invocation of `lib/checkpoint_resume.py`'s own `__main__` block, taking its two inputs from
the environment (not argv, not an inline `-c` snippet), printing its one-line result to stdout. This
is pinned so two independent implementers cannot diverge on code shape.

---

## Proof Obligations

Tier legend (lean mode — this feature's whole surface is Tier 0/1; no Tier 2/3 formal-methods
machinery is warranted for ~20 lines of path/existence logic): **Tier 0** = trivial/no-proof-needed
(constant-shaped fallback behavior). **Tier 1** = property/unit test over synthetic `tmp_path`
directory trees, no mocking beyond building a fake filesystem tree. **Tier "wire"** = a shell-level
check that `run_evolve.sh`'s new step is actually invoked and its output actually reaches the
`openevolve-run` argument list (no orphan implementation).

| ID | Description | Tier | Required | Tool |
|---|---|---|---|---|
| PROP-CR1 | `find_latest_checkpoint` returns `None` for a nonexistent `runs_dir` (REQ-CR4, EDGE-CR2) | 0 | true | pytest |
| PROP-CR1b | `find_latest_checkpoint`, called with a RELATIVE `runs_dir` string against a `tmp_path`-rooted fixture (via `os.chdir` into a known cwd for the test) that has one valid prior checkpoint, returns an ABSOLUTE path string (`os.path.isabs(result) is True`), not a relative one (REQ-CR1) | 0 | true | pytest, `tmp_path` + `monkeypatch.chdir` |
| PROP-CR2 | `find_latest_checkpoint` returns `None` for an empty `runs_dir`, and for a `runs_dir` containing ONLY `current_run_id`'s own directory (REQ-CR4, EDGE-CR3, EDGE-CR9) | 1 | true | pytest, `tmp_path` |
| PROP-CR3 | Given two prior run directories with checkpoints, the MOST RECENT one (by lexicographic-descending `run-YYYYMMDDTHHMMSSZ` name) is selected, never the older one, even when the older one has a higher checkpoint number (REQ-CR2, EDGE-CR7) | 1 | true | pytest, `tmp_path`, parametrized names |
| PROP-CR4 | Within the selected run, `checkpoint_100` is selected over `checkpoint_20` (integer comparison, not lexicographic) (REQ-CR3) | 1 | true | pytest, `tmp_path` |
| PROP-CR5 | A prior run with no `checkpoints/` subdirectory, or a literally empty one, is skipped in favor of the next-most-recent qualifying run (REQ-CR2, EDGE-CR4, EDGE-CR5; contrast PROP-CR11's non-empty-but-zero-valid-entries variant, EDGE-CR11) | 1 | true | pytest, `tmp_path` |
| PROP-CR6 | Non-`checkpoint_<N>`-shaped entries inside `checkpoints/` (a stray file, a hidden dotfile, a non-numeric-suffixed directory) are ignored without raising an exception, interleaved with valid entries (REQ-CR3, EDGE-CR6) | 1 | true | pytest, `tmp_path` |
| PROP-CR7 | `current_run_id` is always excluded from candidate selection, even when its own (empty) directory already exists under `runs_dir` at scan time (REQ-CR2, EDGE-CR9) | 1 | true | pytest, `tmp_path` |
| PROP-CR8 | `find_latest_checkpoint` performs zero file-content reads — a `checkpoint_<N>` directory that is empty or contains arbitrary/garbage file contents is still selected purely on its NAME/existence, never inspected further (REQ-CR5, EDGE-CR8) | 1 | true | pytest, `tmp_path` (checkpoint dirs created with no real openevolve state inside) |
| PROP-CR9 | Static source-text check: `find_latest_checkpoint`'s module source (`lib/checkpoint_resume.py`, excluding its own `__main__` CLI-entrypoint block, which legitimately touches `os.environ`/stdout per REQ-CR6) contains no `open(`, `subprocess`, `requests`, `socket`, or `urllib` reference — purity restated as an executable check, standing on its own: it asserts INV-CR1 directly, over this module's own source text, rather than by comparison to any other file's test (INV-CR1) | 0 | true | pytest source-text scan |
| PROP-CR10 | A `runs_dir` entry that does NOT match REQ-CR10's `^run-\d{8}T\d{6}Z$` shape (concretely, an entry named `db`, matching the real production `runs/db` sibling from `config.yaml`'s `database.db_path`) is NEVER selected as a candidate, even when it is lexicographically ordered such that a naive unfiltered sort would place it first, and even when it is given its own `checkpoints/checkpoint_1/` subdirectory as an adversarial fixture (REQ-CR10, EDGE-CR10) | 1 | true | pytest, `tmp_path` (fixture includes a non-run-shaped `db` entry alongside real `run-*` entries) |
| PROP-CR11 | A run-shaped candidate whose `checkpoints/` subdirectory is non-empty at the OS-listing level (`os.listdir` returns >= 1 entry) but contains ZERO `checkpoint_<N>`-shaped entries (fixture: a single stray file, e.g. `.DS_Store`, and nothing else) causes `find_latest_checkpoint` to fall through to the next-most-recent run-shaped candidate (which DOES have a valid `checkpoint_<N>` entry) and return THAT candidate's checkpoint path — never `None` and never an exception, even though the "non-empty checkpoints/ dir" test alone would wrongly treat this candidate as usable (REQ-CR2, REQ-CR3, EDGE-CR11) | 1 | true | pytest, `tmp_path`, two-run fixture (newer run: stray-file-only `checkpoints/`; older run: valid `checkpoint_<N>/`) |
| PROP-CR14 | A `runs_dir` entry whose name matches REQ-CR10's shape but is a PLAIN FILE (not a directory) causes `find_latest_checkpoint` to fall through to the next-most-recent run-shaped candidate without raising `NotADirectoryError`/`FileNotFoundError`/any exception (REQ-CR2, REQ-CR3, EDGE-CR12) | 1 | true | pytest, `tmp_path`, fixture with a zero-byte file named `run-<timestamp>` alongside a real older run directory with a valid `checkpoint_<N>/` |
| PROP-CR12 | Filesystem-mutation prohibition (REQ-CR11, INV-CR1), verified THREE ways: **(a) static denylist** — `lib/checkpoint_resume.py`'s FULL module source (including its `__main__` block; only its legitimate `os.environ` read and stdout write are exempt) contains no reference to `os.remove`, `os.unlink`, `os.rmdir`, `os.removedirs`, `os.mkdir`, `os.makedirs`, `os.rename`, `os.replace`, `os.truncate`, `os.symlink`, `os.link`, any `shutil.` attribute access, or `open(` used with a non-default (write/append/create/truncate) mode — this expands PROP-CR9's network/subprocess-only denylist to also cover filesystem-mutation APIs. **(b) static import-absence scan** — the module source contains no `import pathlib` and no `from pathlib import`, which (per REQ-CR11) makes every `pathlib.Path` mutating method structurally unreachable without an exhaustive method-name denylist. **(c) dynamic** — snapshot a synthetic `tmp_path` `runs/` tree (a recursive listing of every path plus its `os.stat` mtime, or a full byte-for-byte directory copy) BEFORE calling `find_latest_checkpoint` at least twice against it (once where it returns `None` — e.g. an empty tree — and once where it returns a real checkpoint path — e.g. a populated two-run fixture), then re-snapshot the SAME tree AFTER both calls and assert it is byte-for-byte/mtime-for-mtime identical to the BEFORE snapshot. This closes the gap a static-only or unit-test-only check cannot: a function could pass every REQ-CR1-10 test above by returning the right paths while ALSO, incidentally, mutating disk — (a)+(b) catch that via source inspection, (c) catches it via observed behavior, independently of each other. | 0/1 | true | pytest source-text scan (a)+(b) + pytest `tmp_path` before/after directory-tree snapshot comparison (c) |
| PROP-CR13 | Resume-check crash handling (REQ-CR12): when the REQ-CR6 subprocess call exits non-zero (simulated via a broken/non-executable stand-in for `$PY_BIN` or a deliberately-erroring stand-in script in the test fixture), `run_evolve.sh`'s new step (i) still proceeds to invoke `openevolve-run` with NO `--checkpoint` flag (same as REQ-CR8's fallback), and (ii) the log line's message contains the literal substring `checkpoint_resume: resume-check crashed` followed by the captured non-zero exit status — distinct from both the found-branch and not-found-branch wording | wire | true | shell-level test: substitute a stand-in for the REQ-CR6 call that exits non-zero, assert both the resulting `openevolve-run` argument list (no `--checkpoint`) and the exact log substring |
| PROP-CR-WIRE1 | `run_evolve.sh`'s source text contains the EXACT substring `RUNS_DIR="$RUNS_DIR" RUN_ID="$RUN_ID" "$PY_BIN" "$SKILL_DIR/lib/checkpoint_resume.py"` (no `-c`, no other argv), that call's line number is BEFORE the `"$OPENEVOLVE_BIN"` invocation's line number, and the invocation's argument list conditionally includes `--checkpoint` (REQ-CR6, REQ-CR7) | wire | true | grep/text-position check over `run_evolve.sh` for the exact pinned command string |
| PROP-CR-WIRE2 | WHEN no checkpoint is found, the resulting `openevolve-run` argument list is IDENTICAL (same arguments, same order) to the pre-feature invocation — no `--checkpoint` flag appears (REQ-CR8, INV-CR4) | 1 | true | a synthetic re-assembly test of the argument array (bash unit check or a small harness that captures the composed command line under both branches) |
| PROP-CR-WIRE2b | WHEN a checkpoint IS found, the resulting `openevolve-run` argument list is IDENTICAL to the pre-feature invocation for every EXISTING argument (`initial_program`, `evaluation_file`, `--config`, `--iterations`, `--output`, same values, same order) with EXACTLY ONE addition, `--checkpoint "<path>"`, appended at the end (REQ-CR7) — closes the gap where only the not-found branch's argument-list stability was previously tested | 1 | true | the same synthetic re-assembly test as PROP-CR-WIRE2, run against the with-checkpoint branch and diffed against the pre-feature argument list plus the expected single addition |
| PROP-CR-WIRE3 | Every code path through the new step (found / not-found) appends exactly one line to `$LOG` before proceeding to invoke `openevolve-run`, AND that line's CONTENT (not merely its count) is asserted in BOTH branches: the found-branch line contains the literal substring `checkpoint_resume: resuming from checkpoint` followed by the actual selected path; the not-found-branch line contains the literal substring `checkpoint_resume: no prior checkpoint found` (REQ-CR9) | 1 | true | shell-level check: run the new step in isolation against both a with-checkpoint and without-checkpoint fixture, assert `$LOG` gained exactly one new line each time AND that the new line's text contains the required substring for that branch — never merely `count(lines) == 1` |
| PROP-CR-LIVE1 | End-to-end: a hand-constructed two-run `tmp_path` tree (an older run with `checkpoints/checkpoint_10/` and `checkpoints/checkpoint_20/`, and a current run with no checkpoints yet) fed through `run_evolve.sh`'s new step (invoked directly, not via the full openevolve subprocess) produces a log line containing the literal substring `checkpoint_resume: resuming from checkpoint` immediately followed by `checkpoint_20`'s path (REQ-CR6, REQ-CR9) | live (Tier 1, no real openevolve invocation required) | true | integration test against a synthetic fixture tree, per EDGE-CR1's worktree constraint below |

**Execution locus note (mirrors the prior phase's EDGE-RL5a pattern, EDGE-CR1):** this worktree's
`skills/earn/self-improve/.gitignore` ignores `runs/` and `state/` — a fresh checkout has no
`runs/` directory. Every test above (PROP-CR1 through PROP-CR-LIVE1) MUST build its own synthetic
`runs_dir` under pytest's `tmp_path`, and MUST NEVER read, symlink, or copy any real production
`runs/` directory into this worktree. A true end-to-end run of the FULL `run_evolve.sh` script
(including a real `openevolve-run` invocation actually resuming from a real checkpoint) is
optional, out-of-band verification evidence for Phase 5 — not a Phase 2 gating requirement — and,
if performed, MUST run from a real instance body (e.g. this feature's own production `runs/`
directory after merge), never fabricated inside a worktree.

## Verification Strategy

- **Tier 0**: `find_latest_checkpoint`'s trivial no-input-tree fallback cases (missing/empty
  `runs_dir`) and PROP-CR12(a)'s static filesystem-mutation-API source-text denylist scan — no
  formal proof needed, a single assertion each settles them.
- **Tier 1**: the bulk of this feature's proof burden — deterministic unit/property tests over
  synthetic `tmp_path` directory trees covering every REQ-CR/EDGE-CR combination (recency ordering,
  integer-vs-lexicographic checkpoint comparison, malformed-entry tolerance, self-exclusion,
  no-file-content-read), PLUS PROP-CR12(b)'s dynamic before/after directory-snapshot comparison
  (REQ-CR11) and PROP-CR-WIRE3/PROP-CR-LIVE1's log-content substring assertions (REQ-CR9) — none of
  these are "count-only" or "ran without crashing" checks; each asserts a specific, pinned piece of
  content (a byte-identical tree, or a literal log substring). This is standard `pytest`, matching
  this repo's existing convention for `gate_math.py`/`ledger_reader.py` pure-function tests — no
  `hypothesis`/`kani`/`fast-check` property-fuzzing harness is introduced for ~20 lines of path logic
  (lean mode: do not over-specify formal machinery this feature's size does not warrant).
- **Tier 2**: not used. This feature has no numeric/financial invariant, no concurrency, and no
  security-sensitive parsing surface that would justify lightweight formal methods (contrast with
  `gate_math.py`'s `is_implausible_jump`/reward-hacking trip-wire math in the parent harness, which
  DOES warrant Tier 2 in that feature's own spec).
- **Tier 3**: not used. No cryptographic, concurrency-safety, or strong-correctness claim is made by
  this feature.

## Regression Table

The pre-existing `skills/earn/self-improve/tests/` suite (14 files, covering ledger resolution,
gate math, adversary wiring, denylist, reward-hacking trip-wire, etc.) MUST remain green after this
feature's changes. This feature adds ONE new file (`lib/checkpoint_resume.py`) and edits ONE
existing file (`run_evolve.sh`, bash only — no Python module this feature touches is imported by
any pre-existing test), so the regression risk surface is the full existing pytest suite re-run
unmodified, plus a bash syntax/execution smoke check of `run_evolve.sh` itself (`bash -n
run_evolve.sh`).
