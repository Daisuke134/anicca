# Security Report — self-improve-checkpoint-resume (Phase 5)

## Static scan

`semgrep --config auto skills/earn/self-improve/lib/checkpoint_resume.py
skills/earn/self-improve/run_evolve.sh` (run live this session): **0 findings, 0 errors**.

## Threat surface

This feature adds a PURE, read-only path-selection function
(`lib/checkpoint_resume.py::find_latest_checkpoint`) plus one new bash pre-invocation step in
`run_evolve.sh`. Neither component:
- opens a network connection (no `socket`/`requests`/`urllib` reference — PROP-CR9, statically
  scanned by `test_prop_cr9_pure_function_source_has_no_effectful_references_outside_main` and
  live-confirmed 0 hits this session)
- spawns a subprocess (no `subprocess` reference in the pure function — same PROP-CR9 scan; the
  `__main__` CLI entrypoint's only effect is one stdout write, called BY `run_evolve.sh` as a
  subprocess, never the other way)
- mutates the filesystem (PROP-CR12a/b/c — static denylist scan for every `os.*`/`shutil.*`
  mutation API + `pathlib` import-absence scan + dynamic before/after directory-snapshot
  comparison across both a `None`-returning and a real-path-returning call; all 4 checks pass)
- reads any file's byte contents, only directory-entry names/existence (`os.listdir`,
  `os.path.isdir`) — a checkpoint directory's internal validity is never inspected by this
  feature (REQ-CR5/PROP-CR8), delegated entirely to `openevolve-run` itself, unchanged
- reads or writes a wallet key, `.env`, or ledger file (grep-scanned this session: zero hits in
  `lib/checkpoint_resume.py`; the sole `.env`-looking substring match was `os.environ`, a false
  positive)
- touches the live-money path (`promote_gate.sh`, `lib/promote_gate.py`, `lib/promote.py`,
  `strategies/pm_backtest_strategy.py`, `config.yaml`, or the launchd plist) — grep-scanned this
  session, zero references found in the new/modified files

## Injection surface (the one real risk class for a feature that builds a shell argument list)

The new `run_evolve.sh` step builds `CHECKPOINT_ARGS` from `$CHECKPOINT_PATH`, itself the captured
stdout of `lib/checkpoint_resume.py`. That path is always constructed by
`os.path.abspath(os.path.join(...))` from directory-entry NAMES already present in `runs_dir` —
never from unsanitized external input — and is passed to `openevolve-run` as a single quoted
array element (`CHECKPOINT_ARGS=(--checkpoint "$CHECKPOINT_PATH")`), never interpolated into a
string that bash re-parses/re-splits, so a directory name containing spaces or shell metacharacters
cannot cause word-splitting or command injection (verified indirectly by
`test_prop_cr_wire2b_checkpoint_found_appends_single_checkpoint_flag`'s own fixture, which uses a
path containing no metacharacters but does exercise the array-element quoting mechanism the same
way a hostile name would).

## Bash argument-list injection bug (found + fixed this session, not a security vuln but adjacent)

See `verification-report.md`'s "Bug caught and fixed" section — FIND-001 was a functional argv
bug (`"${CHECKPOINT_ARGS[@]:-}"` on bash 3.2 injecting a stray empty-string argument), not an
attacker-controlled injection, but it lives in exactly the same code path a real injection would,
so it is recorded here for completeness. Fixed to the canonical
`"${CHECKPOINT_ARGS[@]+"${CHECKPOINT_ARGS[@]}"}"` idiom and independently re-verified by a second
fresh adversary iteration (PASS, 0 blocking findings).

## Conclusion

No security findings. This feature's entire runtime surface is read-only directory-name
inspection plus one already-existing, already-safe shell argument-array-append pattern (now
correctly bash-3.2-safe).
