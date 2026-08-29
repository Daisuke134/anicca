# ELZ-F01〜F10 Eliza Local Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 固定したElizaOS sourceをLife Managerの正式forkとして取得し、Life Manager固有code・model call・外部作用なしでlocal server、PGlite、health、clean restartを証明する。

**Architecture:** 現行`Daisuke134/life-manager`は一切変更せず、`Daisuke134/life-manager-eliza`を`elizaOS/eliza`の正式forkとして作る。Eliza fixed treeをproject-local Node/Bunでbuildし、private state directoryとloopback portだけを使って起動する。Phase Fでは`plugin-life-manager`、Lancers、credential、model download、production ownerを扱わない。

**Tech Stack:** ElizaOS `29bed1bb394a2c0c7c0df6dc12babbe28667efbe`, MIT, Node.js `24.15.0`, Bun `1.3.14`, Git submodules, PGlite, HTTP `GET /api/health`, macOS arm64.

**Spec:** `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

## Global Constraints

- 現行repo `/Users/anicca/Projects/life-manager-main`では`reset`、`stash`、`clean`、rebase、gc/prune、checkout切替、file変更をしない。
- 新fork cloneは`/Users/anicca/Projects/life-manager-eliza-migration`、private receiptは`/Users/anicca/.local/state/life-manager/migration/elz-f`だけに置く。
- 既存credential、browser profile、ledger、receipt、customer project、wallet、launchd owner、immutable releaseを読込・複製・停止しない。
- `plugin-life-manager`、model provider call、GGUF/native inference download、Lancers/Coconala/Upwork、Telegram、email、支払いを実行しない。
- `ELIZA_PORT=2138`が既に使用中なら別portへ逃げず、`port_in_use`でF08を未完のまま止める。
- `bun install`のnetwork/ENOSPC failureをcacheやpartial buildでPASSへ昇格しない。
- 各Taskはnamed receipt一件、focused verification、fresh review、canonical spec row更新、commit/pushを閉じてから次へ進む。
- F01〜F10はupstream/read-only/operations中心なので人工的な新規TDDを作らない。既存focused testはF06とF10の二地点だけで一度ずつ実行する。
- adversarial reviewは各Task完了前のP0/P1一回だけ。finding修正後はそのfindingだけを再確認し、複数reviewer・反復full review・無関係な全suiteへ拡張しない。
- 実装executorはこのplanとupstream treeだけを触り、canonical specの完了判定はprimary agentだけが行う。

## Fixed Paths and Values

```bash
LM_LEGACY_REPO=/Users/anicca/Projects/life-manager-main
LM_ELIZA_REPO=/Users/anicca/Projects/life-manager-eliza-migration
LM_ELIZA_STATE=/Users/anicca/.local/state/life-manager/migration/elz-f
LM_TOOL_ROOT=/Users/anicca/.local/share/life-manager/toolchains/elz-f
LM_ELIZA_SHA=29bed1bb394a2c0c7c0df6dc12babbe28667efbe
LM_ELIZA_PORT=2138
LM_NODE_VERSION=24.15.0
LM_BUN_VERSION=1.3.14
```

---

### Task 1: ELZ-F01 — Freeze a read-only legacy baseline

**Files:**
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-f/fork-baseline-receipt.json`
- Read only: `/Users/anicca/Projects/life-manager-main/.git`

**Interfaces:**
- Consumes: current legacy checkout, remote refs, worktree registry, disk and installed tool versions.
- Produces: `fork-baseline-receipt.json`; no Git or runtime mutation.

- [ ] **Step 1: Prove the legacy checkout is the known dirty shared checkout**

```bash
test "$(git -C /Users/anicca/Projects/life-manager-main rev-parse --show-toplevel)" = "/Users/anicca/Projects/life-manager-main"
git -C /Users/anicca/Projects/life-manager-main status --porcelain=v1
git -C /Users/anicca/Projects/life-manager-main rev-parse HEAD refs/remotes/origin/main
```

Expected: status may be dirty; both SHAs are non-empty. Do not normalize either state.

- [ ] **Step 2: Inventory refs, worktrees, disk, and toolchain without printing secrets**

```bash
mkdir -p -m 700 /Users/anicca/.local/state/life-manager/migration/elz-f
git -C /Users/anicca/Projects/life-manager-main for-each-ref --format='%(refname) %(objectname)' \
  > /Users/anicca/.local/state/life-manager/migration/elz-f/legacy-refs.txt
git -C /Users/anicca/Projects/life-manager-main worktree list --porcelain \
  > /Users/anicca/.local/state/life-manager/migration/elz-f/legacy-worktrees.txt
df -k /Users/anicca/Projects/life-manager-main
node --version
bun --version
```

Expected: inventory files are non-empty; no credential/state contents appear.

- [ ] **Step 3: Write the baseline receipt with hashes, never raw dirty content**

```bash
LEGACY_HEAD=$(git -C /Users/anicca/Projects/life-manager-main rev-parse HEAD)
LEGACY_REMOTE=$(git -C /Users/anicca/Projects/life-manager-main rev-parse refs/remotes/origin/main)
STATUS_SHA=$(git -C /Users/anicca/Projects/life-manager-main status --porcelain=v1 | shasum -a 256 | awk '{print $1}')
REFS_SHA=$(shasum -a 256 /Users/anicca/.local/state/life-manager/migration/elz-f/legacy-refs.txt | awk '{print $1}')
WORKTREES_SHA=$(shasum -a 256 /Users/anicca/.local/state/life-manager/migration/elz-f/legacy-worktrees.txt | awk '{print $1}')
FREE_KIB=$(df -k /Users/anicca/Projects/life-manager-main | awk 'NR==2 {print $4}')
INSTALLED_NODE=$(node --version)
INSTALLED_BUN=$(bun --version)
jq -n \
  --arg atom ELZ-F01 \
  --arg status passed \
  --arg legacy_head "$LEGACY_HEAD" \
  --arg legacy_remote "$LEGACY_REMOTE" \
  --arg status_sha256 "$STATUS_SHA" \
  --arg refs_sha256 "$REFS_SHA" \
  --arg worktrees_sha256 "$WORKTREES_SHA" \
  --argjson free_kib "$FREE_KIB" \
  --arg installed_node "$INSTALLED_NODE" \
  --arg installed_bun "$INSTALLED_BUN" \
  '{atom:$atom,status:$status,legacy_head:$legacy_head,legacy_remote:$legacy_remote,status_sha256:$status_sha256,refs_sha256:$refs_sha256,worktrees_sha256:$worktrees_sha256,free_kib:$free_kib,installed_node:$installed_node,installed_bun:$installed_bun,mutations:0}' \
  > /Users/anicca/.local/state/life-manager/migration/elz-f/fork-baseline-receipt.json
chmod 600 /Users/anicca/.local/state/life-manager/migration/elz-f/fork-baseline-receipt.json
```

- [ ] **Step 4: Verify the receipt and unchanged legacy status hash**

```bash
jq -e '.atom=="ELZ-F01" and .status=="passed" and .free_kib>0 and (.installed_node|length)>0 and (.installed_bun|length)>0 and .mutations==0' \
  /Users/anicca/.local/state/life-manager/migration/elz-f/fork-baseline-receipt.json
test "$(stat -f '%Lp' /Users/anicca/.local/state/life-manager/migration/elz-f/fork-baseline-receipt.json)" = 600
RECORDED_STATUS_SHA=$(jq -r .status_sha256 /Users/anicca/.local/state/life-manager/migration/elz-f/fork-baseline-receipt.json)
CURRENT_STATUS_SHA=$(git -C /Users/anicca/Projects/life-manager-main status --porcelain=v1 | shasum -a 256 | awk '{print $1}')
test "$CURRENT_STATUS_SHA" = "$RECORDED_STATUS_SHA"
```

Expected: all commands exit 0.

### Task 2: ELZ-F02 — Create the official fork at the fixed source SHA

**Files:**
- Create remote: `https://github.com/Daisuke134/life-manager-eliza`
- Create local clone: `/Users/anicca/Projects/life-manager-eliza-migration`
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-f/fork-source-receipt.json`

**Interfaces:**
- Consumes: `fork-baseline-receipt.json`, authenticated `gh`, Eliza fixed SHA.
- Produces: public GitHub fork, `eliza-upstream` remote, pinned migration branch.

- [ ] **Step 1: Verify the authenticated GitHub owner and fork-name availability**

```bash
test "$(gh api user --jq .login)" = "Daisuke134"
if gh repo view Daisuke134/life-manager-eliza >/dev/null 2>&1; then
  gh repo view Daisuke134/life-manager-eliza --json isFork,parent,url --jq \
    'select(.isFork==true and .parent.nameWithOwner=="elizaOS/eliza")'
fi
```

Expected: owner is exact. An existing correct fork is reused; an existing non-fork or wrong-parent repository fails the predicate and stops F02.

- [ ] **Step 2: Create and clone the fork**

```bash
if ! gh repo view Daisuke134/life-manager-eliza >/dev/null 2>&1; then
  gh repo fork elizaOS/eliza --fork-name life-manager-eliza --clone=false
fi
if [ ! -d /Users/anicca/Projects/life-manager-eliza-migration/.git ]; then
  git clone --no-recurse-submodules https://github.com/Daisuke134/life-manager-eliza.git \
    /Users/anicca/Projects/life-manager-eliza-migration
else
  test "$(git -C /Users/anicca/Projects/life-manager-eliza-migration remote get-url origin)" = \
    https://github.com/Daisuke134/life-manager-eliza.git
fi
```

Expected: GitHub reports a fork and clone exits 0.

- [ ] **Step 3: Add the stable upstream name and pin the branch**

```bash
if git -C /Users/anicca/Projects/life-manager-eliza-migration remote get-url eliza-upstream >/dev/null 2>&1; then
  test "$(git -C /Users/anicca/Projects/life-manager-eliza-migration remote get-url eliza-upstream)" = https://github.com/elizaOS/eliza.git
else
  git -C /Users/anicca/Projects/life-manager-eliza-migration remote add eliza-upstream https://github.com/elizaOS/eliza.git
fi
git -C /Users/anicca/Projects/life-manager-eliza-migration fetch eliza-upstream --tags
if git -C /Users/anicca/Projects/life-manager-eliza-migration show-ref --verify --quiet refs/heads/migration/eliza-pinned; then
  git -C /Users/anicca/Projects/life-manager-eliza-migration switch migration/eliza-pinned
else
  git -C /Users/anicca/Projects/life-manager-eliza-migration switch -c migration/eliza-pinned \
    29bed1bb394a2c0c7c0df6dc12babbe28667efbe
fi
```

- [ ] **Step 4: Read back fork lineage and fixed SHA**

```bash
test "$(git -C /Users/anicca/Projects/life-manager-eliza-migration rev-parse HEAD)" = \
  29bed1bb394a2c0c7c0df6dc12babbe28667efbe
gh repo view Daisuke134/life-manager-eliza --json isFork,parent,url --jq \
  'select(.isFork==true and .parent.nameWithOwner=="elizaOS/eliza")'
```

Expected: both commands exit 0.

- [ ] **Step 5: Write and verify the fork-source receipt**

```bash
FORK_URL=$(gh repo view Daisuke134/life-manager-eliza --json url --jq .url)
jq -n --arg url "$FORK_URL" '{
  atom:"ELZ-F02",status:"passed",fork_url:$url,parent:"elizaOS/eliza",
  source_sha:"29bed1bb394a2c0c7c0df6dc12babbe28667efbe"
}' > /Users/anicca/.local/state/life-manager/migration/elz-f/fork-source-receipt.json
chmod 600 /Users/anicca/.local/state/life-manager/migration/elz-f/fork-source-receipt.json
jq -e '.status=="passed" and .parent=="elizaOS/eliza" and .source_sha=="29bed1bb394a2c0c7c0df6dc12babbe28667efbe"' \
  /Users/anicca/.local/state/life-manager/migration/elz-f/fork-source-receipt.json
```

### Task 3: ELZ-F03 — Seal repository topology before any history join

**Files:**
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-f/fork-topology-receipt.json`

**Interfaces:**
- Consumes: fork lineage, legacy baseline.
- Produces: immutable names/remotes/transition/rollback contract; no rename/archive yet.

- [ ] **Step 1: Read current remote URLs**

```bash
git -C /Users/anicca/Projects/life-manager-eliza-migration remote -v
git -C /Users/anicca/Projects/life-manager-main remote -v
```

Expected: new `origin` points to `life-manager-eliza`, `eliza-upstream` points to `elizaOS/eliza`, legacy `origin` remains `life-manager`.

- [ ] **Step 2: Write and verify the topology receipt**

```bash
jq -n '{
  atom:"ELZ-F03",status:"passed",
  current_repo:"Daisuke134/life-manager",
  migration_fork:"Daisuke134/life-manager-eliza",
  final_repo:"Daisuke134/life-manager",
  archived_repo:"Daisuke134/life-manager-legacy",
  upstream_remote:"eliza-upstream",
  transition_gate:"ELZ-O05+ELZ-T11",
  delete_repositories:0,
  force_push_main:0,
  bulk_owner_restart:0
}' > /Users/anicca/.local/state/life-manager/migration/elz-f/fork-topology-receipt.json
chmod 600 /Users/anicca/.local/state/life-manager/migration/elz-f/fork-topology-receipt.json
jq -e '.status=="passed" and .delete_repositories==0 and .transition_gate=="ELZ-O05+ELZ-T11"' \
  /Users/anicca/.local/state/life-manager/migration/elz-f/fork-topology-receipt.json
```

### Task 4: ELZ-F04 — Install project-local Node and Bun versions

**Files:**
- Create outside repo: `/Users/anicca/.local/share/life-manager/toolchains/elz-f/`
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-f/toolchain-receipt.json`

**Interfaces:**
- Consumes: macOS arm64, official Node/Bun release endpoints.
- Produces: project-local Node `24.15.0` and Bun `1.3.14`; system binaries unchanged.

- [ ] **Step 1: Create the private tool root and download verified Node**

```bash
mkdir -p -m 700 /Users/anicca/.local/share/life-manager/toolchains/elz-f
cd /Users/anicca/.local/share/life-manager/toolchains/elz-f
curl -fsSLO https://nodejs.org/dist/v24.15.0/node-v24.15.0-darwin-arm64.tar.gz
curl -fsSLO https://nodejs.org/dist/v24.15.0/SHASUMS256.txt
grep ' node-v24.15.0-darwin-arm64.tar.gz$' SHASUMS256.txt | shasum -a 256 -c -
tar -xzf node-v24.15.0-darwin-arm64.tar.gz
```

Expected: checksum says `OK`; extracted `node --version` is `v24.15.0`.

- [ ] **Step 2: Install Bun into the private tool root**

```bash
export BUN_INSTALL=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14
curl -fsSL https://bun.sh/install | bash -s 'bun-v1.3.14'
test "$($BUN_INSTALL/bin/bun --version)" = 1.3.14
```

- [ ] **Step 3: Prove the pinned PATH without changing shell profiles**

```bash
export PATH=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin:/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
test "$(node --version)" = v24.15.0
test "$(bun --version)" = 1.3.14
```

Expected: no `.zshrc`, global Bun, Homebrew, or system Node mutation.

- [ ] **Step 4: Write and verify the toolchain receipt**

```bash
NODE_BIN=/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin/node
BUN_BIN=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin/bun
jq -n --arg node "$($NODE_BIN --version)" --arg bun "$($BUN_BIN --version)" '{
  atom:"ELZ-F04",status:"passed",node:$node,bun:$bun,system_profile_mutations:0
}' > /Users/anicca/.local/state/life-manager/migration/elz-f/toolchain-receipt.json
chmod 600 /Users/anicca/.local/state/life-manager/migration/elz-f/toolchain-receipt.json
jq -e '.status=="passed" and .node=="v24.15.0" and .bun=="1.3.14" and .system_profile_mutations==0' \
  /Users/anicca/.local/state/life-manager/migration/elz-f/toolchain-receipt.json
```

### Task 5: ELZ-F05 — Initialize every fixed submodule

**Files:**
- Modify only in migration fork: Git submodule worktrees under `plugins/plugin-local-inference/native/llama.cpp`
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-f/submodule-receipt.json`

**Interfaces:**
- Consumes: fixed Eliza checkout.
- Produces: all submodules initialized at committed SHAs.

- [ ] **Step 1: Record the expected submodule status**

```bash
git -C /Users/anicca/Projects/life-manager-eliza-migration submodule status --recursive
```

- [ ] **Step 2: Initialize recursively**

```bash
git -C /Users/anicca/Projects/life-manager-eliza-migration submodule update --init --recursive
```

- [ ] **Step 3: Reject any remaining uninitialized submodule**

```bash
test -z "$(git -C /Users/anicca/Projects/life-manager-eliza-migration submodule status --recursive | awk '$1 ~ /^-/ {print}')"
git -C /Users/anicca/Projects/life-manager-eliza-migration diff --submodule=short --exit-code
```

Expected: both commands exit 0.

- [ ] **Step 4: Write and verify the submodule receipt**

```bash
SUBMODULE_SHA=$(git -C /Users/anicca/Projects/life-manager-eliza-migration submodule status --recursive | shasum -a 256 | awk '{print $1}')
jq -n --arg inventory "$SUBMODULE_SHA" '{
  atom:"ELZ-F05",status:"passed",inventory_sha256:$inventory,uninitialized:0,tracked_diff:0
}' > /Users/anicca/.local/state/life-manager/migration/elz-f/submodule-receipt.json
chmod 600 /Users/anicca/.local/state/life-manager/migration/elz-f/submodule-receipt.json
jq -e '.status=="passed" and .uninitialized==0 and .tracked_diff==0' \
  /Users/anicca/.local/state/life-manager/migration/elz-f/submodule-receipt.json
```

### Task 6: ELZ-F06 — Frozen install and server build

**Files:**
- Modify generated ignored content only: migration fork dependency/build output.
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-f/toolchain-build-receipt.json`

**Interfaces:**
- Consumes: pinned toolchain, initialized submodules, network, disk.
- Produces: frozen dependency graph and server build; Git tracked diff 0.

- [ ] **Step 1: Prove network and disk before install**

```bash
curl -fsS --max-time 10 https://registry.npmjs.org/bun >/dev/null
mkdir -p -m 700 /Users/anicca/.local/state/life-manager/migration/elz-f
df -k /Users/anicca/Projects/life-manager-eliza-migration | awk 'NR==2 {print $4}' \
  > /Users/anicca/.local/state/life-manager/migration/elz-f/build-free-before-kib.txt
test "$(cat /Users/anicca/.local/state/life-manager/migration/elz-f/build-free-before-kib.txt)" -gt 0
```

Expected: registry request exits 0. A failure is `network_unavailable`, not a build PASS.

- [ ] **Step 2: Run the frozen install**

```bash
export PATH=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin:/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd /Users/anicca/Projects/life-manager-eliza-migration
bun install --frozen-lockfile
```

Expected: exit 0; no ConnectionRefused, DNS, ENOSPC, or lockfile mutation.

- [ ] **Step 3: Build only the server surface**

```bash
export PATH=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin:/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd /Users/anicca/Projects/life-manager-eliza-migration
bun run build:server
test -z "$(git status --porcelain=v1)"
```

Expected: build exits 0; tracked status is empty.

- [ ] **Step 4: Run the focused upstream foundation tests**

```bash
export PATH=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin:/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd /Users/anicca/Projects/life-manager-eliza-migration
bunx vitest run --config packages/agent/vitest.config.ts \
  packages/agent/src/runtime/eliza-database-config.test.ts \
  packages/agent/src/api/health-routes.test.ts \
  packages/agent/src/api/health-routes.database-liveness.test.ts \
  packages/agent/src/api/server-skip-listen.test.ts
```

Expected: failures 0.

- [ ] **Step 5: Write and verify the build receipt**

```bash
cd /Users/anicca/Projects/life-manager-eliza-migration
SOURCE_SHA=$(git rev-parse HEAD)
LOCK_SHA=$(shasum -a 256 bun.lock | awk '{print $1}')
FREE_BEFORE_KIB=$(cat /Users/anicca/.local/state/life-manager/migration/elz-f/build-free-before-kib.txt)
FREE_AFTER_KIB=$(df -k /Users/anicca/Projects/life-manager-eliza-migration | awk 'NR==2 {print $4}')
TRACKED_DIFF_COUNT=$(git status --porcelain=v1 | wc -l | tr -d ' ')
test "$TRACKED_DIFF_COUNT" = 0
jq -n --arg source "$SOURCE_SHA" --arg lock "$LOCK_SHA" --argjson free_before "$FREE_BEFORE_KIB" --argjson free_after "$FREE_AFTER_KIB" --argjson tracked_diff "$TRACKED_DIFF_COUNT" '{
  atom:"ELZ-F06",status:"passed",source_sha:$source,lock_sha256:$lock,
  frozen_install:true,build_server:true,focused_tests:"passed",free_before_kib:$free_before,free_after_kib:$free_after,tracked_diff:$tracked_diff
}' > /Users/anicca/.local/state/life-manager/migration/elz-f/toolchain-build-receipt.json
chmod 600 /Users/anicca/.local/state/life-manager/migration/elz-f/toolchain-build-receipt.json
jq -e '.status=="passed" and .source_sha=="29bed1bb394a2c0c7c0df6dc12babbe28667efbe" and .frozen_install and .build_server and .tracked_diff==0' \
  /Users/anicca/.local/state/life-manager/migration/elz-f/toolchain-build-receipt.json
```

### Task 7: ELZ-F07 — Lock license and notice evidence

**Files:**
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-f/license-notice-receipt.json`
- Read only: root/package license and notice files.

**Interfaces:**
- Consumes: fixed Git tree.
- Produces: hash inventory for Eliza root MIT and relevant packages/submodules.

- [ ] **Step 1: Hash the authoritative license files**

```bash
cd /Users/anicca/Projects/life-manager-eliza-migration
test -f LICENSE
test -f packages/core/LICENSE
ROOT_LICENSE_SHA=$(shasum -a 256 LICENSE | awk '{print $1}')
CORE_LICENSE_SHA=$(shasum -a 256 packages/core/LICENSE | awk '{print $1}')
```

- [ ] **Step 2: Verify manifest license fields**

```bash
cd /Users/anicca/Projects/life-manager-eliza-migration
test "$(jq -r .license packages/agent/package.json)" = MIT
test "$(jq -r .license plugins/plugin-sql/package.json)" = MIT
```

- [ ] **Step 3: Inventory every tracked license/notice and submodule SHA**

```bash
cd /Users/anicca/Projects/life-manager-eliza-migration
git ls-files | awk 'tolower($0) ~ /(^|\/)(license|notice|copying)(\.|$)/ {print}' | sort \
  > /Users/anicca/.local/state/life-manager/migration/elz-f/license-files.txt
git submodule foreach --quiet --recursive 'printf "%s %s\n" "$displaypath" "$(git rev-parse HEAD)"' | sort \
  > /Users/anicca/.local/state/life-manager/migration/elz-f/submodule-shas.txt
test -s /Users/anicca/.local/state/life-manager/migration/elz-f/license-files.txt
test -s /Users/anicca/.local/state/life-manager/migration/elz-f/submodule-shas.txt
rg -n 'Copyright|copyright' LICENSE packages/core/LICENSE \
  > /Users/anicca/.local/state/life-manager/migration/elz-f/copyright-lines.txt
test -s /Users/anicca/.local/state/life-manager/migration/elz-f/copyright-lines.txt
```

- [ ] **Step 4: Write the receipt without changing upstream notices**

```bash
cd /Users/anicca/Projects/life-manager-eliza-migration
ROOT_LICENSE_SHA=$(shasum -a 256 LICENSE | awk '{print $1}')
CORE_LICENSE_SHA=$(shasum -a 256 packages/core/LICENSE | awk '{print $1}')
LICENSE_INVENTORY_SHA=$(shasum -a 256 /Users/anicca/.local/state/life-manager/migration/elz-f/license-files.txt | awk '{print $1}')
SUBMODULE_INVENTORY_SHA=$(shasum -a 256 /Users/anicca/.local/state/life-manager/migration/elz-f/submodule-shas.txt | awk '{print $1}')
COPYRIGHT_SHA=$(shasum -a 256 /Users/anicca/.local/state/life-manager/migration/elz-f/copyright-lines.txt | awk '{print $1}')
LICENSE_COUNT=$(wc -l < /Users/anicca/.local/state/life-manager/migration/elz-f/license-files.txt | tr -d ' ')
SUBMODULE_COUNT=$(wc -l < /Users/anicca/.local/state/life-manager/migration/elz-f/submodule-shas.txt | tr -d ' ')
test "$LICENSE_COUNT" -gt 0
test "$SUBMODULE_COUNT" -gt 0
jq -n --arg root "$ROOT_LICENSE_SHA" --arg core "$CORE_LICENSE_SHA" --arg licenses "$LICENSE_INVENTORY_SHA" --arg submodules "$SUBMODULE_INVENTORY_SHA" --arg copyright "$COPYRIGHT_SHA" --argjson license_count "$LICENSE_COUNT" --argjson submodule_count "$SUBMODULE_COUNT" '{
  atom:"ELZ-F07",status:"passed",source_sha:"29bed1bb394a2c0c7c0df6dc12babbe28667efbe",
  root_license_sha256:$root,core_license_sha256:$core,license_inventory_sha256:$licenses,
  submodule_inventory_sha256:$submodules,copyright_inventory_sha256:$copyright,
  license_count:$license_count,submodule_count:$submodule_count,root_license:"MIT",notice_mutations:0
}' > /Users/anicca/.local/state/life-manager/migration/elz-f/license-notice-receipt.json
chmod 600 /Users/anicca/.local/state/life-manager/migration/elz-f/license-notice-receipt.json
jq -e '.status=="passed" and .license_count>0 and .submodule_count>0 and .notice_mutations==0' \
  /Users/anicca/.local/state/life-manager/migration/elz-f/license-notice-receipt.json
```

### Task 8: ELZ-F08 — Boot the unmodified local server and read health

**Files:**
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-f/runtime/`
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-f/local-boot-receipt.json`

**Interfaces:**
- Consumes: server build, port 2138, no model credential.
- Produces: loopback server and healthy PGlite readback; no chat capability requirement.

- [ ] **Step 1: Fail if the owned port or runtime path is unsafe**

```bash
test -z "$(lsof -nP -iTCP:2138 -sTCP:LISTEN 2>/dev/null)"
mkdir -p -m 700 /Users/anicca/.local/state/life-manager/migration/elz-f/runtime/db
test ! -L /Users/anicca/.local/state/life-manager/migration/elz-f/runtime
test ! -f /Users/anicca/Projects/life-manager-eliza-migration/.env
test ! -f /Users/anicca/.local/state/life-manager/migration/elz-f/runtime/.env
```

- [ ] **Step 2: Start the server in a PTY-owned session**

Run with the execution tool in `/Users/anicca/Projects/life-manager-eliza-migration`:

```bash
LM_TMPDIR=$(/usr/bin/getconf DARWIN_USER_TEMP_DIR)
env -i \
  HOME=/Users/anicca USER=anicca LOGNAME=anicca TMPDIR="$LM_TMPDIR" \
  PATH=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin:/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin \
  ELIZA_PORT=2138 \
  ELIZA_STATE_DIR=/Users/anicca/.local/state/life-manager/migration/elz-f/runtime \
  PGLITE_DATA_DIR=/Users/anicca/.local/state/life-manager/migration/elz-f/runtime/db \
  bun run start
```

Expected: stdout contains `[eliza-api] Listening on http://127.0.0.1:2138`. Preserve the execution session ID.

- [ ] **Step 3: Read `/api/health` and `/api/status`**

```bash
curl -fsS http://127.0.0.1:2138/api/health | tee /tmp/elz-f08-health.json
jq -e '.ready==true and .runtime=="ok" and .database=="ok" and .databaseLiveness.ok==true and .databaseLiveness.terminal==false' /tmp/elz-f08-health.json
curl -fsS http://127.0.0.1:2138/api/status | jq -e '.state != null and .startedAt != null and .uptime >= 0'
```

Expected: both `jq -e` commands exit 0. `canRespond:false` is allowed in F08.

- [ ] **Step 4: Prove the launch command contained no model credential or external-effect tool**

```bash
curl -fsS http://127.0.0.1:2138/api/status | jq -e '.state != null'
```

Expected: exit 0. The Step 2 command explicitly shadows all four model-key env fields with empty values and loads no Life Manager plugin.

- [ ] **Step 5: Write and verify the local-boot receipt**

```bash
ELIZA_PID=$(lsof -nP -tiTCP:2138 -sTCP:LISTEN)
ELIZA_EXECUTABLE=$(ps -p "$ELIZA_PID" -o comm= | xargs)
ELIZA_ARGV_SHA=$(ps -p "$ELIZA_PID" -o command= | shasum -a 256 | awk '{print $1}')
ELIZA_START_IDENTITY=$(ps -p "$ELIZA_PID" -o lstart= | xargs)
jq -n --slurpfile health /tmp/elz-f08-health.json --arg pid "$ELIZA_PID" --arg executable "$ELIZA_EXECUTABLE" --arg argv_sha "$ELIZA_ARGV_SHA" --arg start_identity "$ELIZA_START_IDENTITY" '{
  atom:"ELZ-F08",status:"passed",source_sha:"29bed1bb394a2c0c7c0df6dc12babbe28667efbe",
  host:"127.0.0.1",port:2138,pid:$pid,executable:$executable,argv_sha256:$argv_sha,start_identity:$start_identity,
  health:$health[0],environment:"env-i-allowlist",model_credentials:0,external_effects:0
}' > /Users/anicca/.local/state/life-manager/migration/elz-f/local-boot-receipt.json
chmod 600 /Users/anicca/.local/state/life-manager/migration/elz-f/local-boot-receipt.json
jq -e '.status=="passed" and .health.ready==true and .health.runtime=="ok" and .health.database=="ok" and .model_credentials==0 and .external_effects==0' \
  /Users/anicca/.local/state/life-manager/migration/elz-f/local-boot-receipt.json
```

### Task 9: ELZ-F09 — Prove a persistent PGlite marker across process boundaries

**Files:**
- Modify private DB only: `/Users/anicca/.local/state/life-manager/migration/elz-f/runtime/db`
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-f/local-persistence-receipt.json`

**Interfaces:**
- Consumes: healthy F08 server and its exact process ID.
- Produces: private probe row that survives close/reopen; no source change.

- [ ] **Step 1: Resolve the exact listener PID and send SIGTERM**

```bash
RECORDED_PID=$(jq -r .pid /Users/anicca/.local/state/life-manager/migration/elz-f/local-boot-receipt.json)
RECORDED_EXECUTABLE=$(jq -r .executable /Users/anicca/.local/state/life-manager/migration/elz-f/local-boot-receipt.json)
RECORDED_ARGV_SHA=$(jq -r .argv_sha256 /Users/anicca/.local/state/life-manager/migration/elz-f/local-boot-receipt.json)
RECORDED_START=$(jq -r .start_identity /Users/anicca/.local/state/life-manager/migration/elz-f/local-boot-receipt.json)
LISTENER_PID=$(lsof -nP -tiTCP:2138 -sTCP:LISTEN)
test "$LISTENER_PID" = "$RECORDED_PID"
test "$(ps -p "$LISTENER_PID" -o comm= | xargs)" = "$RECORDED_EXECUTABLE"
test "$(ps -p "$LISTENER_PID" -o command= | shasum -a 256 | awk '{print $1}')" = "$RECORDED_ARGV_SHA"
test "$(ps -p "$LISTENER_PID" -o lstart= | xargs)" = "$RECORDED_START"
kill -TERM "$LISTENER_PID"
for attempt in $(seq 1 30); do
  kill -0 "$LISTENER_PID" 2>/dev/null || break
  sleep 1
done
! kill -0 "$LISTENER_PID" 2>/dev/null
test -z "$(lsof -nP -iTCP:2138 -sTCP:LISTEN 2>/dev/null)"
```

Expected: listener exits and port is free.

- [ ] **Step 2: Write one marker while the runtime is stopped**

```bash
cd /Users/anicca/Projects/life-manager-eliza-migration
PGLITE_DATA_DIR=/Users/anicca/.local/state/life-manager/migration/elz-f/runtime/db \
  /Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin/bun -e '
  import { PGlite } from "@electric-sql/pglite";
  const db = new PGlite(process.env.PGLITE_DATA_DIR);
  await db.exec("create table if not exists lm_elz01_probe (id text primary key, value text not null)");
  await db.query("insert into lm_elz01_probe(id,value) values ($1,$2) on conflict(id) do update set value=excluded.value", ["foundation", "fixed-sha-29bed1bb3"]);
  await db.close();
'
```

Expected: exit 0 and no `eliza-pglite.lock` remains held by a process.

- [ ] **Step 3: Reopen and read the exact marker**

```bash
cd /Users/anicca/Projects/life-manager-eliza-migration
PGLITE_DATA_DIR=/Users/anicca/.local/state/life-manager/migration/elz-f/runtime/db \
  /Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin/bun -e '
  import { PGlite } from "@electric-sql/pglite";
  const db = new PGlite(process.env.PGLITE_DATA_DIR);
  const rows = await db.query("select value from lm_elz01_probe where id=$1", ["foundation"]);
  if (rows.rows?.[0]?.value !== "fixed-sha-29bed1bb3") process.exit(1);
  await db.close();
'
```

Expected: exit 0.

- [ ] **Step 4: Write and verify the persistence receipt**

```bash
DB_DIR=/Users/anicca/.local/state/life-manager/migration/elz-f/runtime/db
DB_MODE=$(/usr/bin/stat -f '%Lp' "$DB_DIR")
WRITER_COUNT=$(lsof +D "$DB_DIR" 2>/dev/null | awk 'NR>1' | wc -l | tr -d ' ')
LOCK_PATH="$DB_DIR/eliza-pglite.lock"
LOCK_OPEN_HANDLES=$(lsof "$LOCK_PATH" 2>/dev/null | awk 'NR>1' | wc -l | tr -d ' ')
test "$DB_MODE" = 700
test "$WRITER_COUNT" = 0
test "$LOCK_OPEN_HANDLES" = 0
jq -n --argjson mode "$DB_MODE" --argjson writers "$WRITER_COUNT" --argjson lock_handles "$LOCK_OPEN_HANDLES" '{
  atom:"ELZ-F09",status:"passed",
  pglite_data_dir:"/Users/anicca/.local/state/life-manager/migration/elz-f/runtime/db",
  marker_id:"foundation",marker_value:"fixed-sha-29bed1bb3",directory_mode:$mode,
  writer_processes:$writers,lock_open_handles:$lock_handles
}' > /Users/anicca/.local/state/life-manager/migration/elz-f/local-persistence-receipt.json
chmod 600 /Users/anicca/.local/state/life-manager/migration/elz-f/local-persistence-receipt.json
jq -e '.status=="passed" and .marker_id=="foundation" and .marker_value=="fixed-sha-29bed1bb3" and .directory_mode==700 and .writer_processes==0 and .lock_open_handles==0' \
  /Users/anicca/.local/state/life-manager/migration/elz-f/local-persistence-receipt.json
```

### Task 10: ELZ-F10 — Restart the same DB and close the foundation slice

**Files:**
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-f/local-health-receipt.json`
- Modify as primary only: canonical spec `ELZ-F10` state after verification.

**Interfaces:**
- Consumes: F09 DB marker, fixed runtime command.
- Produces: same-path restart health, clean stop, pushed spec evidence.

- [ ] **Step 1: Restart with the identical command and paths**

Use a new PTY-owned execution session with the exact Task 8 Step 2 command. After bind, record the restart process identity:

```bash
RESTART_PID=$(lsof -nP -tiTCP:2138 -sTCP:LISTEN)
RESTART_EXECUTABLE=$(ps -p "$RESTART_PID" -o comm= | xargs)
RESTART_ARGV_SHA=$(ps -p "$RESTART_PID" -o command= | shasum -a 256 | awk '{print $1}')
RESTART_START=$(ps -p "$RESTART_PID" -o lstart= | xargs)
jq -n --arg pid "$RESTART_PID" --arg executable "$RESTART_EXECUTABLE" --arg argv_sha "$RESTART_ARGV_SHA" --arg start "$RESTART_START" \
  '{pid:$pid,executable:$executable,argv_sha256:$argv_sha,start_identity:$start}' \
  > /Users/anicca/.local/state/life-manager/migration/elz-f/restart-process-identity.json
chmod 600 /Users/anicca/.local/state/life-manager/migration/elz-f/restart-process-identity.json
```

Expected: listener binds 2138 and `/api/health` passes the same predicate.

- [ ] **Step 2: Verify health and marker after restart**

```bash
curl -fsS http://127.0.0.1:2138/api/health | jq -e '.ready==true and .runtime=="ok" and .database=="ok" and .databaseLiveness.ok==true'
RESTART_PID=$(jq -r .pid /Users/anicca/.local/state/life-manager/migration/elz-f/restart-process-identity.json)
test "$(lsof -nP -tiTCP:2138 -sTCP:LISTEN)" = "$RESTART_PID"
test "$(ps -p "$RESTART_PID" -o comm= | xargs)" = "$(jq -r .executable /Users/anicca/.local/state/life-manager/migration/elz-f/restart-process-identity.json)"
test "$(ps -p "$RESTART_PID" -o command= | shasum -a 256 | awk '{print $1}')" = "$(jq -r .argv_sha256 /Users/anicca/.local/state/life-manager/migration/elz-f/restart-process-identity.json)"
test "$(ps -p "$RESTART_PID" -o lstart= | xargs)" = "$(jq -r .start_identity /Users/anicca/.local/state/life-manager/migration/elz-f/restart-process-identity.json)"
kill -TERM "$RESTART_PID"
```

Wait on the PTY-owned execution session and require process exit code `0`. Then run the Task 9 Step 3 marker query again with its absolute Bun path.

Expected: health and marker both PASS; port 2138 ends free.

- [ ] **Step 3: Run the focused foundation verification again**

```bash
export PATH=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin:/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd /Users/anicca/Projects/life-manager-eliza-migration
bunx vitest run --config packages/agent/vitest.config.ts \
  packages/agent/src/runtime/eliza-database-config.test.ts \
  packages/agent/src/api/health-routes.test.ts \
  packages/agent/src/api/health-routes.database-liveness.test.ts \
  packages/agent/src/api/server-skip-listen.test.ts
git diff --check
git status --porcelain=v1
```

Expected: tests fail 0, diff check exits 0, tracked status empty.

- [ ] **Step 4: Write and verify the restart-health receipt**

```bash
: "${ELIZA_RESTART_EXIT_CODE:?set this to the exact PTY execution-tool exit_code before writing the receipt}"
PORT_LISTENER_COUNT=$(lsof -nP -iTCP:2138 -sTCP:LISTEN 2>/dev/null | awk 'NR>1' | wc -l | tr -d ' ')
test "$ELIZA_RESTART_EXIT_CODE" = 0
test "$PORT_LISTENER_COUNT" = 0
jq -n --argjson exit_code "$ELIZA_RESTART_EXIT_CODE" --argjson listener_count "$PORT_LISTENER_COUNT" '{
  atom:"ELZ-F10",status:"passed",source_sha:"29bed1bb394a2c0c7c0df6dc12babbe28667efbe",
  restart_same_db:true,health_after_restart:"passed",marker_after_restart:"passed",
  sigterm_exit_code:$exit_code,listener_count_after_stop:$listener_count,external_effects:0
}' > /Users/anicca/.local/state/life-manager/migration/elz-f/local-health-receipt.json
chmod 600 /Users/anicca/.local/state/life-manager/migration/elz-f/local-health-receipt.json
jq -e '.status=="passed" and .restart_same_db and .sigterm_exit_code==0 and .listener_count_after_stop==0 and .external_effects==0' \
  /Users/anicca/.local/state/life-manager/migration/elz-f/local-health-receipt.json
```

- [ ] **Step 5: Primary updates only the completed Phase F rows**

Primary reads the F10 receipt, records exact evidence in the canonical spec, and leaves F11 onward untouched. F01〜F09 were already closed one by one by the rule below with `ATOM_ID` set to their exact IDs. Run the closeout block with `ATOM_ID=ELZ-F10`.

Expected: pushed SHA readback matches local SHA, CI required checks PASS, and no Life Manager plugin/model/provider/marketplace effect occurred.

## Primary-Only Closeout After Every Task

After each Task, the primary agent reads that Task's named receipt, changes only the matching Atomic program ledger row from the active state to `DONE`, records the exact receipt path/hash and measured command result, then moves `IN_PROGRESS — NEXT` to the immediately following Seq. Executors never edit the canonical spec. No second full review runs unless the first review produced a blocking finding; that re-review checks only the fix.

Set `ATOM_ID` to the exact completed ID, for example `ELZ-F01` or `ELZ-F10`, then use one isolated spec worktree:

```bash
ATOM_ID=ELZ-F10
ATOM_SLUG=$(printf '%s' "$ATOM_ID" | tr '[:upper:]' '[:lower:]')
STATE_BRANCH="docs/${ATOM_SLUG}-state"
STATE_WORKTREE="/Users/anicca/Projects/life-manager-main/.worktrees/${ATOM_SLUG}-state"
git -C /Users/anicca/Projects/life-manager-main fetch origin --prune
git -C /Users/anicca/Projects/life-manager-main worktree add "$STATE_WORKTREE" -b "$STATE_BRANCH" origin/main
```

Primary uses `apply_patch` inside `$STATE_WORKTREE` to update only the matching row and its immediate successor. Then:

```bash
git -C "$STATE_WORKTREE" diff --check
node "$STATE_WORKTREE/scripts/verify-oss-self-contained.mjs"
git -C "$STATE_WORKTREE" add docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md
git -C "$STATE_WORKTREE" commit -m "docs(agent): close ${ATOM_SLUG}"
git -C "$STATE_WORKTREE" fetch origin --prune
git -C "$STATE_WORKTREE" rebase origin/main
git -C "$STATE_WORKTREE" push -u origin "$STATE_BRANCH"
gh pr create --repo Daisuke134/life-manager --base main --head "$STATE_BRANCH" --title "docs(agent): close ${ATOM_SLUG}" --body "Measured atomic receipt closeout for ${ATOM_ID}."
```

Run one P0/P1 adversarial review before merge, wait for required CI, merge the PR, then prove main contains the commit:

```bash
gh pr merge --repo Daisuke134/life-manager "$STATE_BRANCH" --merge
git -C /Users/anicca/Projects/life-manager-main fetch origin --prune
STATE_COMMIT=$(git -C "$STATE_WORKTREE" rev-parse HEAD)
git -C /Users/anicca/Projects/life-manager-main merge-base --is-ancestor "$STATE_COMMIT" origin/main
```

## Plan Self-Review

- Spec coverage: ELZ-F01〜F10 each has one task and one named receipt.
- Placeholder scan: every path, version, command, expected result, and failure boundary is explicit.
- Type/name consistency: every path/value comes from `Fixed Paths and Values`; health predicates match upstream fixed commit.
- Scope: F11 history join, F12 import, F13 clean-clone replay, plugin, model call, Lancers, legacy cutover, cloud are excluded and receive separate plans after F10 evidence.

## Execution Handoff

Execute with `superpowers:subagent-driven-development`: one fresh implementer per Task, primary receipt review between Tasks, and fresh read-only adversarial review before each state update. Start only with Task 1 `ELZ-F01`.
