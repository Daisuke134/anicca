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
| `find_latest_checkpoint(runs_dir, current_run_id)` | `(str, str) -> Optional[str]` | deterministic directory-listing + string/integer comparison over an already-given path; no subprocess, no network, no file-content reads, no writes — same input tree yields same output every call | REQ-CR1, REQ-CR2, REQ-CR3, REQ-CR4, REQ-CR5 |

This is the feature's ENTIRE testable surface. There is no additional pure helper to extract — the
function is small and single-purpose by design (lean mode; do not add abstractions the spec does
not require).

### Effectful Shell

| module / function | primary I/O surface | REQ traced |
|---|---|---|
| `run_evolve.sh` (EXTENDED, existing script) | shells out to `"$PY_BIN"` to call `find_latest_checkpoint` against the REAL `runs_dir` (`$SKILL_DIR/runs`) and the real `$RUN_ID`; appends a log line to `$LOG`; conditionally appends `--checkpoint "<path>"` to the existing `"$OPENEVOLVE_BIN"` invocation | REQ-CR6, REQ-CR7, REQ-CR8, REQ-CR9 |
| `openevolve-run` (external, unchanged binary, not part of this feature) | reads the checkpoint directory's own internal contents and resumes from it — entirely outside this feature's code; this feature only ever hands it a PATH | REQ-CR7 (downstream consumer only) |

The pure `find_latest_checkpoint` never itself invokes `openevolve-run` or writes to `$LOG` — those
are `run_evolve.sh`'s own effectful responsibilities, exactly mirroring how `lib/ledger_reader.py`'s
pure predicates are called from, but never call into, the shell script that logs their results.

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
| PROP-CR2 | `find_latest_checkpoint` returns `None` for an empty `runs_dir`, and for a `runs_dir` containing ONLY `current_run_id`'s own directory (REQ-CR4, EDGE-CR3, EDGE-CR9) | 1 | true | pytest, `tmp_path` |
| PROP-CR3 | Given two prior run directories with checkpoints, the MOST RECENT one (by lexicographic-descending `run-YYYYMMDDTHHMMSSZ` name) is selected, never the older one, even when the older one has a higher checkpoint number (REQ-CR2, EDGE-CR7) | 1 | true | pytest, `tmp_path`, parametrized names |
| PROP-CR4 | Within the selected run, `checkpoint_100` is selected over `checkpoint_20` (integer comparison, not lexicographic) (REQ-CR3) | 1 | true | pytest, `tmp_path` |
| PROP-CR5 | A prior run with no `checkpoints/` subdirectory, or an empty one, is skipped in favor of the next-most-recent qualifying run (REQ-CR2, EDGE-CR4, EDGE-CR5) | 1 | true | pytest, `tmp_path` |
| PROP-CR6 | Non-`checkpoint_<N>`-shaped entries inside `checkpoints/` (a stray file, a hidden dotfile, a non-numeric-suffixed directory) are ignored without raising an exception, interleaved with valid entries (REQ-CR3, EDGE-CR6) | 1 | true | pytest, `tmp_path` |
| PROP-CR7 | `current_run_id` is always excluded from candidate selection, even when its own (empty) directory already exists under `runs_dir` at scan time (REQ-CR2, EDGE-CR9) | 1 | true | pytest, `tmp_path` |
| PROP-CR8 | `find_latest_checkpoint` performs zero file-content reads — a `checkpoint_<N>` directory that is empty or contains arbitrary/garbage file contents is still selected purely on its NAME/existence, never inspected further (REQ-CR5, EDGE-CR8) | 1 | true | pytest, `tmp_path` (checkpoint dirs created with no real openevolve state inside) |
| PROP-CR9 | Static source-text check: `find_latest_checkpoint`'s module source contains no `open(`, `subprocess`, `requests`, `socket`, or `urllib` reference (purity restated as an executable check, mirrors this repo's existing `gate_math.py` AST/text-scan convention) (INV-CR1) | 0 | true | pytest source-text scan |
| PROP-CR-WIRE1 | `run_evolve.sh`'s source text: the `find_latest_checkpoint` call (via `$PY_BIN`) appears BEFORE the `"$OPENEVOLVE_BIN"` invocation, and the invocation's argument list conditionally includes `--checkpoint` (REQ-CR6, REQ-CR7) | wire | true | grep/text-position check over `run_evolve.sh` |
| PROP-CR-WIRE2 | WHEN no checkpoint is found, the resulting `openevolve-run` argument list is IDENTICAL (same arguments, same order) to the pre-feature invocation — no `--checkpoint` flag appears (REQ-CR8, INV-CR4) | 1 | true | a synthetic re-assembly test of the argument array (bash unit check or a small harness that captures the composed command line under both branches) |
| PROP-CR-WIRE3 | Every code path through the new step (found / not-found) appends exactly one line to `$LOG` before proceeding to invoke `openevolve-run` (REQ-CR9) | 1 | true | shell-level check: run the new step in isolation against both a with-checkpoint and without-checkpoint fixture, assert `$LOG` gained exactly one new line each time |
| PROP-CR-LIVE1 | End-to-end: a hand-constructed two-run `tmp_path` tree (an older run with `checkpoints/checkpoint_10/` and `checkpoints/checkpoint_20/`, and a current run with no checkpoints yet) fed through `run_evolve.sh`'s new step (invoked directly, not via the full openevolve subprocess) produces the log line naming `checkpoint_20`'s path (REQ-CR6, REQ-CR9) | live (Tier 1, no real openevolve invocation required) | true | integration test against a synthetic fixture tree, per EDGE-CR1's worktree constraint below |

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
  `runs_dir`) and the static purity source-scan — no formal proof needed, a single assertion each
  settles them.
- **Tier 1**: the bulk of this feature's proof burden — deterministic unit/property tests over
  synthetic `tmp_path` directory trees covering every REQ-CR/EDGE-CR combination (recency ordering,
  integer-vs-lexicographic checkpoint comparison, malformed-entry tolerance, self-exclusion,
  no-file-content-read). This is standard `pytest`, matching this repo's existing convention for
  `gate_math.py`/`ledger_reader.py` pure-function tests — no `hypothesis`/`kani`/`fast-check`
  property-fuzzing harness is introduced for ~20 lines of path logic (lean mode: do not
  over-specify formal machinery this feature's size does not warrant).
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
