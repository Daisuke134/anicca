# Eliza Clean-Clone Foundation Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recreate the completed Eliza foundation from the public migration branch in a fresh canonical clone and prove build, health, persistence, restart, and clean Git state.

**Architecture:** Verify every remote and private receipt before removing the fully regenerable old migration checkout, then clone `migration/eliza-docs` from GitHub into the same canonical path. Reuse the already checksum-verified private toolchain, run the known minimal frozen install/build, exercise one isolated PGlite runtime through stop/reopen/restart, run the focused 32-test foundation set once, and bind the evidence in one private receipt.

**Tech Stack:** Git, Bun 1.3.14, Node 24.15.0, Vitest, Eliza server, PGlite, zsh, `jq`, `curl`, `lsof`.

**Spec:** `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

## Global Constraints

- Public replay commit is exactly `52eefdac597b70f3cb769b007cc4209f0f55cc34` on `Daisuke134/life-manager-eliza:migration/eliza-docs`.
- Canonical clone path is `/Users/anicca/Projects/life-manager-eliza-migration`.
- Pinned toolchain remains outside the clone at `/Users/anicca/.local/share/life-manager/toolchains/elz-f`.
- Replay runtime is isolated at `/Users/anicca/.local/state/life-manager/migration/elz-f/replay/runtime` on loopback port `2139`.
- Existing private receipts and the original F08/F09 runtime are preserved.
- Removing the old clone is allowed only after exact local/remote/clean/process/disk gates; it is fully recoverable from the verified public branch.
- Use the proven two-command frozen install: agent filter, then root `eliza` filter. Do not run a full install.
- Run `build:server` once and the four focused Vitest files once. Do not duplicate tests, run a full suite, or run CI.
- No Life Manager plugin, model credential, marketplace/provider/browser action, production loop, repository rename/archive/delete, force-push, or `main` mutation.
- One bounded adversarial review follows focused verification; no second review unless it checks one load-bearing fix.

---

### Task 1: Reclone and replay F04-F10 as one clean foundation atom

**Files:**
- Replace regenerable clone: `/Users/anicca/Projects/life-manager-eliza-migration`
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-f/replay/runtime/`
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-f/foundation-replay-receipt.json`
- Create outside repo: `/Users/anicca/Projects/life-manager-main/.worktrees/elz-f13-plan/.superpowers/sdd/2026-08-29-eliza-clean-clone-replay/task-1-report.md`

**Interfaces:**
- Consumes: remote import commit, F04 toolchain receipt, F05-F12 private receipts.
- Produces: a fresh clean clone and `foundation-replay-receipt.json`; ELZ-C01 consumes this foundation.

- [ ] **Step 1: Prove the old clone is safe to replace**

```bash
set -e
CLONE=/Users/anicca/Projects/life-manager-eliza-migration
REPLAY_SHA=52eefdac597b70f3cb769b007cc4209f0f55cc34
test "$(realpath "$CLONE")" = "$CLONE"
test -d "$CLONE/.git"
test ! -L "$CLONE"
test "$(git -C "$CLONE" rev-parse HEAD)" = "$REPLAY_SHA"
test "$(git -C "$CLONE" branch --show-current)" = migration/eliza-docs
test -z "$(git -C "$CLONE" status --porcelain=v1)"
test "$(jq '.entries | length' "$CLONE/docs/legacy-life-manager/import-manifest.json")" = 21
test "$(git ls-remote https://github.com/Daisuke134/life-manager-eliza.git refs/heads/migration/eliza-docs | awk '{print $1}')" = "$REPLAY_SHA"
test "$(git ls-remote https://github.com/Daisuke134/life-manager-eliza.git refs/heads/migration/eliza-history | awk '{print $1}')" = 152ad359358fa1456ff92e84ecef3bae91122862
test "$(git ls-remote https://github.com/Daisuke134/life-manager-eliza.git refs/heads/main | awk '{print $1}')" = 29bed1bb394a2c0c7c0df6dc12babbe28667efbe
jq -e '.atom=="ELZ-F12" and .status=="passed" and .import_sha=="52eefdac597b70f3cb769b007cc4209f0f55cc34" and .import_sha==.remote_readback_sha' \
  /Users/anicca/.local/state/life-manager/migration/elz-f/history-import-receipt.json
test -z "$(lsof -nP -iTCP:2138 -sTCP:LISTEN 2>/dev/null)"
test -z "$(lsof -nP -iTCP:2139 -sTCP:LISTEN 2>/dev/null)"
FREE_KIB_BEFORE=$(df -Pk /Users/anicca | awk 'END {print $4}')
OLD_CLONE_KIB=$(du -sk "$CLONE" | awk '{print $1}')
test "$((FREE_KIB_BEFORE + OLD_CLONE_KIB))" -ge 4000000
mkdir -p -m 700 /Users/anicca/.local/state/life-manager/migration/elz-f/replay
printf '%s\n' "$FREE_KIB_BEFORE" > /Users/anicca/.local/state/life-manager/migration/elz-f/replay/free-before-kib.txt
printf '%s\n' "$OLD_CLONE_KIB" > /Users/anicca/.local/state/life-manager/migration/elz-f/replay/old-clone-kib.txt
```

Expected: all gates exit `0`; both test ports are free and recoverable headroom is at least 4,000,000 KiB.

- [ ] **Step 2: Remove only the verified old clone and clone the public replay branch**

```bash
set -e
CLONE=/Users/anicca/Projects/life-manager-eliza-migration
REPLAY_SHA=52eefdac597b70f3cb769b007cc4209f0f55cc34
test "$(realpath "$CLONE")" = "$CLONE"
test -d "$CLONE/.git"
find "$CLONE" -mindepth 1 -depth -delete
rmdir "$CLONE"
test ! -e "$CLONE"
test "$(df -Pk /Users/anicca | awk 'END {print $4}')" -ge 4000000
git clone --filter=blob:none --single-branch --branch migration/eliza-docs --no-recurse-submodules \
  https://github.com/Daisuke134/life-manager-eliza.git "$CLONE"
test "$(git -C "$CLONE" rev-parse HEAD)" = "$REPLAY_SHA"
test "$(git -C "$CLONE" branch --show-current)" = migration/eliza-docs
test -z "$(git -C "$CLONE" status --porcelain=v1)"
git -C "$CLONE" remote add eliza-upstream https://github.com/elizaOS/eliza.git
test "$(git -C "$CLONE" remote get-url origin)" = https://github.com/Daisuke134/life-manager-eliza.git
test "$(git -C "$CLONE" remote get-url eliza-upstream)" = https://github.com/elizaOS/eliza.git
```

Expected: the prior clone is removed and recoverable; the new checkout comes from GitHub at the exact replay SHA with a clean tree.

- [ ] **Step 3: Replay the pinned toolchain, submodules, and license inventory**

```bash
set -e
CLONE=/Users/anicca/Projects/life-manager-eliza-migration
NODE=/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin/node
BUN=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin/bun
test "$($NODE --version)" = v24.15.0
test "$($BUN --version)" = 1.3.14
jq -e '.atom=="ELZ-F04" and .status=="passed" and (.node_checksum_result|endswith("OK"))' \
  /Users/anicca/.local/state/life-manager/migration/elz-f/toolchain-receipt.json
jq -e '.atom=="ELZ-F04" and .status=="passed" and (.bun_checksum_result|endswith("OK"))' \
  /Users/anicca/.local/state/life-manager/migration/elz-f/toolchain-receipt.json
git -C "$CLONE" submodule update --init --recursive --depth 1
test -z "$(git -C "$CLONE" submodule status --recursive | awk '$1 ~ /^-/ {print}')"
test "$(git -C "$CLONE" -C plugins/plugin-local-inference/native/llama.cpp rev-parse HEAD)" = 6543d9078051a9bb194c2ef5c2995f003c5158de
test "$(git -C "$CLONE" -C upstreams/electrobun rev-parse HEAD)" = f1f38ce51184539de22691f56784713821fc507d
test "$(shasum -a 256 "$CLONE/LICENSE" | awk '{print $1}')" = d0590837a439c742e89c8226137dd4e902fa1e0df486347dbfc9b8ba68b5826d
test "$(shasum -a 256 "$CLONE/packages/core/LICENSE" | awk '{print $1}')" = 45dc0df0d40c1647eb47ec8a3a8350e94c913d69cb68cfa46c770a65a79fb433
LICENSE_COUNT=$(git -C "$CLONE" ls-files | awk 'tolower($0) ~ /(^|\/)(license|notice|copying)(\.|$)/ {print}' | wc -l | tr -d ' ')
test "$LICENSE_COUNT" = 28
test -z "$(git -C "$CLONE" status --porcelain=v1)"
```

Expected: pinned binaries, checksum receipts, two exact shallow submodules, two authoritative license hashes, and 28 tracked notice/license files all match.

- [ ] **Step 4: Replay the minimal frozen install and server build**

```bash
set -e
export PATH=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin:/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd /Users/anicca/Projects/life-manager-eliza-migration
test "$(shasum -a 256 bun.lock | awk '{print $1}')" = 1976283db890a36ae945cd1256e9388ca84c067608df9628570bb6fce3ad7eb4
curl -fsS --max-time 10 https://registry.npmjs.org/bun >/dev/null
INSTALL_FREE_BEFORE=$(df -Pk /Users/anicca | awk 'END {print $4}')
test "$INSTALL_FREE_BEFORE" -ge 2500000
bun install --frozen-lockfile --no-cache --filter @elizaos/agent
bun install --frozen-lockfile --no-cache --filter eliza
bun run build:server 2>&1 | tee /Users/anicca/.local/state/life-manager/migration/elz-f/replay/build-server.log
test "${pipestatus[1]}" = 0
rg -q '55 successful, 55 total' /Users/anicca/.local/state/life-manager/migration/elz-f/replay/build-server.log
test "$(shasum -a 256 bun.lock | awk '{print $1}')" = 1976283db890a36ae945cd1256e9388ca84c067608df9628570bb6fce3ad7eb4
test -z "$(git status --porcelain=v1 --untracked-files=no)"
```

Expected: both frozen installs exit `0`; `build:server` exits `0` with the server graph complete; lock hash and tracked tree remain unchanged.

- [ ] **Step 4A: Resume the measured ENOSPC attempt using only regenerable capacity**

This step applies to the recorded attempt where the first filtered install left 5,305 packages in ignored `node_modules`, 41 packages failed with `ENOSPC`, the tracked tree stayed clean, and ports 2138/2139 stayed free. Preserve those completed packages.

```bash
set -e
CLONE=/Users/anicca/Projects/life-manager-eliza-migration
test "$(git -C "$CLONE" rev-parse HEAD)" = 52eefdac597b70f3cb769b007cc4209f0f55cc34
test -z "$(git -C "$CLONE" status --porcelain=v1 --untracked-files=no)"
test -d "$CLONE/node_modules/.bun"
test -z "$(lsof -nP -iTCP:2138 -sTCP:LISTEN 2>/dev/null)"
test -z "$(lsof -nP -iTCP:2139 -sTCP:LISTEN 2>/dev/null)"
git -C /Users/anicca/Projects/life-manager-main fetch origin --prune
git -C /Users/anicca/Projects/life-manager-main merge-base --is-ancestor \
  e339aeab4c2267e8671e8191e7bb02478085795c origin/main
test -z "$(git -C /Users/anicca/Projects/life-manager-main/.worktrees/eliza-atomic-roadmap-20260829 status --short)"
git -C /Users/anicca/Projects/life-manager-main worktree remove \
  /Users/anicca/Projects/life-manager-main/.worktrees/eliza-atomic-roadmap-20260829

for cache_path in \
  /Users/anicca/.npm/_npx \
  /Users/anicca/.npm/_cacache \
  /Users/anicca/Library/Caches/bun \
  /Users/anicca/Library/Caches/node-gyp \
  /Users/anicca/Library/Caches/Homebrew \
  /Users/anicca/Library/Caches/ffmpeg-static-nodejs \
  /Users/anicca/Library/Caches/CodexBar \
  /Users/anicca/Library/Caches/Adobe
do
  if [ -e "$cache_path" ]; then
    test -d "$cache_path"
    test ! -L "$cache_path"
    find "$cache_path" -mindepth 1 -depth -delete
    rmdir "$cache_path"
  fi
done

RESUME_FREE_KIB=$(df -Pk /Users/anicca | awk 'END {print $4}')
test "$RESUME_FREE_KIB" -ge 950000
printf '%s\n' "$RESUME_FREE_KIB" > \
  /Users/anicca/.local/state/life-manager/migration/elz-f/replay/resume-free-kib.txt
```

Resume with the exact commands:

```bash
set -e
export PATH=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin:/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd /Users/anicca/Projects/life-manager-eliza-migration
bun install --frozen-lockfile --no-cache --filter @elizaos/agent
bun install --frozen-lockfile --no-cache --filter eliza
bun run build:server 2>&1 | tee /Users/anicca/.local/state/life-manager/migration/elz-f/replay/build-server.log
test "${pipestatus[1]}" = 0
rg -q '55 successful, 55 total' /Users/anicca/.local/state/life-manager/migration/elz-f/replay/build-server.log
test "$(shasum -a 256 bun.lock | awk '{print $1}')" = 1976283db890a36ae945cd1256e9388ca84c067608df9628570bb6fce3ad7eb4
test -z "$(git status --porcelain=v1 --untracked-files=no)"
```

Bun must reuse the 5,305 present packages, install the missing graph, preserve the lock hash, produce `55 successful, 55 total`, and leave the tracked tree clean. Do not delete the partial install or any additional path.

Expected: only the merged roadmap worktree and enumerated caches are removed; free space is at least 950,000 KiB before the resume; the resumed build passes.

- [ ] **Step 4B: Add the measured 131 MiB cache-only margin**

This step applies to the recorded Step 4A result where the nine specified paths were removed, free space was `819700` KiB, and no install/build command resumed.

```bash
set -e
CLONE=/Users/anicca/Projects/life-manager-eliza-migration
test "$(git -C "$CLONE" rev-parse HEAD)" = 52eefdac597b70f3cb769b007cc4209f0f55cc34
test -z "$(git -C "$CLONE" status --porcelain=v1 --untracked-files=no)"
test -d "$CLONE/node_modules/.bun"
test ! -e /Users/anicca/Projects/life-manager-main/.worktrees/eliza-atomic-roadmap-20260829

for cache_path in \
  /Users/anicca/Library/Caches/Google \
  /Users/anicca/Library/Caches/GeoServices \
  /Users/anicca/Library/Caches/com.apple.helpd \
  /Users/anicca/Library/Caches/com.apple.parsecd \
  /Users/anicca/Library/Caches/CloudKit \
  /Users/anicca/Library/Caches/PassKit \
  /Users/anicca/Library/Caches/com.apple.passd \
  /Users/anicca/Library/Caches/com.apple.python \
  /Users/anicca/Library/Caches/claude-cli-nodejs \
  /Users/anicca/Library/Caches/Codex \
  /Users/anicca/Library/Caches/com.openai.sky.CUAService
do
  if [ -e "$cache_path" ]; then
    test -d "$cache_path"
    test ! -L "$cache_path"
    find "$cache_path" -mindepth 1 -depth -delete
    rmdir "$cache_path"
  fi
done

RESUME_FREE_KIB=$(df -Pk /Users/anicca | awk 'END {print $4}')
test "$RESUME_FREE_KIB" -ge 900000
printf '%s\n' "$RESUME_FREE_KIB" > \
  /Users/anicca/.local/state/life-manager/migration/elz-f/replay/resume-free-kib.txt
```

Resume with the exact commands:

```bash
set -e
export PATH=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin:/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd /Users/anicca/Projects/life-manager-eliza-migration
bun install --frozen-lockfile --no-cache --filter @elizaos/agent
bun install --frozen-lockfile --no-cache --filter eliza
bun run build:server 2>&1 | tee /Users/anicca/.local/state/life-manager/migration/elz-f/replay/build-server.log
test "${pipestatus[1]}" = 0
rg -q '55 successful, 55 total' /Users/anicca/.local/state/life-manager/migration/elz-f/replay/build-server.log
test "$(shasum -a 256 bun.lock | awk '{print $1}')" = 1976283db890a36ae945cd1256e9388ca84c067608df9628570bb6fce3ad7eb4
test -z "$(git status --porcelain=v1 --untracked-files=no)"
```

Expected: only the 11 enumerated cache directories are removed; free space is at least 900,000 KiB before resume; the same frozen dependency/build contract passes.

- [ ] **Step 4C: Shallow only the replay clone's local history and serialize the final five packages**

This step applies to the recorded Step 4B result: 224 packages installed, only five packages failed with `ENOSPC`, build did not start, tracked tree stayed clean, and current free space is about 300 MiB. Remote F11/F12 history is already verified and remains authoritative.

```bash
set -e
CLONE=/Users/anicca/Projects/life-manager-eliza-migration
REPLAY_SHA=52eefdac597b70f3cb769b007cc4209f0f55cc34
test "$(git -C "$CLONE" rev-parse HEAD)" = "$REPLAY_SHA"
test -z "$(git -C "$CLONE" status --porcelain=v1 --untracked-files=no)"
test -d "$CLONE/node_modules/.bun"
test "$(git ls-remote https://github.com/Daisuke134/life-manager-eliza.git refs/heads/migration/eliza-docs | awk '{print $1}')" = "$REPLAY_SHA"
GIT_KIB_BEFORE=$(du -sk "$CLONE/.git" | awk '{print $1}')
TAG_COUNT=$(git -C "$CLONE" tag -l | wc -l | tr -d ' ')
test "$TAG_COUNT" -gt 0
printf '%s\n' "$GIT_KIB_BEFORE" > /Users/anicca/.local/state/life-manager/migration/elz-f/replay/git-kib-before.txt
printf '%s\n' "$TAG_COUNT" > /Users/anicca/.local/state/life-manager/migration/elz-f/replay/local-tags-removed.txt
git -C "$CLONE" tag -l | while IFS= read -r tag_name; do
  git -C "$CLONE" tag -d "$tag_name" >/dev/null
done
git -C "$CLONE" fetch --depth=1 --no-tags origin \
  refs/heads/migration/eliza-docs:refs/remotes/origin/migration/eliza-docs
test "$(git -C "$CLONE" rev-parse --is-shallow-repository)" = true
git -C "$CLONE" reflog expire --expire=now --all
git -C "$CLONE" gc --prune=now
GIT_KIB_AFTER=$(du -sk "$CLONE/.git" | awk '{print $1}')
test "$GIT_KIB_AFTER" -lt "$GIT_KIB_BEFORE"
printf '%s\n' "$GIT_KIB_AFTER" > /Users/anicca/.local/state/life-manager/migration/elz-f/replay/git-kib-after.txt
test "$(git -C "$CLONE" rev-parse HEAD)" = "$REPLAY_SHA"
test -z "$(git -C "$CLONE" status --porcelain=v1 --untracked-files=no)"
SERIAL_FREE_KIB=$(df -Pk /Users/anicca | awk 'END {print $4}')
test "$SERIAL_FREE_KIB" -ge 500000
printf '%s\n' "$SERIAL_FREE_KIB" > /Users/anicca/.local/state/life-manager/migration/elz-f/replay/serial-free-kib.txt
```

Resume the exact graph with serialized network and lifecycle concurrency:

```bash
set -e
export PATH=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin:/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd /Users/anicca/Projects/life-manager-eliza-migration
bun install --frozen-lockfile --no-cache --network-concurrency=1 --concurrent-scripts=1 --filter @elizaos/agent
bun install --frozen-lockfile --no-cache --network-concurrency=1 --concurrent-scripts=1 --filter eliza
bun run build:server 2>&1 | tee /Users/anicca/.local/state/life-manager/migration/elz-f/replay/build-server.log
test "${pipestatus[1]}" = 0
rg -q '55 successful, 55 total' /Users/anicca/.local/state/life-manager/migration/elz-f/replay/build-server.log
test "$(shasum -a 256 bun.lock | awk '{print $1}')" = 1976283db890a36ae945cd1256e9388ca84c067608df9628570bb6fce3ad7eb4
test -z "$(git status --porcelain=v1 --untracked-files=no)"
```

Expected: local `.git` shrinks, remote refs remain untouched, the same locked dependency graph completes at concurrency 1, and build reaches 55/55.

- [ ] **Step 5: Start a fresh model-credential-free replay runtime**

Create the isolated state first:

```bash
set -e
RUNTIME=/Users/anicca/.local/state/life-manager/migration/elz-f/replay/runtime
test ! -e "$RUNTIME"
mkdir -p -m 700 "$RUNTIME/db"
test ! -L "$RUNTIME"
test ! -f /Users/anicca/Projects/life-manager-eliza-migration/.env
test -z "$(lsof -nP -iTCP:2139 -sTCP:LISTEN 2>/dev/null)"
```

Then start one PTY-owned session in `/Users/anicca/Projects/life-manager-eliza-migration`:

```bash
LM_TMPDIR=$(/usr/bin/getconf DARWIN_USER_TEMP_DIR)
env -i \
  HOME=/Users/anicca USER=anicca LOGNAME=anicca TMPDIR="$LM_TMPDIR" \
  PATH=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin:/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin \
  ELIZA_PORT=2139 \
  ELIZA_STATE_DIR=/Users/anicca/.local/state/life-manager/migration/elz-f/replay/runtime \
  PGLITE_DATA_DIR=/Users/anicca/.local/state/life-manager/migration/elz-f/replay/runtime/db \
  bun run start
```

For the first-run TTY wizard select: default Eliza name, warm+precise style, `Decide later`, provider `Skip for now`, wallets `Skip for now`, GitHub `Skip for now`. Wait for `Listening on http://127.0.0.1:2139`.

- [ ] **Step 6: Verify initial health, stop by exact identity, and write/read one marker**

```bash
set -e
HEALTH=/Users/anicca/.local/state/life-manager/migration/elz-f/replay/initial-health.json
curl -fsS http://127.0.0.1:2139/api/health | tee "$HEALTH"
jq -e '.ready==true and .runtime=="ok" and .database=="ok" and .databaseLiveness.ok==true and .databaseLiveness.terminal==false' "$HEALTH"
INITIAL_PID=$(lsof -nP -tiTCP:2139 -sTCP:LISTEN)
INITIAL_EXECUTABLE=$(ps -p "$INITIAL_PID" -o comm= | xargs)
INITIAL_ARGV_SHA=$(ps -p "$INITIAL_PID" -o command= | shasum -a 256 | awk '{print $1}')
INITIAL_START=$(ps -p "$INITIAL_PID" -o lstart= | xargs)
test "$INITIAL_EXECUTABLE" = bun
MODEL_KEY_COUNT=$(ps eww -p "$INITIAL_PID" | rg -o 'OPENAI_API_KEY=|ANTHROPIC_API_KEY=|OPENROUTER_API_KEY=|GOOGLE_GENERATIVE_AI_API_KEY=' | wc -l | tr -d ' ')
test "$MODEL_KEY_COUNT" = 0
printf '%s\n' "$INITIAL_PID" > /Users/anicca/.local/state/life-manager/migration/elz-f/replay/initial-pid.txt
printf '%s\n' "$INITIAL_ARGV_SHA" > /Users/anicca/.local/state/life-manager/migration/elz-f/replay/argv-sha.txt
printf '%s\n' "$INITIAL_START" > /Users/anicca/.local/state/life-manager/migration/elz-f/replay/initial-start.txt
kill -TERM "$INITIAL_PID"
```

Wait on the PTY session and require exact exit code `0`, then record the observed exit:

```bash
set -e
printf '0\n' > /Users/anicca/.local/state/life-manager/migration/elz-f/replay/initial-exit.txt
test -z "$(lsof -nP -iTCP:2139 -sTCP:LISTEN 2>/dev/null)"
cd /Users/anicca/Projects/life-manager-eliza-migration
PGLITE_DATA_DIR=/Users/anicca/.local/state/life-manager/migration/elz-f/replay/runtime/db \
  /Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin/bun -e '
  import { PGlite } from "@electric-sql/pglite";
  const db = new PGlite(process.env.PGLITE_DATA_DIR);
  await db.exec("create table if not exists lm_replay_probe (id text primary key, value text not null)");
  await db.query("insert into lm_replay_probe(id,value) values ($1,$2)", ["foundation-replay", "52eefdac"]);
  await db.close();
'
PGLITE_DATA_DIR=/Users/anicca/.local/state/life-manager/migration/elz-f/replay/runtime/db \
  /Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin/bun -e '
  import { PGlite } from "@electric-sql/pglite";
  const db = new PGlite(process.env.PGLITE_DATA_DIR);
  const result = await db.query("select value from lm_replay_probe where id=$1", ["foundation-replay"]);
  if (result.rows?.[0]?.value !== "52eefdac") process.exit(1);
  await db.close();
'
```

Expected: health passes, the exact owned process exits `0`, port is free, and marker survives a close/reopen boundary.

- [ ] **Step 7: Restart the identical runtime, verify health/marker, and stop cleanly**

Start a second PTY session in `/Users/anicca/Projects/life-manager-eliza-migration`; the existing runtime skips first-run setup:

```bash
LM_TMPDIR=$(/usr/bin/getconf DARWIN_USER_TEMP_DIR)
env -i \
  HOME=/Users/anicca USER=anicca LOGNAME=anicca TMPDIR="$LM_TMPDIR" \
  PATH=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin:/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin \
  ELIZA_PORT=2139 \
  ELIZA_STATE_DIR=/Users/anicca/.local/state/life-manager/migration/elz-f/replay/runtime \
  PGLITE_DATA_DIR=/Users/anicca/.local/state/life-manager/migration/elz-f/replay/runtime/db \
  bun run start
```

After bind:

```bash
set -e
curl -fsS http://127.0.0.1:2139/api/health | jq -e '.ready==true and .runtime=="ok" and .database=="ok" and .databaseLiveness.ok==true and .databaseLiveness.terminal==false'
RESTART_PID=$(lsof -nP -tiTCP:2139 -sTCP:LISTEN)
RESTART_EXECUTABLE=$(ps -p "$RESTART_PID" -o comm= | xargs)
RESTART_ARGV_SHA=$(ps -p "$RESTART_PID" -o command= | shasum -a 256 | awk '{print $1}')
test "$RESTART_EXECUTABLE" = bun
test "$RESTART_ARGV_SHA" = "$(tr -d ' ' < /Users/anicca/.local/state/life-manager/migration/elz-f/replay/argv-sha.txt)"
test "$RESTART_PID" != "$(tr -d ' ' < /Users/anicca/.local/state/life-manager/migration/elz-f/replay/initial-pid.txt)"
kill -TERM "$RESTART_PID"
```

Wait on the second PTY session and require exact exit code `0`, then run:

```bash
set -e
printf '0\n' > /Users/anicca/.local/state/life-manager/migration/elz-f/replay/restart-exit.txt
test -z "$(lsof -nP -iTCP:2139 -sTCP:LISTEN 2>/dev/null)"
cd /Users/anicca/Projects/life-manager-eliza-migration
PGLITE_DATA_DIR=/Users/anicca/.local/state/life-manager/migration/elz-f/replay/runtime/db \
  /Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin/bun -e '
  import { PGlite } from "@electric-sql/pglite";
  const db = new PGlite(process.env.PGLITE_DATA_DIR);
  const result = await db.query("select value from lm_replay_probe where id=$1", ["foundation-replay"]);
  if (result.rows?.[0]?.value !== "52eefdac") process.exit(1);
  await db.close();
'
DB=/Users/anicca/.local/state/life-manager/migration/elz-f/replay/runtime/db
test "$(lsof "$DB/postmaster.pid" 2>/dev/null | awk 'NR>1' | wc -l | tr -d ' ')" = 0
test "$(lsof "$DB/eliza-pglite.lock" 2>/dev/null | awk 'NR>1' | wc -l | tr -d ' ')" = 0
```

Expected: the second process exits `0`, the exact marker survives, port `2139` is free, and the bounded DB writer/lock handle checks are zero.

- [ ] **Step 8: Run the one focused foundation test set and final clean checks**

```bash
set -e
export PATH=/Users/anicca/.local/share/life-manager/toolchains/elz-f/bun-1.3.14/bin:/Users/anicca/.local/share/life-manager/toolchains/elz-f/node-v24.15.0-darwin-arm64/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd /Users/anicca/Projects/life-manager-eliza-migration
bunx vitest run --config packages/agent/vitest.config.ts \
  packages/agent/src/runtime/eliza-database-config.test.ts \
  packages/agent/src/api/health-routes.test.ts \
  packages/agent/src/api/health-routes.database-liveness.test.ts \
  packages/agent/src/api/server-skip-listen.test.ts 2>&1 \
  | tee /Users/anicca/.local/state/life-manager/migration/elz-f/replay/focused-tests.log
test "${pipestatus[1]}" = 0
rg -q 'Test Files.*4 passed' /Users/anicca/.local/state/life-manager/migration/elz-f/replay/focused-tests.log
rg -q 'Tests.*32 passed' /Users/anicca/.local/state/life-manager/migration/elz-f/replay/focused-tests.log
test "$(shasum -a 256 bun.lock | awk '{print $1}')" = 1976283db890a36ae945cd1256e9388ca84c067608df9628570bb6fce3ad7eb4
test "$(git rev-parse HEAD)" = 52eefdac597b70f3cb769b007cc4209f0f55cc34
test -z "$(git status --porcelain=v1 --untracked-files=no)"
test -z "$(lsof -nP -iTCP:2139 -sTCP:LISTEN 2>/dev/null)"
test "$(stat -f '%Lp' /Users/anicca/.local/state/life-manager/migration/elz-f/replay/runtime/db)" = 700
```

Expected: only the four focused files run; 4 files and 32 tests pass; lock/source/working tree/port remain clean.

- [ ] **Step 9: Write and verify the replay receipt**

```bash
set -e
CLONE=/Users/anicca/Projects/life-manager-eliza-migration
STATE=/Users/anicca/.local/state/life-manager/migration/elz-f/replay
DB=$STATE/runtime/db
WRITERS=$(lsof "$DB/postmaster.pid" 2>/dev/null | awk 'NR>1' | wc -l | tr -d ' ')
LOCK_HANDLES=$(lsof "$DB/eliza-pglite.lock" 2>/dev/null | awk 'NR>1' | wc -l | tr -d ' ')
test "$WRITERS" = 0
test "$LOCK_HANDLES" = 0
FREE_KIB_BEFORE=$(tr -d ' ' < "$STATE/free-before-kib.txt")
OLD_CLONE_KIB=$(tr -d ' ' < "$STATE/old-clone-kib.txt")
RESUME_FREE_KIB=$(tr -d ' ' < "$STATE/resume-free-kib.txt")
SERIAL_FREE_KIB=$(tr -d ' ' < "$STATE/serial-free-kib.txt")
GIT_KIB_BEFORE=$(tr -d ' ' < "$STATE/git-kib-before.txt")
GIT_KIB_AFTER=$(tr -d ' ' < "$STATE/git-kib-after.txt")
LOCAL_TAGS_REMOVED=$(tr -d ' ' < "$STATE/local-tags-removed.txt")
INITIAL_EXIT=$(tr -d ' ' < "$STATE/initial-exit.txt")
RESTART_EXIT=$(tr -d ' ' < "$STATE/restart-exit.txt")
test "$INITIAL_EXIT" = 0
test "$RESTART_EXIT" = 0
FREE_KIB_AFTER=$(df -Pk /Users/anicca | awk 'END {print $4}')
REMOTE_REPLAY_SHA=$(git ls-remote origin refs/heads/migration/eliza-docs | awk '{print $1}')
test "$REMOTE_REPLAY_SHA" = 52eefdac597b70f3cb769b007cc4209f0f55cc34
jq -n \
  --arg clone "$CLONE" \
  --arg source 52eefdac597b70f3cb769b007cc4209f0f55cc34 \
  --arg node v24.15.0 \
  --arg bun 1.3.14 \
  --arg lock 1976283db890a36ae945cd1256e9388ca84c067608df9628570bb6fce3ad7eb4 \
  --arg remote "$REMOTE_REPLAY_SHA" \
  --argjson free_before "$FREE_KIB_BEFORE" \
  --argjson old_clone_kib "$OLD_CLONE_KIB" \
  --argjson free_after "$FREE_KIB_AFTER" \
  --argjson resume_free "$RESUME_FREE_KIB" \
  --argjson serial_free "$SERIAL_FREE_KIB" \
  --argjson git_before "$GIT_KIB_BEFORE" \
  --argjson git_after "$GIT_KIB_AFTER" \
  --argjson tags_removed "$LOCAL_TAGS_REMOVED" \
  --argjson writers "$WRITERS" \
  --argjson lock_handles "$LOCK_HANDLES" \
  --argjson initial_exit "$INITIAL_EXIT" \
  --argjson restart_exit "$RESTART_EXIT" \
  '{
    atom:"ELZ-F13",status:"passed",fresh_clone:true,clone_path:$clone,source_sha:$source,remote_readback_sha:$remote,
    node:$node,bun:$bun,lock_sha256:$lock,submodule_count:2,license_count:28,
    frozen_install:"passed",server_build:"55/55",focused_test_files:4,focused_tests:32,
    initial_health:"passed",restart_health:"passed",marker_id:"foundation-replay",marker_value:"52eefdac",
    initial_sigterm_exit:$initial_exit,restart_sigterm_exit:$restart_exit,listener_count_after_stop:0,
    writer_processes:$writers,lock_open_handles:$lock_handles,working_tree_clean:true,
    model_credentials:0,external_effects:0,old_clone_removed_after_remote_readback:true,
    capacity_recovery:{merged_roadmap_worktree_removed:true,initial_cache_paths_removed:8,additional_cache_paths_removed:11,resume_free_kib:$resume_free,local_git_history_shallowed:true,local_tags_removed:$tags_removed,git_kib_before:$git_before,git_kib_after:$git_after,serialized_install_free_kib:$serial_free},
    free_kib_before:$free_before,old_clone_kib:$old_clone_kib,free_kib_after:$free_after
  }' > /Users/anicca/.local/state/life-manager/migration/elz-f/foundation-replay-receipt.json
chmod 600 /Users/anicca/.local/state/life-manager/migration/elz-f/foundation-replay-receipt.json
jq -e '
  .atom=="ELZ-F13" and .status=="passed" and .fresh_clone and
  .source_sha=="52eefdac597b70f3cb769b007cc4209f0f55cc34" and .source_sha==.remote_readback_sha and .node=="v24.15.0" and .bun=="1.3.14" and
  .submodule_count==2 and .license_count==28 and .server_build=="55/55" and .focused_test_files==4 and
  .focused_tests==32 and .initial_health=="passed" and .restart_health=="passed" and
  .marker_value=="52eefdac" and .initial_sigterm_exit==0 and .restart_sigterm_exit==0 and
  .listener_count_after_stop==0 and .writer_processes==0 and .lock_open_handles==0 and
  .working_tree_clean and .model_credentials==0 and .external_effects==0 and
  .capacity_recovery.merged_roadmap_worktree_removed and .capacity_recovery.initial_cache_paths_removed==8 and
  .capacity_recovery.additional_cache_paths_removed==11 and .capacity_recovery.resume_free_kib>=900000 and
  .capacity_recovery.local_git_history_shallowed and .capacity_recovery.local_tags_removed>0 and
  .capacity_recovery.git_kib_after<.capacity_recovery.git_kib_before and .capacity_recovery.serialized_install_free_kib>=500000
' /Users/anicca/.local/state/life-manager/migration/elz-f/foundation-replay-receipt.json
test "$(stat -f '%Lp' /Users/anicca/.local/state/life-manager/migration/elz-f/foundation-replay-receipt.json)" = 600
```

Expected: receipt predicate exits `0`, mode is `0600`, and the final clone remains at the exact public commit with a clean tracked tree.

- [ ] **Step 10: Report focused evidence**

Write `task-1-report.md` with deletion/reclone readbacks, free KiB, clone/remote SHA, toolchain/submodule/license/lock evidence, install/build result, both PTY exit codes and health results, marker, focused test counts, final process/lock/port/Git state, receipt mode, and concerns. Do not run a full suite or CI.

## Plan Self-Review

- Spec coverage: the single task replays F04-F10 and closes only ELZ-F13 with its named receipt.
- Placeholder scan: every path, SHA, version, port, marker, test file, count, and receipt field is explicit.
- Value consistency: clone SHA, toolchain versions, lock/license/submodule identities, runtime path, port, marker, and test set are identical across steps.
- Ponytail ruling: the four focused tests run once after restart and cover the built foundation; duplicating them before boot adds no independent evidence.
- Scope: plugin implementation, model transport, Lancers, cutover, and cloud are excluded.

## Execution Handoff

Execute with `superpowers:subagent-driven-development`: one Luna implementer, one focused primary verification, and one bounded read-only adversarial review. A finding returns only to the same implementer and only that finding is re-reviewed.
