---
name: loop-development
description: Build, modify, migrate, debug, or retire macOS Life Manager loops without breaking sibling production loops. Use for any change to loop code, config/loop-registry.json, launchd, releases, runtime events, provider routing, or loop cleanup.
---

# Life Manager Loop Development

`config/loop-registry.json` is the only lifecycle registry. `bin/lm-loop` is the
only installer, lifecycle command, and runtime observer. A loop owns business
effects; it never owns its plist, release selector, provider profile, sibling
restart, global monitor, or shared cleanup.

## Before editing

1. Work only in a dedicated linked worktree. Run `git worktree lock --reason
   '<task>' <path>` for work that spans production validation. Never develop in
   the shared checkout and never point launchd at a worktree.
2. Fetch and record `HEAD`, upstream, `origin/main`, dirty state, the loop's
   registry row, `bin/lm-loop status <id>`, loaded argv, latest runtime event,
   and official effect receipt. Process liveness is not business success.
3. Select one registry TODO. Do not combine unrelated loop changes.

## Source and state contract

- All executable code, schemas, prompts, adapters, and locked dependency
  manifests live in this repository. Runtime code may not depend on another
  checkout, worktree, or `~/.../skills` source tree.
- Mutable state, logs, credentials, ledgers, receipts, sessions, locks, and
  evidence live under the registry `state_root`/`log_root` or another explicit
  private state root. They never default inside an immutable release.
- Add a loop with one registry row plus one executable repository-relative
  entrypoint. If argv is required, use `runtime/loop/entry_dispatch.py`.
- Model work goes through `runtime/agent-runner/agent_runner.py` using a task
  class. Loop code may not select provider credentials, `CODEX_HOME`, auth
  files, or direct provider REST endpoints.
- Do not write plists or call raw mutating `launchctl`. Do not add installers or
  self-healing sibling restarts. Use `lm-loop apply/start/stop/restart`.

## Required development loop

1. Write the focused failing test before production code. Cover the real
   failure boundary: state outside release, replay-zero, exact argv, no sibling
   mutation, secret-free event, or effect readback.
2. Make the smallest root-cause change. Normal target: at most three files and
   100 production LOC; split larger work by registry TODO.
3. Run focused tests, then:

   ```bash
   python3 -m unittest discover -s runtime/loop/tests -p 'test_*.py'
   node --test apps/life-manager/lib/loop-adapter-registry.test.js
   bin/lm-loop doctor
   ```

4. Fetch, preserve concurrent commits, commit, push the task branch, and
   fast-forward `main`. Never force-push or overwrite another session.
5. Build from an exact pushed main commit. The build stage installs locked
   production dependencies before sealing the release read-only. Never patch an
   active release.
6. Validate the complete registry before mutation. Apply one label at a time in
   domain order. After each swap require plist argv, loaded argv, release SHA,
   state path, and rollback receipt. Stop on the first disagreement.
7. Require a natural scheduled event from the installed SHA. Keep process
   status, terminal status, and official effect status separate; only official
   readback may set an external effect to `verified`.

## Cross-loop gates

Before Done, prove all of these from current state:

- Every managed label exists exactly once, is enabled and loaded, and points to
  one existing immutable release.
- `doctor` has no unmanaged, missing-entrypoint, or installed-retired labels.
- Active registry entrypoints contain no legacy plist installer, raw launchd
  mutation for managed labels, direct provider selection, or worktree source.
- The release dependency import smoke tests pass; no code writes below the
  release root.
- Runtime events are valid and secret-free. A successful process does not imply
  a successful payment, message, publication, application, or trade.
- Cleanup replay reports zero protected deletions and preserves every loaded
  release, receipt, ledger, credential, session, and active run.
- The 500-loop test, clean-user install test, reboot recovery, natural pass, and
  replay-zero test pass.

## Recovery

Fail closed. Preserve the old plist and release, use the host-wide apply lock,
and restore the prior loaded argv if a swap fails. Never retry an uncertain
external effect. For lifecycle recovery use `bin/lm-loop`; for source recovery
rebuild a new release from a pushed commit. Record the incident and the missing
gate in the control-plane spec before continuing.

## Primary references

- Apple launchd guide: https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html
- Git worktree: https://git-scm.com/docs/git-worktree
- Twelve-Factor build/release/run: https://12factor.net/build-release-run
- Control-plane spec: `docs/superpowers/specs/2026-08-27-macos-loop-control-plane-design.md`
