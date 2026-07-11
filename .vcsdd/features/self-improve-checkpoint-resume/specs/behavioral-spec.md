---
feature: self-improve-checkpoint-resume
phase: 1a/1b
mode: lean
sources:
  - skills/earn/self-improve/run_evolve.sh (read directly, this worktree) — the launchd-triggered
    recurring cycle this feature edits; confirms today's `openevolve-run` invocation passes a fresh
    `--output "$RUN_DIR"` every cycle and NEVER passes `--checkpoint`
  - `openevolve-run --help` (run live in this worktree's venv, `~/.anicca-venvs/self-improve/bin/
    openevolve-run`) — confirms the real, installed `openevolve==0.3.0` CLI flag is `--checkpoint
    CHECKPOINT   Path to checkpoint directory to resume from (e.g.,
    openevolve_output/checkpoints/checkpoint_50)` — this feature adds exactly this flag, no new
    mechanism invented
  - skills/earn/self-improve/config.yaml line 11 (read directly) — `checkpoint_interval: 10  #
    top-level Config field (NOT database.checkpoint_interval)` and line 128's own comment "a
    rate-limit-interrupted run can be resumed with `--checkpoint`" — confirms checkpoint resume was
    already an anticipated, designed-for capability of this harness, just never wired into
    `run_evolve.sh`'s automatic recurring invocation
  - direct log inspection this session (real `runs/*/assessment.json` files under this worktree's
    launchd-produced production body, read by the parent agent-economy loop, not hypothesized):
    three consecutive ~6h cycles (`run-20260710T190919Z`, `run-20260711T011638Z`,
    `run-20260711T072156Z`) each produced a best-candidate `combined_score` numerically IDENTICAL
    to `baseline_stage2_score` (e.g. `4.015488840463803` to many decimal places) — `stage2_pass`
    was `False` (a tie never counts as "beats baseline") every time, so zero candidates reached the
    fresh-adversary review step for 18+ hours despite the loop firing, iterating, and logging
    normally
  - .vcsdd/features/anicca-self-improve-harness/specs/behavioral-spec.md (same repo, prior phase)
    — REQ-OE1/OE5/OE6/OE7, INV-1..8 — this feature extends REQ-OE7's recurring-trigger wiring and
    MUST NOT contradict any of them
  - .vcsdd/features/self-improve-real-ledger/specs/behavioral-spec.md (same repo, prior phase) —
    REQ-RL group, INV-RL1..6, EDGE-RL5a — this feature's own EDGE-CR1 mirrors EDGE-RL5a's
    already-established "runs/ and state/ are gitignored, dev worktrees have neither" pattern
    (confirmed live: this worktree's own `skills/earn/self-improve/.gitignore` contains `runs/` and
    `state/`)
  - skills/earn/self-improve/lib/ledger_reader.py's own module docstring (read directly) — this
    repo's established convention for a pure-Python core called from bash via `"$PY_BIN" "$SKILL_DIR/
    lib/<module>.py"`, the exact pattern this feature's own `lib/checkpoint_resume.py` follows for
    its shell call site
integration:
  extends:
    - anicca-self-improve-harness (REQ-OE7's recurring-trigger wiring gains one new pre-invocation
      step; REQ-OE1/OE5/OE6, INV-1..8 all stay in force, none weakened)
  does_not_replace_or_modify:
    - openevolve's own checkpoint internals (`openevolve/controller.py`'s checkpoint save/load
      code) — this feature only ever passes an EXISTING CLI flag pointing at a path openevolve
      itself already knows how to read; it never reads or writes checkpoint file contents
    - config.yaml's `checkpoint_interval`/`database` settings (unchanged)
    - promote_gate.sh / lib/promote_gate.py / lib/promote.py (the promotion-gate step downstream of
      openevolve-run is untouched; this feature only affects what population openevolve STARTS
      from, never what gets promoted or how)
    - strategies/pm_backtest_strategy.py's EVOLVE-BLOCK content or fixed region
    - any live-money path, wallet key, `.env`, ledger file, spend cap, or the launchd plist itself
      (`ai.anicca.self-improve-evolve.plist` is not edited by this feature — it already invokes
      `run_evolve.sh` with no arguments this feature needs to change)
  out_of_scope_this_phase:
    - Any change to `--iterations`/`SELF_IMPROVE_ITERATIONS` (REQ-OE5's per-run budget is
      unaffected; this feature makes MORE of each run's iterations count toward NEW exploration by
      not re-deriving the same starting population, but does not itself raise the per-run cap)
    - Cross-run checkpoint garbage collection / retention policy for `runs/*/checkpoints/` (old
      checkpoint directories accumulate on disk exactly as they do today; a future feature may
      prune them — not specified here)
---

# Behavioral Specification — self-improve-checkpoint-resume (Phase 1a)

## Purpose

`run_evolve.sh` fires on a recurring ~6h launchd timer (REQ-OE7). Every firing creates a brand-new
`runs/run-<timestamp>/` directory and invokes `openevolve-run` with `initial_program =
strategies/pm_backtest_strategy.py` (the single committed baseline) and NO `--checkpoint` flag.
`openevolve-run` itself already checkpoints its MAP-Elites population under `<output>/checkpoints/
checkpoint_<N>/` every `checkpoint_interval` iterations (config.yaml line 11) — but because the
next cycle never points at ANY prior run's checkpoint, that population is discarded at the end of
every cycle. Each cycle re-starts from a population of exactly one program (the seed) and gets only
`ITERATIONS` (today 20-40) total iterations to both rediscover and try to beat the same
already-known-optimum baseline from a cold start — which is the directly-observed, confirmed-live
root cause of three consecutive ~6h cycles producing a tied (never-improving) `combined_score` and
zero forward progress for 18+ hours (see sources above).

This feature adds ONE pre-invocation step to `run_evolve.sh`: before calling `openevolve-run`, look
for the most recent PRIOR run's highest-numbered checkpoint and pass it via `--checkpoint <path>` —
an existing, already-installed, already-documented `openevolve-run` CLI flag, not a new mechanism.
When no prior checkpoint exists (first-ever run, or every prior run crashed before
`checkpoint_interval`), the command runs exactly as it does today — this feature strictly ADDS an
optional flag, it never removes or alters the existing fallback path.

This is a harness-only change: no strategy file, promotion gate, live-money path, or launchd plist
is touched.

## Purity Boundary Analysis

- **Pure core (this feature's entire testable surface):** `lib/checkpoint_resume.py::
  find_latest_checkpoint(runs_dir: str, current_run_id: str) -> Optional[str]`. Given a `runs_dir`
  path and the CURRENT run's own ID (so it never picks itself), it decides which checkpoint path
  (if any) to resume from. It is deterministic path/existence logic ONLY: `os.listdir`,
  `os.path.isdir`, string parsing/sorting — no subprocess, no network, no mutation of anything on
  disk, no reading of ANY file's byte contents (it never opens/parses a checkpoint's internal
  files — see REQ-CR5). Same input directory tree → same output, every time, in-process.
- **Effectful shell:** `run_evolve.sh`'s existing bash — it already creates `$RUN_DIR`, invokes
  `openevolve-run`, and appends to `$LOG` (REQ-OE6/OE7, unchanged conventions). This feature adds
  exactly one new effectful step to that shell script: shell out to the pure function (via
  `"$PY_BIN" -c` or a thin CLI entrypoint, mirroring `lib/ledger_reader.py`'s existing
  `"$PY_BIN" "$SKILL_DIR/lib/<module>.py"` call convention) BEFORE the `openevolve-run` invocation,
  capture its stdout (a path or empty string), log the outcome, and conditionally append
  `--checkpoint "<path>"` to the existing command array. `openevolve-run` itself (a separate
  process, already effectful, unchanged by this feature) is what actually reads the checkpoint
  directory's contents and resumes from it — that read is entirely outside this feature's own
  code.

## EARS-Format Functional Requirements

### Group CR-FIND — pure checkpoint discovery

- **REQ-CR1** `lib/checkpoint_resume.py` SHALL expose a PURE function `find_latest_checkpoint(
  runs_dir: str, current_run_id: str) -> Optional[str]` that returns the absolute path to a
  checkpoint directory to resume from, or `None` when no prior run has any usable checkpoint.

- **REQ-CR2** WHEN selecting which PRIOR RUN to resume from, THE SYSTEM SHALL: list the immediate
  subdirectories of `runs_dir`, EXCLUDE any entry equal to `current_run_id`, sort the REMAINING
  candidate names lexicographically DESCENDING (run directory names are `run-YYYYMMDDTHHMMSSZ` UTC
  timestamps, which sort correctly as plain strings — REQ-OE7's existing naming convention,
  unchanged), and select the FIRST (most recent) candidate that has a non-empty `checkpoints/`
  subdirectory (per REQ-CR3's definition of "has a checkpoint"). Runs with no `checkpoints/`
  subdirectory, or an EMPTY one, SHALL be skipped over (not selected, but also not treated as a
  fatal error) in favor of the next-most-recent candidate.

- **REQ-CR3** WITHIN the selected prior run's `checkpoints/` directory, THE SYSTEM SHALL consider
  only entries whose name matches the literal pattern `checkpoint_<N>` where `<N>` is one or more
  ASCII digits, parse `<N>` as an INTEGER (not a string), and select the entry with the LARGEST
  integer `<N>` (e.g. `checkpoint_100` SHALL be selected over `checkpoint_20` — NEVER a lexicographic
  comparison, which would incorrectly rank `checkpoint_20` above `checkpoint_100`). Any entry inside
  `checkpoints/` that does NOT match this pattern (a stray file, a differently-named directory, a
  hidden dotfile) SHALL be ignored — its presence SHALL NEVER raise an exception or abort the scan.

- **REQ-CR4** WHEN `runs_dir` does not exist at all, is empty, or contains ONLY the excluded
  `current_run_id` entry, THE SYSTEM SHALL return `None` — this is the ordinary, expected "first-ever
  run" case, not an error condition.

- **REQ-CR5** `find_latest_checkpoint` SHALL perform PATH/EXISTENCE logic only (directory listing,
  name pattern matching, integer comparison). It SHALL NEVER open, read, or validate the byte
  contents of any file inside a `checkpoint_<N>` directory (no checking for openevolve's own
  expected internal files, no deserializing any checkpoint state). Whether a selected checkpoint
  directory is internally complete/valid enough for `openevolve-run` to actually resume from is
  ENTIRELY `openevolve-run`'s own concern, at a LATER, separate point in the pipeline (REQ-CR7) —
  this function's contract ends at "a directory matching the expected shape and naming convention
  exists at this path."

### Group CR-WIRE — wiring into run_evolve.sh

- **REQ-CR6** `run_evolve.sh` SHALL invoke the REQ-CR1 function, via `"$PY_BIN"`, AFTER `$RUN_DIR`
  is created (so `current_run_id` = the just-created `$RUN_ID`, correctly excluding itself even
  though its own now-empty directory already exists under `runs/`) and BEFORE the existing
  `"$OPENEVOLVE_BIN"` invocation.

- **REQ-CR7** WHEN the REQ-CR6 call returns a non-empty checkpoint path, THE SYSTEM SHALL append
  exactly one additional argument pair, `--checkpoint "<path>"`, to the EXISTING `openevolve-run`
  invocation (unchanged otherwise: same `initial_program`, `evaluation_file`, `--config`,
  `--iterations`, `--output` arguments, in the same order) — `openevolve-run`'s OWN internal
  behavior when given a `--checkpoint` path (including how it handles an internally
  incomplete/corrupt one) is entirely `openevolve-run`'s concern; if it fails or exits non-zero for
  that reason, that failure SHALL surface through the EXISTING REQ-OE6 "crashed run is inconclusive"
  handling in `run_evolve.sh` — this feature introduces NO new failure-handling branch for that
  case.

- **REQ-CR8** WHEN the REQ-CR6 call returns empty/`None` (no prior checkpoint found, for ANY reason
  — first-ever run, all prior runs lack a `checkpoints/` dir, or `runs_dir` itself is missing), THE
  SYSTEM SHALL invoke `openevolve-run` with EXACTLY the same argument list it uses today (no
  `--checkpoint` flag at all) — i.e. this feature's fallback path is byte-for-byte the pre-existing
  behavior, never a degraded or different variant of it.

- **REQ-CR9** THE SYSTEM SHALL append a log line to `$LOG` (the same file/convention every other
  `run_evolve.sh` step already writes to) stating EITHER the checkpoint path selected and used, OR
  that none was found — this decision SHALL NEVER be silent. This restates this repo's existing
  "loud, visible logging, never a silent branch" convention (every other step in `run_evolve.sh`
  already follows it; REQ-CR9 makes it explicit for this feature's own new step).

## Global Invariants

| # | Invariant |
|---|---|
| INV-CR1 | `find_latest_checkpoint` NEVER writes, deletes, renames, or mutates anything on disk — it is a pure read-only path/existence query (REQ-CR5) |
| INV-CR2 | This feature never touches `strategies/pm_backtest_strategy.py`, `promote_gate.sh`, `lib/promote_gate.py`, `lib/promote.py`, `config.yaml`, or `ai.anicca.self-improve-evolve.plist` |
| INV-CR3 | This feature never reads or writes any wallet key, `.env`, ledger file, or spend-cap value — it is scoped exclusively to `runs/*/checkpoints/*` path selection |
| INV-CR4 | The fallback path (no checkpoint found) is byte-for-byte identical, in its `openevolve-run` invocation, to `run_evolve.sh`'s pre-feature behavior (REQ-CR8) — this feature can only ADD a `--checkpoint` argument, never change any other existing argument |
| INV-CR5 | REQ-OE6's "a crashed/killed/timed-out openevolve run is inconclusive, no candidate promoted, baseline untouched" invariant is preserved unchanged — this feature adds no new promotion path and does not weaken that handling for a `--checkpoint`-resumed run |

## Edge Cases

- **EDGE-CR1** (mirrors the prior phase's already-established EDGE-RL5a pattern) `runs/` is
  gitignored (confirmed: this worktree's own `skills/earn/self-improve/.gitignore` contains
  `runs/`) — a fresh dev worktree checkout has NO `runs/` directory at all. Tests for
  `find_latest_checkpoint` MUST construct a synthetic `runs_dir` tree under `tmp_path` (pytest
  fixture), never rely on or read this worktree's own (nonexistent) `runs/` directory, and MUST
  NEVER symlink or copy any real production `runs/` directory into a worktree.
- **EDGE-CR2** No `runs/` directory exists at all (very first invocation ever) → REQ-CR4 → `None` →
  REQ-CR8 fallback.
- **EDGE-CR3** `runs/` exists but is empty, or contains ONLY the current run's own just-created
  directory → REQ-CR4 → `None` → REQ-CR8 fallback.
- **EDGE-CR4** A prior run directory exists but has no `checkpoints/` subdirectory at all (e.g. it
  crashed before `checkpoint_interval` iterations, or predates this feature) → skipped per REQ-CR2,
  next-most-recent candidate considered instead; if none qualifies, REQ-CR4 → `None`.
- **EDGE-CR5** A prior run directory has a `checkpoints/` subdirectory that is present but EMPTY →
  same treatment as EDGE-CR4 (skipped, not selected).
- **EDGE-CR6** A `checkpoints/` directory contains non-`checkpoint_<N>`-shaped entries (a stray
  file, a hidden dotfile, a directory with a non-numeric suffix) interleaved with valid
  `checkpoint_<N>` entries → REQ-CR3 ignores the non-matching entries and selects correctly among
  the valid ones; their mere presence never raises an exception.
- **EDGE-CR7** Multiple prior runs each have checkpoints; the most recent run BY DIRECTORY NAME has
  fewer/lower-numbered checkpoints than an older run (e.g. it crashed early). REQ-CR2 still selects
  the MOST RECENT run (by directory-name recency), NOT the run with the globally highest checkpoint
  number — "resume from the last cycle's population" is defined as most-recent-cycle, not
  highest-ever-checkpoint-count, so this feature keeps extending the SAME chronological lineage
  rather than possibly reaching further back in time.
- **EDGE-CR8** The selected checkpoint directory exists (by REQ-CR3's path logic) but is internally
  incomplete/corrupt (missing files `openevolve-run` itself needs to resume) — explicitly OUT of
  this function's responsibility (REQ-CR5); if `openevolve-run` then fails to resume, that surfaces
  as REQ-OE6's existing "crashed run is inconclusive" handling, not a new failure mode this feature
  must detect or prevent.
- **EDGE-CR9** `current_run_id` happens to already have its OWN (freshly created, necessarily empty)
  directory present under `runs_dir` at scan time (true in practice, since `run_evolve.sh` creates
  `$RUN_DIR` before calling this function, per REQ-CR6) — REQ-CR2's explicit exclusion of
  `current_run_id` prevents a run from ever "resuming from itself."

## "Done" / 4-D Convergence

| dimension | condition |
|---|---|
| spec | this document + verification-architecture.md |
| test | RED: unit tests for `find_latest_checkpoint` covering REQ-CR1-5 and EDGE-CR1-9 all written and failing (module does not yet exist) before any implementation; GREEN: all passing |
| impl | `lib/checkpoint_resume.py::find_latest_checkpoint` + `run_evolve.sh`'s new pre-invocation step (REQ-CR6-9), both present and runnable |
| impl review | fresh-context `vcsdd-adversary` review of both files returns PASS (lean mode: no BLOCKING findings) |
| verification | Phase 5: proof obligations in verification-architecture.md discharged; a real, hand-constructed two-run `tmp_path` fixture demonstrates `run_evolve.sh`'s new step selecting and logging the correct `--checkpoint` path end-to-end (or a documented reason it could not be exercised without touching the production `runs/` tree, per EDGE-CR1) |

## UNVERIFIED

- Whether resuming from a stale/older checkpoint (REQ-CR2's "most recent run by directory name,"
  EDGE-CR7) ever meaningfully out-performs the alternative "highest checkpoint number across all
  runs" policy in practice is an empirical question about openevolve's own MAP-Elites dynamics, not
  something this feature's pure path-selection logic can prove — the chronological-lineage choice
  is a documented, defensible design decision (see EDGE-CR7's rationale), not an empirically-tuned
  one. A future feature may revisit this if real cycle-over-cycle score data suggests otherwise.
