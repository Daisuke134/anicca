# Skill Trio OSS + Monk-Factory 5 パッチ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** monk-factory の 3 日 0-post を 5 パッチで止血した後、 anicca-monk-factory と mau-clipping を OSS skill repo として GitHub に publish する (naist は v1 defer)。

**Architecture:** Phase A (runtime fix、 worktree なし、 ~/.openclaw 直編集) → Phase B (OSS publish、 worktree `feature/skill-trio-oss` で git 整備) → Phase C (X 告知 + verify gate)。 既存 bash + camofox + Postiz API は rewrite ゼロ、 CLI 化なし。

**Tech Stack:** bash 4+, jq, ffmpeg, whisper (openai-whisper), camofox-browser :9377, Postiz HTTP API v1, ElevenLabs HTTP API, agent-browser CLI (naist は触らず)、 GitHub CLI (`gh`)、 git worktree。

**Parent spec:** `docs/superpowers/specs/2026-06-04-skill-trio-oss-design.md`

**重要前提**:
- `~/.openclaw/` は runtime canonical store。 **worktree 不可** (CLAUDE.md HARD RULE #0 例外条項)。 Phase A は main 直編集。
- Phase B は `anicca-project` の worktree 切る (= `feature/skill-trio-oss`)、 GitHub repo は別 push (`github.com/Daisuke134/anicca-monk-factory`、 `mau-clipping`)。
- 並列実装禁止 (HARD RULE #62): Phase A 完走 → verify gate pass → Phase B 開始。

---

## Phase A: Monk-Factory 5 パッチ (= 沈黙止血、 最優先)

### Task A0: Pre-flight 診断 + stale lock 即削除 (= P4 即実行部分)

**Files:**
- Modify: `~/anicca-monk-factory/state/monk-factory-en.lock` (削除)

**Goal:** 次 cron が正常に走れる土台を作る (5 秒で完了)。

- [ ] **A0.1 — stale lock の現状確認**

Run:
```bash
ls -la ~/anicca-monk-factory/state/monk-factory-en.lock 2>&1
cat ~/anicca-monk-factory/state/monk-factory-en.lock 2>&1
ps -p $(cat ~/anicca-monk-factory/state/monk-factory-en.lock 2>/dev/null || echo 0) 2>&1 || echo "PID dead"
```
Expected: lock file 存在 + PID 11943 + "PID dead"。

- [ ] **A0.2 — stale lock 削除**

Run:
```bash
rm -f ~/anicca-monk-factory/state/monk-factory-en.lock
ls -la ~/anicca-monk-factory/state/monk-factory-en.lock 2>&1
```
Expected: "No such file or directory"。

- [ ] **A0.3 — 最新失敗 cron jsonl から root cause 再確認**

Run:
```bash
find ~/.openclaw/cron/runs -mtime -2 -type f -name "*.jsonl" 2>/dev/null | \
  xargs grep -l "monk-factory-en" 2>/dev/null | head -3 | \
  xargs -I{} sh -c 'echo "=== {} ===" ; tail -3 {}' | head -50
```
Expected: `RENDER_TIMEOUT: no HeyGen ready-mail after 18 min` が直近 run に出てる確認。

### Task A1: render-download.sh — mail wait 18→60 min + `HEYGEN_MAIL_TIMEOUT_MIN` env (= P1)

**Files:**
- Modify: `~/.openclaw/skills/anicca-monk-factory-v3/scripts/render-download.sh:16-34`

**Goal:** HeyGen の長尺 render (50min 級) を取りこぼさず、 env で override 可能。

- [ ] **A1.1 — 旧 timeout block の現状確認**

Run:
```bash
grep -n -E "(sleep 300|seq 1 13|RENDER_TIMEOUT)" ~/.openclaw/skills/anicca-monk-factory-v3/scripts/render-download.sh
```
Expected: 3 行ヒット (line 番号 = sleep 300、 seq 1 13、 RENDER_TIMEOUT echo)。

- [ ] **A1.2 — Edit: 旧 timeout block を env-aware に置換**

Edit `~/.openclaw/skills/anicca-monk-factory-v3/scripts/render-download.sh`:

Old:
```bash
START_TS=$(date +%s)
echo "MAIL_WAIT_START ts=$START_TS — minimum 5min before first check (HeyGen never <5min)"
sleep 300  # 5 min — render takes 5-10 min, so this is safe lower bound

MAIL_READY=0
for i in $(seq 1 13); do  # 13 more iterations × 60s = 13 min, total 18 min
```

New:
```bash
START_TS=$(date +%s)
TIMEOUT_MIN="${HEYGEN_MAIL_TIMEOUT_MIN:-60}"
[ "$TIMEOUT_MIN" -lt 6 ] && TIMEOUT_MIN=6   # 最低 6 min (sleep 300 + 1 poll)
POLL_ITER=$(( TIMEOUT_MIN - 5 ))
echo "MAIL_WAIT_START ts=$START_TS — minimum 5min before first check, total timeout ${TIMEOUT_MIN}min"
sleep 300  # 5 min — render takes 5-10 min, so this is safe lower bound

MAIL_READY=0
for i in $(seq 1 "$POLL_ITER"); do  # poll up to (TIMEOUT_MIN - 5) iterations × 60s
```

Also update the timeout message at line ~52:
Old:
```bash
[ "$MAIL_READY" = "1" ] || { echo "RENDER_TIMEOUT: no HeyGen ready-mail after 18 min on $URL"; exit 1; }
```
New:
```bash
[ "$MAIL_READY" = "1" ] || { echo "RENDER_TIMEOUT: no HeyGen ready-mail after ${TIMEOUT_MIN} min on $URL"; exit 1; }
```

- [ ] **A1.3 — Smoke test: env override が効く確認 (sleep を short-circuit)**

Run:
```bash
HEYGEN_MAIL_TIMEOUT_MIN=6 bash -c '
TIMEOUT_MIN="${HEYGEN_MAIL_TIMEOUT_MIN:-60}"
POLL_ITER=$(( TIMEOUT_MIN - 5 ))
echo "TIMEOUT_MIN=$TIMEOUT_MIN POLL_ITER=$POLL_ITER"
'
```
Expected: `TIMEOUT_MIN=6 POLL_ITER=1`。

- [ ] **A1.4 — syntax check**

Run:
```bash
bash -n ~/.openclaw/skills/anicca-monk-factory-v3/scripts/render-download.sh
```
Expected: no output (= syntax OK)。

### Task A2: run-daily.sh — mark のタイミングを submit 直後 → 1+ platform 成功直後 に移動 (= P2) + lock TTL 2h (= P4 後半)

**Files:**
- Modify: `~/.openclaw/skills/anicca-monk-factory-v3/scripts/run-daily.sh:16-30, 56, 88-89`

**Goal:** render-download 失敗時に script を喪失しない + stale lock が 2h で自動 clear される。

- [ ] **A2.1 — 旧 mark コール削除 (line 56)**

Edit `~/.openclaw/skills/anicca-monk-factory-v3/scripts/run-daily.sh`:

Old (around line 54-56):
```bash
# #41 rotation fix: mark used AS SOON AS the render is submitted, so a later cron never re-picks the
# same script on a mid-pipeline failure (the 8am-fail→2pm-dup bug). A spent script cycles back when all used.
bash "$S/pick-next-script.sh" mark "$ID" >/dev/null 2>&1 || true
```

New:
```bash
# 2026-06-04 P2 修正: 旧 #41 rotation fix は render-download 失敗時の script 喪失を起こした。
# Mark は post 成功直後に移動 (step 7 の後)。 全 platform fail 時は次 cron で同 script を retry。
```

- [ ] **A2.2 — 新 mark コールを step 7 (post IG) の後 + 8 (report-slack) の前に追加**

Edit same file、 step `=== [8] report ===` の直前に挿入:

Old (around line 88-90):
```bash
echo "=== [8] report ==="   # (mark used already happened right after render-submit — #41 rotation fix)
bash "$S/report-slack.sh" "🧎 Monk Factory $ID DONE — TikTok=${TTURL:-FAILED} | IG=${IGURL:-FAILED}"
echo "RUN_DONE id=$ID tiktok=${TTURL:-FAILED} ig=${IGURL:-FAILED}"
```

New:
```bash
# 2026-06-04 P2: 1 platform でも post 成功なら mark、 全 fail なら次 cron で retry
if [ -n "$TTURL" ] || [ -n "$IGURL" ]; then
  bash "$S/pick-next-script.sh" mark "$ID" >/dev/null 2>&1 || true
  echo "MARKED_USED: $ID (>=1 platform success)"
else
  echo "ALL_PLATFORMS_FAILED — script $ID kept unused for retry"
fi

echo "=== [8] report ==="
bash "$S/report-slack.sh" "🧎 Monk Factory $ID DONE — TikTok=${TTURL:-FAILED} | IG=${IGURL:-FAILED}"
echo "RUN_DONE id=$ID tiktok=${TTURL:-FAILED} ig=${IGURL:-FAILED}"
```

- [ ] **A2.3 — lock check に TTL 2h を追加 (= P4 後半)**

Edit same file、 line 16-30 の lock check block:

Old:
```bash
if [ -f "$LOCK" ]; then
  OLD_PID=$(cat "$LOCK" 2>/dev/null || echo 0)
  if [ "$OLD_PID" -gt 0 ] 2>/dev/null && kill -0 "$OLD_PID" 2>/dev/null; then
    # 2026-06-01 fix: exit 75 (EX_TEMPFAIL) so cron framework records this run
    # as transient-failure instead of "ok". Otherwise multiple mutex no-ops mask
    # the underlying RL_FAILED runs and harvester drops monk from chronic-fail
    # list → Anicca's auto-fix never sees it. 75 = "try again later" convention.
    echo "ALREADY_RUNNING: pid=$OLD_PID holds $LOCK — exit 75 (transient)"
    exit 75
  fi
  # stale lock from killed process — clear it
  echo "stale lock (pid=$OLD_PID not alive) — cleaning"
fi
```

New:
```bash
if [ -f "$LOCK" ]; then
  OLD_PID=$(cat "$LOCK" 2>/dev/null || echo 0)
  LOCK_AGE=$(( $(date +%s) - $(stat -f %m "$LOCK" 2>/dev/null || echo 0) ))
  if [ "$LOCK_AGE" -gt 7200 ]; then
    # 2026-06-04 P4: 2h 超は強制 stale 扱い (long-running run-daily を超える時間)
    echo "lock older than 2h (age=${LOCK_AGE}s, pid=$OLD_PID) — forcing stale clear"
    rm -f "$LOCK"
  elif [ "$OLD_PID" -gt 0 ] 2>/dev/null && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "ALREADY_RUNNING: pid=$OLD_PID holds $LOCK — exit 75 (transient)"
    exit 75
  else
    # stale lock from killed process — clear it
    echo "stale lock (pid=$OLD_PID not alive) — cleaning"
  fi
fi
```

- [ ] **A2.4 — syntax + diff check**

Run:
```bash
bash -n ~/.openclaw/skills/anicca-monk-factory-v3/scripts/run-daily.sh && echo "syntax OK"
grep -n -E "(MARKED_USED|ALL_PLATFORMS_FAILED|LOCK_AGE|forcing stale clear)" ~/.openclaw/skills/anicca-monk-factory-v3/scripts/run-daily.sh
```
Expected: "syntax OK" + 4 個の grep hit。

### Task A3: reconcile-used.sh 新規 (= P5)

**Files:**
- Create: `~/.openclaw/skills/anicca-monk-factory-v3/scripts/reconcile-used.sh`
- Modify: `~/.openclaw/skills/anicca-monk-factory-v3/scripts/run-daily.sh` (step [1] の直前に呼出追加)

**Goal:** 喪失した script (mark 済 / mp4 無し / 未 post) を unused に restore する。

- [ ] **A3.1 — Create reconcile-used.sh**

Write `~/.openclaw/skills/anicca-monk-factory-v3/scripts/reconcile-used.sh`:

```bash
#!/usr/bin/env bash
# reconcile-used.sh — used.log と renders_v3 / posted.jsonl の整合性を回復
# 2026-06-04 P5: render-download 失敗で「mark 済 / mp4 無し / 未 post」 になった script を
# unused に戻すことで、 次 cron で retry されるようにする。
# Usage: bash reconcile-used.sh (= run-daily.sh の step [1] 直前に呼ぶ)
set -uo pipefail

SKILL="$HOME/.openclaw/skills/anicca-monk-factory-v3"
USED="$SKILL/04-script/used.log"
OUT_DIR="$HOME/anicca-monk-factory/renders_v3"
POSTED="$HOME/anicca-monk-factory/state/posted.jsonl"

[ -f "$USED" ] || { echo "no used.log — skip reconcile"; exit 0; }

NEW_USED=$(mktemp)
RESTORED=0
KEPT=0
while IFS= read -r ID; do
  [ -z "$ID" ] && continue
  if [ -f "$OUT_DIR/${ID}_captioned.mp4" ] || grep -q "\"$ID\"" "$POSTED" 2>/dev/null; then
    echo "$ID" >> "$NEW_USED"
    KEPT=$((KEPT + 1))
  else
    echo "RECONCILE: $ID was marked but never posted → restoring to unused"
    RESTORED=$((RESTORED + 1))
  fi
done < "$USED"

mv "$NEW_USED" "$USED"
echo "reconcile done: kept=$KEPT restored=$RESTORED total=$((KEPT + RESTORED))"
```

- [ ] **A3.2 — chmod + syntax check**

Run:
```bash
chmod +x ~/.openclaw/skills/anicca-monk-factory-v3/scripts/reconcile-used.sh
bash -n ~/.openclaw/skills/anicca-monk-factory-v3/scripts/reconcile-used.sh && echo "syntax OK"
```
Expected: "syntax OK"。

- [ ] **A3.3 — Smoke test: dry-run で現状確認 (実 used.log を読むだけ)**

Run:
```bash
# 現状の used.log と renders_v3 を見て、 何個 restore されるか preview
USED=~/.openclaw/skills/anicca-monk-factory-v3/04-script/used.log
OUT_DIR=~/anicca-monk-factory/renders_v3
POSTED=~/anicca-monk-factory/state/posted.jsonl
echo "=== current used.log ==="; cat "$USED" 2>/dev/null
echo "=== renders_v3 captioned mp4 ==="; ls "$OUT_DIR"/*_captioned.mp4 2>/dev/null | head -5
echo "=== posted.jsonl tail ==="; tail -5 "$POSTED" 2>/dev/null
```
Expected: used.log に A01/A02/A03 だけ、 renders_v3 に A20_captioned.mp4 まで存在を確認。

- [ ] **A3.4 — 実行 (本番、 used.log を実際 reconcile)**

Run:
```bash
bash ~/.openclaw/skills/anicca-monk-factory-v3/scripts/reconcile-used.sh
```
Expected: `reconcile done: kept=N restored=M total=N+M`、 0 件 restored ならそれで OK (= 既に整合的)。

- [ ] **A3.5 — run-daily.sh の step [1] 直前に reconcile 呼出を挿入**

Edit `~/.openclaw/skills/anicca-monk-factory-v3/scripts/run-daily.sh`:

Old (around line 36-40):
```bash
echo "=== [0] ensure HeyGen login ==="
bash "$S/ensure-heygen-login.sh" || fail login "ensure-heygen-login.sh failed"

echo "=== [1] pick next script (rotation) ==="
J=$(bash "$S/pick-next-script.sh" next) || fail pick "pick-next failed"
```

New:
```bash
echo "=== [0] ensure HeyGen login ==="
bash "$S/ensure-heygen-login.sh" || fail login "ensure-heygen-login.sh failed"

echo "=== [0.5] reconcile used.log (P5) ==="
bash "$S/reconcile-used.sh" || true   # reconcile failure should not block run

echo "=== [1] pick next script (rotation) ==="
J=$(bash "$S/pick-next-script.sh" next) || fail pick "pick-next failed"
```

- [ ] **A3.6 — syntax check**

Run:
```bash
bash -n ~/.openclaw/skills/anicca-monk-factory-v3/scripts/run-daily.sh && echo "syntax OK"
grep -n "reconcile-used.sh" ~/.openclaw/skills/anicca-monk-factory-v3/scripts/run-daily.sh
```
Expected: "syntax OK" + 1 grep hit。

### Task A4: recovery cron 新設 (= P3)

**Files:**
- Modify: `~/.openclaw/cron/jobs.json` (新 cron entry 1 件追加)

**Goal:** 2h 毎に `resume-render.sh` を走らせて、 60min wait でも取りこぼした render を救う。

- [ ] **A4.1 — 現状の cron 数を記録 (backup 用)**

Run:
```bash
cp ~/.openclaw/cron/jobs.json ~/.openclaw/cron/jobs.json.bak-pre-A4-$(date +%Y%m%d-%H%M%S)
python3 -c "import json; print('total jobs:', len(json.load(open('/Users/anicca/.openclaw/cron/jobs.json'))['jobs']))"
```
Expected: backup file 作成 + `total jobs: N` 表示。

- [ ] **A4.2 — 新 cron entry を JSON に追加 (jq で安全に)**

Run:
```bash
NEW_JOB='{
  "id": "monk-factory-en-recovery",
  "agentId": "anicca",
  "name": "monk-factory-en-recovery",
  "enabled": true,
  "createdAtMs": '"$(date +%s)"'000,
  "schedule": {"kind": "cron", "expr": "0 */2 * * *", "tz": "Asia/Tokyo"},
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "Execute this exact shell command and BLOCK until it exits. Do NOT report progress before exit:\n\nbash /Users/anicca/.openclaw/skills/anicca-monk-factory-v3/scripts/resume-render.sh\n\nYour summary MUST be EXACTLY the last 6 lines of stdout.",
    "model": "deepseek/deepseek-v4-pro",
    "timeoutSeconds": 1800
  },
  "delivery": {"mode": "announce", "channel": "slack", "to": "channel:C091G3PKHL2", "bestEffort": true},
  "state": {}
}'
python3 -c "
import json, sys
j = json.load(open('/Users/anicca/.openclaw/cron/jobs.json'))
new_job = json.loads('''$NEW_JOB''')
# 既存に同名が居たら置換、 居なければ append
existing = [i for i, x in enumerate(j['jobs']) if x.get('name') == 'monk-factory-en-recovery']
if existing:
    j['jobs'][existing[0]] = new_job
    print('replaced existing monk-factory-en-recovery at index', existing[0])
else:
    j['jobs'].append(new_job)
    print('appended monk-factory-en-recovery (now', len(j['jobs']), 'jobs total)')
json.dump(j, open('/Users/anicca/.openclaw/cron/jobs.json', 'w'), indent=2)
"
```
Expected: "appended monk-factory-en-recovery (now N+1 jobs total)" or "replaced existing"。

- [ ] **A4.3 — JSON valid + cron entry 内容確認**

Run:
```bash
python3 -c "
import json
j = json.load(open('/Users/anicca/.openclaw/cron/jobs.json'))
for job in j['jobs']:
    if job.get('name') == 'monk-factory-en-recovery':
        print('FOUND:', job['name'], 'enabled=', job['enabled'], 'cron=', job['schedule']['expr'])
        print('msg[:200]:', (job['payload'].get('message','') or '')[:200])
"
```
Expected: 「FOUND: monk-factory-en-recovery enabled= True cron= 0 */2 * * *」。

- [ ] **A4.4 — gateway restart で cron を再 register**

Run:
```bash
openclaw gateway restart 2>&1 | tail -5
# 数秒待って status 確認
sleep 5
openclaw gateway status 2>&1 | head -10
```
Expected: gateway running + new job loaded。 (もし openclaw コマンドが PATH に無ければ `~/.openclaw/bin/openclaw` を試す)。

- [ ] **A4.5 — resume-render.sh の存在確認 (= cron が呼ぶ実体)**

Run:
```bash
ls -la ~/.openclaw/skills/anicca-monk-factory-v3/scripts/resume-render.sh
bash -n ~/.openclaw/skills/anicca-monk-factory-v3/scripts/resume-render.sh && echo "syntax OK"
```
Expected: 実体存在 + "syntax OK"。

### Task A5: 5 パッチ統合 dry-run (= 実 cron 走る前の最終確認)

**Files:** 触らない (verify-only)

**Goal:** A1-A4 の変更が syntax/論理ともに正しいか、 実 cron 走る前に最後確認。

- [ ] **A5.1 — 全 patch 適用済 diff サマリ**

Run:
```bash
cd ~/.openclaw && git diff --stat HEAD -- skills/anicca-monk-factory-v3/scripts/ cron/jobs.json 2>/dev/null | head -10
# git 管理されてない場合は ls -la の mtime で確認:
ls -la ~/.openclaw/skills/anicca-monk-factory-v3/scripts/render-download.sh \
       ~/.openclaw/skills/anicca-monk-factory-v3/scripts/run-daily.sh \
       ~/.openclaw/skills/anicca-monk-factory-v3/scripts/reconcile-used.sh
```
Expected: 3 file の mtime が today (2026-06-04)。

- [ ] **A5.2 — env-aware timeout を mock 実行 (短 timeout で 1 ループ通す)**

Run:
```bash
# render-download.sh の poll loop を仮想的に「mail 来ない」 シナリオで走らせる (=実 wait なし)
HEYGEN_MAIL_TIMEOUT_MIN=6 bash -c '
TIMEOUT_MIN="${HEYGEN_MAIL_TIMEOUT_MIN:-60}"
POLL_ITER=$(( TIMEOUT_MIN - 5 ))
echo "TIMEOUT_MIN=$TIMEOUT_MIN POLL_ITER=$POLL_ITER"
echo "(skipping sleep 300 for smoke test)"
for i in $(seq 1 "$POLL_ITER"); do
  echo "iter $i (would gog gmail search here)"
done
echo "RENDER_TIMEOUT would fire after $TIMEOUT_MIN min"
'
```
Expected: 「TIMEOUT_MIN=6 POLL_ITER=1 ... iter 1 ... RENDER_TIMEOUT would fire after 6 min」。

- [ ] **A5.3 — 統合 commit (= ~/.openclaw が git 管理されてるなら)**

Run:
```bash
cd ~/.openclaw && git status --short skills/anicca-monk-factory-v3/scripts/ cron/jobs.json 2>/dev/null || echo "~/.openclaw is not a git repo or no changes tracked"
# 管理されてるなら:
# cd ~/.openclaw && git add skills/anicca-monk-factory-v3/scripts/render-download.sh skills/anicca-monk-factory-v3/scripts/run-daily.sh skills/anicca-monk-factory-v3/scripts/reconcile-used.sh cron/jobs.json && git commit -m "fix(monk-factory): 5 patches for 3-day silence (P1 timeout 18→60min, P2 mark timing, P3 recovery cron, P4 lock TTL, P5 reconcile-used)" && git push
```
Expected: commit success or "not a git repo"。 後者なら skip。

### Task A6: 21:00 JST cron 実行 → 24h 投稿確認 (= 5 パッチ verify gate)

**Files:** 触らない (live observation)

**Goal:** P1-P5 適用後の monk-factory が 1 本 post 完了するまで観測。 これが CLAUDE.md 0.12 verification-before-completion gate。

- [ ] **A6.1 — 次 cron 21:00 JST の予定確認**

Run:
```bash
date "+now=%Y-%m-%d %H:%M:%S %Z"
python3 -c "
from datetime import datetime, timedelta
import zoneinfo
now = datetime.now(zoneinfo.ZoneInfo('Asia/Tokyo'))
next_21 = now.replace(hour=21, minute=0, second=0, microsecond=0)
if next_21 <= now: next_21 += timedelta(days=1)
print('next monk-factory-en-2100:', next_21.isoformat())
print('next recovery (every 2h):', now.replace(minute=0, second=0).isoformat())
"
```
Expected: next run time が future。

- [ ] **A6.2 — (live wait) 21:00 JST cron 完走を観測**

Run after 21:00 JST:
```bash
# cron 走った直後の lock 確認
ls -la ~/anicca-monk-factory/state/monk-factory-en.lock 2>&1 && echo "RUNNING"
# 最新 render-submit.log を tail
ls -lat ~/anicca-monk-factory/renders_v3/*.render-submit.log 2>/dev/null | head -3
# 最新 captioned mp4 (= 完走の証拠)
ls -lat ~/anicca-monk-factory/renders_v3/*_captioned.mp4 2>/dev/null | head -3
```
Expected (21:00 起動後 60-90 min 以内): 新しい `*_captioned.mp4` 出現。

- [ ] **A6.3 — Slack #metrics で TT URL + IG URL 確認**

Run via slack tool or `slack-search public`:
```
キーワード "Monk Factory" を Slack #metrics で検索、 直近 24h で 「RUN_DONE id=... tiktok=https://... ig=https://...」 の投稿を確認。
```
Expected: 1 件以上「TikTok=https://... | IG=https://...」 が出てる。

- [ ] **A6.4 — TikTok @anicca_cemetery + IG @monk.anicca 実視聴**

Visit:
- https://www.tiktok.com/@anicca_cemetery → 24h 以内の最新投稿
- https://www.instagram.com/monk.anicca → 24h 以内の最新投稿

Expected: 両方とも new monk video が実際に publish されてる。 これが fix verified の決定的証拠 (CLAUDE.md 0.12)。

- [ ] **A6.5 — verify 結果を spec に追記 + commit**

Edit `docs/superpowers/specs/2026-06-04-skill-trio-oss-design.md`、 § 8 Verification 表の anicca-monk-factory 行に:
```
verified 2026-06-0X JST: TikTok=<URL> IG=<URL> (recovery cron N回 fire 後)
```

Run:
```bash
cd /Users/anicca/anicca-project
git add docs/superpowers/specs/2026-06-04-skill-trio-oss-design.md
git commit -m "docs(spec): monk-factory 5 patch verified 2026-06-0X — TikTok+IG live"
git push origin dev
```
Expected: push success。

---

## Phase B: OSS Publish (anicca-monk-factory + mau-clipping)

**前提**: Phase A の Task A6 が pass (= 24h 1 投稿以上) してから着手。 未 pass で Phase B 進めるの **禁止** (HARD RULE: 動かないものを OSS 出さない)。

### Task B0: worktree 作成

**Files:**
- Create: `/Users/anicca/anicca-project/.worktrees/skill-trio-oss/`

- [ ] **B0.1 — worktree branch 切る**

Run:
```bash
cd /Users/anicca/anicca-project
git worktree add .worktrees/skill-trio-oss -b feature/skill-trio-oss
cd .worktrees/skill-trio-oss
git status
```
Expected: clean worktree on `feature/skill-trio-oss`。

- [ ] **B0.2 — .gitignore で worktree dir を除外確認**

Run:
```bash
grep -q "^\.worktrees/" .gitignore && echo "already ignored" || echo ".worktrees not ignored — add it"
# 追加が必要なら:
# echo ".worktrees/" >> .gitignore
```
Expected: "already ignored"。

### Task B1: anicca-monk-factory repo bootstrap (= GitHub publish 準備、 ~/.cache に scaffold)

**Files:**
- Create: `~/.cache/anicca-oss-scaffold/anicca-monk-factory/` (= 公開前の scaffold dir)
- Create: SKILL.md, README.md, QUICKSTART.md, install.sh, .env.example, examples/, scripts/ (= ~/.openclaw のを copy)

**Goal:** GitHub 公開できる状態の repo 構造を作る。 publish は B5 で。

- [ ] **B1.1 — scaffold dir 作成 + 既存 scripts copy**

Run:
```bash
SCAFFOLD=~/.cache/anicca-oss-scaffold/anicca-monk-factory
rm -rf "$SCAFFOLD"
mkdir -p "$SCAFFOLD"/{scripts,examples,docs,tests}
# 既存 scripts/ を丸ごと copy (Patch A 適用済)
cp -R ~/.openclaw/skills/anicca-monk-factory-v3/scripts/ "$SCAFFOLD/scripts/"
# 04-script/ から bank と formula を copy (= OSS user の参考に 3 例だけ)
mkdir -p "$SCAFFOLD/examples/scripts"
head -3 ~/.openclaw/skills/anicca-monk-factory-v3/04-script/bank_en.jsonl > "$SCAFFOLD/examples/scripts/bank_en.example.jsonl"
cp ~/.openclaw/skills/anicca-monk-factory-v3/04-script/formulas.md "$SCAFFOLD/examples/scripts/formulas.md"
ls -la "$SCAFFOLD"
```
Expected: scaffold 構造 + scripts/ に bash file 一覧。

- [ ] **B1.2 — character.yaml.example を新規 (= 顔/声/CTA の template、 Dais の中身は入れない)**

Write `~/.cache/anicca-oss-scaffold/anicca-monk-factory/examples/character.yaml.example`:

```yaml
# character.yaml — define your monk character once, never change it
# 1 character = 1 face + 1 voice + 1 script formula
# Replace all <YOUR_*> placeholders with your own values.

name: "Your Monk Name"
biography: |
  A 2-3 line bio that describes who your monk is, where they're from,
  why they speak about suffering and the body-mind connection.
  Example: "Master Tao Hua, fifty years a monk in the mountains of Zhejiang.
  I have seen ten thousand winters and learned the silence of the pines."

voice:
  elevenlabs_voice_id_en: "<YOUR_ELEVENLABS_VOICE_ID_EN>"
  elevenlabs_voice_id_jp: "<YOUR_ELEVENLABS_VOICE_ID_JP>"   # optional
  settings:
    stability: 0.45
    style: 0.30
    speed: 0.90

face:
  locked_face_jpeg: "/path/to/your/locked-face.jpeg"   # absolute path

heygen:
  avatar_group_alt: "<YOUR_HEYGEN_AVATAR_GROUP_NAME>"
  avatar_look_name: "<YOUR_AVATAR_LOOK_NAME>"   # e.g. "Wise Elder of Tranquility"
  avatar_mp4: "/path/to/your/avatar-talking.mp4"   # 9:16, ~90s

script_bank:
  path: "./examples/scripts/bank_en.example.jsonl"  # replace with your own bank
  formula_path: "./examples/scripts/formulas.md"
```

- [ ] **B1.3 — .env.example を新規 (= 必要 env 全部)**

Write `~/.cache/anicca-oss-scaffold/anicca-monk-factory/.env.example`:

```bash
# anicca-monk-factory — environment variables
# Copy to .env and fill. NEVER commit .env to git.

# === HeyGen ===
HEYGEN_EMAIL="your-email@example.com"
HEYGEN_PASSWORD="your-password"
HEYGEN_TOTP_SEED=""          # optional, base32 from Authenticator migration QR (zbarimg + decode-otp-migration.py)

# === ElevenLabs ===
ELEVENLABS_API_KEY="sk_..."

# === Postiz (self-host or cloud) ===
POSTIZ_API_KEY="..."
POSTIZ_TT_INTEGRATION_ID=""   # TikTok (optional if posting only IG)
POSTIZ_IG_INTEGRATION_ID=""   # Instagram
POSTIZ_YT_INTEGRATION_ID=""   # YouTube (optional)

# === Google (for HeyGen 2FA + TikTok 2FA mail read) ===
GOOGLE_LOGIN_EMAIL="your-gmail@gmail.com"
GOG_KEYRING_PASSWORD=""        # optional, only if using gog gmail polling

# === Slack reporting ===
SLACK_BOT_TOKEN=""             # optional, for Slack #metrics digest
SLACK_METRICS_CHANNEL=""       # e.g. C091G3PKHL2

# === Runtime tuning ===
HEYGEN_MAIL_TIMEOUT_MIN=60     # HeyGen mail wait (default 60min)
AI_MONK_PROFILE=default         # profile name, used as workspace dir suffix
```

- [ ] **B1.4 — SKILL.md を新規 (= 薄、 use when + run command のみ)**

Write `~/.cache/anicca-oss-scaffold/anicca-monk-factory/SKILL.md`:

```markdown
---
name: anicca-monk-factory
description: "Yang-Mun-style AI monk video factory. Locked face + locked voice + 30-script bank → HeyGen render → caption burn → TikTok + IG post. Faithful clone of @yangmun2 / @shalevhvs methodology."
homepage: https://github.com/Daisuke134/anicca-monk-factory
metadata:
  tags: tiktok, ai-avatar, heygen, elevenlabs, monk, postiz, automation, yangmun
  requires:
    bins: [ffmpeg, ffprobe, whisper, jq, oathtool, magick]
    env: [HEYGEN_EMAIL, HEYGEN_PASSWORD, ELEVENLABS_API_KEY, POSTIZ_API_KEY, GOOGLE_LOGIN_EMAIL]
---

# anicca-monk-factory

Make 1 talking-head monk video per cron run. Same face, same voice, different script every day (or 30 at once per month).

## Use when

- You want daily 75-120s talking-head monk videos posted to TikTok + Instagram on autopilot.
- You have an ElevenLabs voice you want locked, a HeyGen avatar you want locked, and a script bank you want to rotate through.
- You're cloning the @yangmun2 / @shalevhvs methodology (hook + retention bait + authority + numbered body + comment keyword).

## Use when NOT

- You want cinematic avatars with varied expression (this skill is talking-head only).
- You want >2 min long-form videos.
- You want to use Sora2 / Veo / Runway instead of HeyGen (other skills).

## Quick run

```bash
bash scripts/run-daily.sh
```

Full setup: see `QUICKSTART.md`.

## Architecture

`docs/ARCHITECTURE.md`
```

- [ ] **B1.5 — README.md (= 入口、 X visitor が最初に見る)**

Write `~/.cache/anicca-oss-scaffold/anicca-monk-factory/README.md`:

```markdown
# anicca-monk-factory

> Daily AI monk videos on TikTok + Instagram, end-to-end automated.
> Inspired by [@yangmun2](https://www.tiktok.com/@yangmun2) and [@shalevhvs](https://x.com/shalevhvs/status/2042242260784537736).

## What it does

Every cron run, this skill:

1. Picks the next unused script from your bank of 30.
2. Renders it as a talking-head 9:16 video using HeyGen (with your locked face + voice).
3. Burns word-synced captions (Yang Mun style: 2-word UPPERCASE chunks, one yellow keyword).
4. Posts to TikTok (browser upload via camofox) + Instagram (Postiz API).
5. Reports the live URLs to Slack #metrics.

You set up the locked face + voice + 30-script bank **once**, then the rotation runs forever.

## Cost

| Service | Monthly cost |
|---|---|
| HeyGen Creator | $24 |
| ElevenLabs Starter | $5 |
| Postiz (self-host) | $0 |
| Total | **~$30/mo** |

> **Don't use HeyGen's REST API.** It costs ~$20 per video. We use the HeyGen Web UI (driven by camofox-browser) so you stay in the Creator plan's flat fee.

## Quickstart

See `QUICKSTART.md` (5 minutes).

## Prereqs

- macOS (tested) or Linux with brew + python 3.10+
- `brew install ffmpeg jq oathtool imagemagick`
- `pip install openai-whisper`
- HeyGen account + ElevenLabs voice + Postiz integration
- `camofox-browser` running at :9377 (see [Daisuke134/camofox-browser](https://github.com/Daisuke134/camofox-browser))

## Architecture

```
cron (0 8,14,21 * * * JST)
   │
   ▼
run-daily.sh
   ├── ensure HeyGen login (camofox)
   ├── reconcile used.log (P5)
   ├── pick next script (rotation)
   ├── render-submit (camofox + HeyGen Video Agent UI)
   ├── render-download (poll gmail for "Your Video is Ready!" up to 60min)
   ├── quality gate (whisper >=70% words)
   ├── burn captions (whisper word-timestamp + ffmpeg ass)
   ├── gen unique caption
   ├── post TikTok (camofox + tiktok.com/upload)
   ├── post IG (Postiz API)
   ├── mark used (only if >=1 platform success)
   └── report to Slack

parallel (0 */2 * * * JST): resume-render.sh
   └── recover any project whose download timed out
```

## Inspiration + credits

- @yangmun2 (TikTok) — the original Yang Mun monk format
- @shalevhvs (X) — system description
- @maboroshi_app — Mau, for the "clone proven viral content" philosophy

## License

MIT
```

- [ ] **B1.6 — QUICKSTART.md**

Write `~/.cache/anicca-oss-scaffold/anicca-monk-factory/QUICKSTART.md`:

```markdown
# Quickstart (5 minutes)

## 1. Prereqs

```bash
brew install ffmpeg jq oathtool imagemagick
pip install openai-whisper
```

## 2. Clone + install the skill

```bash
git clone https://github.com/Daisuke134/anicca-monk-factory
cd anicca-monk-factory
bash install.sh   # symlinks ~/.claude/skills/anicca-monk-factory/ + runs doctor
```

## 3. Set credentials

```bash
cp .env.example .env
$EDITOR .env   # fill HEYGEN_*, ELEVENLABS_*, POSTIZ_*, GOOGLE_LOGIN_EMAIL
```

## 4. Define your character

```bash
cp examples/character.yaml.example character.yaml
$EDITOR character.yaml   # name, voice IDs, face JPEG path, HeyGen avatar
cp examples/scripts/bank_en.example.jsonl bank.jsonl
# Edit bank.jsonl — at least 1 script (75-120s text, T1 body/wellness or T2 mind/suffering)
```

## 5. Bring up camofox-browser

```bash
# In another terminal:
git clone https://github.com/Daisuke134/camofox-browser
cd camofox-browser && bash scripts/start.sh   # listens on :9377
```

## 6. First run

```bash
bash scripts/run-daily.sh
```

Expected:
- `RUN_DONE id=<your-script-id> tiktok=https://... ig=https://...`
- New video on your TikTok + Instagram.

## Troubleshooting

See `docs/TROUBLESHOOTING.md`.
```

- [ ] **B1.7 — install.sh + LICENSE + .gitignore**

Write `~/.cache/anicca-oss-scaffold/anicca-monk-factory/install.sh`:

```bash
#!/usr/bin/env bash
# install.sh — register skill into ~/.claude/skills/ + prereq doctor
set -euo pipefail

SKILL_NAME="anicca-monk-factory"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$HOME/.claude/skills/$SKILL_NAME"

if [ -L "$TARGET" ] || [ -d "$TARGET" ]; then
  echo "removing existing $TARGET"
  rm -rf "$TARGET"
fi
mkdir -p "$HOME/.claude/skills"
ln -s "$REPO_DIR" "$TARGET"
echo "✓ symlinked $TARGET → $REPO_DIR"

echo
echo "=== prereq doctor ==="
miss=0
for bin in ffmpeg ffprobe jq oathtool magick; do
  if command -v "$bin" >/dev/null 2>&1; then echo "✓ $bin"; else echo "✗ $bin not found"; miss=1; fi
done
python3 -c "import whisper" 2>/dev/null && echo "✓ whisper (python)" || { echo "✗ whisper not installed (pip install openai-whisper)"; miss=1; }
[ -f "$REPO_DIR/.env" ] && echo "✓ .env present" || { echo "✗ .env missing — cp .env.example .env"; miss=1; }
[ -f "$REPO_DIR/character.yaml" ] && echo "✓ character.yaml present" || { echo "✗ character.yaml missing — cp examples/character.yaml.example character.yaml"; miss=1; }
[ -f "$REPO_DIR/bank.jsonl" ] && echo "✓ bank.jsonl present" || { echo "✗ bank.jsonl missing — cp examples/scripts/bank_en.example.jsonl bank.jsonl"; miss=1; }

curl -sf http://localhost:9377/health >/dev/null 2>&1 && echo "✓ camofox-browser running on :9377" || { echo "✗ camofox-browser not running on :9377"; miss=1; }

echo
[ "$miss" = "0" ] && echo "🟢 ready to run: bash scripts/run-daily.sh" || echo "🟡 install missing prereqs first"
exit "$miss"
```

Run:
```bash
chmod +x ~/.cache/anicca-oss-scaffold/anicca-monk-factory/install.sh
```

Write `~/.cache/anicca-oss-scaffold/anicca-monk-factory/.gitignore`:
```
.env
state/
renders/
captions/
*.mp4
*.mp3
*.log
.DS_Store
character.yaml
bank.jsonl
__pycache__/
```

Write `~/.cache/anicca-oss-scaffold/anicca-monk-factory/LICENSE` (MIT、 standard text):
```
MIT License

Copyright (c) 2026 Daisuke Narita

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **B1.8 — scaffold 検証: ls + install.sh dry-run**

Run:
```bash
SCAFFOLD=~/.cache/anicca-oss-scaffold/anicca-monk-factory
find "$SCAFFOLD" -maxdepth 2 -type f | sort
bash -n "$SCAFFOLD/install.sh" && echo "install.sh syntax OK"
```
Expected: 全 file 揃ってる + syntax OK。

### Task B2: mau-clipping repo bootstrap + D8 patch (POST_PLATFORMS env)

**Files:**
- Create: `~/.cache/anicca-oss-scaffold/mau-clipping/`
- Modify: `scripts/post-to-postiz.js` (= D8 適用、 OSS では 3 platform 既定)

**Goal:** mau-clipping を OSS publish 可能な構造に。 旧 YT-only 縛りを env で切り替え可能化。

- [ ] **B2.1 — scaffold dir + 既存 scripts copy**

Run:
```bash
SCAFFOLD=~/.cache/anicca-oss-scaffold/mau-clipping
rm -rf "$SCAFFOLD"
mkdir -p "$SCAFFOLD"/{scripts,examples,docs,tests}
cp -R ~/.openclaw/skills/mau-tiktok/scripts/ "$SCAFFOLD/scripts/"
ls -la "$SCAFFOLD/scripts/"
```
Expected: 3 .js file (scrape-hooks, trim-and-stitch, post-to-postiz)。

- [ ] **B2.2 — post-to-postiz.js に POST_PLATFORMS env support 追加 (D8)**

Edit `~/.cache/anicca-oss-scaffold/mau-clipping/scripts/post-to-postiz.js`、 line ~255-266 を置換:

Old:
```javascript
  // Dais 2026-05-22: mau-tiktok posts ONLY to YouTube (limited accounts).
  // NO TikTok, NO Instagram — those platforms are intentionally skipped here.
  // T0-#70 2026-05-29: EN YT (cmn8ymq6c "Daily Affirmation App") rejects custom
  // thumbnails (58 ERROR / 0 PUBLISHED in 30d, JA YT cmn1oukj works = 47 PUBLISHED).
  // Skip thumbnail for EN → Postiz can publish video with YT auto-thumbnail instead.
  // (Dais: "電話認証は俺やってる、cron params が間違ってる" → params=thumbnail incompat.)
  if (integrations.youtube && integrations.youtube.id) {
    const ytThumb = lang === "en" ? null : thumbnail;
    results.youtube = postToYouTube(integrations.youtube.id, uploaded.id, uploaded.path, caption, title, apiKey, ytThumb);
  } else {
    console.error("[ERR] mau-tiktok is YouTube-only but no youtube integration configured");
  }
```

New:
```javascript
  // 2026-06-04 D8: OSS default = 3 platform。 Anicca runtime は env POST_PLATFORMS=youtube で従来挙動維持。
  // 旧 mau-tiktok の YT-only 縛り (Dais 2026-05-22 「電話認証 + cron params 問題」) は env で切替可能化。
  const PLATFORMS = (process.env.POST_PLATFORMS || "tiktok,instagram,youtube")
    .split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
  console.log(`[POLICY] POST_PLATFORMS = ${PLATFORMS.join(",")}`);

  if (PLATFORMS.includes("tiktok") && integrations.tiktok && integrations.tiktok.id) {
    results.tiktok = postToTikTok(integrations.tiktok.id, uploaded.id, uploaded.path, caption, title, apiKey);
  }
  if (PLATFORMS.includes("instagram") && integrations.instagram && integrations.instagram.id) {
    results.instagram = postToInstagram(integrations.instagram.id, uploaded.id, uploaded.path, caption, apiKey);
  }
  if (PLATFORMS.includes("youtube") && integrations.youtube && integrations.youtube.id) {
    const ytThumb = lang === "en" ? null : thumbnail;   // EN YT thumbnail incompat 維持
    results.youtube = postToYouTube(integrations.youtube.id, uploaded.id, uploaded.path, caption, title, apiKey, ytThumb);
  }

  if (Object.keys(results).length === 0) {
    console.error(`[ERR] No platforms posted. POST_PLATFORMS=${PLATFORMS.join(",")} but no matching integration configured.`);
  }
```

- [ ] **B2.3 — syntax check + dry-run (POST_PLATFORMS 切替)**

Run:
```bash
node -c ~/.cache/anicca-oss-scaffold/mau-clipping/scripts/post-to-postiz.js 2>&1 || node --check ~/.cache/anicca-oss-scaffold/mau-clipping/scripts/post-to-postiz.js
echo "---"
POST_PLATFORMS=tiktok,instagram node -e "
const PLATFORMS = (process.env.POST_PLATFORMS || 'tiktok,instagram,youtube').split(',').map(s=>s.trim().toLowerCase()).filter(Boolean);
console.log('parsed:', PLATFORMS);
console.log('tiktok?', PLATFORMS.includes('tiktok'));
console.log('youtube?', PLATFORMS.includes('youtube'));
"
```
Expected: syntax OK + `parsed: [ 'tiktok', 'instagram' ]` + `tiktok? true` + `youtube? false`。

- [ ] **B2.4 — Anicca runtime 側にも同パッチ反映 (= ~/.openclaw のも 3 platform 化、 但し env で YT-only 維持)**

Run:
```bash
diff ~/.openclaw/skills/mau-tiktok/scripts/post-to-postiz.js ~/.cache/anicca-oss-scaffold/mau-clipping/scripts/post-to-postiz.js | head -50
# 内容を反映:
cp ~/.cache/anicca-oss-scaffold/mau-clipping/scripts/post-to-postiz.js ~/.openclaw/skills/mau-tiktok/scripts/post-to-postiz.js
```

- [ ] **B2.5 — Anicca runtime cron message に POST_PLATFORMS=youtube 追加 (= 従来挙動維持)**

Edit `~/.openclaw/cron/jobs.json`、 `mau-tiktok-en-morning` + `mau-tiktok-en-evening` の payload.message を更新:

Old:
```
node post-to-postiz.js --lang en
```

New:
```
POST_PLATFORMS=youtube node post-to-postiz.js --lang en
```

実装:
```bash
python3 -c "
import json
fp='/Users/anicca/.openclaw/cron/jobs.json'
j=json.load(open(fp))
patched=0
for job in j['jobs']:
    if 'mau-tiktok' in job.get('name',''):
        msg=job['payload'].get('message','')
        if 'POST_PLATFORMS=youtube' not in msg and 'post-to-postiz.js --lang' in msg:
            job['payload']['message'] = msg.replace('node post-to-postiz.js --lang', 'POST_PLATFORMS=youtube node post-to-postiz.js --lang')
            patched += 1
            print(f'patched {job[\"name\"]}')
json.dump(j, open(fp,'w'), indent=2)
print(f'total patched: {patched}')
"
openclaw gateway restart 2>&1 | tail -5
```
Expected: 2-4 cron patched + gateway restart success。

- [ ] **B2.6 — .env.example + SKILL.md + README.md + QUICKSTART.md + install.sh + LICENSE + .gitignore**

Write each (構造は B1 と同形、 中身は mau-clipping 用):

`.env.example`:
```bash
# mau-clipping — environment variables
POSTIZ_API_KEY="..."
POSTIZ_TT_INTEGRATION_ID=""
POSTIZ_IG_INTEGRATION_ID=""
POSTIZ_YT_INTEGRATION_ID=""
POST_PLATFORMS="tiktok,instagram,youtube"   # comma-separated, default 3-platform
```

`SKILL.md`:
```markdown
---
name: mau-clipping
description: "Viral YouTube Shorts hook + CTA stitching for TikTok + IG + YT. Grabs the first 3s of a proven viral video, stitches your 6s CTA, posts to 3 platforms via Postiz."
homepage: https://github.com/Daisuke134/mau-clipping
metadata:
  tags: tiktok, youtube, instagram, video, marketing, automation, postiz, ffmpeg, yt-dlp
  requires:
    bins: [ffmpeg, ffprobe, yt-dlp, node]
    env: [POSTIZ_API_KEY]
---

# mau-clipping

Inspired by [@maboroshi_app](https://x.com/maboroshi_app) — 7M views by stitching the first 3s of viral YouTube Shorts with a CTA, posted to 3 platforms.

## Use when

- You have a CTA video (your product / service / story) you want to amplify daily.
- You have a list of YouTube channels whose Shorts go viral, and you want to "borrow" their first 3s as hooks.

## Quick run

```bash
node scripts/scrape-hooks.js --lang en --count 1
node scripts/trim-and-stitch.js --lang en --count 1
POST_PLATFORMS=tiktok,instagram,youtube node scripts/post-to-postiz.js --lang en
```

Full setup: `QUICKSTART.md`.
```

`README.md` (similar shape to B1.5 but for mau-clipping、 cost = $0-15/mo Postiz、 architecture diagram は spec § Phase C を参照)。

`QUICKSTART.md` (similar shape to B1.6 but for mau-clipping)。

`install.sh` (similar shape to B1.7 but check ffmpeg/yt-dlp/node only、 no whisper)。

`.gitignore` (same as B1 minus character.yaml/bank.jsonl)。

`LICENSE` (= MIT、 same as B1)。

- [ ] **B2.7 — scaffold 検証**

Run:
```bash
SCAFFOLD=~/.cache/anicca-oss-scaffold/mau-clipping
find "$SCAFFOLD" -maxdepth 2 -type f | sort
bash -n "$SCAFFOLD/install.sh" && echo "install.sh syntax OK"
```
Expected: 全 file 揃い + syntax OK。

### Task B3: GitHub repo 作成 + initial push

**Files:** 触らない (GitHub 側 + push only)

- [ ] **B3.1 — anicca-monk-factory repo 作成 + initial commit**

Run:
```bash
cd ~/.cache/anicca-oss-scaffold/anicca-monk-factory
git init
git add -A
git status --short | head -30
git -c user.name="Daisuke Narita" -c user.email="keiodaisuke@gmail.com" commit -m "feat: initial OSS publish — anicca-monk-factory skill (P1-P5 applied)"
gh repo create Daisuke134/anicca-monk-factory --public --source=. --remote=origin --push --description "Yang-Mun-style AI monk video factory — daily talking-head shorts on TikTok + IG, end-to-end automated"
gh repo view Daisuke134/anicca-monk-factory --json url -q .url
```
Expected: public repo created、 URL = `https://github.com/Daisuke134/anicca-monk-factory`。

- [ ] **B3.2 — mau-clipping repo 作成 + initial commit**

Run:
```bash
cd ~/.cache/anicca-oss-scaffold/mau-clipping
git init
git add -A
git -c user.name="Daisuke Narita" -c user.email="keiodaisuke@gmail.com" commit -m "feat: initial OSS publish — mau-clipping skill (D8 POST_PLATFORMS env)"
gh repo create Daisuke134/mau-clipping --public --source=. --remote=origin --push --description "Viral YouTube Shorts hook + CTA stitching for TikTok + IG + YT (inspired by @maboroshi_app)"
gh repo view Daisuke134/mau-clipping --json url -q .url
```
Expected: public repo created、 URL = `https://github.com/Daisuke134/mau-clipping`。

### Task B4: OSS user fresh-install smoke test (= verify gate)

**Files:** 触らない (live test)

**Goal:** OSS user の experience を Mac Mini 上の別 dir で再現、 fresh install が通るか確認。

- [ ] **B4.1 — anicca-monk-factory を fresh dir に clone + install**

Run:
```bash
FRESH=~/.cache/oss-fresh-test/anicca-monk-factory-$(date +%s)
mkdir -p "$(dirname "$FRESH")"
git clone https://github.com/Daisuke134/anicca-monk-factory "$FRESH"
cd "$FRESH"
bash install.sh 2>&1 | head -30
```
Expected: install.sh doctor が prereq report (.env / character.yaml / bank.jsonl が missing と出る = 正常)。

- [ ] **B4.2 — mau-clipping を fresh dir に clone + install**

Run:
```bash
FRESH=~/.cache/oss-fresh-test/mau-clipping-$(date +%s)
mkdir -p "$(dirname "$FRESH")"
git clone https://github.com/Daisuke134/mau-clipping "$FRESH"
cd "$FRESH"
bash install.sh 2>&1 | head -30
```
Expected: install.sh doctor が prereq report (.env missing と出る = 正常)。

- [ ] **B4.3 — fresh dir cleanup**

Run:
```bash
rm -rf ~/.cache/oss-fresh-test/
```

### Task B5: X 告知 draft + humanizer + verbatim-guard

**Files:**
- Create: `.worktrees/skill-trio-oss/docs/superpowers/specs/oss-launch-posts.md`

**Goal:** X 告知文を humanizer + verbatim-guard 通したら、 投稿待ち状態にする (実投稿は Dais 承認後)。

- [ ] **B5.1 — anicca-monk-factory 用 X post draft**

Write `.worktrees/skill-trio-oss/docs/superpowers/specs/oss-launch-posts.md`:

```markdown
# OSS Launch X Posts (drafts, 投稿前 Dais 承認 + verbatim-guard 通し)

## anicca-monk-factory

Built a skill that generates AI monk videos like @yangmun2 — locked face, locked voice, 30-script bank rotation → HeyGen render → caption burn → TikTok + IG. One `bash install.sh`.

Inspired by https://x.com/shalevhvs/status/2042242260784537736

github.com/Daisuke134/anicca-monk-factory

## mau-clipping

Built a skill that clones what @maboroshi_app is running on YouTube — grab the first 3s of a viral Short, stitch your CTA, post to TikTok + IG + YT. One `bash install.sh`.

Inspired by https://x.com/maubaron/status/2030716132093460742

github.com/Daisuke134/mau-clipping
```

- [ ] **B5.2 — humanizer 通し**

Run:
```bash
echo "<paste anicca-monk-factory text>" | humanizer
echo "<paste mau-clipping text>" | humanizer
```
保存: humanizer 後の出力で `oss-launch-posts.md` を更新。

- [ ] **B5.3 — verbatim-guard 通し (= HARD RULE 文体盗用 防止)**

Run:
```bash
bash ~/.openclaw/skills/_shared/lib/verbatim-guard.sh check oss-launch-posts.md 2>&1 | head -20
```
Expected: 0 hit (= 既存 anicca account-history.jsonl と verbatim 一致なし)。

- [ ] **B5.4 — X (投稿) は Dais の手動承認後**

Open Slack #metrics、 draft を投稿 + Dais 承認待ち。 自分では X に投げない (= HARD RULE 公式アカウント保護)。

### Task B6: worktree merge + push → dev

**Files:** worktree → dev branch

- [ ] **B6.1 — worktree commit + push**

Run:
```bash
cd /Users/anicca/anicca-project/.worktrees/skill-trio-oss
git add -A
git status --short
git commit -m "feat(oss): publish anicca-monk-factory + mau-clipping skill repos, X launch drafts"
git push -u origin feature/skill-trio-oss
```
Expected: branch push success。

- [ ] **B6.2 — PR 作成 (worktree → dev)**

Run:
```bash
gh pr create --base dev --head feature/skill-trio-oss \
  --title "feat(oss): publish anicca-monk-factory + mau-clipping skill repos" \
  --body "$(cat <<'EOF'
## Summary
- monk-factory P1-P5 verified in Phase A (TikTok+IG live)
- 2 OSS repos created: anicca-monk-factory, mau-clipping
- X launch drafts saved to docs/superpowers/specs/oss-launch-posts.md

## Test plan
- [x] fresh `git clone` + `bash install.sh` smoke test passes
- [x] Anicca runtime mau-tiktok cron uses `POST_PLATFORMS=youtube` for backward compat
- [x] monk-factory 24h verify gate (Task A6) green
EOF
)"
```
Expected: PR URL。

- [ ] **B6.3 — worktree cleanup (PR merge 後)**

Run after PR merge:
```bash
cd /Users/anicca/anicca-project
git worktree remove .worktrees/skill-trio-oss
git branch -d feature/skill-trio-oss
```
Expected: worktree + branch cleanup。

---

## Phase C: 観測 + 後追い修正

### Task C1: 投稿後 7 日間の観察

**Files:** 触らない

- [ ] **C1.1 — X 投稿後の反応観測**

Run daily:
```bash
# X post engagement check (anicca-monk-factory + mau-clipping)
gh repo view Daisuke134/anicca-monk-factory --json stargazerCount,forkCount,openIssuesCount
gh repo view Daisuke134/mau-clipping --json stargazerCount,forkCount,openIssuesCount
```
Expected: star / issue 数の推移を Slack #metrics に digest。

- [ ] **C1.2 — Issue 来たら対応**

GitHub issues に対応、 重大 bug は hotfix → patch release。

### Task C2: naist v2 着手判定 (= 別 spec)

**Files:** 触らない

- [ ] **C2.1 — 安定 7 日後、 naist OSS 化を再評価**

Phase C 終了後、 naist の OSS 化 (academic-integrity refactor) を別 spec で評価。 本 plan の scope 外。

---

## Self-review (= 書いた本人の最終 check、 spec gap 探し)

| Spec 要求 | 対応 task |
|---|---|
| D1 CLI 化しない | Phase A + B 全部 bash + JS + scaffold、 CLI 化なし |
| D2 HeyGen API 不採用 | A1-A6 で camofox + UI 維持 |
| D3 human-in-loop 禁止 | A1 timeout 延長 + A4 recovery cron で人間不要 |
| D4 3 独立 repo | B3.1 + B3.2 = 2 repo (naist 除外) |
| D5 Dais profile 同梱なし | B1.2 character.yaml.example が placeholder のみ、 face/voice/bank は OSS user 任せ |
| D6 naist defer | Phase B から除外、 Task C2 で v2 |
| D7 monk 5 パッチ即実行 | Phase A 全部 |
| D8 mau YT-only 解除 | B2.2 + B2.5 (Anicca runtime は env で YT-only 維持) |
| § 4.1.4 P1-P5 全部 | A1=P1, A2=P2+P4, A3=P5, A4=P3, A0=P4-stale-lock |
| § 6 install.sh template | B1.7 + B2.6 |
| § 7 Risks 対応 | A1 60min timeout, B1.7/B2.6 doctor で Postiz integration check |
| § 8 Verification | A6 (monk 24h gate) + B4 (fresh install smoke) |

| Placeholder scan | 結果 |
|---|---|
| TBD/TODO/XXX/FIXME | A6.5 の `<URL>` `2026-06-0X` は live observation 後に埋める意図、 これは plan の placeholder ではなく runtime fill-in |
| "implement later" | 無し |
| "add appropriate error handling" | 無し (具体的な if/echo を書いた) |
| "similar to Task N" | 無し (B2.6 で「B1 と同形」とは書いたが install.sh の中身まで再列挙した) |

| Type consistency | OK |
|---|---|
| `HEYGEN_MAIL_TIMEOUT_MIN` | A1, B1.3 で同名 |
| `POST_PLATFORMS` | B2.2, B2.5, B2.6 で同名、 値も同 format |
| skill name `anicca-monk-factory` / `mau-clipping` | 全 task で一貫 |
| repo URL `github.com/Daisuke134/...` | 全 task で一貫 |

Self-review pass。 spec gap なし。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-04-skill-trio-oss-and-monk-fix.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — Anicca が fresh subagent per task で dispatch、 task 間で review、 fast iteration。 Phase A の A0-A6 を 1 task 1 subagent で連続実行 (= 24h monk verify gate まで)、 Phase B は merge gate 通ってから。

2. **Inline Execution** — このセッション内で executing-plans skill 使って checkpoint 単位で実行。 Phase A 各 task 完了後 Dais に報告 → 続行 / 中断判断。

Which approach? — Dais の return 待ち。
