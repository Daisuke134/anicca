# macOS Loop Control Plane — TODO 8 bounded cleanup

Every generated plist now runs through immutable `bin/lm-loop-run`. Before
executing the exact repository entrypoint, the wrapper applies that registry
entry's cleanup contract to its own state/log roots.

## Per-loop deletion boundary

A run directory is eligible only when all are true:

- it is a real directory directly below `<root>/runs`;
- it contains regular `.lm-regenerable` and terminal `summary.json` files;
- it is not an active run ID;
- it has no `.lm-protected` marker; and
- no descendant name denotes a receipt, ledger, credential, session, wallet,
  or payment artifact.

Eligible completed runs are bounded by `max_runs` and `max_age_days`, renamed
inside the same filesystem, then removed. Symlinks and unmarked directories
are never traversed. `cleanup-latest.json` is outside `runs` and mode 0600.

## Central shared-artifact owner

`runtime/loop/central_cleanup.py` owns only `~/loops/releases`. It accepts only
timestamp/SHA directories with a valid 40-character-SHA `RELEASE.json` and
preserves:

- the `current` symlink target;
- every release referenced by any installed `ai.anicca.*` plist argv;
- every explicitly protected release; and
- the newest configured rollback generations.

No business state, receipts, ledgers, browser sessions, credentials, shared
cache, or orphan path is currently configured as a central candidate. The
registry's disk-cleanup label points to this central entrypoint.

## Verification

Five cleanup tests cover active/unmarked/receipt preservation, pressure
reclamation, release current/protected retention, per-loop wrapper ordering,
and loaded-plist release discovery. Apply tests prove generated argv is exactly
`<release>/bin/lm-loop-run <loop-id> <release>` and missing wrappers fail the
whole generation before mutation.

An isolated central E2E created four releases with 2 MiB payloads. It removed
only the old unreferenced release, reclaimed 2,097,203 bytes, retained current,
loaded-protected, and newest releases, and recorded `protected_deletions=0`.

Production readback remains separated from source completion: the existing
`ai.anicca.mr-bot-disk-cleanup` job is running its prior Gig-release
entrypoint with last exit 0. TODO 9 performs its one-label cutover; this slice
does not restart or replace it.

