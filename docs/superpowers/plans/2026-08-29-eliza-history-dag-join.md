# Eliza History DAG Join Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the fixed ElizaOS root tree unchanged while making the Phase F-closeout Mr.bot commit a direct second parent in the migration fork.

**Architecture:** Use Git's built-in `ours` merge strategy on a new migration branch. Fetch the legacy repository with `blob:none`, join the exact fixed commits, verify the tree and parent order, push only the new branch, and store one private receipt.

**Tech Stack:** Git, POSIX shell, `jq`, `shasum`.

**Spec:** `docs/superpowers/specs/2026-08-01-dais-mr-bot-five-phase-execution-spec.md`

## Global Constraints

- Eliza source commit is exactly `29bed1bb394a2c0c7c0df6dc12babbe28667efbe`.
- Phase F-closeout legacy commit is exactly `c9bea215b87755434704a5d16dd8c0a55aff1981`.
- Migration repository is `/Users/anicca/Projects/mr-bot-eliza-migration`.
- Push only new branch `migration/eliza-history` to `Daisuke134/life-manager-eliza`.
- Root tree before and after the join must be byte-identical.
- The join commit must have exactly two parents: Eliza first, legacy Mr.bot second.
- Do not modify either repository's `main`, force-push, delete a repository, import files, install dependencies, run CI, or touch runtime/provider/browser/credential/loop state.
- Verification is Git invariants plus one bounded adversarial review. No unit test or full suite is added for a history-only atom.

---

### Task 1: Join the fixed legacy history without changing the Eliza tree

**Files:**
- Create outside repo: `/Users/anicca/.local/state/mr-bot/migration/elz-f/history-join-receipt.json`
- Create outside repo: `/Users/anicca/Projects/mr-bot-main/.worktrees/elz-f11-plan/.superpowers/sdd/2026-08-29-eliza-history-dag-join/task-1-report.md`
- Modify Git history only: branch `migration/eliza-history` in `/Users/anicca/Projects/mr-bot-eliza-migration`

**Interfaces:**
- Consumes: fixed Eliza commit `29bed1bb394a2c0c7c0df6dc12babbe28667efbe` and fixed legacy commit `c9bea215b87755434704a5d16dd8c0a55aff1981`.
- Produces: a pushed two-parent join commit and private `history-join-receipt.json`; ELZ-F12 consumes the joined branch.

- [ ] **Step 1: Fail closed on branch, worktree, disk, and remote drift**

```bash
cd /Users/anicca/Projects/mr-bot-eliza-migration
ELIZA_SHA=29bed1bb394a2c0c7c0df6dc12babbe28667efbe
LEGACY_SHA=c9bea215b87755434704a5d16dd8c0a55aff1981
test "$(git rev-parse HEAD)" = "$ELIZA_SHA"
test -z "$(git status --porcelain=v1)"
test -z "$(git branch --list migration/eliza-history)"
test -z "$(git ls-remote --heads origin refs/heads/migration/eliza-history)"
test -n "$(git ls-remote https://github.com/Daisuke134/life-manager.git refs/heads/main | awk '{print $1}')"
test "$(git ls-remote origin refs/heads/main | awk '{print $1}')" = "$ELIZA_SHA"
FREE_KIB=$(df -Pk /Users/anicca | awk 'END {print $4}')
test "$FREE_KIB" -ge 1048576
```

Expected: every check exits `0`; there is at least 1 GiB free; neither target branch exists.

- [ ] **Step 2: Fetch only the legacy commit graph and create the join branch**

```bash
cd /Users/anicca/Projects/mr-bot-eliza-migration
ELIZA_SHA=29bed1bb394a2c0c7c0df6dc12babbe28667efbe
LEGACY_SHA=c9bea215b87755434704a5d16dd8c0a55aff1981
git fetch --filter=blob:none --no-tags \
  https://github.com/Daisuke134/life-manager.git \
  refs/heads/main:refs/remotes/legacy-mr-bot/main
git cat-file -e "$LEGACY_SHA^{commit}"
git merge-base --is-ancestor "$LEGACY_SHA" refs/remotes/legacy-mr-bot/main
git switch -c migration/eliza-history "$ELIZA_SHA"
git merge -s ours --no-ff --allow-unrelated-histories \
  "$LEGACY_SHA" \
  -m "chore: join legacy Mr.bot history"
```

Expected: merge exits `0` and creates one commit; it does not check out legacy blobs into the Eliza tree.

- [ ] **Step 3: Prove exact tree and direct parent order before push**

```bash
cd /Users/anicca/Projects/mr-bot-eliza-migration
ELIZA_SHA=29bed1bb394a2c0c7c0df6dc12babbe28667efbe
LEGACY_SHA=c9bea215b87755434704a5d16dd8c0a55aff1981
JOIN_SHA=$(git rev-parse HEAD)
ELIZA_TREE=$(git rev-parse "$ELIZA_SHA^{tree}")
JOIN_TREE=$(git rev-parse "$JOIN_SHA^{tree}")
PARENTS=$(git show -s --format='%P' "$JOIN_SHA")
test "$JOIN_TREE" = "$ELIZA_TREE"
test "$(printf '%s\n' "$PARENTS" | awk '{print NF}')" = 2
test "$(printf '%s\n' "$PARENTS" | awk '{print $1}')" = "$ELIZA_SHA"
test "$(printf '%s\n' "$PARENTS" | awk '{print $2}')" = "$LEGACY_SHA"
git diff --exit-code "$ELIZA_SHA" "$JOIN_SHA" -- .
git merge-base --is-ancestor "$LEGACY_SHA" "$JOIN_SHA"
test -z "$(git status --porcelain=v1)"
```

Expected: all commands exit `0`; `JOIN_TREE` equals `ELIZA_TREE`; the two parents are exact and ordered.

- [ ] **Step 4: Push only the new branch and verify official readback**

```bash
cd /Users/anicca/Projects/mr-bot-eliza-migration
JOIN_SHA=$(git rev-parse HEAD)
git push -u origin migration/eliza-history
REMOTE_JOIN_SHA=$(git ls-remote origin refs/heads/migration/eliza-history | awk '{print $1}')
test "$REMOTE_JOIN_SHA" = "$JOIN_SHA"
test "$(git ls-remote origin refs/heads/main | awk '{print $1}')" = 29bed1bb394a2c0c7c0df6dc12babbe28667efbe
```

Expected: the new remote branch equals the local join commit; migration fork `main` remains fixed.

- [ ] **Step 5: Write and verify the private receipt**

```bash
cd /Users/anicca/Projects/mr-bot-eliza-migration
ELIZA_SHA=29bed1bb394a2c0c7c0df6dc12babbe28667efbe
LEGACY_SHA=c9bea215b87755434704a5d16dd8c0a55aff1981
JOIN_SHA=$(git rev-parse HEAD)
ELIZA_TREE=$(git rev-parse "$ELIZA_SHA^{tree}")
JOIN_TREE=$(git rev-parse "$JOIN_SHA^{tree}")
REMOTE_JOIN_SHA=$(git ls-remote origin refs/heads/migration/eliza-history | awk '{print $1}')
test "$ELIZA_TREE" = "$JOIN_TREE"
jq -n \
  --arg source "$ELIZA_SHA" \
  --arg legacy "$LEGACY_SHA" \
  --arg join "$JOIN_SHA" \
  --arg before "$ELIZA_TREE" \
  --arg after "$JOIN_TREE" \
  --arg remote "$REMOTE_JOIN_SHA" \
  '{
    atom:"ELZ-F11",status:"passed",source_sha:$source,legacy_second_parent:$legacy,
    join_sha:$join,root_tree_before:$before,root_tree_after:$after,parent_count:2,
    root_tree_changed:false,remote_branch:"migration/eliza-history",remote_readback_sha:$remote,
    force_pushes:0,main_mutations:0,repository_deletions:0,file_imports:0
  }' > /Users/anicca/.local/state/mr-bot/migration/elz-f/history-join-receipt.json
chmod 600 /Users/anicca/.local/state/mr-bot/migration/elz-f/history-join-receipt.json
jq -e '
  .atom=="ELZ-F11" and .status=="passed" and .source_sha=="29bed1bb394a2c0c7c0df6dc12babbe28667efbe" and
  .legacy_second_parent=="c9bea215b87755434704a5d16dd8c0a55aff1981" and .parent_count==2 and
  .root_tree_changed==false and .join_sha==.remote_readback_sha and .force_pushes==0 and
  .main_mutations==0 and .repository_deletions==0 and .file_imports==0
' /Users/anicca/.local/state/mr-bot/migration/elz-f/history-join-receipt.json
test "$(stat -f '%Lp' /Users/anicca/.local/state/mr-bot/migration/elz-f/history-join-receipt.json)" = 600
```

Expected: receipt predicate exits `0`; receipt mode is `0600`.

- [ ] **Step 6: Report focused evidence**

Write `task-1-report.md` with the exact local/remote join SHA, both parent SHAs in order, before/after tree SHA, free KiB before/after, receipt mode, `git status`, and concerns. Do not run build, unit tests, full suites, or CI.

## Plan Self-Review

- Spec coverage: the single task closes only ELZ-F11 and produces its named receipt.
- Placeholder scan: every command and value is explicit.
- Value consistency: Eliza SHA, legacy SHA, branch, tree invariant, parent order, and receipt fields are identical across all steps.
- Scope: ELZ-F12 file import, ELZ-F13 replay, plugin code, Lancers, cutover, and cloud are excluded.

## Execution Handoff

Execute with `superpowers:subagent-driven-development`: one Luna implementer, one focused primary verification, and one bounded read-only adversarial review. A finding returns only to the same implementer and only that finding is re-reviewed.
