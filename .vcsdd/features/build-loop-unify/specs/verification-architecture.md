# Verification Architecture — build-loop-unify

## Purity Boundary Map
- **Pure Core**: none in scope (this feature edits an effectful shell script + a prompt
  text file; there is no algorithmic core to formally verify).
- **Effectful Shell**: `skills/self/claude-p-mainloop.sh` (subprocess spawn, pidfile I/O,
  log I/O), `skills/self/claude-p-mainloop-prompt.txt` (static text, read-only at runtime).
- **Explicitly out of boundary** (verified untouched): `skills/self/founder-loop/**`
  (deterministic ledger writer + CEO allocator — REQ-001).

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-000 | REQ-000 evidence commands (grep/find for `claude` invocations) reproduce the stated zero/one counts in this worktree | 0 | true | grep/find (Bash) |
| PROP-001 | `claude-p-mainloop.sh` passes `bash -n` (syntax) and `shellcheck` with no new warnings vs. baseline | 1 | true | shellcheck |
| PROP-002 | Unset `CLAUDE_P_MAINLOOP_MODEL` → script's constructed command line contains `--model sonnet` (dry-run capture via a stub `claude` on PATH + `CLAUDE_P_MAINLOOP_TEST=1` dir isolation, no real `claude` invocation, no touch of the live pidfile/log paths) | 1 | true | bash test harness |
| PROP-003 | `CLAUDE_P_MAINLOOP_MODEL=opus` → constructed command line contains `--model opus` (same isolated harness) | 1 | true | bash test harness |
| PROP-007 | With `CLAUDE_P_MAINLOOP_TEST=1` and all dir vars pointed at a temp dir, the real `$HOME/.openclaw/state/claude-p-mainloop.pid` (the live cron's pidfile) is untouched by the test run | 0 | true | `find`/`stat` mtime check (Bash) |
| PROP-004 | pidfile guard, kill-switch check, and `$(cat "$PROMPT_FILE")` pattern are still present (grep for the exact guard lines) | 0 | true | grep (Bash) |
| PROP-005 | Prompt file contains the two new explicit sentences (no-earn boundary, wallet-is-truth boundary) | 0 | true | grep (Bash) |
| PROP-006 | `founder-loop.sh`, `record-earn.mjs`, `ceo/*` have zero diff vs. `origin/main` after this feature's changes | 0 | true | `git diff --stat` scope check |

## Verification Strategy
- **Tier 0** (no formal proof needed): file-existence/content greps (PROP-000, PROP-004,
  PROP-005, PROP-006) — these are static text assertions, not algorithmic behavior.
- **Tier 1** (property/example tests): PROP-001 (shellcheck), PROP-002/PROP-003 (a stub
  `claude` binary is placed first on `PATH` inside the test that just echoes its argv to a
  file, so the test observes the real command line the script constructs without spawning
  a real `claude --dangerously-skip-permissions` process — this is the RED/GREEN test for
  Phase 2a/2b).
- **Tier 2/3**: not applicable — no algorithmic core, no concurrency, no numeric
  invariants in this feature's surface.
