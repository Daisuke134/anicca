# Task worktree lifecycle

Every temporary Life Manager worktree has one named owner, one task, and a renewable lease. The lease is stored in the repository's shared Git metadata, not committed source, while Git's native worktree lock points to it.

```bash
python3 scripts/worktree-lease.py acquire --owner codex-root --task WT-04
python3 scripts/worktree-lease.py heartbeat --owner codex-root
python3 scripts/worktree-lease.py audit
```

The default lease lasts 24 hours. The owner renews it while working and retires the worktree after merge. An expired lease is only a signal to contact or verify the owner; it is never permission to unlock or delete the worktree.

Before an exact-path retirement, the owner must re-check all of these conditions in the same operation:

1. the path is still a registered worktree and its HEAD has not changed;
2. the caller matches the lease owner;
3. tracked, untracked, and ignored state are empty;
4. HEAD is reachable from the freshly fetched `origin/main`;
5. the branch has no open pull request;
6. no process has its working directory or an open file under the path.

If any check is unavailable or fails, retain the worktree. Never force-remove, bulk-unlock, or treat lease expiry as proof of abandonment. The verified owner then records the lease path from the native lock reason, runs `git worktree unlock <exact-path>` followed by `git worktree remove <exact-path>` from a different checkout, and deletes only that recorded lease file. Finally run `git worktree list --porcelain` plus `git worktree prune -n -v` for readback. These retirement commands are deliberately not automated until one command can enforce all six preconditions without a race.
