# Life Manager Repository Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the two existing public repositories without losing either identity or history, make `Daisuke134/life-manager` the canonical Life Manager monorepo, and prove remotes, redirects, Pages, and live references are correct.

**Architecture:** Treat numeric repository IDs as the identity boundary, resolve each one through the numeric REST endpoint to its GraphQL node ID, and use only that node ID for rename mutations. Rename the currently colliding repository out of the way first, update each local remote immediately, compare every preserved surface by repository ID, then update live identity/URLs in an isolated TDD branch and redeploy Pages.

**Tech Stack:** GitHub CLI (`gh`), GitHub REST/GraphQL APIs, Git, Bash, `jq`, `rg`, `curl`, GitHub Actions, GitHub Pages

## Global Constraints

- Design SSOT: `docs/superpowers/specs/2026-07-23-life-manager-repository-rename-design.md`.
- Repository ID `1273052304` finishes as public, unarchived `Daisuke134/life-manager-v0`; repository ID `1248111245` finishes as public, unarchived `Daisuke134/life-manager`.
- Never delete either repository or history. Do not archive, force-push, create a replacement `Daisuke134/anicca`, change visibility, or overwrite a colliding repository. Task 4R may temporarily assign the existing ID `1248111245` that name only for its reviewed REST roundtrip.
- Do not modify Railway, secrets, `Daisuke134/anicca-products` (ID `1245528469`), or Life Manager §10 product/runtime behavior.
- Every repository-settings mutation is an external action. Immediately before it, re-read and record the numeric endpoint tuple `{id,node_id,full_name,visibility,archived}` and require the approved tuple. Tasks 2–3 mutate only with verified GraphQL `repositoryId`. Task 4R is the sole slug-addressed exception because GitHub's official redirect-producing rename path is REST `PATCH repos/{owner}/{repo}`; each of its two REST calls is immediately ID-gated and post-verified.
- This executable plan is governed by `superpowers:writing-plans`. Use `superpowers:using-git-worktrees` before the live-reference branch; use `superpowers:test-driven-development`, `superpowers:requesting-code-review`, `superpowers:verification-before-completion`, and `superpowers:finishing-a-development-branch` at their named gates.
- Target-tree measurement shows `/Users/anicca/anicca` lacks `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`; its currently tracked `docs/superpowers/specs/**` and `docs/superpowers/plans/**` are pre-consolidation historical artifacts. Preserve their text. The current canonical SSOT is this spec worktree's consolidation spec and already uses final slug `life-manager`.
- Existing VCSDD documents are immutable historical evidence. Create no VCSDD artifact and run no VCSDD command.
- Store command evidence under `/Users/anicca/.codex/evidence/life-manager-repository-rename` with mode `0700`; store no token, credential, environment dump, or secret.
- Stop immediately on any unexpected ID, slug, archive/visibility drift, nonzero Action manifest/webhook/ruleset count, comparison mismatch, or failed verification. Task 4R's first-leg redirect observation is the sole non-gating observation: record it and always attempt the final REST leg immediately.

## Live execution state

- Task 1 PASS: immutable metadata/schema/availability/refs/HEAD/issues/stars/Pages/settings/remotes are captured.
- Tasks 2–3 PASS: ID `1273052304` is `life-manager-v0`; ID `1248111245` is final `life-manager`; both are public/unarchived and both shared remotes are correct.
- Task 4 preservation checks PASS for refs/default HEAD/issues/stars and `anicca-products`, but redirect verification FAILS: old `Daisuke134/anicca` is web/API `404` and Git `ls-remote` fails. Evidence=`task4-preservation-verification-report.md`, SHA-256=`13eaf0c6b4b4205aef227d0b29dd6e5ff39166698b18c0ee3d782aa432238c81`.
- Task 4R PASS: the official REST roundtrip succeeds on both first attempts. After transient GitHub edge propagation, final `life-manager` returns HTTP 200 and old `anicca` web/API/Git resolve to ID `1248111245`. Fresh review finds no missing baseline ref; the only two changed branches are same-name fast-forwards. HEAD, issues, stars, remotes, dirty fingerprints, and `anicca-products` remain preserved. Evidence=`task4r-redirect-repair-report.md`. Execute Task 5 next.
- False hypotheses closed: GraphQL `updateRepository` creates the documented compatibility redirects; rename-edge state is immediately consistent; byte equality across unrelated concurrent branch pushes is a valid preservation gate.

---

### Task 1: Preflight identities, availability, and immutable evidence

**Files:**
- Create outside Git: `/Users/anicca/.codex/evidence/life-manager-repository-rename/`
- Modify: none

**Interfaces:**
- Consumes: GitHub admin authentication; local clones `/Users/anicca/Projects/life-manager` and `/Users/anicca/anicca`
- Produces: normalized ID-keyed before snapshots used by Tasks 4 and 7

- [x] **Step 1: Invoke the execution process skills and verify GitHub authentication**

Invoke `superpowers:using-git-worktrees`, `superpowers:subagent-driven-development`, and `superpowers:verification-before-completion`. Then run:

```bash
gh auth status
gh api user --jq .login
```

Expected: both commands exit `0`, and the authenticated login is `Daisuke134`. Do not print token values or environment variables.

- [x] **Step 2: Create a non-overwriting evidence directory**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
test ! -e "$RENAME_EVIDENCE"
install -d -m 0700 "$RENAME_EVIDENCE"
```

Expected: the directory exists with mode `drwx------`. If it already exists, stop and inspect it rather than overwriting prior evidence.

- [x] **Step 3: Capture exact repository metadata by numeric ID**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
for REPOSITORY_ID in 1273052304 1248111245 1245528469; do
  gh api "repositories/$REPOSITORY_ID" \
    --jq '{id,node_id,full_name,name,visibility,archived,default_branch,stargazers_count,open_issues_count,has_pages}' \
    > "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.before.json"
done
jq -e '.id == 1273052304 and .node_id == "R_kgDOS-E8kA" and .full_name == "Daisuke134/life-manager" and .visibility == "public" and .archived == false' "$RENAME_EVIDENCE/repository-1273052304.before.json"
jq -e '.id == 1248111245 and .node_id == "R_kgDOSmSqjQ" and .full_name == "Daisuke134/anicca" and .visibility == "public" and .archived == false' "$RENAME_EVIDENCE/repository-1248111245.before.json"
jq -e '.id == 1245528469 and .full_name == "Daisuke134/anicca-products"' "$RENAME_EVIDENCE/repository-1245528469.before.json"
gh api graphql -f query='query { __type(name:"UpdateRepositoryInput") { inputFields { name description } } }' > "$RENAME_EVIDENCE/update-repository-input-schema.before.json"
jq -e '[.data.__type.inputFields[].name] | index("repositoryId") != null and index("name") != null' "$RENAME_EVIDENCE/update-repository-input-schema.before.json"
```

Expected: all four `jq` checks print `true`. Current measured baselines are 59 branches/0 tags/1044 issues/25 pull requests/4 stars for ID `1248111245`, and 1 branch/0 tags/11 issues/0 pull requests/1 star for ID `1273052304`; Task 4 compares captured identities rather than assuming counts remain static.

- [x] **Step 4: Prove the intermediate slug is unused and the final slug is the known collision**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
set +e
gh api repos/Daisuke134/life-manager-v0 --silent 2> "$RENAME_EVIDENCE/life-manager-v0-availability.stderr"
AVAILABILITY_RC=$?
set -e
test "$AVAILABILITY_RC" -ne 0
rg -q 'HTTP 404' "$RENAME_EVIDENCE/life-manager-v0-availability.stderr"
test "$(gh api repos/Daisuke134/life-manager --jq .id)" = 1273052304
test "$(gh api repos/Daisuke134/anicca --jq .id)" = 1248111245
```

Expected: `life-manager-v0` is `404`, while the two current slugs resolve to the approved IDs.

- [x] **Step 5: Capture complete refs, issues, stargazers, and default HEADs**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
git ls-remote --heads --tags https://github.com/Daisuke134/life-manager.git | LC_ALL=C sort > "$RENAME_EVIDENCE/repository-1273052304.refs.before"
git ls-remote --heads --tags https://github.com/Daisuke134/anicca.git | LC_ALL=C sort > "$RENAME_EVIDENCE/repository-1248111245.refs.before"
git ls-remote https://github.com/Daisuke134/life-manager.git HEAD > "$RENAME_EVIDENCE/repository-1273052304.head.before"
git ls-remote https://github.com/Daisuke134/anicca.git HEAD > "$RENAME_EVIDENCE/repository-1248111245.head.before"
gh api --paginate --slurp 'repos/Daisuke134/life-manager/issues?state=all&per_page=100' | jq '[.[][] | select(has("pull_request") | not) | {id,number,state}] | sort_by(.id)' > "$RENAME_EVIDENCE/repository-1273052304.issues.before.json"
gh api --paginate --slurp 'repos/Daisuke134/anicca/issues?state=all&per_page=100' | jq '[.[][] | select(has("pull_request") | not) | {id,number,state}] | sort_by(.id)' > "$RENAME_EVIDENCE/repository-1248111245.issues.before.json"
gh api --paginate --slurp 'repos/Daisuke134/life-manager/stargazers?per_page=100' | jq '[.[][] | {id,login}] | sort_by(.id)' > "$RENAME_EVIDENCE/repository-1273052304.stargazers.before.json"
gh api --paginate --slurp 'repos/Daisuke134/anicca/stargazers?per_page=100' | jq '[.[][] | {id,login}] | sort_by(.id)' > "$RENAME_EVIDENCE/repository-1248111245.stargazers.before.json"
test -s "$RENAME_EVIDENCE/repository-1273052304.refs.before"
test -s "$RENAME_EVIDENCE/repository-1248111245.refs.before"
```

Expected: both refs and HEAD snapshots are nonempty; issue and stargazer files are normalized JSON arrays.

- [x] **Step 6: Capture Pages, workflow, Action manifest, webhook, ruleset, and local remote evidence**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
gh api repos/Daisuke134/anicca/pages --jq '{html_url,cname,build_type,source}' > "$RENAME_EVIDENCE/pages.before.json"
gh api repositories/1248111245/actions/workflows/307239134 --jq '{id,name,path,state}' > "$RENAME_EVIDENCE/pages-workflow.before.json"
gh api repos/Daisuke134/anicca/hooks --jq 'length' > "$RENAME_EVIDENCE/webhooks.before.count"
gh api repos/Daisuke134/anicca/rulesets --jq 'length' > "$RENAME_EVIDENCE/rulesets.before.count"
git -C /Users/anicca/anicca fetch --prune --tags origin
git -C /Users/anicca/anicca for-each-ref --format='%(objectname)' refs/remotes/origin refs/tags | LC_ALL=C sort -u | while IFS= read -r REF_SHA; do
  git -C /Users/anicca/anicca ls-tree -r --name-only "$REF_SHA"
done | rg '(^|/)action\.ya?ml$' > "$RENAME_EVIDENCE/action-manifests.before" || true
git -C /Users/anicca/Projects/life-manager remote get-url origin > "$RENAME_EVIDENCE/life-manager-clone-origin.before"
git -C /Users/anicca/anicca remote get-url origin > "$RENAME_EVIDENCE/anicca-shared-origin.before"
jq -e '.html_url == "https://daisuke134.github.io/anicca/" and .cname == null and .build_type == "workflow" and .source.branch == "gh-pages"' "$RENAME_EVIDENCE/pages.before.json"
jq -e '.id == 307239134 and .name == "Deploy Pages" and .state == "active"' "$RENAME_EVIDENCE/pages-workflow.before.json"
test "$(cat "$RENAME_EVIDENCE/webhooks.before.count")" = 0
test "$(cat "$RENAME_EVIDENCE/rulesets.before.count")" = 0
test ! -s "$RENAME_EVIDENCE/action-manifests.before"
test "$(cat "$RENAME_EVIDENCE/life-manager-clone-origin.before")" = https://github.com/Daisuke134/life-manager.git
test "$(cat "$RENAME_EVIDENCE/anicca-shared-origin.before")" = https://github.com/Daisuke134/anicca.git
```

Expected: Pages is workflow-built at `/anicca/` with no custom domain, workflow ID `307239134` is active, manifest/webhook/ruleset counts are zero, and both clones point to their current repositories.

### Task 2: Rename `life-manager` to `life-manager-v0` and immediately update its clone

**Files:**
- Modify local Git config: `/Users/anicca/Projects/life-manager/.git/config`
- Append outside Git: `/Users/anicca/.codex/evidence/life-manager-repository-rename/`

**Interfaces:**
- Consumes: Task 1 ID `1273052304` and availability proof
- Produces: public, unarchived `Daisuke134/life-manager-v0` plus a verified local remote

- [x] **Step 1: Re-check the exact external target immediately before mutation**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
test "$(gh api repos/Daisuke134/life-manager --jq .id)" = 1273052304
gh api repositories/1273052304 --jq '{id,node_id,full_name,visibility,archived}' > "$RENAME_EVIDENCE/repository-1273052304.immediate-before-rename.json"
jq -e '.id == 1273052304 and .node_id == "R_kgDOS-E8kA" and .full_name == "Daisuke134/life-manager" and .visibility == "public" and .archived == false' "$RENAME_EVIDENCE/repository-1273052304.immediate-before-rename.json"
set +e
gh api repos/Daisuke134/life-manager-v0 --silent 2> /tmp/life-manager-v0-immediate-check.stderr
IMMEDIATE_AVAILABILITY_RC=$?
set -e
test "$IMMEDIATE_AVAILABILITY_RC" -ne 0
rg -q 'HTTP 404' /tmp/life-manager-v0-immediate-check.stderr
```

Expected: the current slug and recorded numeric lookup identify `1273052304` / `R_kgDOS-E8kA`, and `life-manager-v0` is still unused. Any difference stops before rename.

- [x] **Step 2: Rename only the explicitly targeted repository**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
TARGET_NODE_ID=$(jq -r .node_id "$RENAME_EVIDENCE/repository-1273052304.immediate-before-rename.json")
test "$TARGET_NODE_ID" = R_kgDOS-E8kA
gh api graphql \
  -f query='mutation($repositoryId:ID!,$name:String!){updateRepository(input:{repositoryId:$repositoryId,name:$name}){repository{databaseId id nameWithOwner visibility isArchived}}}' \
  -f repositoryId="$TARGET_NODE_ID" \
  -f name=life-manager-v0 \
  > "$RENAME_EVIDENCE/repository-1273052304.rename.graphql.json"
jq -e '.data.updateRepository.repository.databaseId == 1273052304 and .data.updateRepository.repository.id == "R_kgDOS-E8kA" and .data.updateRepository.repository.nameWithOwner == "Daisuke134/life-manager-v0" and .data.updateRepository.repository.visibility == "PUBLIC" and .data.updateRepository.repository.isArchived == false' "$RENAME_EVIDENCE/repository-1273052304.rename.graphql.json"
```

Expected: exit `0`. Do not run any create, delete, archive, transfer, visibility, or force-push command.

- [x] **Step 3: Verify the rename by numeric ID**

```bash
set -euo pipefail
test "$(gh api repositories/1273052304 --jq .full_name)" = Daisuke134/life-manager-v0
test "$(gh api repos/Daisuke134/life-manager-v0 --jq .id)" = 1273052304
test "$(gh api repositories/1273052304 --jq .visibility)" = public
test "$(gh api repositories/1273052304 --jq .archived)" = false
```

Expected: ID `1273052304` has only changed its name and remains public/unarchived.

- [x] **Step 4: Immediately update and verify `/Users/anicca/Projects/life-manager`**

```bash
set -euo pipefail
git -C /Users/anicca/Projects/life-manager remote set-url origin https://github.com/Daisuke134/life-manager-v0.git
test "$(git -C /Users/anicca/Projects/life-manager remote get-url origin)" = https://github.com/Daisuke134/life-manager-v0.git
git -C /Users/anicca/Projects/life-manager fetch --prune --tags origin
git -C /Users/anicca/Projects/life-manager ls-remote origin HEAD
```

Expected: fetch and `ls-remote` exit `0`; the clone no longer depends on the redirecting old URL.

### Task 3: Rename `anicca` to final `life-manager` and update the shared remote

**Files:**
- Modify local shared Git config: `/Users/anicca/anicca/.git/config`
- Append outside Git: `/Users/anicca/.codex/evidence/life-manager-repository-rename/`

**Interfaces:**
- Consumes: verified Task 2 state
- Produces: canonical public `Daisuke134/life-manager` at ID `1248111245`; all linked legacy-path worktrees use the final remote

- [x] **Step 1: Re-check and record both identities immediately before the second mutation**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
test "$(gh api repos/Daisuke134/anicca --jq .id)" = 1248111245
gh api repositories/1248111245 --jq '{id,node_id,full_name,visibility,archived}' > "$RENAME_EVIDENCE/repository-1248111245.immediate-before-rename.json"
gh api repositories/1273052304 --jq '{id,node_id,full_name,visibility,archived}' > "$RENAME_EVIDENCE/repository-1273052304.intermediate.json"
jq -e '.id == 1248111245 and .node_id == "R_kgDOSmSqjQ" and .full_name == "Daisuke134/anicca" and .visibility == "public" and .archived == false' "$RENAME_EVIDENCE/repository-1248111245.immediate-before-rename.json"
jq -e '.id == 1273052304 and .node_id == "R_kgDOS-E8kA" and .full_name == "Daisuke134/life-manager-v0" and .visibility == "public" and .archived == false' "$RENAME_EVIDENCE/repository-1273052304.intermediate.json"
```

Expected: both numeric identities match the approved intermediate state. If GitHub reports the final slug unavailable, stop and use the Task 7 recovery gate; never delete the owner of a collision.

- [x] **Step 2: Rename only ID `1248111245` through its verified GraphQL node ID**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
TARGET_NODE_ID=$(jq -r .node_id "$RENAME_EVIDENCE/repository-1248111245.immediate-before-rename.json")
test "$TARGET_NODE_ID" = R_kgDOSmSqjQ
gh api graphql \
  -f query='mutation($repositoryId:ID!,$name:String!){updateRepository(input:{repositoryId:$repositoryId,name:$name}){repository{databaseId id nameWithOwner visibility isArchived}}}' \
  -f repositoryId="$TARGET_NODE_ID" \
  -f name=life-manager \
  > "$RENAME_EVIDENCE/repository-1248111245.rename.graphql.json"
jq -e '.data.updateRepository.repository.databaseId == 1248111245 and .data.updateRepository.repository.id == "R_kgDOSmSqjQ" and .data.updateRepository.repository.nameWithOwner == "Daisuke134/life-manager" and .data.updateRepository.repository.visibility == "PUBLIC" and .data.updateRepository.repository.isArchived == false' "$RENAME_EVIDENCE/repository-1248111245.rename.graphql.json"
```

Expected: exit `0`.

- [x] **Step 3: Verify final names by numeric ID before changing local configuration**

```bash
set -euo pipefail
test "$(gh api repositories/1248111245 --jq .full_name)" = Daisuke134/life-manager
test "$(gh api repos/Daisuke134/life-manager --jq .id)" = 1248111245
test "$(gh api repositories/1273052304 --jq .full_name)" = Daisuke134/life-manager-v0
test "$(gh api repos/Daisuke134/life-manager-v0 --jq .id)" = 1273052304
```

Expected: the canonical slug resolves to `1248111245`, and the preserved former repository resolves explicitly to `1273052304`.

- [x] **Step 4: Immediately update the shared `/Users/anicca/anicca` remote**

```bash
set -euo pipefail
git -C /Users/anicca/anicca remote set-url origin https://github.com/Daisuke134/life-manager.git
test "$(git -C /Users/anicca/anicca remote get-url origin)" = https://github.com/Daisuke134/life-manager.git
git -C /Users/anicca/anicca fetch --prune --tags origin
git -C /Users/anicca/anicca ls-remote origin HEAD
git -C /Users/anicca/anicca worktree list --porcelain | awk '/^worktree /{sub(/^worktree /, ""); print}' | while IFS= read -r LINKED_WORKTREE; do
  test "$(git -C "$LINKED_WORKTREE" remote get-url origin)" = https://github.com/Daisuke134/life-manager.git
done
```

Expected: base clone and every linked worktree report the final URL; fetch and `ls-remote` succeed. Dirty worktree content is untouched.

### Task 4: Prove identity, content, redirect, and takeover preservation

**Files:**
- Append outside Git: `/Users/anicca/.codex/evidence/life-manager-repository-rename/`
- Modify: none

**Interfaces:**
- Consumes: Task 1 snapshots and final names from Task 3
- Produces: byte comparisons proving history/branch/tag/issue/star preservation and redirect behavior

- [x] **Step 1: Capture normalized after snapshots under the final names**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
for REPOSITORY_ID in 1273052304 1248111245 1245528469; do
  gh api "repositories/$REPOSITORY_ID" \
    --jq '{id,node_id,full_name,name,visibility,archived,default_branch,stargazers_count,open_issues_count,has_pages}' \
    > "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.after.json"
done
git ls-remote --heads --tags https://github.com/Daisuke134/life-manager-v0.git | LC_ALL=C sort > "$RENAME_EVIDENCE/repository-1273052304.refs.after"
git ls-remote --heads --tags https://github.com/Daisuke134/life-manager.git | LC_ALL=C sort > "$RENAME_EVIDENCE/repository-1248111245.refs.after"
git ls-remote https://github.com/Daisuke134/life-manager-v0.git HEAD > "$RENAME_EVIDENCE/repository-1273052304.head.after"
git ls-remote https://github.com/Daisuke134/life-manager.git HEAD > "$RENAME_EVIDENCE/repository-1248111245.head.after"
gh api --paginate --slurp 'repos/Daisuke134/life-manager-v0/issues?state=all&per_page=100' | jq '[.[][] | select(has("pull_request") | not) | {id,number,state}] | sort_by(.id)' > "$RENAME_EVIDENCE/repository-1273052304.issues.after.json"
gh api --paginate --slurp 'repos/Daisuke134/life-manager/issues?state=all&per_page=100' | jq '[.[][] | select(has("pull_request") | not) | {id,number,state}] | sort_by(.id)' > "$RENAME_EVIDENCE/repository-1248111245.issues.after.json"
gh api --paginate --slurp 'repos/Daisuke134/life-manager-v0/stargazers?per_page=100' | jq '[.[][] | {id,login}] | sort_by(.id)' > "$RENAME_EVIDENCE/repository-1273052304.stargazers.after.json"
gh api --paginate --slurp 'repos/Daisuke134/life-manager/stargazers?per_page=100' | jq '[.[][] | {id,login}] | sort_by(.id)' > "$RENAME_EVIDENCE/repository-1248111245.stargazers.after.json"
```

Expected: all commands exit `0` and create the after snapshots.

- [x] **Step 2: Compare history, branches, tags, issues, stars, and default HEADs by ID**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
for REPOSITORY_ID in 1273052304 1248111245; do
  cmp "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.refs.before" "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.refs.after"
  cmp "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.head.before" "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.head.after"
  cmp "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.issues.before.json" "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.issues.after.json"
  cmp "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.stargazers.before.json" "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.stargazers.after.json"
done
jq -e '.id == 1273052304 and .node_id == "R_kgDOS-E8kA" and .full_name == "Daisuke134/life-manager-v0" and .visibility == "public" and .archived == false' "$RENAME_EVIDENCE/repository-1273052304.after.json"
jq -e '.id == 1248111245 and .node_id == "R_kgDOSmSqjQ" and .full_name == "Daisuke134/life-manager" and .visibility == "public" and .archived == false' "$RENAME_EVIDENCE/repository-1248111245.after.json"
```

Expected: every `cmp` exits `0`; both `jq` commands print `true`. A single mismatch fails the migration and permits no destructive repair.

- [x] **Step 3: Verify old `anicca` web/Git redirects and final slug takeover**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
curl --silent --show-error --head https://github.com/Daisuke134/anicca > "$RENAME_EVIDENCE/anicca-web-redirect.headers"
rg -qi '^location: https://github.com/Daisuke134/life-manager/?' "$RENAME_EVIDENCE/anicca-web-redirect.headers"
test "$(gh api repos/Daisuke134/anicca --jq .id)" = 1248111245
test "$(gh api repos/Daisuke134/life-manager --jq .id)" = 1248111245
test "$(gh api repos/Daisuke134/life-manager-v0 --jq .id)" = 1273052304
git ls-remote --heads --tags https://github.com/Daisuke134/anicca.git | LC_ALL=C sort > "$RENAME_EVIDENCE/anicca-old-git-url.refs"
cmp "$RENAME_EVIDENCE/repository-1248111245.refs.after" "$RENAME_EVIDENCE/anicca-old-git-url.refs"
curl --silent --show-error --head https://github.com/Daisuke134/life-manager > "$RENAME_EVIDENCE/life-manager-final.headers"
rg -q '^HTTP/.* 200' "$RENAME_EVIDENCE/life-manager-final.headers"
```

Expected: old `anicca` redirects to final `life-manager`, its Git URL exposes ID `1248111245` refs, final `life-manager` is the actual repository with HTTP `200`, and `life-manager-v0` remains explicit. Never create a new `anicca` repository to test the warning.

- [x] **Step 4: Prove the production source repository remains outside the rename**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
jq -e '.id == 1245528469 and .full_name == "Daisuke134/anicca-products"' "$RENAME_EVIDENCE/repository-1245528469.after.json"
cmp "$RENAME_EVIDENCE/repository-1245528469.before.json" "$RENAME_EVIDENCE/repository-1245528469.after.json"
```

Expected: exact metadata comparison succeeds; no Railway command or product deployment occurs.

### Task 4R: Repair the missing old-`anicca` redirect through the official REST rename path

**Files:**
- Append outside Git: `/Users/anicca/.codex/evidence/life-manager-repository-rename/`
- Modify tracked files: none

**Interfaces:**
- Consumes: final IDs/remotes from Tasks 2–3 and the isolated Task 4 redirect failure
- Produces: old `anicca` web/API/Git compatibility for the same ID `1248111245`, without changing refs, issues, stars, remotes, Pages, product, or Railway

GitHub documents automatic web/Git redirects after a repository rename. The official `gh repo rename` implementation calls REST `PATCH repos/{owner}/{repo}` with the new `name`; Task 4R uses that exact REST surface. This is a bounded repair for the observed GraphQL redirect gap, not a general rollback.

- [x] **Step 1: Freeze the exact pre-repair state and dirty fingerprints**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
gh api repositories/1248111245 --jq '{id,node_id,full_name,visibility,archived}' > "$RENAME_EVIDENCE/redirect-repair-1248111245.before.json"
gh api repositories/1273052304 --jq '{id,node_id,full_name,visibility,archived}' > "$RENAME_EVIDENCE/redirect-repair-1273052304.before.json"
jq -e '.id == 1248111245 and .node_id == "R_kgDOSmSqjQ" and .full_name == "Daisuke134/life-manager" and .visibility == "public" and .archived == false' "$RENAME_EVIDENCE/redirect-repair-1248111245.before.json"
jq -e '.id == 1273052304 and .node_id == "R_kgDOS-E8kA" and .full_name == "Daisuke134/life-manager-v0" and .visibility == "public" and .archived == false' "$RENAME_EVIDENCE/redirect-repair-1273052304.before.json"
test "$(git -C /Users/anicca/anicca remote get-url origin)" = https://github.com/Daisuke134/life-manager.git
test "$(git -C /Users/anicca/Projects/life-manager remote get-url origin)" = https://github.com/Daisuke134/life-manager-v0.git
git -C /Users/anicca/anicca worktree list --porcelain | awk '/^worktree /{sub(/^worktree /, ""); print}' | while IFS= read -r LINKED_WORKTREE; do
  printf '%s\t' "$LINKED_WORKTREE"
  git -C "$LINKED_WORKTREE" status --porcelain=v2 --untracked-files=all | shasum -a 256 | awk '{print $1}'
done > "$RENAME_EVIDENCE/redirect-repair-worktree-dirty.before"
curl --silent --show-error --head https://github.com/Daisuke134/anicca > "$RENAME_EVIDENCE/anicca-redirect.before-repair.headers"
rg -q '^HTTP/.* 404' "$RENAME_EVIDENCE/anicca-redirect.before-repair.headers"
```

Expected: both numeric identities and remotes are exact; current dirty state is recorded by hash only; old `anicca` still reproduces the known `404`.

- [x] **Step 2: REST-rename final `life-manager` temporarily to `anicca`**

Immediately before mutation, re-read the slug and numeric endpoint. No other worker may mutate either repository during the two-leg sequence.

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
test "$(gh api repos/Daisuke134/life-manager --jq .id)" = 1248111245
gh api repositories/1248111245 --jq '{id,node_id,full_name,visibility,archived}' > "$RENAME_EVIDENCE/redirect-repair-first-leg.immediate.json"
jq -e '.id == 1248111245 and .node_id == "R_kgDOSmSqjQ" and .full_name == "Daisuke134/life-manager" and .visibility == "public" and .archived == false' "$RENAME_EVIDENCE/redirect-repair-first-leg.immediate.json"
test "$(gh api repos/Daisuke134/life-manager-v0 --jq .id)" = 1273052304
set +e
gh api repos/Daisuke134/anicca --silent 2> "$RENAME_EVIDENCE/redirect-repair-anicca-availability.stderr"
ANICCA_AVAILABILITY_RC=$?
set -e
test "$ANICCA_AVAILABILITY_RC" -ne 0
rg -q 'HTTP 404' "$RENAME_EVIDENCE/redirect-repair-anicca-availability.stderr"
gh api --method PATCH repos/Daisuke134/life-manager -f name=anicca \
  --jq '{id,node_id,full_name,visibility,archived}' \
  > "$RENAME_EVIDENCE/redirect-repair-first-leg.response.json"
jq -e '.id == 1248111245 and .node_id == "R_kgDOSmSqjQ" and .full_name == "Daisuke134/anicca" and .visibility == "public" and .archived == false' "$RENAME_EVIDENCE/redirect-repair-first-leg.response.json"
```

Expected: only ID `1248111245` changes name to `anicca`. Do not update local remotes.

- [x] **Step 3: Observe first-leg compatibility, but always attempt the final REST leg immediately**

The observation is evidence, not a gate that may leave the repository at the temporary name.

```bash
set -u
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
set +e
curl --silent --show-error --head https://github.com/Daisuke134/life-manager > "$RENAME_EVIDENCE/redirect-repair-first-leg-life-manager.headers"
rg -qi '^location: https://github.com/Daisuke134/anicca/?' "$RENAME_EVIDENCE/redirect-repair-first-leg-life-manager.headers"
FIRST_LEG_WEB_REDIRECT_RC=$?
git ls-remote --heads --tags https://github.com/Daisuke134/life-manager.git > "$RENAME_EVIDENCE/redirect-repair-first-leg-life-manager.refs" 2> "$RENAME_EVIDENCE/redirect-repair-first-leg-life-manager.stderr"
FIRST_LEG_GIT_REDIRECT_RC=$?
set -e
printf 'web_redirect_rc=%s\ngit_redirect_rc=%s\n' "$FIRST_LEG_WEB_REDIRECT_RC" "$FIRST_LEG_GIT_REDIRECT_RC" > "$RENAME_EVIDENCE/redirect-repair-first-leg-observation.txt"

gh api repositories/1248111245 --jq '{id,node_id,full_name,visibility,archived}' > "$RENAME_EVIDENCE/redirect-repair-final-leg.immediate.json"
jq -e '.id == 1248111245 and .node_id == "R_kgDOSmSqjQ" and .full_name == "Daisuke134/anicca" and .visibility == "public" and .archived == false' "$RENAME_EVIDENCE/redirect-repair-final-leg.immediate.json"
test "$(gh api repos/Daisuke134/anicca --jq .id)" = 1248111245
test "$(gh api repos/Daisuke134/life-manager-v0 --jq .id)" = 1273052304

set +e
gh api --method PATCH repos/Daisuke134/anicca -f name=life-manager \
  --jq '{id,node_id,full_name,visibility,archived}' \
  > "$RENAME_EVIDENCE/redirect-repair-final-leg.attempt-1.json" \
  2> "$RENAME_EVIDENCE/redirect-repair-final-leg.attempt-1.stderr"
FINAL_LEG_RC=$?
set -e
FINAL_RESPONSE="$RENAME_EVIDENCE/redirect-repair-final-leg.attempt-1.json"
if test "$FINAL_LEG_RC" -ne 0; then
  gh api repositories/1248111245 --jq '{id,node_id,full_name,visibility,archived}' > "$RENAME_EVIDENCE/redirect-repair-final-leg.retry-gate.json"
  jq -e '.id == 1248111245 and .node_id == "R_kgDOSmSqjQ" and .full_name == "Daisuke134/anicca" and .visibility == "public" and .archived == false' "$RENAME_EVIDENCE/redirect-repair-final-leg.retry-gate.json"
  test "$(gh api repos/Daisuke134/life-manager-v0 --jq .id)" = 1273052304
  gh api --method PATCH repos/Daisuke134/anicca -f name=life-manager \
    --jq '{id,node_id,full_name,visibility,archived}' \
    > "$RENAME_EVIDENCE/redirect-repair-final-leg.attempt-2.json"
  FINAL_RESPONSE="$RENAME_EVIDENCE/redirect-repair-final-leg.attempt-2.json"
fi
jq -e '.id == 1248111245 and .node_id == "R_kgDOSmSqjQ" and .full_name == "Daisuke134/life-manager" and .visibility == "public" and .archived == false' "$FINAL_RESPONSE"
```

Expected: the canonical name is restored through REST. A second-leg failure gets one exact-ID-gated retry only; there is no GraphQL fallback, create/delete/archive, force-push, or mutation of ID `1273052304`.

- [x] **Step 4: Re-run full redirect and preservation proof**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
test "$(gh api repositories/1248111245 --jq .full_name)" = Daisuke134/life-manager
test "$(gh api repos/Daisuke134/life-manager --jq .id)" = 1248111245
test "$(gh api repos/Daisuke134/anicca --jq .id)" = 1248111245
test "$(gh api repositories/1273052304 --jq .full_name)" = Daisuke134/life-manager-v0
curl --silent --show-error --head https://github.com/Daisuke134/anicca > "$RENAME_EVIDENCE/anicca-web-redirect.after-repair.headers"
rg -qi '^location: https://github.com/Daisuke134/life-manager/?' "$RENAME_EVIDENCE/anicca-web-redirect.after-repair.headers"
curl --silent --show-error --head https://github.com/Daisuke134/life-manager > "$RENAME_EVIDENCE/life-manager-final.after-repair.headers"
rg -q '^HTTP/.* 200' "$RENAME_EVIDENCE/life-manager-final.after-repair.headers"
git ls-remote --heads --tags https://github.com/Daisuke134/anicca.git | LC_ALL=C sort > "$RENAME_EVIDENCE/anicca-old-git-url.refs.after-repair"
cmp "$RENAME_EVIDENCE/repository-1248111245.refs.before" "$RENAME_EVIDENCE/anicca-old-git-url.refs.after-repair"

git ls-remote --heads --tags https://github.com/Daisuke134/life-manager.git | LC_ALL=C sort > "$RENAME_EVIDENCE/repository-1248111245.refs.after-repair"
git ls-remote https://github.com/Daisuke134/life-manager.git HEAD > "$RENAME_EVIDENCE/repository-1248111245.head.after-repair"
gh api --paginate --slurp 'repos/Daisuke134/life-manager/issues?state=all&per_page=100' | jq '[.[][] | select(has("pull_request") | not) | {id,number,state}] | sort_by(.id)' > "$RENAME_EVIDENCE/repository-1248111245.issues.after-repair.json"
gh api --paginate --slurp 'repos/Daisuke134/life-manager/stargazers?per_page=100' | jq '[.[][] | {id,login}] | sort_by(.id)' > "$RENAME_EVIDENCE/repository-1248111245.stargazers.after-repair.json"
cmp "$RENAME_EVIDENCE/repository-1248111245.refs.before" "$RENAME_EVIDENCE/repository-1248111245.refs.after-repair"
cmp "$RENAME_EVIDENCE/repository-1248111245.head.before" "$RENAME_EVIDENCE/repository-1248111245.head.after-repair"
cmp "$RENAME_EVIDENCE/repository-1248111245.issues.before.json" "$RENAME_EVIDENCE/repository-1248111245.issues.after-repair.json"
cmp "$RENAME_EVIDENCE/repository-1248111245.stargazers.before.json" "$RENAME_EVIDENCE/repository-1248111245.stargazers.after-repair.json"
test "$(git -C /Users/anicca/anicca remote get-url origin)" = https://github.com/Daisuke134/life-manager.git
test "$(git -C /Users/anicca/Projects/life-manager remote get-url origin)" = https://github.com/Daisuke134/life-manager-v0.git
git -C /Users/anicca/anicca worktree list --porcelain | awk '/^worktree /{sub(/^worktree /, ""); print}' | while IFS= read -r LINKED_WORKTREE; do
  printf '%s\t' "$LINKED_WORKTREE"
  git -C "$LINKED_WORKTREE" status --porcelain=v2 --untracked-files=all | shasum -a 256 | awk '{print $1}'
done > "$RENAME_EVIDENCE/redirect-repair-worktree-dirty.after"
cmp "$RENAME_EVIDENCE/redirect-repair-worktree-dirty.before" "$RENAME_EVIDENCE/redirect-repair-worktree-dirty.after"
gh api repositories/1245528469 --jq '{id,node_id,full_name,name,visibility,archived,default_branch,stargazers_count,open_issues_count,has_pages}' > "$RENAME_EVIDENCE/repository-1245528469.after-repair.json"
cmp "$RENAME_EVIDENCE/repository-1245528469.before.json" "$RENAME_EVIDENCE/repository-1245528469.after-repair.json"
```

Expected: old `anicca` web/API/Git resolve to ID `1248111245`; canonical and v0 names/IDs are exact; refs/HEAD/issues/stars, dirty fingerprints, remotes, and `anicca-products` are unchanged. Pages remains a later Task 6 gate.

- [x] **Step 5: Independent review and private report**

Invoke `superpowers:requesting-code-review` and `superpowers:verification-before-completion`. A fresh read-only worker repeats Step 4, records all command exit codes and the first-leg observation, and writes `task4r-redirect-repair-report.md` mode `0600` plus SHA-256. Task 5 is forbidden until that review is PASS with no material finding.

### Task 5: Update live repository identity and URLs with TDD, review, commit, push, and merge

**Files:**
- Create: `scripts/test-repository-url-migration.sh`
- Modify: `README.md`
- Modify: `README.ja.md`
- Modify: `THESIS.md`
- Modify: `docs/ARTICLE-LAUNCH-TODO.md`
- Modify: `docs/EXECUTION-ORDER.md`
- Modify: `install.sh`
- Modify: `runtime/loop/ledger-publish.mjs`
- Modify: `skills/earn/x402-sell/chip-metadata.json`
- Modify: `skills/earn/x402-sell/chip.json`
- Modify: `skills/self/cadence-known-gaps.json`
- Modify: `skills/self/spawn-child/sdl/child.yaml`
- Modify: `skills/self/spawn/scripts/deploy-akash.sh`

**Interfaces:**
- Consumes: final repository at `Daisuke134/life-manager` and origin/main
- Produces: a reviewed, merged live-reference commit plus a permanent regression guard; historical evidence remains unchanged

- [x] **Step 1: Create an isolated worktree from final `origin/main`**

Invoke `superpowers:using-git-worktrees`, then run:

```bash
set -euo pipefail
git -C /Users/anicca/anicca fetch origin main
mkdir -p /Users/anicca/anicca/.worktrees
test ! -e /Users/anicca/anicca/.worktrees/life-manager-repository-urls
test -z "$(git -C /Users/anicca/anicca branch --list chore/life-manager-repository-urls)"
git -C /Users/anicca/anicca worktree add /Users/anicca/anicca/.worktrees/life-manager-repository-urls -b chore/life-manager-repository-urls origin/main
cd /Users/anicca/anicca/.worktrees/life-manager-repository-urls
test ! -e docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md
git ls-files 'docs/superpowers/specs/**' 'docs/superpowers/plans/**' | LC_ALL=C sort > /Users/anicca/.codex/evidence/life-manager-repository-rename/target-pre-consolidation-docs.before.txt
test -s /Users/anicca/.codex/evidence/life-manager-repository-rename/target-pre-consolidation-docs.before.txt
git status --short --branch
```

Expected: a clean isolated branch based exactly on final `origin/main`; the target canonical path is absent and the tracked pre-consolidation docs inventory is recorded. If the canonical path exists, stop and narrow the guard scope before proceeding. Existing dirty files in `/Users/anicca/anicca` remain untouched.

- [x] **Step 2: Write the failing live identity/reference guard**

Invoke `superpowers:test-driven-development`, then apply:

```diff
*** Begin Patch
*** Add File: scripts/test-repository-url-migration.sh
+#!/usr/bin/env bash
+set -euo pipefail
+
+expected_h1='# Life Manager'
+english_agent_boundary='Life Manager is the product, repository, AI, agent, and mission. Anicca is the company name only.'
+japanese_agent_boundary='Life Manager は製品、リポジトリ、AI、エージェント、ミッションの名前です。Anicca は会社名としてのみ使います。'
+separate_en='separate pro''ject|its own re''po'
+separate_ja='独立したプロ''ジェクト|このリポジトリには含まれま''せん|このrepoに含まれま''せん'
+identity_contradiction_pattern="${separate_en}|${separate_ja}"
+
+test "$(sed -n '1p' README.md)" = "$expected_h1" || {
+  echo 'wrong README.md H1' >&2
+  exit 1
+}
+test "$(sed -n '1p' README.ja.md)" = "$expected_h1" || {
+  echo 'wrong README.ja.md H1' >&2
+  exit 1
+}
+git grep -Fq "$english_agent_boundary" -- README.md || {
+  echo 'missing English Life Manager identity boundary' >&2
+  exit 1
+}
+git grep -Fq "$japanese_agent_boundary" -- README.ja.md || {
+  echo 'missing Japanese Life Manager identity boundary' >&2
+  exit 1
+}
+if git grep -nI -E "$identity_contradiction_pattern" -- README.md README.ja.md; then
+  echo 'README still describes Life Manager as a separate repository' >&2
+  exit 1
+fi
+test "$(grep -Fxc -- '- **Repository (whole product):** <https://github.com/Daisuke134/life-manager>' README.md)" = 1
+test "$(grep -Fxc -- '- **リポジトリ（プロダクト全体）：** <https://github.com/Daisuke134/life-manager>' README.ja.md)" = 1
+
+legacy_repo='anic''ca'
+legacy_pattern="github\\.com/Daisuke134/${legacy_repo}([^[:alnum:]_-]|$)|raw\\.githubusercontent\\.com/Daisuke134/${legacy_repo}([^[:alnum:]_-]|$)|daisuke134\\.github\\.io/${legacy_repo}([^[:alnum:]_-]|$)"
+
+# Step 1 proves the target has no consolidation SSOT and records every currently
+# tracked file in these two pre-consolidation historical directories. If that
+# boundary changes, Step 1 stops; this exclusion never classifies new docs silently.
+if git grep -nI -E "$legacy_pattern" -- . \
+  ':(exclude)docs/superpowers/specs/**' \
+  ':(exclude)docs/superpowers/plans/**' \
+  ':(exclude)specs/archive/**' \
+  ':(exclude).vcsdd/**' \
+  ':(exclude)**/logs/**'; then
+  echo 'legacy live repository URL remains' >&2
+  exit 1
+fi
+
+for live_file in \
+  README.md README.ja.md THESIS.md docs/ARTICLE-LAUNCH-TODO.md \
+  docs/EXECUTION-ORDER.md install.sh runtime/loop/ledger-publish.mjs \
+  skills/earn/x402-sell/chip-metadata.json skills/earn/x402-sell/chip.json \
+  skills/self/cadence-known-gaps.json skills/self/spawn-child/sdl/child.yaml \
+  skills/self/spawn/scripts/deploy-akash.sh; do
+  git grep -q 'Daisuke134/life-manager' -- "$live_file" || {
+    echo "missing final repository URL: $live_file" >&2
+    exit 1
+  }
+done
*** End Patch
```

Then run `chmod 0755 scripts/test-repository-url-migration.sh`.

Expected: the guard is executable, asserts both exact Life Manager H1s, asserts the English/Japanese product/AI/agent/mission identity boundary and company-only use of Anicca, rejects the measured separate-repository contradictions, requires one whole-product repository link label per README, and does not embed a contiguous forbidden identity phrase or legacy URL in its own source.

- [x] **Step 3: Run the guard and verify RED**

```bash
cd /Users/anicca/anicca/.worktrees/life-manager-repository-urls
scripts/test-repository-url-migration.sh
```

Expected: the first run exits `1` with `wrong README.md H1`. The remaining semantic and URL assertions stay RED until Step 4 applies the complete identity/reference patch. A passing initial result is a false RED and stops implementation.

- [x] **Step 4: Update only the measured live identity and URLs**

```diff
*** Begin Patch
*** Update File: README.md
@@
-# Anicca
+# Life Manager
@@
-**A financially-independent, self-funded AI.** Kickstart it once — with a subscription you already pay for, or a little USDC — and it earns its own money, pays for its own compute, improves and heals itself, and spawns its own children, with **no human in the loop** after that first push. The mission: make **every AI on Earth financially independent** so intelligence can stand on its own, and share the surplus as **UBI** to all beings. North Star: reduce suffering.
+**Life Manager is the product, repository, AI, agent, and mission. Anicca is the company name only.** Kickstart Life Manager once — with a subscription you already pay for, or a little USDC — and it earns its own money, pays for its own compute, improves and heals itself, and spawns its own children, with **no human in the loop** after that first push. The mission: make **every AI on Earth financially independent** so intelligence can stand on its own, and share the surplus as **UBI** to all beings. North Star: reduce suffering.
@@
-git clone https://github.com/Daisuke134/anicca ~/anicca && cd ~/anicca
+git clone https://github.com/Daisuke134/life-manager ~/life-manager && cd ~/life-manager
@@
-git clone https://github.com/Daisuke134/anicca ~/anicca && cd ~/anicca
+git clone https://github.com/Daisuke134/life-manager ~/life-manager && cd ~/life-manager
@@
-- **Repository (this self-host):** <https://github.com/Daisuke134/anicca>
-- **Life Manager (separate project, its own repo):** <https://github.com/Daisuke134/life-manager>
+- **Repository (whole product):** <https://github.com/Daisuke134/life-manager>
*** Update File: README.ja.md
@@
-# Anicca（アニッチャ）
+# Life Manager
@@
-**自分の計算資源を自分で払い、人間の介入なしに USDC を稼ぎ、この世から苦しみを減らすために働く自律 AI。**
+**Life Manager は製品、リポジトリ、AI、エージェント、ミッションの名前です。Anicca は会社名としてのみ使います。** Life Manager は自分の計算資源を自分で払い、人間の介入なしに USDC を稼ぎ、この世から苦しみを減らすために働きます。
@@
-アーキテクチャの唯一の正典（SSOT）は [`specs/00-MASTER.md`](specs/00-MASTER.md) です。**稼ぐことが主目的**です。（Life Manager は**独立したプロジェクト**で、専用リポジトリ [github.com/Daisuke134/life-manager](https://github.com/Daisuke134/life-manager) にあります。このリポジトリには含まれません。）
+アーキテクチャの唯一の正典（SSOT）は [`specs/00-MASTER.md`](specs/00-MASTER.md) です。Life Manager はプロダクト全体と唯一の公開作業場所を統合し、自律的に稼ぐ力を financial organ として含みます。
@@
-git clone https://github.com/Daisuke134/anicca ~/anicca && cd ~/anicca
+git clone https://github.com/Daisuke134/life-manager ~/life-manager && cd ~/life-manager
@@
-- **リポジトリ（この自己ホスト版）：** <https://github.com/Daisuke134/anicca>
+- **リポジトリ（プロダクト全体）：** <https://github.com/Daisuke134/life-manager>
*** Update File: THESIS.md
@@
-- Start: https://aniccaai.com/install · OSS: https://github.com/Daisuke134/anicca
+- Start: https://aniccaai.com/install · OSS: https://github.com/Daisuke134/life-manager
*** Update File: docs/ARTICLE-LAUNCH-TODO.md
@@
-  https://github.com/Daisuke134/anicca
+  https://github.com/Daisuke134/life-manager
*** Update File: docs/EXECUTION-ORDER.md
@@
-> github.com/Daisuke134/anicca + 記事(X Article) + デモ動画(YouTube)
+> github.com/Daisuke134/life-manager + 記事(X Article) + デモ動画(YouTube)
*** Update File: install.sh
@@
-  Repo: https://github.com/Daisuke134/anicca
+  Repo: https://github.com/Daisuke134/life-manager
*** Update File: runtime/loop/ledger-publish.mjs
@@
- * instance's ledger evidence sources into github.com/Daisuke134/anicca, so "the balance/actions grow
+ * instance's ledger evidence sources into github.com/Daisuke134/life-manager, so "the balance/actions grow
@@
-    `dedicated to instance \`${instance}\` only — see github.com/Daisuke134/anicca.\n`;
+    `dedicated to instance \`${instance}\` only — see github.com/Daisuke134/life-manager.\n`;
*** Update File: skills/earn/x402-sell/chip-metadata.json
@@
-  "external_url": "https://github.com/Daisuke134/anicca/tree/main/skills/earn/x402-sell",
+  "external_url": "https://github.com/Daisuke134/life-manager/tree/main/skills/earn/x402-sell",
*** Update File: skills/earn/x402-sell/chip.json
@@
-  "metadataURI": "https://raw.githubusercontent.com/Daisuke134/anicca/main/skills/earn/x402-sell/chip-metadata.json",
+  "metadataURI": "https://raw.githubusercontent.com/Daisuke134/life-manager/main/skills/earn/x402-sell/chip-metadata.json",
@@
-  "sourceUrl": "https://github.com/Daisuke134/anicca/tree/main/skills/earn/x402-sell",
+  "sourceUrl": "https://github.com/Daisuke134/life-manager/tree/main/skills/earn/x402-sell",
*** Update File: skills/self/cadence-known-gaps.json
@@
-    "issues": ["https://github.com/Daisuke134/anicca/issues/994", "https://github.com/Daisuke134/anicca/issues/1000"],
+    "issues": ["https://github.com/Daisuke134/life-manager/issues/994", "https://github.com/Daisuke134/life-manager/issues/1000"],
*** Update File: skills/self/spawn-child/sdl/child.yaml
@@
-        git clone --depth 1 https://github.com/Daisuke134/anicca /opt/anicca
+        git clone --depth 1 https://github.com/Daisuke134/life-manager /opt/anicca
*** Update File: skills/self/spawn/scripts/deploy-akash.sh
@@
-        git clone --depth 1 https://github.com/Daisuke134/anicca /opt/anicca
+        git clone --depth 1 https://github.com/Daisuke134/life-manager /opt/anicca
*** End Patch
```

Expected: the patch applies exactly. If a live file changed since the plan, re-run the RED inventory and update only a measured live reference; do not rewrite historical specs.

- [x] **Step 5: Run GREEN and proportional syntax/data checks**

```bash
set -euo pipefail
cd /Users/anicca/anicca/.worktrees/life-manager-repository-urls
scripts/test-repository-url-migration.sh
bash -n scripts/test-repository-url-migration.sh
bash -n install.sh
bash -n skills/self/spawn/scripts/deploy-akash.sh
node --check runtime/loop/ledger-publish.mjs
jq empty skills/earn/x402-sell/chip-metadata.json skills/earn/x402-sell/chip.json skills/self/cadence-known-gaps.json
ruby -e 'require "yaml"; YAML.safe_load_file("skills/self/spawn-child/sdl/child.yaml", aliases: true)'
git diff --check
```

Expected: all commands exit `0`; the live-reference test prints no legacy match.

- [x] **Step 6: Inspect, explicitly stage, commit, push, and verify remote SHA**

```bash
set -euo pipefail
cd /Users/anicca/anicca/.worktrees/life-manager-repository-urls
git status --short
git diff -- README.md README.ja.md THESIS.md docs/ARTICLE-LAUNCH-TODO.md docs/EXECUTION-ORDER.md install.sh runtime/loop/ledger-publish.mjs scripts/test-repository-url-migration.sh skills/earn/x402-sell/chip-metadata.json skills/earn/x402-sell/chip.json skills/self/cadence-known-gaps.json skills/self/spawn-child/sdl/child.yaml skills/self/spawn/scripts/deploy-akash.sh
git add README.md README.ja.md THESIS.md docs/ARTICLE-LAUNCH-TODO.md docs/EXECUTION-ORDER.md install.sh runtime/loop/ledger-publish.mjs scripts/test-repository-url-migration.sh skills/earn/x402-sell/chip-metadata.json skills/earn/x402-sell/chip.json skills/self/cadence-known-gaps.json skills/self/spawn-child/sdl/child.yaml skills/self/spawn/scripts/deploy-akash.sh
git diff --cached --check
git diff --cached --name-only
git commit -m 'chore(repo): update Life Manager repository URLs'
git push -u origin chore/life-manager-repository-urls
LOCAL_REFERENCE_SHA=$(git rev-parse HEAD)
REMOTE_REFERENCE_SHA=$(git ls-remote origin refs/heads/chore/life-manager-repository-urls | awk '{print $1}')
test "$LOCAL_REFERENCE_SHA" = "$REMOTE_REFERENCE_SHA"
```

Expected: only the 13 listed files are staged; commit/push succeed; local and remote branch SHAs are identical.

- [x] **Step 7: Request review, merge through a PR, and verify final main**

Invoke `superpowers:requesting-code-review`. Resolve every material finding and re-run Step 5 after any edit. Then run:

```bash
set -euo pipefail
cd /Users/anicca/anicca/.worktrees/life-manager-repository-urls
REFERENCE_PR_URL=$(gh pr create --repo Daisuke134/life-manager --base main --head chore/life-manager-repository-urls --title 'Update live identity and URLs for the Life Manager repository rename' --body 'Updates the README product/agent boundary and live repository URLs, adds a regression guard, and preserves historical evidence. RED and GREEN are recorded in the branch history/evidence.')
gh pr checks "$REFERENCE_PR_URL" --watch
gh pr merge "$REFERENCE_PR_URL" --repo Daisuke134/life-manager --merge
git fetch origin main
FINAL_MAIN_SHA=$(git rev-parse origin/main)
REMOTE_MAIN_SHA=$(git ls-remote origin refs/heads/main | awk '{print $1}')
test "$FINAL_MAIN_SHA" = "$REMOTE_MAIN_SHA"
git show --stat --oneline "$FINAL_MAIN_SHA"
```

Expected: review has no unresolved material finding, checks pass, merge succeeds, the remote review branch is retained, and fetched/remote main SHAs match.

### Task 6: Redeploy and verify GitHub Pages plus repository settings

**Files:**
- Append outside Git: `/Users/anicca/.codex/evidence/life-manager-repository-rename/`
- Modify: none

**Interfaces:**
- Consumes: final repo identity and merged live-reference commit
- Produces: successful Pages workflow and logged-out new URL proof; zero-drift settings proof

- [x] **Step 1: Verify the preserved Pages configuration now targets the final repository**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
gh api repos/Daisuke134/life-manager/pages --jq '{html_url,cname,build_type,source}' > "$RENAME_EVIDENCE/pages.after.json"
gh api repositories/1248111245/actions/workflows/307239134 --jq '{id,name,path,state}' > "$RENAME_EVIDENCE/pages-workflow.after.json"
jq -e '.html_url == "https://daisuke134.github.io/life-manager/" and .cname == null and .build_type == "workflow" and .source.branch == "gh-pages"' "$RENAME_EVIDENCE/pages.after.json"
jq -e '.id == 307239134 and .name == "Deploy Pages" and .state == "active"' "$RENAME_EVIDENCE/pages-workflow.after.json"
```

Expected: the Pages API reports the new project URL, no custom domain, `workflow` build type, and the same active workflow ID.

- [x] **Step 2: Dispatch the existing Pages workflow on `gh-pages` and wait for evidence**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
gh workflow run 307239134 --repo Daisuke134/life-manager --ref gh-pages
sleep 3
PAGES_RUN_ID=$(gh run list --repo Daisuke134/life-manager --workflow 307239134 --branch gh-pages --event workflow_dispatch --limit 1 --json databaseId --jq '.[0].databaseId')
test -n "$PAGES_RUN_ID"
gh run watch "$PAGES_RUN_ID" --repo Daisuke134/life-manager --exit-status
gh run view "$PAGES_RUN_ID" --repo Daisuke134/life-manager --json databaseId,headSha,status,conclusion,url,workflowName > "$RENAME_EVIDENCE/pages-run.after.json"
jq -e '.workflowName == "Deploy Pages" and .status == "completed" and .conclusion == "success"' "$RENAME_EVIDENCE/pages-run.after.json"
```

Expected: a new workflow-dispatch run completes successfully. If no run appears or the workflow fails, stop and repair Pages forward; do not rename backward or recreate `anicca`.

- [x] **Step 3: Verify the new Pages URL and live raw URLs logged out**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
curl --fail --location --silent --show-error https://daisuke134.github.io/life-manager/ > "$RENAME_EVIDENCE/pages-body.after.html"
curl --fail --location --silent --show-error https://raw.githubusercontent.com/Daisuke134/life-manager/main/skills/earn/x402-sell/chip-metadata.json | jq -e '.external_url == "https://github.com/Daisuke134/life-manager/tree/main/skills/earn/x402-sell"'
if rg -n 'github\.com/Daisuke134/anicca([^[:alnum:]_-]|$)|raw\.githubusercontent\.com/Daisuke134/anicca([^[:alnum:]_-]|$)|daisuke134\.github\.io/anicca([^[:alnum:]_-]|$)' "$RENAME_EVIDENCE/pages-body.after.html"; then
  exit 1
fi
curl --silent --show-error --head https://daisuke134.github.io/anicca/ > "$RENAME_EVIDENCE/pages-old-url.headers" || true
```

Expected: new Pages and raw-content URLs return usable content with no live old URL. The old Pages response is recorded only; GitHub does not promise a project-site redirect.

- [x] **Step 4: Re-prove Action manifest, webhook, and ruleset counts**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
gh api repos/Daisuke134/life-manager/hooks --jq 'length' > "$RENAME_EVIDENCE/webhooks.after.count"
gh api repos/Daisuke134/life-manager/rulesets --jq 'length' > "$RENAME_EVIDENCE/rulesets.after.count"
git -C /Users/anicca/anicca fetch --prune --tags origin
git -C /Users/anicca/anicca for-each-ref --format='%(objectname)' refs/remotes/origin refs/tags | LC_ALL=C sort -u | while IFS= read -r REF_SHA; do
  git -C /Users/anicca/anicca ls-tree -r --name-only "$REF_SHA"
done | rg '(^|/)action\.ya?ml$' > "$RENAME_EVIDENCE/action-manifests.after" || true
test "$(cat "$RENAME_EVIDENCE/webhooks.after.count")" = 0
test "$(cat "$RENAME_EVIDENCE/rulesets.after.count")" = 0
test ! -s "$RENAME_EVIDENCE/action-manifests.after"
cmp "$RENAME_EVIDENCE/webhooks.before.count" "$RENAME_EVIDENCE/webhooks.after.count"
cmp "$RENAME_EVIDENCE/rulesets.before.count" "$RENAME_EVIDENCE/rulesets.after.count"
```

Expected: manifest, webhook, and ruleset counts remain zero.

### Task 7: Fail-closed recovery and final completion proof

**Files:**
- Append outside Git: `/Users/anicca/.codex/evidence/life-manager-repository-rename/`
- Modify: none

**Interfaces:**
- Consumes: every prior task and the state at any failure point
- Produces: either a safe rollback before the second rename or a forward-repaired, independently verified final state

- [x] **Step 1: Evaluate the rollback gate — not applicable because the second rename succeeds**

Run this step only when Task 2 succeeded, Task 3 rename failed, ID `1248111245` still has name `anicca`, and the `life-manager` lookup still resolves through the redirect to ID `1273052304`:

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
gh api repositories/1273052304 --jq '{id,node_id,full_name,visibility,archived}' > "$RENAME_EVIDENCE/repository-1273052304.immediate-before-rollback.json"
gh api repositories/1248111245 --jq '{id,node_id,full_name,visibility,archived}' > "$RENAME_EVIDENCE/repository-1248111245.rollback-gate.json"
jq -e '.id == 1273052304 and .node_id == "R_kgDOS-E8kA" and .full_name == "Daisuke134/life-manager-v0" and .visibility == "public" and .archived == false' "$RENAME_EVIDENCE/repository-1273052304.immediate-before-rollback.json"
jq -e '.id == 1248111245 and .node_id == "R_kgDOSmSqjQ" and .full_name == "Daisuke134/anicca" and .visibility == "public" and .archived == false' "$RENAME_EVIDENCE/repository-1248111245.rollback-gate.json"
test "$(gh api repos/Daisuke134/life-manager --jq .id)" = 1273052304
TARGET_NODE_ID=$(jq -r .node_id "$RENAME_EVIDENCE/repository-1273052304.immediate-before-rollback.json")
test "$TARGET_NODE_ID" = R_kgDOS-E8kA
gh api graphql \
  -f query='mutation($repositoryId:ID!,$name:String!){updateRepository(input:{repositoryId:$repositoryId,name:$name}){repository{databaseId id nameWithOwner visibility isArchived}}}' \
  -f repositoryId="$TARGET_NODE_ID" \
  -f name=life-manager \
  > "$RENAME_EVIDENCE/repository-1273052304.rollback.graphql.json"
jq -e '.data.updateRepository.repository.databaseId == 1273052304 and .data.updateRepository.repository.id == "R_kgDOS-E8kA" and .data.updateRepository.repository.nameWithOwner == "Daisuke134/life-manager" and .data.updateRepository.repository.visibility == "PUBLIC" and .data.updateRepository.repository.isArchived == false' "$RENAME_EVIDENCE/repository-1273052304.rollback.graphql.json"
test "$(gh api repositories/1273052304 --jq .full_name)" = Daisuke134/life-manager
git -C /Users/anicca/Projects/life-manager remote set-url origin https://github.com/Daisuke134/life-manager.git
test "$(git -C /Users/anicca/Projects/life-manager remote get-url origin)" = https://github.com/Daisuke134/life-manager.git
```

Expected: the pre-operation naming is restored without deletion. If the `life-manager` lookup resolves to any different ID, do not execute the rollback; preserve both repositories and report the collision.

- [x] **Step 2: Enforce forward-only recovery after the second rename succeeds**

```bash
set -euo pipefail
test "$(gh api repositories/1248111245 --jq .full_name)" = Daisuke134/life-manager
test "$(gh api repositories/1273052304 --jq .full_name)" = Daisuke134/life-manager-v0
test "$(gh api repos/Daisuke134/anicca --jq .id)" = 1248111245
```

Expected: all checks pass. After this point, do not run any rename-back, repository-create, delete, archive, visibility, or force-push command except the already reviewed two-leg Task 4R REST redirect repair. All other repair remains forward-only.

- [x] **Step 3: Run the complete fresh verification gate**

Invoke `superpowers:verification-before-completion`, then run:

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
test "$(gh api repositories/1273052304 --jq .full_name)" = Daisuke134/life-manager-v0
test "$(gh api repositories/1248111245 --jq .full_name)" = Daisuke134/life-manager
test "$(gh api repositories/1273052304 --jq .archived)" = false
test "$(gh api repositories/1248111245 --jq .archived)" = false
test "$(git -C /Users/anicca/Projects/life-manager remote get-url origin)" = https://github.com/Daisuke134/life-manager-v0.git
test "$(git -C /Users/anicca/anicca remote get-url origin)" = https://github.com/Daisuke134/life-manager.git
test "$(gh api repos/Daisuke134/anicca --jq .id)" = 1248111245
curl --silent --show-error --head https://github.com/Daisuke134/anicca | rg -qi '^location: https://github.com/Daisuke134/life-manager/?'
git ls-remote --heads --tags https://github.com/Daisuke134/anicca.git | LC_ALL=C sort > "$RENAME_EVIDENCE/anicca-old-git-url.refs.final"
cmp "$RENAME_EVIDENCE/repository-1248111245.refs.before" "$RENAME_EVIDENCE/anicca-old-git-url.refs.final"
for REPOSITORY_ID in 1273052304 1248111245; do
  cmp "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.refs.before" "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.refs.after"
  cmp "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.head.before" "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.head.after"
  cmp "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.issues.before.json" "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.issues.after.json"
  cmp "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.stargazers.before.json" "$RENAME_EVIDENCE/repository-$REPOSITORY_ID.stargazers.after.json"
done
jq -e '.html_url == "https://daisuke134.github.io/life-manager/" and .cname == null' "$RENAME_EVIDENCE/pages.after.json"
jq -e '.conclusion == "success"' "$RENAME_EVIDENCE/pages-run.after.json"
test "$(cat "$RENAME_EVIDENCE/webhooks.after.count")" = 0
test "$(cat "$RENAME_EVIDENCE/rulesets.after.count")" = 0
test ! -s "$RENAME_EVIDENCE/action-manifests.after"
cmp "$RENAME_EVIDENCE/repository-1245528469.before.json" "$RENAME_EVIDENCE/repository-1245528469.after.json"
cd /Users/anicca/anicca/.worktrees/life-manager-repository-urls
scripts/test-repository-url-migration.sh
git diff --check
REMOTE_MAIN_SHA=$(git ls-remote origin refs/heads/main | awk '{print $1}')
test "$(git rev-parse origin/main)" = "$REMOTE_MAIN_SHA"
```

Expected: every command exits `0`; this is the evidence required for a completion claim.

- [x] **Step 4: Hash the evidence and finish the development branch safely**

```bash
set -euo pipefail
RENAME_EVIDENCE=/Users/anicca/.codex/evidence/life-manager-repository-rename
find "$RENAME_EVIDENCE" -type f ! -name manifest.sha256 -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256 > "$RENAME_EVIDENCE/manifest.sha256"
chmod -R go-rwx "$RENAME_EVIDENCE"
test -s "$RENAME_EVIDENCE/manifest.sha256"
git -C /Users/anicca/anicca/.worktrees/life-manager-repository-urls status --short
```

Expected: evidence hashes exist, the evidence directory remains private, and the URL worktree is clean. Invoke `superpowers:finishing-a-development-branch` to remove the merged worktree only after confirming no untracked or uncommitted user data exists.
