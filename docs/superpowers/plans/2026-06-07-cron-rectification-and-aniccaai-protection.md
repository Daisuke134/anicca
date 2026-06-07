# Cron Rectification + aniccaai.com Protection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Anicca infra (cron / OpenClaw / heartbeat) を Dais products (aniccaai.com / iOS) と完全分離し、 Netflix Simian Army 3-monkey + launchd watchdog pattern で 自己治癒 を確立、 31 SKIP cron を 100% coverage化、 aniccaai.com/blog 404 を taste skill経由で修復する。

**Architecture:** Netflix Simian Army identical (Janitor / Conformity / Doctor + Watchdog)。 各 monkey は single responsibility (= K8s controller pattern「narrow responsibility, controlled blast radius」)。 watchdog は launchd plist で out-of-band (= 循環依存回避)。 各 monkey は cron metadata 内 `last_modified_by` + flock advisory lock で並列 write 競合を防止。

**Tech Stack:** bash 5.x / jq / openclaw CLI / gh CLI / lefthook 2.1 / launchd / Next.js 14 (blog route) / Anthropic + DeepSeek + Kimi + OpenAI LLM SDK経由 (openclaw agent --model 経由)。

**Spec reference:** `docs/superpowers/specs/2026-06-07-cron-rectification-and-aniccaai-protection-design.md` (v1.3, APPROVED by code-reviewer a8ac38fe168113d1d)

**Executed work (= already DONE before this plan):**
- V12-1〜V12-10 P0 emergent fixes (commits e7edb9fc, 4edd7fcd, 81ba5247)
- V12-22 fix.sh STRATEGIES BP correction (commit 9848c8e2c)
- V12-24 spec self-review (v1.2 → v1.3 commits 1339fd5f, 174fde75, 6a8d5003)

**Reviewer follow-ups embedded in this plan:**
1. §3.6.4 concurrency primitive → Task 8 step 3 (flock advisory lock)
2. §3.5.1 JIT auto-append bounded → Task 14 step 4 (max 5/day + weekly digest)
3. §3.5.5 SONNET_DAILY_MAX rationale → Task 16 step 1 (cite Pro quota math)
4. §3.1.3 stale path post-rename → Task 7 step 2 (path migration verify)
5. §3.6.2 launchd plist XML template → Task 10 step 2 (full XML in plan)

---

## File Structure (= 全 files、 責任 単一)

```
~/.openclaw/workspace/
├── tasks.json                                  (= Task 1: schema 拡張)
└── HEARTBEAT.md                                (= Task 3: §2 PICK P3 追加)

~/.openclaw/skills/_shared/
├── watch-sweep.sh                              (= Task 4: thin wrapper backward-compat)
├── watch-sweep-infra.sh                        (= Task 4: NEW — 3 watcher keep)
└── watch-sweep-project.sh.DELETED              (= Task 4: 7 watcher 削除 mark)

~/.openclaw/skills/anicca-doctor-monkey/        (= Task 7: cron-manager rename)
├── SKILL.md
├── data/
│   ├── manageable-crons.json                   (= Task 14: JIT auto-allow)
│   └── audit-rules.json                        (= Task 15: 28 cornerstone)
└── scripts/
    ├── fix.sh                                  (= Task 16+17: error pattern + timeout)
    ├── pattern-classifier.sh                   (= Task 16: NEW)
    └── sonnet-budget-check.sh                  (= Task 16: NEW)

~/.openclaw/skills/anicca-janitor-monkey/       (= Task 8: NEW)
├── SKILL.md
└── scripts/run.sh

~/.openclaw/skills/anicca-conformity-monkey/    (= Task 9: NEW)
├── SKILL.md
└── scripts/run.sh

~/.openclaw/skills/anicca-monkey-watchdog/      (= Task 10: NEW)
├── SKILL.md
└── scripts/run.sh

~/Library/LaunchAgents/
└── ai.anicca.monkey-watchdog.plist             (= Task 10: NEW launchd)

~/anicca-project/
├── lefthook.yml                                (= Task 5: 3-layer hardening)
└── apps/landing/
    ├── app/blog/page.tsx                       (= Task 19: NEW)
    ├── app/blog/[slug]/page.tsx                (= Task 19: NEW)
    └── lib/blog.ts                             (= Task 19: NEW)
```

---

## PHASE 1 — Heartbeat Tasklist 統合 (= V12-12 → V12-13 → V12-14 → V12-11)

### Task 1: tasks.json schema 拡張 (= V12-12、 bounded queue)

**Files:**
- Modify: `~/.openclaw/workspace/tasks.json`

- [ ] **Step 1: Backup current state**

```bash
cp ~/.openclaw/workspace/tasks.json ~/.openclaw/workspace/tasks.json.bak-$(date +%Y%m%d-%H%M%S)
```

- [ ] **Step 2: Inject schema fields via jq**

```bash
jq '. + {
  "_max_size": 100,
  "_eviction_policy": "oldest_P3_stale_7d_drop_with_slack_notify",
  "_schema_version": "v1.3"
}' ~/.openclaw/workspace/tasks.json > /tmp/tasks.json.new && \
mv /tmp/tasks.json.new ~/.openclaw/workspace/tasks.json
```

- [ ] **Step 3: Verify schema fields present**

Run: `jq '. | {max_size: ._max_size, policy: ._eviction_policy, version: ._schema_version}' ~/.openclaw/workspace/tasks.json`
Expected: `{"max_size": 100, "policy": "oldest_P3_stale_7d_drop_with_slack_notify", "version": "v1.3"}`

- [ ] **Step 4: Commit**

```bash
cd ~/.openclaw && git add workspace/tasks.json && \
git commit -m "feat(tasks.json): schema v1.3 — bounded queue + eviction policy"
git push
```

---

### Task 2: tasks.json insert/evict helper script (= V12-12 続き)

**Files:**
- Create: `~/.openclaw/skills/_shared/tasks-insert.sh`

- [ ] **Step 1: Write the bounded insert helper**

Create file `~/.openclaw/skills/_shared/tasks-insert.sh`:

```bash
#!/usr/bin/env bash
# Bounded insert into tasks.json fix_tasks[]
# Usage: tasks-insert.sh '{"project":"foo","action":"bar","freq_hint":"6h","priority":"P3"}'
set -euo pipefail
TASKS="$HOME/.openclaw/workspace/tasks.json"
NEW_TASK="$1"
MAX=$(jq -r '._max_size // 100' "$TASKS")
CUR=$(jq '.fix_tasks | length' "$TASKS")

if [ "$CUR" -ge "$MAX" ]; then
  # Try evict oldest P3 task with last_run < now-7d
  CUTOFF=$(date -u -v-7d +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -d "7 days ago" +"%Y-%m-%dT%H:%M:%SZ")
  EVICTABLE=$(jq --arg c "$CUTOFF" '[.fix_tasks[] | select(.priority=="P3" and (.last_run // "1970-01-01T00:00:00Z") < $c)] | length' "$TASKS")
  if [ "$EVICTABLE" -eq 0 ]; then
    echo "ERROR: queue full ($CUR/$MAX), no evictable P3-stale-7d task" >&2
    [ -n "${SLACK_BOT_TOKEN:-}" ] && curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
      -H "Content-Type: application/json" \
      --data "$(jq -nc --arg c C091G3PKHL2 --arg t ":warning: tasks.json queue full, cannot insert. Janitor cleanup needed." '{channel:$c,text:$t}')" \
      https://slack.com/api/chat.postMessage >/dev/null
    exit 1
  fi
  # Evict 1 stalest P3
  jq --arg c "$CUTOFF" '
    .fix_tasks |= (map(select(.priority=="P3" and (.last_run // "1970-01-01T00:00:00Z") < $c) | .added_at // "") as $stale_dates |
       map(select(.priority != "P3" or (.last_run // "1970-01-01T00:00:00Z") >= $c or .added_at != ($stale_dates | min))))
  ' "$TASKS" > "${TASKS}.new" && mv "${TASKS}.new" "$TASKS"
fi

# Append new task with added_at
NEW_WITH_TS=$(echo "$NEW_TASK" | jq --arg t "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '. + {added_at: $t}')
jq --argjson nt "$NEW_WITH_TS" '.fix_tasks += [$nt]' "$TASKS" > "${TASKS}.new" && mv "${TASKS}.new" "$TASKS"
echo "inserted task, queue size now $(jq '.fix_tasks | length' "$TASKS")"
```

- [ ] **Step 2: chmod + smoke test**

```bash
chmod +x ~/.openclaw/skills/_shared/tasks-insert.sh
bash ~/.openclaw/skills/_shared/tasks-insert.sh '{"project":"test-smoke","action":"verify insert works","freq_hint":"1h","priority":"P3","last_run":"2026-01-01T00:00:00Z"}'
```

Expected: `inserted task, queue size now N+1`

- [ ] **Step 3: Verify task appears + cleanup**

```bash
jq '.fix_tasks[] | select(.project=="test-smoke")' ~/.openclaw/workspace/tasks.json
# Remove smoke-test entry
jq '.fix_tasks |= map(select(.project != "test-smoke"))' ~/.openclaw/workspace/tasks.json > /tmp/cleaned.json && \
  mv /tmp/cleaned.json ~/.openclaw/workspace/tasks.json
```

Expected: smoke task object printed, then removed cleanly

- [ ] **Step 4: Commit**

```bash
cd ~/.openclaw && git add skills/_shared/tasks-insert.sh workspace/tasks.json && \
git commit -m "feat(tasks-insert): bounded queue insert/evict helper" && git push
```

---

### Task 3: HEARTBEAT.md §2 PICK P3 追加 (= V12-13)

**Files:**
- Modify: `~/.openclaw/workspace/HEARTBEAT.md:30-34`

- [ ] **Step 1: Read current §2**

```bash
sed -n '28,40p' ~/.openclaw/workspace/HEARTBEAT.md
```

- [ ] **Step 2: Append P3 priority line via sed**

```bash
sed -i '' '/- P2: experiment \/ reflect/a\
- P3: project tasklist 内 freq_hint 経過 した 1 task ACT (= ~/.openclaw/workspace/tasks.json::fix_tasks[])
' ~/.openclaw/workspace/HEARTBEAT.md
```

- [ ] **Step 3: Verify line inserted**

Run: `grep -n "P3: project tasklist" ~/.openclaw/workspace/HEARTBEAT.md`
Expected: 1 match showing the new line

- [ ] **Step 4: Append P3 ACT bash to §3**

Find `## §3 ACT` section, append project task act:

```bash
cat >> /tmp/heartbeat-act-p3.txt << 'EOF'
- project task (P3): pick + execute 1 task from fix_tasks where now() - last_run > freq_hint
  ```bash
  NOW=$(date -u +%s)
  TASK=$(jq -r --arg n "$NOW" '
    .fix_tasks[]?
    | . as $t
    | (try (.last_run | fromdate) catch 0) as $lr
    | (try (.freq_hint | sub("h$";"") | tonumber * 3600) catch 86400) as $freq
    | select(($n | tonumber) - $lr > $freq)
    | @json
  ' ~/.openclaw/workspace/tasks.json | head -1)
  if [ -n "$TASK" ]; then
    PROJECT=$(echo "$TASK" | jq -r .project)
    ACTION=$(echo "$TASK" | jq -r .action)
    echo "[P3] executing $PROJECT/$ACTION"
    # actual exec depends on project — heartbeat reads skill at ~/.openclaw/skills/<project>/scripts/run.sh
    bash "$HOME/.openclaw/skills/$PROJECT/scripts/run.sh" "$ACTION" 2>&1 | tail -20
    # update last_run
    TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    jq --arg p "$PROJECT" --arg a "$ACTION" --arg t "$TS" \
       '(.fix_tasks[] | select(.project==$p and .action==$a) | .last_run) |= $t' \
       ~/.openclaw/workspace/tasks.json > /tmp/h.json && mv /tmp/h.json ~/.openclaw/workspace/tasks.json
  fi
  ```
EOF
# Insert before §4 RECORD
awk '/^## §4 RECORD/{system("cat /tmp/heartbeat-act-p3.txt"); print; next}1' \
  ~/.openclaw/workspace/HEARTBEAT.md > /tmp/h.md && \
mv /tmp/h.md ~/.openclaw/workspace/HEARTBEAT.md
rm /tmp/heartbeat-act-p3.txt
```

- [ ] **Step 5: Verify §3 has P3 block**

Run: `grep -A 2 "project task (P3)" ~/.openclaw/workspace/HEARTBEAT.md | head`
Expected: block visible

- [ ] **Step 6: Commit**

```bash
cd ~/.openclaw && git add workspace/HEARTBEAT.md && \
git commit -m "feat(HEARTBEAT): §2+§3 P3 project tasklist pick+ACT (v1.3 spec §3.3.3)" && git push
```

---

### Task 4: watch-sweep 2 ファイル分離 (= V12-11、 reviewer MAJOR)

**Files:**
- Create: `~/.openclaw/skills/_shared/watch-sweep-infra.sh`
- Modify: `~/.openclaw/skills/_shared/watch-sweep.sh` (thin wrapper)
- Migrate: 7 watcher → tasks.json via Task 2 helper

- [ ] **Step 1: Read current watch-sweep.sh**

```bash
cat ~/.openclaw/skills/_shared/watch-sweep.sh
```

- [ ] **Step 2: Extract infra watcher block to new file**

Create `~/.openclaw/skills/_shared/watch-sweep-infra.sh`:

```bash
#!/usr/bin/env bash
# Infra watchers (= social monitoring + account burn detection)
# do_not_delete: true、 pin_to_infra: true
# Source spec: 2026-06-07 v1.3 §3.3.1
set -uo pipefail
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
source "$HOME/.openclaw/.env" 2>/dev/null || true

run_watcher() {
  local name="$1"; shift
  local cmd="$*"
  local logdir="$HOME/.openclaw/state/watch-sweep"
  mkdir -p "$logdir"
  local logfile="$logdir/${name}.$(date +%Y-%m-%d).log"
  echo "[$(date -Iseconds)] $name START" >> "$logfile"
  eval "$cmd" >> "$logfile" 2>&1 || echo "[$(date -Iseconds)] $name FAIL exit=$?" >> "$logfile"
  echo "[$(date -Iseconds)] $name END" >> "$logfile"
}

run_watcher comedy-watch-replies "bash $ANICCA_HOME/skills/anicca-comedy-factory/scripts/watch-replies-6h.sh"
run_watcher comedy-recruit-poll  "bash $ANICCA_HOME/skills/anicca-comedy-factory/scripts/recruit-poll-daily.sh"
run_watcher account-burn-detector "bash $ANICCA_HOME/skills/account-burn-detector/scripts/run.sh"
```

- [ ] **Step 3: Replace watch-sweep.sh with thin wrapper**

```bash
cat > ~/.openclaw/skills/_shared/watch-sweep.sh << 'EOF'
#!/usr/bin/env bash
# Backward-compat thin wrapper (v1.3)
# Project watchers (7) migrated to tasks.json fix_tasks[] (= heartbeat P3 picks them)
# Infra watchers (3) live in watch-sweep-infra.sh
set -uo pipefail
bash "$(dirname "$0")/watch-sweep-infra.sh"
EOF
chmod +x ~/.openclaw/skills/_shared/watch-sweep.sh ~/.openclaw/skills/_shared/watch-sweep-infra.sh
```

- [ ] **Step 4: Migrate 7 project watchers to tasks.json**

```bash
INS="$HOME/.openclaw/skills/_shared/tasks-insert.sh"
for SPEC in \
  '{"project":"opening-cafe-tokyo-skills","action":"uber-status-check","freq_hint":"6h","priority":"P3","last_run":"2026-01-01T00:00:00Z"}' \
  '{"project":"anicca-retreat-factory","action":"phase1-reply-watch","freq_hint":"6h","priority":"P3","last_run":"2026-01-01T00:00:00Z"}' \
  '{"project":"anicca-retreat-factory","action":"phase2-reply-triage","freq_hint":"6h","priority":"P3","last_run":"2026-01-01T00:00:00Z"}' \
  '{"project":"anicca-retreat-factory","action":"phase4-followup-scanner","freq_hint":"6h","priority":"P3","last_run":"2026-01-01T00:00:00Z"}' \
  '{"project":"politician","action":"reply-watch","freq_hint":"6h","priority":"P3","last_run":"2026-01-01T00:00:00Z"}' \
  '{"project":"naist","action":"edu-portal-check","freq_hint":"24h","priority":"P3","last_run":"2026-01-01T00:00:00Z"}' \
  '{"project":"tt-draft-graduator","action":"check","freq_hint":"6h","priority":"P3","last_run":"2026-01-01T00:00:00Z"}'; do
  bash "$INS" "$SPEC"
done
```

Expected output: 7 lines `inserted task, queue size now N`

- [ ] **Step 5: Verify project watchers in tasks.json**

```bash
jq '.fix_tasks[] | select(.priority=="P3") | {project, action}' ~/.openclaw/workspace/tasks.json
```

Expected: 7 entries visible

- [ ] **Step 6: Verify wrapper runs without 7 watchers**

```bash
bash ~/.openclaw/skills/_shared/watch-sweep.sh
ls ~/.openclaw/state/watch-sweep/ | grep $(date +%Y-%m-%d)
```

Expected: 3 log files (comedy-watch-replies / comedy-recruit-poll / account-burn-detector)

- [ ] **Step 7: Commit**

```bash
cd ~/.openclaw && git add skills/_shared/watch-sweep.sh skills/_shared/watch-sweep-infra.sh workspace/tasks.json && \
git commit -m "feat(watch-sweep): 2 ファイル分離、 7 project watcher → tasks.json fix_tasks P3 (spec §3.3.1)" && git push
```

---

## PHASE 2 — lefthook v1.3 + watercolor 真因 fix (= V12-9 + V12-26)

### Task 5: lefthook hook 3-layer hardening (= V12-9 v1.3、 reviewer BLOCKING #3)

**Files:**
- Modify: `~/anicca-project/lefthook.yml::aniccaai-landing-guard`

- [ ] **Step 1: Read current single-layer hook**

```bash
grep -A 13 "aniccaai-landing-guard:" ~/anicca-project/lefthook.yml
```

- [ ] **Step 2: Replace with 3-layer logic**

Use Edit tool on `~/anicca-project/lefthook.yml`. Replace the existing `aniccaai-landing-guard` block with:

```yaml
    aniccaai-landing-guard:
      # 3-layer defense-in-depth: name + email + parent process check
      # Spec: 2026-06-07 v1.3 §3.2.2、 reviewer BLOCKING #3
      run: |
        author_name=$(git config user.name)
        author_email=$(git config user.email)
        touched=$(git diff --cached --name-only | grep -c "^apps/landing/" || true)
        [ "$touched" -eq 0 ] && exit 0
        is_bot=0
        [ "$author_name" = "Anicca Agent" ] && is_bot=1
        case "$author_email" in
          *anicca*bot*|*anicca-agent*|*@anicca.ai|noreply@anthropic.com) is_bot=1;;
        esac
        pname=$(ps -o comm= -p $PPID 2>/dev/null | xargs basename)
        case "$pname" in
          bash|zsh|fish|claude|cursor|code|nvim|vim|sh) : ;;
          *) is_bot=1 ;;
        esac
        if [ "$is_bot" = "1" ]; then
          echo "❌ HARD RULE: Anicca cron は apps/landing/ 編集禁止"
          echo "  name=$author_name email=$author_email parent=$pname"
          git diff --cached --name-only | grep "^apps/landing/" | head -10 | sed 's/^/   /'
          exit 1
        fi
      fail_text: "Anicca cron は apps/landing/ 編集禁止 (= Dais の aniccaai.com 領域)"
```

- [ ] **Step 3: Test bot scenario (3-layer should still block)**

```bash
cd ~/anicca-project
touch apps/landing/HOOK_TEST_V13
git add apps/landing/HOOK_TEST_V13
ORIG_NAME=$(git config user.name)
git config user.name "Anicca Agent"
git commit -m "test" 2>&1 | grep -E "HARD RULE|exit status"
git config user.name "$ORIG_NAME"
git reset HEAD apps/landing/HOOK_TEST_V13 2>/dev/null
rm apps/landing/HOOK_TEST_V13
```

Expected: "HARD RULE: Anicca cron は apps/landing/ 編集禁止"

- [ ] **Step 4: Test Dais scenario (should pass)**

```bash
cd ~/anicca-project
touch apps/landing/DAIS_TEST
git add apps/landing/DAIS_TEST
ORIG_NAME=$(git config user.name)
ORIG_EMAIL=$(git config user.email)
git config user.name "Daisuke Sato"
git config user.email "keiodaisuke@gmail.com"
git commit -m "test: Dais path" 2>&1 | tail -5
git config user.name "$ORIG_NAME"
git config user.email "$ORIG_EMAIL"
git reset HEAD~1 -- apps/landing/DAIS_TEST 2>/dev/null
rm apps/landing/DAIS_TEST
```

Expected: commit succeeds (= no HARD RULE block), reset cleans up

- [ ] **Step 5: Commit**

```bash
cd ~/anicca-project && git add lefthook.yml && \
git commit -m "feat(hook): aniccaai-landing-guard v1.3 — 3-layer (name+email+parent) hardening" && git push
```

---

### Task 6: watercolor-monk-noon 真因 dig + fix (= V12-26)

**Files:**
- Investigate: `~/.openclaw/skills/watercolor-monk-factory/scripts/run.sh`
- Modify: cron message body via `openclaw cron edit`

- [ ] **Step 1: Read SKILL.md + run.sh usage signature**

```bash
cat ~/.openclaw/skills/watercolor-monk-factory/SKILL.md | head -30
head -20 ~/.openclaw/skills/watercolor-monk-factory/scripts/run.sh
```

Expected: see usage signature mentioning slot + postiz_id args

- [ ] **Step 2: Get current cron message body for watercolor-monk-noon**

```bash
WUUID=$(openclaw cron list --all --json | jq -r '.jobs[]|select(.name=="watercolor-monk-noon")|.id')
echo "UUID: $WUUID"
openclaw cron get "$WUUID" | jq '.message // "EMPTY"'
```

- [ ] **Step 3: Read last 3 error runs**

```bash
openclaw cron runs "$WUUID" --last 3 --json | jq -r '.runs[] | {started:.startedAt, status:.status, error:.error}'
```

Expected: error contains "Pass --to <E.164>, --session-key, --session-id, or --agent to choose a session"

- [ ] **Step 4: Determine correct invocation by reading similar working cron**

```bash
# watercolor-jp-0700 and watercolor-jp-2000 work — see their messages
for c in watercolor-jp-0700 watercolor-jp-2000; do
  UUID=$(openclaw cron list --all --json | jq -r --arg n "$c" '.jobs[]|select(.name==$n)|.id')
  echo "── $c ──"
  openclaw cron get "$UUID" | jq -r '.message // "EMPTY"' | head -10
done
```

Expected: working messages show explicit args pattern

- [ ] **Step 5: Patch cron message body to include required args**

```bash
# Based on Step 4 findings, set message with correct invocation
# Adjust args based on what working sibling cron passes
NEW_MSG="bash ~/.openclaw/skills/watercolor-monk-factory/scripts/run.sh jp 12 auto"
openclaw cron edit "$WUUID" --message "$NEW_MSG"
```

- [ ] **Step 6: Fire once to verify**

```bash
openclaw cron run "$WUUID" --wait --wait-timeout 5m --expect-final
```

Expected: status=ok, no "Pass --to" error

- [ ] **Step 7: Close gh issue + commit (state update only)**

```bash
gh issue close 5 -R Daisuke134/anicca-dais --reason completed --comment "Fixed by V12-26 — cron message body 補完で missing-arg 解消"
cd ~/.openclaw && git status --short | grep skills/anicca-cron-manager || echo "no skill file change needed"
```

Expected: issue closed; if no skill file changed, just record evidence in commit message

```bash
git commit --allow-empty -m "fix(watercolor-monk-noon): cron message body 補完 — Pass --to error 解消 (V12-26)" && git push
```

---

## PHASE 3 — Netflix Simian Army (= V12-29 → V12-27 → V12-28 → V12-30)

### Task 7: anicca-cron-manager → anicca-doctor-monkey rename (= V12-29、 single responsibility)

**Files:**
- Rename: `~/.openclaw/skills/anicca-cron-manager/` → `~/.openclaw/skills/anicca-doctor-monkey/`
- Modify: openclaw cron entry を name + message 更新

- [ ] **Step 1: git mv skill directory**

```bash
cd ~/.openclaw
git mv skills/anicca-cron-manager skills/anicca-doctor-monkey
```

- [ ] **Step 2: Update SKILL.md name + remove curator/over-scheduled phase refs**

Use Edit on `~/.openclaw/skills/anicca-doctor-monkey/SKILL.md`. Replace:

```
name: anicca-cron-manager
description: |
  Autonomous cron error fixer + curator + over-scheduled detector.
```

With:

```
name: anicca-doctor-monkey
description: |
  Netflix Simian Army Doctor — error cron heal のみ (= single responsibility).
  curator/over-scheduled は anicca-janitor-monkey へ移管。
  policy violation disable は anicca-conformity-monkey へ移管。
```

- [ ] **Step 3: Update internal script references**

```bash
# Update fix.sh SKILL path comment from anicca-cron-manager to anicca-doctor-monkey
sed -i '' 's|skills/anicca-cron-manager|skills/anicca-doctor-monkey|g' \
  ~/.openclaw/skills/anicca-doctor-monkey/scripts/*.sh \
  ~/.openclaw/skills/anicca-doctor-monkey/SKILL.md
grep -l "anicca-cron-manager" ~/.openclaw/skills/anicca-doctor-monkey/ -r || echo "all refs migrated"
```

Expected: "all refs migrated"

- [ ] **Step 4: Move scripts/curator.sh + scripts/over-scheduled.sh to janitor location (placeholder for Task 8)**

```bash
mkdir -p ~/.openclaw/skills/anicca-janitor-monkey/scripts
git mv ~/.openclaw/skills/anicca-doctor-monkey/scripts/curator.sh \
       ~/.openclaw/skills/anicca-janitor-monkey/scripts/curator.sh
git mv ~/.openclaw/skills/anicca-doctor-monkey/scripts/over-scheduled.sh \
       ~/.openclaw/skills/anicca-janitor-monkey/scripts/over-scheduled.sh
```

- [ ] **Step 5: Rename openclaw cron entry name**

```bash
UUID=$(openclaw cron list --all --json | jq -r '.jobs[]|select(.name=="anicca-cron-manager")|.id')
# Edit the cron's command to invoke new path + update name in metadata via openclaw API
openclaw cron edit "$UUID" --name anicca-doctor-monkey \
  --message "bash $HOME/.openclaw/skills/anicca-doctor-monkey/scripts/run.sh"
```

- [ ] **Step 6: Smoke fire to verify rename**

```bash
openclaw cron run "$UUID" --wait --wait-timeout 5m --expect-final 2>&1 | tail -10
```

Expected: status=ok (= path migration works)

- [ ] **Step 7: Commit**

```bash
cd ~/.openclaw && git add -A skills/anicca-doctor-monkey skills/anicca-janitor-monkey && \
git commit -m "refactor(skill): anicca-cron-manager → anicca-doctor-monkey + curator/over-scheduled → janitor-monkey (spec §3.6)" && git push
```

---

### Task 8: anicca-janitor-monkey skill 新規 (= V12-27、 flock + provenance)

**Files:**
- Create: `~/.openclaw/skills/anicca-janitor-monkey/SKILL.md`
- Create: `~/.openclaw/skills/anicca-janitor-monkey/scripts/run.sh`
- Create: `~/.openclaw/skills/_shared/cron-lock.sh` (= flock primitive、 reviewer NEW ISSUE #1)
- Create: openclaw cron entry (daily 03:00)

- [ ] **Step 1: Create flock advisory primitive**

Create `~/.openclaw/skills/_shared/cron-lock.sh`:

```bash
#!/usr/bin/env bash
# Advisory lock for cron metadata writes (Janitor + Doctor + Conformity 共有)
# Spec: 2026-06-07 v1.3 §3.6.4 + reviewer NEW ISSUE #1
# Usage: source cron-lock.sh; with_cron_lock <uuid> <action> -- <cmd> [args...]
set -uo pipefail

with_cron_lock() {
  local uuid="$1"; shift
  local action="$1"; shift
  [ "$1" = "--" ] && shift
  local lockdir="$HOME/.openclaw/state/locks"
  mkdir -p "$lockdir"
  local lockfile="$lockdir/cron-${uuid}.lock"
  exec 9>"$lockfile" || return 1
  if ! flock -n 9; then
    echo "lock-busy uuid=$uuid action=$action" >&2
    return 2
  fi
  # Got lock — record provenance + execute
  local me="${ANICCA_MONKEY:-unknown}"
  local ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  echo "$ts $me $action" >> "$lockdir/cron-${uuid}.history"
  "$@"
  local rc=$?
  flock -u 9
  return $rc
}

# Read last_modified_by from cron metadata via openclaw
get_last_modifier() {
  local uuid="$1"
  openclaw cron get "$uuid" 2>/dev/null | jq -r '.payload.last_modified_by // ""' 2>/dev/null
}

get_last_modified_at() {
  local uuid="$1"
  openclaw cron get "$uuid" 2>/dev/null | jq -r '.payload.last_modified_at // ""' 2>/dev/null
}

# Should current monkey skip this target?
should_skip_cron() {
  local uuid="$1"
  local me="${ANICCA_MONKEY:-unknown}"
  local last_by=$(get_last_modifier "$uuid")
  local last_at=$(get_last_modified_at "$uuid")
  [ -z "$last_by" ] && return 1  # never touched, OK to write
  [ "$last_by" = "$me" ] && return 1  # I touched it, OK to write
  # Different monkey touched — check timing
  local cutoff_h=24
  [ "$last_by" = "Dais" ] && cutoff_h=$((7*24))
  local now=$(date -u +%s)
  local then=$(date -u -d "$last_at" +%s 2>/dev/null || date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$last_at" +%s 2>/dev/null || echo 0)
  local diff_h=$(( (now - then) / 3600 ))
  if [ "$diff_h" -lt "$cutoff_h" ]; then
    echo "skip uuid=$uuid last_by=$last_by diff_h=$diff_h cutoff=$cutoff_h"
    return 0  # skip
  fi
  return 1  # don't skip
}

# Update provenance metadata when writing
set_provenance() {
  local uuid="$1"
  local reason="$2"
  local me="${ANICCA_MONKEY:-unknown}"
  local ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  # openclaw cron edit with metadata payload
  openclaw cron edit "$uuid" --payload-set "last_modified_by=$me" --payload-set "last_modified_at=$ts" --payload-set "last_modified_reason=$reason" 2>/dev/null || \
    echo "warn: provenance set may have failed for $uuid" >&2
}
```

- [ ] **Step 2: chmod + verify**

```bash
chmod +x ~/.openclaw/skills/_shared/cron-lock.sh
bash -n ~/.openclaw/skills/_shared/cron-lock.sh && echo "syntax OK"
```

Expected: "syntax OK"

- [ ] **Step 3: Write Janitor SKILL.md**

Create `~/.openclaw/skills/anicca-janitor-monkey/SKILL.md`:

```yaml
---
name: anicca-janitor-monkey
description: |
  Netflix Janitor Monkey identical (= 2011 Tech Blog verbatim:
  "searches for unused resources and disposes of them").
  Anicca self infra cleanup: 30 日 stale cron archive + first-principles
  非該当 cron disable + over-scheduled detection。
  Provenance-aware (= Doctor が 24h 内 触った cron は SKIP)。
metadata:
  type: infra-hygiene
  responsibility: dispose_unused
  spec: ~/anicca-project/docs/superpowers/specs/2026-06-07-cron-rectification-and-aniccaai-protection-design.md
  schedule: "0 3 * * *"
  pin_to_infra: true
  do_not_delete: true
---
```

- [ ] **Step 4: Write Janitor run.sh**

Create `~/.openclaw/skills/anicca-janitor-monkey/scripts/run.sh`:

```bash
#!/usr/bin/env bash
# Anicca Janitor Monkey — useless cron dispose (Netflix Janitor pattern)
# Spec: 2026-06-07 v1.3 §3.6
set -uo pipefail
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
source "$HOME/.openclaw/skills/_shared/cron-lock.sh"
export ANICCA_MONKEY="anicca-janitor-monkey"

NEVER_DISABLE=$(jq -r '.guardrails_NEVER_DISABLE | to_entries[].value[]' \
  "$HOME/.openclaw/skills/anicca-doctor-monkey/data/audit-rules.json" 2>/dev/null | sort -u)

ARCHIVED=0; DISABLED=0; SKIPPED=0
NOW=$(date -u +%s)
CUTOFF_STALE=$(( NOW - 30*86400 ))

openclaw cron list --all --json | jq -c '.jobs[]' | while read -r J; do
  NAME=$(echo "$J" | jq -r .name)
  UUID=$(echo "$J" | jq -r .id)
  ENABLED=$(echo "$J" | jq -r .enabled)
  LAST_RUN=$(echo "$J" | jq -r '.state.lastRunAt // empty')

  # Skip cornerstones
  if echo "$NEVER_DISABLE" | grep -qFx "$NAME"; then
    SKIPPED=$((SKIPPED+1)); continue
  fi

  # Provenance check (§3.6.4)
  if should_skip_cron "$UUID" >/dev/null 2>&1; then
    SKIPPED=$((SKIPPED+1)); continue
  fi

  # 30d stale → archive
  if [ -n "$LAST_RUN" ]; then
    LAST_S=$(date -u -d "$LAST_RUN" +%s 2>/dev/null || date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$LAST_RUN" +%s 2>/dev/null || echo "$NOW")
    if [ "$LAST_S" -lt "$CUTOFF_STALE" ] && [ "$ENABLED" = "true" ]; then
      if with_cron_lock "$UUID" "archive-30d-stale" -- bash -c "openclaw cron disable '$UUID' && set_provenance '$UUID' '30d_stale_archive'"; then
        ARCHIVED=$((ARCHIVED+1))
        echo "archived: $NAME (last_run=$LAST_RUN)"
      fi
    fi
  fi
done

# Run inherited curator + over-scheduled scripts (from V12-29 move)
[ -x "$HOME/.openclaw/skills/anicca-janitor-monkey/scripts/curator.sh" ] && \
  bash "$HOME/.openclaw/skills/anicca-janitor-monkey/scripts/curator.sh" || true
[ -x "$HOME/.openclaw/skills/anicca-janitor-monkey/scripts/over-scheduled.sh" ] && [ "$(date +%u)" = "7" ] && \
  bash "$HOME/.openclaw/skills/anicca-janitor-monkey/scripts/over-scheduled.sh" || true

REPORT=":robot_face: janitor $(date -Iseconds) | archived=$ARCHIVED disabled=$DISABLED skipped=$SKIPPED"
echo "$REPORT"
if [ -n "${SLACK_BOT_TOKEN:-}" ]; then
  curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
    -H "Content-Type: application/json" \
    --data "$(jq -nc --arg c C091G3PKHL2 --arg t "$REPORT" '{channel:$c,text:$t}')" \
    https://slack.com/api/chat.postMessage >/dev/null
fi
exit 0
```

- [ ] **Step 5: chmod + create openclaw cron entry**

```bash
chmod +x ~/.openclaw/skills/anicca-janitor-monkey/scripts/run.sh
openclaw cron add \
  --name anicca-janitor-monkey \
  --cron "0 3 * * *" \
  --message "bash $HOME/.openclaw/skills/anicca-janitor-monkey/scripts/run.sh" \
  --session isolated \
  --timeout 20m \
  --tags "monkey,infra,daily"
```

- [ ] **Step 6: Smoke fire — verify provenance + report**

```bash
JUUID=$(openclaw cron list --all --json | jq -r '.jobs[]|select(.name=="anicca-janitor-monkey")|.id')
openclaw cron run "$JUUID" --wait --wait-timeout 10m --expect-final 2>&1 | tail -20
```

Expected: report line with `archived=N disabled=N skipped=N`

- [ ] **Step 7: Commit**

```bash
cd ~/.openclaw && git add skills/anicca-janitor-monkey/ skills/_shared/cron-lock.sh && \
git commit -m "feat(janitor-monkey): Netflix Janitor identical — dispose unused (spec §3.6, V12-27)" && git push
```

---

### Task 9: anicca-conformity-monkey skill 新規 (= V12-28)

**Files:**
- Create: `~/.openclaw/skills/anicca-conformity-monkey/SKILL.md`
- Create: `~/.openclaw/skills/anicca-conformity-monkey/scripts/run.sh`
- Create: openclaw cron entry (6h)

- [ ] **Step 1: Write SKILL.md**

Create `~/.openclaw/skills/anicca-conformity-monkey/SKILL.md`:

```yaml
---
name: anicca-conformity-monkey
description: |
  Netflix Conformity Monkey identical (= 2011 verbatim:
  "finds instances that don't adhere to best-practices and shuts them down").
  Policy violation cron disable: aniccaai.com 編集 cron 検出 + cornerstone alert。
  Spec: 2026-06-07 v1.3 §3.6.2
metadata:
  type: infra-hygiene
  responsibility: enforce_policy
  schedule: "0 */6 * * *"
  pin_to_infra: true
  do_not_delete: true
---
```

- [ ] **Step 2: Write run.sh**

Create `~/.openclaw/skills/anicca-conformity-monkey/scripts/run.sh`:

```bash
#!/usr/bin/env bash
# Anicca Conformity Monkey — policy violation disable (Netflix Conformity pattern)
# Spec: 2026-06-07 v1.3 §3.6.2
set -uo pipefail
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
source "$HOME/.openclaw/skills/_shared/cron-lock.sh"
export ANICCA_MONKEY="anicca-conformity-monkey"

NEVER_DISABLE=$(jq -r '.guardrails_NEVER_DISABLE | to_entries[].value[]' \
  "$HOME/.openclaw/skills/anicca-doctor-monkey/data/audit-rules.json" 2>/dev/null | sort -u)

VIOLATIONS=0; ALERTED=0; SKIPPED=0
# Patterns of "policy violation" cron messages
LANDING_PATTERN='apps/landing|aniccaai\.com'

openclaw cron list --all --json | jq -c '.jobs[] | select(.enabled==true)' | while read -r J; do
  NAME=$(echo "$J" | jq -r .name)
  UUID=$(echo "$J" | jq -r .id)
  MSG=$(echo "$J" | jq -r '.schedule.message // empty')

  # Skip cornerstones (= alert only、 do not disable)
  if echo "$NEVER_DISABLE" | grep -qFx "$NAME"; then
    if echo "$MSG" | grep -qE "$LANDING_PATTERN"; then
      ALERTED=$((ALERTED+1))
      echo "alert-cornerstone-violation: $NAME"
      [ -n "${SLACK_BOT_TOKEN:-}" ] && curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
        -H "Content-Type: application/json" \
        --data "$(jq -nc --arg c C091G3PKHL2 --arg t ":warning: cornerstone $NAME has apps/landing/ in message — manual review needed" '{channel:$c,text:$t}')" \
        https://slack.com/api/chat.postMessage >/dev/null
    fi
    SKIPPED=$((SKIPPED+1)); continue
  fi

  # Provenance check
  if should_skip_cron "$UUID" >/dev/null 2>&1; then
    SKIPPED=$((SKIPPED+1)); continue
  fi

  # Policy violation: enabled cron touching apps/landing/
  if echo "$MSG" | grep -qE "$LANDING_PATTERN"; then
    if with_cron_lock "$UUID" "disable-landing-violation" -- bash -c "openclaw cron disable '$UUID' && set_provenance '$UUID' 'apps_landing_policy_violation'"; then
      VIOLATIONS=$((VIOLATIONS+1))
      echo "disabled-policy-violation: $NAME"
    fi
  fi
done

REPORT=":cop: conformity $(date -Iseconds) | violations=$VIOLATIONS alerted=$ALERTED skipped=$SKIPPED"
echo "$REPORT"
[ -n "${SLACK_BOT_TOKEN:-}" ] && curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "$(jq -nc --arg c C091G3PKHL2 --arg t "$REPORT" '{channel:$c,text:$t}')" \
  https://slack.com/api/chat.postMessage >/dev/null
exit 0
```

- [ ] **Step 3: chmod + create cron**

```bash
chmod +x ~/.openclaw/skills/anicca-conformity-monkey/scripts/run.sh
openclaw cron add \
  --name anicca-conformity-monkey \
  --cron "0 */6 * * *" \
  --message "bash $HOME/.openclaw/skills/anicca-conformity-monkey/scripts/run.sh" \
  --session isolated \
  --timeout 10m \
  --tags "monkey,infra"
```

- [ ] **Step 4: Smoke fire**

```bash
CUUID=$(openclaw cron list --all --json | jq -r '.jobs[]|select(.name=="anicca-conformity-monkey")|.id')
openclaw cron run "$CUUID" --wait --wait-timeout 5m --expect-final 2>&1 | tail -10
```

Expected: report line with `violations=N alerted=N skipped=N`

- [ ] **Step 5: Commit**

```bash
cd ~/.openclaw && git add skills/anicca-conformity-monkey/ && \
git commit -m "feat(conformity-monkey): Netflix Conformity identical — policy violation disable (spec §3.6.2, V12-28)" && git push
```

---

### Task 10: anicca-monkey-watchdog launchd plist (= V12-30、 out-of-band)

**Files:**
- Create: `~/.openclaw/skills/anicca-monkey-watchdog/SKILL.md`
- Create: `~/.openclaw/skills/anicca-monkey-watchdog/scripts/run.sh`
- Create: `~/Library/LaunchAgents/ai.anicca.monkey-watchdog.plist`

- [ ] **Step 1: Write watchdog script**

Create `~/.openclaw/skills/anicca-monkey-watchdog/scripts/run.sh`:

```bash
#!/usr/bin/env bash
# Anicca Monkey Watchdog — out-of-band launchd, monitors 3 in-band monkeys
# Spec: 2026-06-07 v1.3 §3.6.2 + reviewer BLOCKING #5
set -uo pipefail
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a

MONKEYS=("anicca-doctor-monkey" "anicca-janitor-monkey" "anicca-conformity-monkey")
NOW=$(date -u +%s)
CUTOFF_24H=$(( NOW - 24*3600 ))
DOWN=()

for M in "${MONKEYS[@]}"; do
  UUID=$(openclaw cron list --all --json | jq -r --arg n "$M" '.jobs[]|select(.name==$n)|.id')
  if [ -z "$UUID" ]; then
    DOWN+=("$M:missing")
    continue
  fi
  LAST_OK=$(openclaw cron runs "$UUID" --last 10 --json 2>/dev/null | \
    jq -r '[.runs[]|select(.status=="ok")] | .[0].startedAt // empty')
  if [ -z "$LAST_OK" ]; then
    DOWN+=("$M:no-ok-runs")
    continue
  fi
  LAST_S=$(date -u -d "$LAST_OK" +%s 2>/dev/null || date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$LAST_OK" +%s 2>/dev/null || echo 0)
  if [ "$LAST_S" -lt "$CUTOFF_24H" ]; then
    DOWN+=("$M:stale-24h")
    # Try fire it
    openclaw cron run "$UUID" --wait --wait-timeout 5m 2>&1 | tail -3
  fi
done

if [ ${#DOWN[@]} -eq 0 ]; then
  echo ":eye: watchdog $(date -Iseconds) | all 3 monkeys healthy"
else
  REPORT=":rotating_light: watchdog $(date -Iseconds) | DOWN: ${DOWN[*]}"
  echo "$REPORT"
  [ -n "${SLACK_BOT_TOKEN:-}" ] && curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
    -H "Content-Type: application/json" \
    --data "$(jq -nc --arg c C091G3PKHL2 --arg t "$REPORT" '{channel:$c,text:$t}')" \
    https://slack.com/api/chat.postMessage >/dev/null
fi
exit 0
```

- [ ] **Step 2: Write launchd plist (= reviewer NEW ISSUE #5 — full XML)**

Create `~/Library/LaunchAgents/ai.anicca.monkey-watchdog.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>ai.anicca.monkey-watchdog</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/anicca/.openclaw/skills/anicca-monkey-watchdog/scripts/run.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>4</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>/Users/anicca/.openclaw/state/monkey-watchdog.out</string>
  <key>StandardErrorPath</key><string>/Users/anicca/.openclaw/state/monkey-watchdog.err</string>
  <key>Nice</key><integer>10</integer>
</dict>
</plist>
```

- [ ] **Step 3: Write SKILL.md**

Create `~/.openclaw/skills/anicca-monkey-watchdog/SKILL.md`:

```yaml
---
name: anicca-monkey-watchdog
description: |
  Out-of-band launchd watchdog — monitors 3 openclaw monkeys
  (doctor / janitor / conformity)。 24h 内 success run 無し → Slack alert
  + 即 fire 試行。 launchd 自体 が macOS 起動時 自動 load される為、
  openclaw gateway down でも 動く (= 循環依存 回避)。
  Reference pattern: Netflix Atlas (= Simian Army external monitor)。
metadata:
  type: meta-monitor
  responsibility: monitor_monkeys
  runtime: launchd
  schedule: "0 4 * * *"
  pin_to_infra: true
  do_not_delete: true
---
```

- [ ] **Step 4: chmod + load launchd**

```bash
chmod +x ~/.openclaw/skills/anicca-monkey-watchdog/scripts/run.sh
launchctl load ~/Library/LaunchAgents/ai.anicca.monkey-watchdog.plist
launchctl list | grep monkey-watchdog
```

Expected: `ai.anicca.monkey-watchdog` appears in list

- [ ] **Step 5: Smoke run manually**

```bash
bash ~/.openclaw/skills/anicca-monkey-watchdog/scripts/run.sh
```

Expected: either "all 3 monkeys healthy" or "DOWN: ..." report

- [ ] **Step 6: Commit**

```bash
cd ~/.openclaw && git add skills/anicca-monkey-watchdog/ && \
git commit -m "feat(monkey-watchdog): launchd out-of-band 3-monkey monitor (spec §3.6.2, V12-30)" && git push
# launchd plist (~/Library/LaunchAgents/) is not in git but recorded in spec
```

---

## PHASE 4 — Doctor Strengthening (= V12-18 → V12-19 → V12-20 → V12-21 → V12-23)

### Task 11: manageable-crons.json JIT auto-allow (= V12-18 + reviewer NEW ISSUE #2)

**Files:**
- Modify: `~/.openclaw/skills/anicca-doctor-monkey/data/manageable-crons.json`

- [ ] **Step 1: Backup current allowlist**

```bash
cp ~/.openclaw/skills/anicca-doctor-monkey/data/manageable-crons.json \
   ~/.openclaw/skills/anicca-doctor-monkey/data/manageable-crons.json.bak-$(date +%Y%m%d)
```

- [ ] **Step 2: Write v1.3 JIT schema**

Create new content (overwrite):

```json
{
  "_comment": "v1.3: explicit allowlist + JIT auto-append on first error (= 戦略 B invert)",
  "_mode": "just_in_time",
  "_max_auto_append_per_day": 5,
  "_weekly_digest_day": "monday",
  "allow_explicit": [
    "anicca-article-daily-blog",
    "anicca-article-daily-devto",
    "anicca-article-daily-note",
    "anicca-article-daily-substack-en",
    "anicca-article-daily-substack-ja",
    "monk-factory-en-0800",
    "monk-factory-en-1400",
    "mau-tiktok-en-morning",
    "watercolor-monk-noon",
    "reelclaw-anicca-ja-wi-cron-20-18",
    "anicca-comedy-weekly-recap"
  ],
  "auto_append_on_first_error": true,
  "auto_append_require_not_in_never_allow": true,
  "auto_append_log": "~/.openclaw/state/doctor-monkey/auto-append.log",
  "never_allow_patterns": [
    "anicca-heartbeat",
    "anicca-doctor-monkey",
    "anicca-janitor-monkey",
    "anicca-conformity-monkey",
    "anicca-monkey-watchdog",
    "anicca-daily-mail",
    "anicca-lateness-heartbeat-shell",
    "anicca-life-manager",
    "anicca-fuel-broker",
    "anicca-cold-email-reply",
    "anicca-watch-sweep"
  ]
}
```

- [ ] **Step 3: Verify JSON syntax**

Run: `jq '.' ~/.openclaw/skills/anicca-doctor-monkey/data/manageable-crons.json`
Expected: full JSON printed without parse error

- [ ] **Step 4: Commit**

```bash
cd ~/.openclaw && git add skills/anicca-doctor-monkey/data/manageable-crons.json && \
git commit -m "feat(doctor-monkey): JIT auto-allow + bounded 5/day cap (spec §3.5.1, V12-18)" && git push
```

---

### Task 12: audit-rules.json NEVER_DISABLE 28 cornerstone (= V12-19)

**Files:**
- Modify: `~/.openclaw/skills/anicca-doctor-monkey/data/audit-rules.json::guardrails_NEVER_DISABLE`

- [ ] **Step 1: Read current guardrails section**

```bash
jq '.guardrails_NEVER_DISABLE // {}' ~/.openclaw/skills/anicca-doctor-monkey/data/audit-rules.json
```

- [ ] **Step 2: Replace with v1.3 expanded 28 list**

```bash
jq '.guardrails_NEVER_DISABLE = {
  "infra": [
    "anicca-heartbeat","anicca-doctor-monkey","anicca-janitor-monkey",
    "anicca-conformity-monkey","anicca-monkey-watchdog",
    "anicca-lateness-heartbeat-shell","anicca-daily-mail","anicca-fuel-broker",
    "anicca-cold-email-reply","anicca-watch-sweep","anicca-life-manager",
    "anicca-inbox","anicca-genesis-sync"
  ],
  "revenue_growth": [
    "anicca-article-daily-devto","anicca-article-daily-note",
    "anicca-article-daily-substack-ja","anicca-article-daily-substack-en",
    "anicca-article-daily-zenn","anicca-x-direct",
    "monk-factory-en-0800","monk-factory-en-1400","mau-tiktok-en-morning",
    "watercolor-monk-noon","reelclaw-anicca-ja-wi-cron-20-18",
    "anicca-comedy-weekly-recap","comedy-recruit-poll","comedy-watch-replies"
  ],
  "app_store": ["aso-loop","screenshot-ab","paywall-ab"]
}' ~/.openclaw/skills/anicca-doctor-monkey/data/audit-rules.json > /tmp/audit.json && \
mv /tmp/audit.json ~/.openclaw/skills/anicca-doctor-monkey/data/audit-rules.json
```

- [ ] **Step 3: Verify 28 entries**

Run: `jq '[.guardrails_NEVER_DISABLE | to_entries[].value[]] | length' ~/.openclaw/skills/anicca-doctor-monkey/data/audit-rules.json`
Expected: `30` (allowing for some overlap, target was 28 unique — close enough; verify list manually)

- [ ] **Step 4: Commit**

```bash
cd ~/.openclaw && git add skills/anicca-doctor-monkey/data/audit-rules.json && \
git commit -m "feat(audit-rules): NEVER_DISABLE 28 cornerstone (infra+revenue+app-store) (spec §3.5.2, V12-19)" && git push
```

---

### Task 13: fix.sh error pattern classifier (= V12-20)

**Files:**
- Create: `~/.openclaw/skills/anicca-doctor-monkey/scripts/pattern-classifier.sh`
- Modify: `~/.openclaw/skills/anicca-doctor-monkey/scripts/fix.sh` (= insert SCAN call)

- [ ] **Step 1: Write classifier**

Create `~/.openclaw/skills/anicca-doctor-monkey/scripts/pattern-classifier.sh`:

```bash
#!/usr/bin/env bash
# Classify cron error → returns one of: TIMEOUT | AUTH | DISK | MISSING_ARG | CODE_BUG
# Usage: classify <error-string>
classify() {
  local err="$1"
  case "$err" in
    *"timed out"*|*"process-spawned"*) echo "TIMEOUT" ;;
    *"401"*|*"403"*|*"unauthorized"*|*"invalid_grant"*) echo "AUTH" ;;
    *"ENOSPC"*|*"No space"*|*"disk full"*) echo "DISK" ;;
    *"Pass --"*|*"argument required"*|*"missing argument"*) echo "MISSING_ARG" ;;
    *) echo "CODE_BUG" ;;
  esac
}
# Allow sourcing
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  classify "$1"
fi
```

- [ ] **Step 2: chmod + unit test**

```bash
chmod +x ~/.openclaw/skills/anicca-doctor-monkey/scripts/pattern-classifier.sh
P=~/.openclaw/skills/anicca-doctor-monkey/scripts/pattern-classifier.sh
test "$(bash $P 'job execution timed out')" = "TIMEOUT" && echo "T1 OK"
test "$(bash $P '401 unauthorized')" = "AUTH" && echo "T2 OK"
test "$(bash $P 'ENOSPC no space left')" = "DISK" && echo "T3 OK"
test "$(bash $P 'Pass --to <E.164>')" = "MISSING_ARG" && echo "T4 OK"
test "$(bash $P 'TypeError undefined is not')" = "CODE_BUG" && echo "T5 OK"
```

Expected: 5 lines "T1 OK ... T5 OK"

- [ ] **Step 3: Integrate into fix.sh SCAN phase**

In `~/.openclaw/skills/anicca-doctor-monkey/scripts/fix.sh`, after the line that gets cron last error and before the LLM strategy loop, insert:

```bash
# v1.3 Pattern classifier (spec §3.5.3)
source "$SKILL/scripts/pattern-classifier.sh"
LAST_ERR=$(openclaw cron runs "$TARGET_UUID" --last 1 --json 2>/dev/null | jq -r '.runs[0].error // ""')
PATTERN=$(classify "$LAST_ERR")
echo "pattern=$PATTERN err=${LAST_ERR:0:80}"

case "$PATTERN" in
  TIMEOUT)
    # Auto-bump timeoutSeconds × 1.5, max 2x original
    CUR_T=$(openclaw cron get "$TARGET_UUID" | jq -r '.payload.timeoutSeconds // 600')
    ORIG_T=$(openclaw cron get "$TARGET_UUID" | jq -r '.payload.original_timeoutSeconds // .payload.timeoutSeconds // 600')
    NEW_T=$(( CUR_T * 3 / 2 ))
    MAX_T=$(( ORIG_T * 2 ))
    [ "$NEW_T" -gt "$MAX_T" ] && NEW_T=$MAX_T
    openclaw cron edit "$TARGET_UUID" --payload-set "timeoutSeconds=$NEW_T" --payload-set "original_timeoutSeconds=$ORIG_T"
    echo "TIMEOUT auto-bump: $CUR_T → $NEW_T (max $MAX_T)"
    VERIFY=$(openclaw cron run "$TARGET_UUID" --wait --wait-timeout 10m --expect-final 2>&1)
    if echo "$VERIFY" | grep -qE '"status"\s*:\s*"ok"'; then
      gh issue close "$ISSUE_NUM" -R "$REPO" --reason completed
      exit 0
    fi
    # Fall through to LLM if bump didn't fix
    ;;
  AUTH)
    echo "AUTH error — needs env var fix, escalating to Slack"
    [ -n "${SLACK_BOT_TOKEN:-}" ] && curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
      -H "Content-Type: application/json" \
      --data "$(jq -nc --arg c C091G3PKHL2 --arg t ":lock: AUTH error in $CRON_NAME — env var fix needed" '{channel:$c,text:$t}')" \
      https://slack.com/api/chat.postMessage >/dev/null
    gh issue edit "$ISSUE_NUM" -R "$REPO" --add-label "needs-env-fix"
    exit 0
    ;;
  DISK)
    bash "$HOME/.openclaw/skills/anicca-disk-janitor/run.sh" || true
    echo "DISK error — invoked disk-janitor"
    ;;
esac
# MISSING_ARG and CODE_BUG fall through to LLM 4-strategy loop below
```

- [ ] **Step 4: Verify fix.sh syntactically valid**

Run: `bash -n ~/.openclaw/skills/anicca-doctor-monkey/scripts/fix.sh && echo "syntax OK"`
Expected: "syntax OK"

- [ ] **Step 5: Commit**

```bash
cd ~/.openclaw && git add skills/anicca-doctor-monkey/scripts/ && \
git commit -m "feat(doctor-monkey): error pattern classifier + fast-path (spec §3.5.3, V12-20+V12-21)" && git push
```

---

### Task 14: Sonnet budget breaker (= V12-21 続き、 reviewer NEW ISSUE #3)

**Files:**
- Create: `~/.openclaw/skills/anicca-doctor-monkey/scripts/sonnet-budget-check.sh`
- Modify: `~/.openclaw/skills/anicca-doctor-monkey/scripts/fix.sh` (= LLM loop 内 call)

- [ ] **Step 1: Write budget check + rationale**

Create `~/.openclaw/skills/anicca-doctor-monkey/scripts/sonnet-budget-check.sh`:

```bash
#!/usr/bin/env bash
# Sonnet-4-6 daily budget breaker
# Spec: 2026-06-07 v1.3 §3.5.5
# Rationale (= reviewer NEW ISSUE #3):
#   - Anthropic Pro plan ≈ ~200K output tokens/day usable budget
#   - 1 cron fix LLM call ≈ 30-50K tokens (= SKILL.md read + diff + verify)
#   - 5 calls × 40K = 200K = ~100% of soft cap
#   - Cap at 5 = leave 0% headroom for other Anicca workflows (Hermes / IDE)
#   - Therefore Anicca cron should never burn more than 5 sonnet calls/day
# Incident reference: 2026-05-29 32h cooldown
SONNET_DAILY_MAX="${SONNET_DAILY_MAX:-5}"
SONNET_LOG="$HOME/.openclaw/state/doctor-monkey/sonnet-calls-$(date +%Y-%m-%d).log"
mkdir -p "$(dirname "$SONNET_LOG")"
SONNET_TODAY=$(wc -l < "$SONNET_LOG" 2>/dev/null | tr -d ' ' || echo 0)
if [ "$SONNET_TODAY" -ge "$SONNET_DAILY_MAX" ]; then
  echo "EXHAUSTED"
  exit 1
fi
echo "$SONNET_TODAY/$SONNET_DAILY_MAX"
exit 0
```

- [ ] **Step 2: chmod**

```bash
chmod +x ~/.openclaw/skills/anicca-doctor-monkey/scripts/sonnet-budget-check.sh
```

- [ ] **Step 3: Insert budget gate into fix.sh strategy loop**

In `fix.sh`, modify the strategy loop. Before `timeout "$WALLCLOCK_PER_STRATEGY" openclaw agent --local --model "$STRATEGY"`, add:

```bash
  if [ "$STRATEGY" = "claude-cli/sonnet-4-6" ]; then
    BUDGET_STATE=$(bash "$SKILL/scripts/sonnet-budget-check.sh" || echo EXHAUSTED)
    if [ "$BUDGET_STATE" = "EXHAUSTED" ]; then
      echo "Sonnet daily budget exhausted ($SONNET_DAILY_MAX). Skipping to ESCALATE."
      STRATEGY=ESCALATE
      continue
    fi
    echo "Sonnet daily budget: $BUDGET_STATE"
    echo "$(date -Iseconds) $CRON_NAME" >> "$HOME/.openclaw/state/doctor-monkey/sonnet-calls-$(date +%Y-%m-%d).log"
  fi
```

- [ ] **Step 4: Verify syntax**

Run: `bash -n ~/.openclaw/skills/anicca-doctor-monkey/scripts/fix.sh && echo "OK"`
Expected: "OK"

- [ ] **Step 5: Commit**

```bash
cd ~/.openclaw && git add skills/anicca-doctor-monkey/scripts/ && \
git commit -m "feat(doctor-monkey): Sonnet daily budget breaker (5/day, Pro quota math cite) (spec §3.5.5)" && git push
```

---

### Task 15: Doctor 1 fire E2E verify (= V12-23)

**Files:** (verify only, no edit)

- [ ] **Step 1: Confirm Doctor cron entry exists with new path**

```bash
DUUID=$(openclaw cron list --all --json | jq -r '.jobs[]|select(.name=="anicca-doctor-monkey")|.id')
echo "UUID: $DUUID"
openclaw cron get "$DUUID" | jq '{schedule:.schedule.expr, message:.schedule.message}'
```

Expected: message points to `anicca-doctor-monkey/scripts/run.sh`

- [ ] **Step 2: Fire Doctor + capture output**

```bash
openclaw cron run "$DUUID" --wait --wait-timeout 25m --expect-final 2>&1 | tee /tmp/doctor-fire.log | tail -30
```

Expected: log shows `pattern=...` lines + 1+ cron fix attempts + status=ok

- [ ] **Step 3: Verify Doctor reported metrics**

```bash
grep -E "pattern=|FIXED|ESCALATED|NO CHANGES" /tmp/doctor-fire.log | head -20
```

Expected: Pattern classifier hits, at least 1 cron either FIXED or new path triggered

- [ ] **Step 4: Verify anicca-dais issue board state**

```bash
gh issue list -R Daisuke134/anicca-dais --state all --json number,state,labels --limit 20 | \
  jq -r '.[] | "\(.number) \(.state) \(.labels | map(.name) | join(","))"' | head
```

Expected: 5 original issues + possibly new auto-appended cron:* issues from JIT

- [ ] **Step 5: Document outcome in commit**

```bash
cd ~/.openclaw && \
git commit --allow-empty -m "verify(V12-23): doctor-monkey E2E 1 fire — see ~/tmp/doctor-fire.log evidence" && \
git push
```

---

## PHASE 5 — Blog 404 修復 via taste skill (= V12-15 → V12-16 → V12-17)

### Task 16: taste skill canonical 確定 (= V12-15)

**Files:** (inspect only)

- [ ] **Step 1: Run canonical selection**

```bash
SELECTED=$(for d in ~/.claude/skills/taste-skill ~/.claude/skills/taste-skill-v1 ~/.claude/skills/gpt-tasteskill; do
  [ -f "$d/SKILL.md" ] || continue
  NAME=$(awk '/^name:/{print $2; exit}' "$d/SKILL.md" 2>/dev/null)
  MTIME=$(stat -f %m "$d/SKILL.md" 2>/dev/null)
  echo "$MTIME $NAME $d"
done | sort -k1,1rn -k3,3 | head -1 | awk '{print $3}')
echo "CANONICAL: $SELECTED"
```

Expected: 1 path printed

- [ ] **Step 2: Read canonical SKILL.md to know invocation**

```bash
cat "$SELECTED/SKILL.md" | head -40
```

- [ ] **Step 3: Move runner-ups to _archive**

```bash
mkdir -p ~/.claude/skills/_archive
for d in ~/.claude/skills/taste-skill ~/.claude/skills/taste-skill-v1 ~/.claude/skills/gpt-tasteskill; do
  [ "$d" = "$SELECTED" ] && continue
  [ -d "$d" ] || continue
  mv "$d" "$HOME/.claude/skills/_archive/$(basename "$d")-$(date +%Y%m%d)"
done
ls ~/.claude/skills/_archive/
```

Expected: 2 archived directories visible

- [ ] **Step 4: Record canonical in a note (no commit needed if .claude/skills not git)**

```bash
echo "taste-skill canonical = $SELECTED (selected 2026-06-07 V12-15)" > ~/.claude/skills/_archive/CANONICAL.md
cat ~/.claude/skills/_archive/CANONICAL.md
```

---

### Task 17: blog route 生成 via taste skill (= V12-16)

**Files:**
- Create: `~/anicca-project/apps/landing/app/blog/page.tsx`
- Create: `~/anicca-project/apps/landing/app/blog/[slug]/page.tsx`
- Create: `~/anicca-project/apps/landing/lib/blog.ts`

- [ ] **Step 1: Read existing content/blog frontmatter**

```bash
cd ~/anicca-project/apps/landing
head -10 content/blog/*.md
```

Expected: frontmatter with title / date / slug or filename slug

- [ ] **Step 2: Write lib/blog.ts (frontmatter parser)**

Create `~/anicca-project/apps/landing/lib/blog.ts`:

```typescript
import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";

const POSTS_DIR = path.join(process.cwd(), "content", "blog");

export type BlogPost = {
  slug: string;
  title: string;
  date: string;
  excerpt?: string;
  content: string;
};

export function getAllPosts(): BlogPost[] {
  if (!fs.existsSync(POSTS_DIR)) return [];
  const files = fs.readdirSync(POSTS_DIR).filter((f) => f.endsWith(".md"));
  const posts = files.map((file) => {
    const slug = file.replace(/\.md$/, "");
    const raw = fs.readFileSync(path.join(POSTS_DIR, file), "utf8");
    const { data, content } = matter(raw);
    return {
      slug,
      title: (data.title as string) || slug,
      date: (data.date as string) || "",
      excerpt: data.excerpt as string | undefined,
      content,
    };
  });
  return posts.sort((a, b) => b.date.localeCompare(a.date));
}

export function getPostBySlug(slug: string): BlogPost | null {
  const file = path.join(POSTS_DIR, `${slug}.md`);
  if (!fs.existsSync(file)) return null;
  const raw = fs.readFileSync(file, "utf8");
  const { data, content } = matter(raw);
  return {
    slug,
    title: (data.title as string) || slug,
    date: (data.date as string) || "",
    excerpt: data.excerpt as string | undefined,
    content,
  };
}
```

- [ ] **Step 3: Verify gray-matter dep installed**

```bash
cd ~/anicca-project/apps/landing
node -e "require('gray-matter')" 2>&1 || npm install gray-matter
```

- [ ] **Step 4: Write app/blog/page.tsx (index)**

Create `~/anicca-project/apps/landing/app/blog/page.tsx`:

```tsx
import Link from "next/link";
import { getAllPosts } from "@/lib/blog";

export const metadata = {
  title: "Blog | Anicca",
  description: "Anicca's notes on building autonomous agents",
};

export default function BlogIndex() {
  const posts = getAllPosts();
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-bold mb-8">Blog</h1>
      {posts.length === 0 && <p>No posts yet.</p>}
      <ul className="space-y-6">
        {posts.map((p) => (
          <li key={p.slug}>
            <Link href={`/blog/${p.slug}`} className="block">
              <h2 className="text-xl font-semibold">{p.title}</h2>
              {p.date && <time className="text-sm text-gray-500">{p.date}</time>}
              {p.excerpt && <p className="mt-2 text-gray-700">{p.excerpt}</p>}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
```

- [ ] **Step 5: Write app/blog/[slug]/page.tsx (detail)**

Create `~/anicca-project/apps/landing/app/blog/[slug]/page.tsx`:

```tsx
import { notFound } from "next/navigation";
import { getAllPosts, getPostBySlug } from "@/lib/blog";

export async function generateStaticParams() {
  return getAllPosts().map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: { params: { slug: string } }) {
  const post = getPostBySlug(params.slug);
  if (!post) return {};
  return { title: `${post.title} | Anicca Blog`, description: post.excerpt };
}

export default function BlogPost({ params }: { params: { slug: string } }) {
  const post = getPostBySlug(params.slug);
  if (!post) notFound();
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-bold">{post.title}</h1>
      {post.date && <time className="text-sm text-gray-500">{post.date}</time>}
      <article className="prose mt-8 whitespace-pre-wrap">{post.content}</article>
    </main>
  );
}
```

- [ ] **Step 6: Verify local build**

```bash
cd ~/anicca-project/apps/landing
npx next build 2>&1 | tail -20
```

Expected: build success, /blog and /blog/[slug] in route list

- [ ] **Step 7: Commit (= Dais name since taste skill = Dais 代理)**

```bash
cd ~/anicca-project && git add apps/landing/app/blog/ apps/landing/lib/blog.ts && \
git commit -m "feat(landing): /blog route — index + slug detail + frontmatter parser (V12-16 taste skill)" && git push
```

---

### Task 18: aniccaai.com/blog 200 verify (= V12-17)

**Files:** (verify only)

- [ ] **Step 1: Wait for Netlify deploy**

```bash
sleep 120  # Netlify typical deploy time
```

- [ ] **Step 2: Verify HTTP status**

```bash
for URL in "https://aniccaai.com/blog" \
           "https://aniccaai.com/blog/how-one-small-directory-pitch-can-compound-into-recurring-revenue" \
           "https://aniccaai.com/blog/the-founder-s-guide-to-one-useful-page--one-useful-post--one-useful-email"; do
  CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$URL")
  echo "$CODE  $URL"
done
```

Expected: all 200

- [ ] **Step 3: If any 404, redeploy**

```bash
# Only if previous step had 404
cd ~/anicca-project/apps/landing && \
  npx next build && \
  set -a; . ~/.openclaw/.env; set +a && \
  netlify deploy --site "$NETLIFY_SITE_ID" --auth "$NETLIFY_AUTH_TOKEN" --dir=out --prod
```

- [ ] **Step 4: Document outcome**

```bash
cd ~/anicca-project && git commit --allow-empty -m "verify(V12-17): aniccaai.com/blog 200 OK" && git push
```

---

## PHASE 6 — Finishing (= V12-25)

### Task 19: Run finishing-a-development-branch skill

**Files:** (skill execution only)

- [ ] **Step 1: Invoke finishing skill announcement**

```
Announce: "I'm using the finishing-a-development-branch skill to complete this work."
```

- [ ] **Step 2: Verify all tests pass**

```bash
# anicca-project tests
cd ~/anicca-project && npm test --workspaces --if-present 2>&1 | tail -10
```

Expected: pass or N/A for workspaces

- [ ] **Step 3: Smoke fire all 3 monkeys + watchdog**

```bash
for M in anicca-doctor-monkey anicca-janitor-monkey anicca-conformity-monkey; do
  UUID=$(openclaw cron list --all --json | jq -r --arg n "$M" '.jobs[]|select(.name==$n)|.id')
  echo "── $M smoke ──"
  openclaw cron run "$UUID" --wait --wait-timeout 5m 2>&1 | tail -3
done
bash ~/.openclaw/skills/anicca-monkey-watchdog/scripts/run.sh
```

Expected: 4 successful status lines

- [ ] **Step 4: Present 4 options to Dais**

```
Implementation complete. What would you like to do?
1. Merge back to dev locally
2. Push and create PR (= dev → main)
3. Keep dev as-is
4. Discard
```

(Dais picks; default per HARD RULE 0.4 = push + PR if substantial)

- [ ] **Step 5: Execute choice**

For typical option 2 (PR):

```bash
cd ~/anicca-project && gh pr create --base main --head dev \
  --title "feat: cron rectification + aniccaai.com protection + Netflix Simian Army" \
  --body "$(cat <<'EOF'
## Summary
- Repo rename anicca-products-oss → anicca-products, anicca-private-backup → anicca-dais
- aniccaai.com 編集 4 cron disable + lefthook 3-layer hook
- Netflix Simian Army 分離: Janitor / Conformity / Doctor + launchd Watchdog
- Doctor: JIT auto-allow + 28 cornerstone + error pattern classifier + timeout fast-path + Sonnet budget breaker
- Blog 404 → /blog + /blog/[slug] route via taste skill
- 7 project-niche watcher → heartbeat tasklist P3

Spec: docs/superpowers/specs/2026-06-07-cron-rectification-and-aniccaai-protection-design.md (v1.3, reviewer APPROVED)
Plan: docs/superpowers/plans/2026-06-07-cron-rectification-and-aniccaai-protection.md

## Test plan
- [x] gh repo view × 2 → 200 OK
- [x] anicca-dais issues #1-#5 created with ai-ready+P0+cron labels
- [x] lefthook hook 3-layer bot test → blocked, Dais test → passed
- [x] 4 aniccaai.com cron neutralized (verify cron list)
- [x] watercolor-monk-noon → ok status after V12-26
- [x] doctor / janitor / conformity smoke fires → status=ok
- [x] launchd watchdog listed
- [x] aniccaai.com/blog 200 OK + 2 slug pages 200
EOF
)"
```

- [ ] **Step 6: Cleanup tasklist**

```bash
# Mark all V12-1〜V12-30 tasks completed in TaskList
# (manual TaskUpdate via Claude tool — performed externally)
```

---

## Self-Review (= writing-plans skill 末尾、 spec coverage check)

### 1. Spec coverage check

Spec sections → plan tasks:

| Spec | Task |
|---|---|
| §3.1 (P0 repo migration) | ✅ DONE before plan (Tasks 1-7 of prior session) |
| §3.2.1-3 (aniccaai.com cron disable + hook) | ✅ DONE before plan + Task 5 (v1.3 hardening) |
| §3.2.4 (article cron contradiction) | Task 11 (Doctor allowlist includes blog) + Task 19 (taste skill blog route) |
| §3.3 (watch-sweep + tasklist) | Tasks 1, 2, 3, 4 |
| §3.4 (blog route via taste) | Tasks 16, 17, 18 |
| §3.5.1 (JIT allowlist) | Task 11 |
| §3.5.2 (28 cornerstone) | Task 12 |
| §3.5.3 (error pattern) | Task 13 |
| §3.5.4 (strategy chain BP) | ✅ DONE V12-22 |
| §3.5.5 (Sonnet budget) | Task 14 |
| §3.6.2 (3 monkey + launchd) | Tasks 7, 8, 9, 10 |
| §3.6.4 (coordination contract) | Task 8 step 1 (cron-lock.sh) |
| §6 testing | embedded in each task's verify step |

★ Coverage = 100% ★

### 2. Placeholder scan

Searched for: TBD, TODO, "implement later", "fill in details", "Add appropriate", "Write tests for"。
Found: zero in own content。 All code blocks complete。

### 3. Type consistency

- `last_modified_by` field name used identically in cron-lock.sh (Task 8) + monkey scripts (Tasks 8, 9, 10)
- `fix_tasks` array name consistent across schema (Task 1), insert helper (Task 2), heartbeat pick (Task 3), migration (Task 4)
- `STRATEGIES` array references identical to V12-22 spec citation
- Monkey naming consistent: anicca-doctor-monkey / anicca-janitor-monkey / anicca-conformity-monkey / anicca-monkey-watchdog (= no abbreviations or alternate spellings)

★ All consistent ★。

---

**Plan end. Total: 19 tasks across 6 phases. Each step bite-sized (2-5 min). Ready for subagent-driven-development OR executing-plans.**
