---
name: loop-development
description: Develop, fix, deploy, migrate, or retire macOS Mr.bot loops without modifying another loop's code, state, browser, launchd job, provider profile, or production release. Use for changes to loop entrypoints, config/loop-registry.json, launchd cadence, runtime events, releases, healthchecks, or cleanup.
---

# Mr.bot Loop Development

Mr.bot has one code source: GitHub `main`; one lifecycle registry:
`config/loop-registry.json`; and one operator interface: `bin/lm-loop`. A loop
owns business effects, not its plist, release selector, provider route, sibling
restart, global monitor, or shared cleanup.

```text
locked worktree -> focused test -> merged main -> immutable release -> lm-loop apply -> readback
                                                           |
                                                           +-> mutable private state outside release
```

## Before editing

1. Read the current spec, registry row, entrypoint, state path, loaded plist
   arguments, latest terminal event, and official effect receipt. Never infer
   production from a checkout or PID.
2. Fetch and record `HEAD`, upstream, `origin/main`, and dirty state. Work only
   in a dedicated linked worktree. For production validation, run `git worktree
   lock --reason '<task>' <path>`. Never edit the shared checkout.
3. Name the exact loop IDs and files owned by one registry TODO. Do not modify a
   sibling loop unless the root cause is its shared runtime boundary.

## Source, state, and ownership

- Executable code, adapters, schemas, prompts, and dependency lockfiles live in
  this repository. Runtime may not depend on another checkout, worktree, or
  `~/.../skills` source tree.
- Credentials, state, logs, ledgers, receipts, sessions, browser profiles,
  evidence, and duplicate fences live outside Git and immutable releases.
- Add a loop with one registry row and one tested repository-relative
  entrypoint. Use `runtime/loop/entry_dispatch.py` when argv is required.
- Model work goes through `runtime/agent-runner/agent_runner.py` with a task
  class. Do not select provider credentials, `CODEX_HOME`, auth files, or a
  direct provider API inside loop code.
- Preserve the working interpreter/runtime named by the old loaded argv. Never
  replace a loop-specific venv with the control-plane Python merely because the
  script path is portable; generate the command, then import-smoke its runtime
  dependency on the target host before apply.
- Do not create production plists, loop installers, release watchers, or raw
  mutating `launchctl` calls. Use `lm-loop apply/start/stop/restart`. Never
  restart another loop's process, browser, profile, or state owner.
- Loaded `ProgramArguments` must contain one exact release directory, never a
  branch, worktree, mutable checkout, or `~/loops/current` symlink.

## Develop, merge, and deploy

1. Write the focused failing test first. Cover the real failure boundary:
   state outside release, exact argv, no sibling mutation, replay-zero,
   secret-free event, cleanup protection, or official effect readback.
2. Make the smallest root-cause change. Normal target is at most three files
   and 100 production LOC; split larger work by registry TODO.
3. Run focused tests, `git diff --check`, then:

   ```bash
   python3 -m unittest discover -s runtime/loop/tests -p 'test_*.py'
   node --test apps/mr-bot/lib/loop-adapter-registry.test.js
   ~/loops/current/bin/lm-loop doctor
   ```

4. Fetch again, preserve concurrent commits, commit and push the task branch,
   and merge or verified-fast-forward `main`. Never force-push.
5. Cut only a pushed main commit with `bin/cut-loop-release.sh origin/main`.
   Build installs locked production dependencies before sealing the release
   read-only. Never patch an active release.
6. The host-wide apply lock must be free. Validate the full registry before
   mutation. Apply one label at a time in domain order; after every swap require
   plist argv, loaded argv, release SHA, state path, and rollback receipt.
7. Require a natural scheduled terminal event from the installed SHA. Keep
   launchd state, process result, and official effect result separate. Only
   official provider/account readback can set an external effect `verified`.

## Done gates

- Every managed label exists once, is enabled and loaded, and points to one
  existing immutable release. `doctor` reports unmanaged 0, missing 0, and
  installed-retired 0.
- Active entrypoints have no legacy installer, managed raw launchd mutation,
  direct provider selection, worktree source, or release-local mutable state.
- Dependency import smoke tests pass through the exact interpreter returned by
  the generated command. Runtime events validate with secret
  violations 0. Process success never substitutes for payment, message,
  publication, application, or trade readback.
- Cleanup replay has errors 0 and protected deletions 0 and preserves every
  loaded release, active run, receipt, ledger, credential, and session.
- 500-loop scale, clean-user install, reboot recovery, natural pass, official
  effect separation, gitleaks, and replay-zero pass.
- The worktree is clean, merged, and unused before it is unlocked and removed.
  Never remove another session's dirty, unmerged, locked, or active worktree.

## One runtime table

```bash
~/loops/current/bin/lm-loop doctor
~/loops/current/bin/lm-loop status all
~/loops/current/bin/lm-loop watch all
```

Do not build another inventory or infer health from process searches.

## Recovery

Fail closed. Preserve old plist/release, use the apply lock, and restore prior
loaded argv on swap failure. Never retry an uncertain external effect. Recover
lifecycle through `lm-loop`; recover source by building a new pushed release.
Record the incident and missing gate in the control-plane spec.

## References

- `docs/loops/README.md`
- `docs/superpowers/specs/2026-08-27-macos-loop-control-plane-design.md`
- https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html
- https://git-scm.com/docs/git-worktree
- https://12factor.net/build-release-run
