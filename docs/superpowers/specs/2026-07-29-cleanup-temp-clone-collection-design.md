# cleanup-control: reclaim ephemeral temp git clones (`git_clone_collection`)

## Measured gap (2026-07-29 22:00 JST)

| Fact | Evidence |
|---|---|
| `/tmp/anicca-products-x402.9hyrYf` held 1.9GB | `du -sh` |
| It was a clean clone of `Daisuke134/anicca-products`, HEAD `1deb9d302` present in `~/anicca-project` | `git status --short` empty, `git cat-file -e` |
| No process held it | `lsof` count 0 |
| Free space was 5.9GB = disk-sentinel TIER 3 (`FREE_GB < 10`) | `df -h /`, `disk-sentinel.sh:241` |
| The sentinel ran and reclaimed nothing | manual run, exit 0, no output |
| Root cause | no manifest entry in `scripts/cleanup-control/artifact-lifecycle.json` covers any `/tmp` path |

The directory was removed by hand (5.9GB → 7.6GB free). This spec fixes the reclaimer so the
class of artifact is reclaimed without a human.

## Contract

New artifact class `git_clone_collection`. Its `path` is a collection root whose *children* are
independent git clones (not worktrees, so `sweep_worktree_collection` cannot see them). Entry
carries `finalizer.kind = "remote_recoverable_remove"` and a required
`finalizer.child_name_prefix` — only children whose directory name starts with that prefix are
ever considered.

## Invariants (the gate; break any one → preserve, never remove)

1. **Prefix-bounded.** A child not matching `child_name_prefix` is never inspected or touched.
2. **Git-only.** A child that is not a git repository is preserved (`reason=not_a_git_repository`).
3. **Clean.** `git status --porcelain` must be empty — any modified *or untracked* file preserves.
4. **Remote-recoverable.** After `git fetch --all --prune` inside the child, HEAD must be contained
   in at least one remote ref. No remote, or unreachable HEAD → preserve.
5. **Unused.** No process may hold an open fd inside the child. `lsof` failure → preserve + error.
6. **Revalidated.** All of 3–5 are re-checked after size measurement; HEAD must be unchanged.
7. **Ledger-complete.** Every child yields exactly one append-only JSONL event (removed, preserved,
   or failed) carrying path, reason, policy version and manifest sha256 — same shape as the
   worktree collection sweep.
8. **Fail-closed.** Any unreadable git/lsof state is an error + preserve, never a removal.

## Production wiring

`artifact-lifecycle.json` gains:

```json
{"id": "tmp-anicca-clones", "path": "/tmp", "owner": "agent-temp-clones",
 "class": "git_clone_collection", "ttl_seconds": null, "quota_bytes": 0, "lease": null,
 "finalizer": {"kind": "remote_recoverable_remove", "child_name_prefix": "anicca-"}}
```

## Tests (RED first)

Mirror `tests/test_worktree_cleanup.py`: real temp git repos with a real remote. Cases —
clean+pushed clone removed; dirty clone preserved; untracked-only clone preserved; unpushed HEAD
preserved; non-git dir preserved; non-prefix sibling untouched; ledger event per child.
`tests/test_production_wiring.py` asserts the manifest entry exists with the class and prefix.

## Done

`pytest scripts/cleanup-control/tests` green, and an end-to-end run of `cleanup_control.py sweep`
against a real throwaway clone under `/tmp/anicca-…` removes it while leaving a dirty sibling.
