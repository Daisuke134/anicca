# Disk Cleanup — Exact Diff Patch Series

Canonical spec: `docs/superpowers/specs/2026-08-20-life-manager-disk-cleanup-loop-design.md`.
This file is the exact file/line/diff/readback SSOT for P0–P7. Execution priority is P4, P1, P2, P3, P5, P6, P0 remaining, pre-merge, final merge/deploy, P7, worktree retirement.

## Branch and merge contract

- Workspace: `~/Projects/life-manager-symphony-workspaces/GH-11`
- Branch: `fix/disk-cleanup-end-to-end`
- Commit and push every finished atom to this branch; do not merge intermediate cleanup PRs to main.
- Finish P0 remaining source work and P1–P6 implementation plus isolated verification in this branch.
- Merge one final PR only after the pre-merge gate in the canonical spec passes.
- Because production accepts only main-derived immutable releases, perform release/readback and P7 24-hour/7-day verification after that merge.
- Retire this worktree and branch only after P7 passes.

## Goal and boundaries

Keep every revenue loop running while each writer bounds its own scratch/cache/log/WAL/artifacts and central cleanup removes only shared regenerable garbage. Normal free space is at least 30 GiB; new unbounded writes projected below 11 GiB are zero.

- Never mutate `gui/$UID` launchd state from Remote (`bootstrap`, `bootout`, `kickstart`, `submit`, direct or wrapped).
- Never delete active/dirty/unpushed worktrees, buyer input, undelivered/resubmission bases, credentials, ledgers, receipts, browser profiles, or protected stores.
- Never add a global disk-pressure loop stop.

## Patch/file map

| Patch | State | Exact surface |
|---|---|---|
| P0 runtime | cleanup done; reconciler self-rollout unfinished | `bin/reconcile-agent-runner-release.sh`, `runtime/loop/lm_loop.py`, production argv/SHA readback |
| P1 zero waste | unfinished | host inventory + exact delete receipt |
| P2 writer retention | common runtime done; census unfinished | `runtime/loop/lm_loop_run.py:45-51,121-135`, `runtime/loop/runtime_event.py:31-84,200-220` |
| P3 release GC | unfinished | `runtime/loop/central_cleanup.py:30-86`, `runtime/loop/loop_cleanup.py:92-135` |
| P4 legacy | unfinished | caller/state inventory + retirement receipt |
| P5 gig terminal | unfinished | project ledger/finalizer; not code-release GC |
| P6 capacity | unfinished | `skills/self/disk-cleanup/disk_cleanup.py:331+` + producer admission |
| P7 verify | unfinished | 24h/7d receipts + spec checkbox |

## P0 — Runtime normalization

### Current checkbox state

- [x] Source fix merged to main.
- [x] Cleanup loaded from `663f1af0...`; natural run PASS with errors 0 and protected deletions 0.
- [x] Compatibility alias has zero references and is removed.
- [ ] Release-reconciler itself is loaded from a main-derived immutable release.
- [ ] P0 closes only after that loaded argv/SHA readback.

Already merged source patch, `runtime/loop/lm_loop.py:443`:

```diff
         eligible = [row for row in rows if (
             row["classification"] == "managed"
+            and row["loop_id"] != os.environ.get("LIFE_MANAGER_LOOP_ID")
             and row["provider_route"] == route
```

Remaining operational patch: the non-Remote owner loads the release-reconciler itself from a main-derived immutable release. Cleanup rollout, its natural PASS, and compatibility-alias removal are complete. Read-only `launchctl print gui/$UID/ai.anicca.life-manager-release-reconciler` must show the main-derived argv and `LIFE_MANAGER_RELEASE_SHA`. Acceptance: reconciler old argv 0; cleanup old argv 0; alias 0; natural cleanup wake PASS.

## P1 — Zero-waste baseline

Write runtime evidence to `~/.local/state/life-manager/disk-cleanup/zero-waste-baseline.json`:

```diff
+{"schema_version":1,
+ "volume_total_bytes":0,"volume_free_before_bytes":0,"volume_free_after_bytes":0,
+ "classified_roots":[],"unclassified_roots_over_100_mib":[],
+ "removed":[],"preserved":[],"errors":[],"protected_deletions":0}
```

Every candidate records `path,bytes,owner,reason,recoverability,open_handles,git_status,action`. Auto-removal is limited to regenerable cache, hash-identical duplicates, clean+merged+idle+unlocked worktrees, expired marked runs, and unused/partial immutable releases. Acceptance: unclassified roots >=100 MiB 0, errors 0, protected deletion 0, free >=30 GiB.

## P2 — Writer-owned retention

Do not reimplement these existing paths: `reset_loop_scratch()` already cleans before/finally; `rotate_jsonl_locked()` already rotates active JSONL at 16 MiB and supports bounded archives. Patch only measured unbounded writers:

```diff
@@ each measured unbounded writer entrypoint/config
-append_without_bound(...)
+append_with_existing_rotation(..., max_bytes=<measured>, keep_archives=<measured>)
```

Acceptance: every managed writer has owner/quota/retention/finalizer/active lease, forced overflow returns to the same bound, active session loss 0.

## P3 — Release GC completion

### P3a actual launchd argv protection

Files: `runtime/loop/central_cleanup.py:30-86`, `runtime/loop/tests/test_loop_cleanup.py`.

```diff
--- a/runtime/loop/central_cleanup.py
+++ b/runtime/loop/central_cleanup.py
@@
+def launchd_release_roots(labels: set[str], releases_root: Path) -> set[Path]:
+    """Protect argv held by launchd; print is read-only."""
+    protected: set[Path] = set()
+    base = releases_root.resolve()
+    for label in labels:
+        completed = subprocess.run(
+            ["launchctl", "print", f"gui/{os.getuid()}/{label}"],
+            capture_output=True, text=True, timeout=15)
+        if completed.returncode != 0:
+            continue
+        for release in base.iterdir():
+            if release.is_dir() and str(release.resolve()) in completed.stdout:
+                protected.add(release.resolve())
+    return protected
@@
-    protected = loaded_release_roots(agents, releases) | open_release_roots(releases)
+    labels = {path.stem for path in agents.glob("ai.anicca.*.plist")}
+    protected = (loaded_release_roots(agents, releases)
+                 | launchd_release_roots(labels, releases)
+                 | open_release_roots(releases))
```

```diff
+def test_release_gc_preserves_argv_held_by_launchd_even_after_plist_changes(self):
+    # plist points new; read-only launchctl print still names old; preserve both.
```

### P3b abandoned partial release collection

Files: `runtime/loop/loop_cleanup.py:92-135`, `bin/cut-loop-release.sh:32-59,86-96`. The cutter already owns `.release-cut.lock` and EXIT cleanup, so GC fails closed while the lock exists and collects only a release-shaped directory without `RELEASE.json` older than one hour.

```diff
--- a/runtime/loop/loop_cleanup.py
+++ b/runtime/loop/loop_cleanup.py
@@
 RELEASE_NAME = re.compile(r"\d{8}T\d{6}-[0-9a-f]{8,40}\Z")
+PARTIAL_RELEASE_GRACE_SECONDS = 3600
@@
-def gc_releases(releases_root: Path, current: Path, *, keep: int, protected: set[Path]):
+def gc_releases(releases_root: Path, current: Path, *, keep: int,
+                protected: set[Path], now: float | None = None):
@@
-    candidates = []
+    now = time.time() if now is None else now
+    candidates, partials = [], []
     for path in releases_root.iterdir():
+        if (RELEASE_NAME.fullmatch(path.name) and path.is_dir() and not path.is_symlink()
+                and not (path / "RELEASE.json").exists()):
+            if not (releases_root.parent / ".release-cut.lock").exists():
+                if now - path.stat().st_mtime > PARTIAL_RELEASE_GRACE_SECONDS:
+                    partials.append(path)
+            continue
         if not _valid_release(path):
             continue
@@
+    for path in partials:
+        if path.resolve() not in protected:
+            _make_tree_removable(path)
+            result["reclaimed_bytes"] += _remove_marked(path)
+            result["removed_releases"] += 1
```

Acceptance: retain current + actual loaded/open + one rollback only; partial/unused 0; immediate replay reclaims 0.

## P4 — Legacy retirement

Add `docs/migrations/disk-cleanup/legacy-retirement.json` before deleting source:

```diff
+{"schema_version":1,"legacy_roots":[],"callers_before":[],"state_migrations":[],
+ "remote_refs":[],"callers_after":[],"retired_roots":[],"rollback":[]}
```

Retire a root only when callers after=0, required source/state is in main, dirty/unpushed=0, and a remote ref or identical copy exists. Never mass-delete Hermes/OpenClaw/workspaces by name alone.

## P5 — Gig terminal lifecycle

`skills/earn/gig/scripts/gig_release.py:240-305` is code-release GC, not buyer-project lifecycle. Patch the project ledger/finalizer instead:

```diff
@@ project ledger
+"artifact_lifecycle":{"terminal":false,"terminal_reason":null,
+ "buyer_accepted_at":null,"payment_settled_at":null,
+ "resubmission_base":[],"regenerable_paths":[]}
@@ project finalizer
+if buyer_accepted and payment_settled and not dispute_open:
+    preserve(resubmission_base, originals, ledger, receipts)
+    remove_only(regenerable_paths)
+    mark_terminal_receipt()
```

Acceptance: undelivered/resubmission bases retained; only accepted+settled terminal projects reclaimed; active project loss 0.

## P6 — Capacity firewall without loop stopping

Anchors: `skills/self/disk-cleanup/disk_cleanup.py:331-333` and each producer admission point.

```diff
@@ each managed producer lifecycle manifest
+"capacity":{"max_bytes":0,"claim_bytes":0,
+ "heartbeat_path":"...","pressure_mode":"stream|rotate|compact|checkpoint"}
@@ before a new bounded allocation
+claim = reserve_capacity(owner, requested_bytes, heartbeat)
+if not claim.granted:
+    continue_useful_work(mode=pressure_mode)  # never global-stop
```

Acceptance: global loop stop 0; every producer has claim/quota/heartbeat; new unbounded write projected below 11 GiB 0.

## P7 — Forever verification

Only after measured evidence:

```diff
--- a/docs/superpowers/specs/2026-08-20-life-manager-disk-cleanup-loop-design.md
+++ b/docs/superpowers/specs/2026-08-20-life-manager-disk-cleanup-loop-design.md
@@
-- [ ] P7 Forever verification
+- [x] P7 Forever verification — receipt: <24h>; <7d>; Telegram messageId: <id>
```

Required: 24h free >=11 GiB and ENOSPC/protected deletion/cleanup failure/global stop all 0; following 7d state-write failure/oversubscription 0; final free >=30 GiB.

## Immutable execution order

P0 production → P1 baseline → P2 unbounded writers → P3 release GC → P4 legacy → P5 gig terminal → P6 capacity → P7 24h+7d. “Done” means bounded writers plus time-window recurrence proof, not one successful cleanup.
