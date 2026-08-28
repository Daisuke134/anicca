---
name: loop-development
description: Develop, fix, deploy, or retire Life Manager loops without modifying another loop's code, state, browser, launchd job, or production release. Use for any change under loops/, runtime/loop/, loop entrypoints, loop registry, launchd cadence, healthchecks, or immutable releases.
---

# Life Manager loop development

Life Manager has one code source: GitHub `main`. A loop never owns a permanent branch, worktree,
checkout, or release. Temporary worktrees isolate development; immutable main-derived releases run
production; each loop owns only its repository-external state.

## Required shape

```text
temporary worktree -> tested PR -> main -> immutable release -> lm-loop apply -> official readback
                                                   |
                                                   +-> loop-specific state outside the release
```

## Before editing

1. Read the loop's current spec, registry entry, entrypoint, state path, loaded plist arguments, and
   latest terminal receipt. Do not infer production from the current checkout.
2. Fetch `origin/main`. If the shared checkout is dirty or another agent may edit it, create one
   temporary `.worktrees/<change>` branch from current `origin/main`. Preserve every unrelated diff.
3. Name the exact files and loop IDs owned by the change. Do not modify sibling loops while fixing
   one loop unless the root cause is in their shared runtime boundary.

## Development rules

- Keep code in the Life Manager repo. Keep credentials, ledgers, receipts, browser profiles,
  candidate caches, and duplicate fences outside Git and outside releases.
- Add or change one registry entry and one tested repository-relative entrypoint. Do not create a
  handwritten production plist, a loop-specific installer, or another provider/router/cleanup owner.
- Use the smallest focused tests that catch the reported failure. Do not run destructive production
  E2E from a worktree.
- Never point launchd at a branch, worktree, mutable checkout, or `~/loops/current` symlink inside
  ProgramArguments. It must hold one exact release path.
- Never directly run `launchctl load/unload/bootstrap/bootout`. Use `bin/launchctl-safe`; use
  `~/loops/current/bin/lm-loop apply` as the only installer.
- Never kill or restart another loop's process, browser, profile, or state owner. Shared browser work
  requires the existing identity lease and sequential execution.

## Merge and deploy

1. Run focused tests and `git diff --check`; inspect the owned diff.
2. Fetch, rebase the temporary branch onto current `origin/main`, commit, push, open a PR, and merge.
3. Cut a release only from the merged `origin/main` commit with `bin/cut-loop-release.sh origin/main`.
4. Apply through `~/loops/current/bin/lm-loop apply`. For a scoped repair, set
   `LIFE_MANAGER_APPLY_TARGET=<loop-id>` one loop at a time. Never regenerate/install plists directly.
5. The release activation and apply lock must be free. A stale release or busy owner is a hard stop;
   do not bypass the lock or retry through another checkout.

## Done means production evidence

All applicable statements must be true:

- PR is merged and release SHA is an ancestor of `origin/main`.
- `RELEASE.json`, installed plist, loaded ProgramArguments, and actual entrypoint identify the same
  exact immutable release.
- The natural or explicitly authorized launchd wake reaches a terminal event from that release.
- External effects have official provider/account readback and a durable receipt.
- A second wake proves the same effect/source is not duplicated.
- Cleanup preserves the loaded release and every durable state/receipt.
- The temporary worktree is clean, merged, unused, then removed. Dirty, unmerged, or active worktrees
  are never removed by another session.

Tests, exit 0, a running PID, or a model `completed` response alone are not Done.

## One runtime table

Use the registry-backed control plane instead of process searches or per-loop status scripts:

```bash
~/loops/current/bin/lm-loop doctor
~/loops/current/bin/lm-loop status all
~/loops/current/bin/lm-loop watch all
```

`doctor` finds unmanaged/missing definitions. `status all` is the snapshot table. `watch all` is
the live table. Do not build another inventory or infer health from launchd PID existence.

## Canonical references

- Loop architecture and commands: `docs/loops/README.md`
- macOS control plane: `docs/superpowers/specs/2026-08-27-macos-loop-control-plane-design.md`
- Runtime truth: `config/loop-registry.json` plus loaded `launchctl-safe print` readback
