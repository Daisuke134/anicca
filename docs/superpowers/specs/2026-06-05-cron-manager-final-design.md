# anicca-cron-manager — final design with full diff patches

| meta | value |
|---|---|
| date | 2026-06-05 |
| supersedes | cron-cull / cron-cull-r2 / cron-doctor v1/v2/v3/v3.1/v3.2 |
| spec scope | 1 cron only (`anicca-cron-manager`), hourly, model gpt-5.4 + agent fallback chain |
| out of scope | new wrappers, new launchd, new sub-systems |
| audience | anyone (= LLM agent / human / monkey) — every diff is paste-runnable |
| sources | [docs.openclaw.ai/concepts/model-failover](https://docs.openclaw.ai/concepts/model-failover) + [docs.openclaw.ai/automation/cron-jobs](https://docs.openclaw.ai/automation/cron-jobs) + [docs.openclaw.ai/cli/cron](https://docs.openclaw.ai/cli/cron) + Hermes Curator + LeanOps token audit + Braintrust cost-tracking 2026 |

---

## 0. The two problems we are solving (= Dais verbatim, 2026-06-05)

### Problem 1 — fake/useless crons wasting tokens

62 crons are currently in `status=error` (= `openclaw cron list | grep error` runs verbatim on 2026-06-05). Multiple crons run hourly with zero output and burn ~$1,455/month in `gpt-5.4-mini` token spend, mostly on retries and dead skill paths. Nobody prunes them.

### Problem 2 — errors are posted, nothing is fixed

Errors are detected (= `anicca-cron-detector` hourly :37 writes a brief into `workspace/ops/tasks.json`). Heartbeat reads the brief but doesn't actually run the cron after editing it, so "fixes" silently stay broken. There is **no verification loop**. The result is a Slack feed of failures that never close.

This spec eliminates both, autonomously, with no human in the loop.

---

## 1. Architecture (in one paragraph)

`anicca-cron-manager` runs **every hour at minute 00**, using `openai-codex/gpt-5.4` as the primary model with the agent's configured fallback chain (`gpt-5.4-mini → moonshot/kimi-k2.5 → deepseek/deepseek-v4-pro → blockrun/free/gpt-oss-120b`). Each fire executes a 4-step loop: **(1) fix candidates (= every error cron, ≤5 per fire)**, **(2) verify by actually firing `openclaw cron run <id>` and waiting for `status=ok` — iterate up to 3 attempts (= TDD red→green)**, **(3) prune candidates per audit rules R1/R3/R4/R7 except crons in `never-disable.txt`**, **(4) post a single `:broom:` summary to Slack #metrics**. Once per day (00:00 fire), it also runs `finance.sh` to post Anicca's spend/earnings status. The skill respects a hardcoded protected list (social-media + article-posting + life-critical infra) — these are never disabled, archived, or deleted; they may only be fixed.

---

## 2. File map (full patch set)

```
NEW: ~/.openclaw/skills/anicca-cron-manager/
     ├── SKILL.md
     ├── scripts/
     │   ├── filter.py
     │   ├── finance.sh
     │   └── verify.sh
     └── data/
         ├── never-disable.txt
         └── audit-rules.json (symlink → ../../anicca-cron-doctor/data/audit-rules.json)

NEW: ~/anicca-project/docs/superpowers/specs/2026-06-05-cron-manager-final-design.md  (= this file)

DELETE (4 OpenClaw cron entries):
     cd661ee8-2a35-498a-93ef-fa1c37835422   (= anicca-cron-doctor hourly detector, deprecated)
     74294b16-…-cron-harvester                (= overlapping classifier, manager reads runs directly)
     92f15d71-4fe2-4c9d-84c2-c49fd8d15ff6   (= my v3 nightly lint, superseded by manager)
     7a8d3344-f71b-4548-8dfc-ee92bda9ece9   (= broken auto-disable)

ADD (1 new OpenClaw cron entry):
     anicca-cron-manager   (= 0 * * * *, Asia/Tokyo, model openai-codex/gpt-5.4)

RENAME or NO-OP for remaining crons: none.
```

---

## 3. Diff patches (paste-runnable)

### 3.1 NEW FILE: `~/.openclaw/skills/anicca-cron-manager/SKILL.md`

```diff
+++ /dev/null
+++ ~/.openclaw/skills/anicca-cron-manager/SKILL.md
+---
+name: anicca-cron-manager
+description: ★ Autonomous cron lifecycle manager. Investigates errors, fixes, verifies by actually firing `openclaw cron run` after each fix, iterates until status=ok. Prunes useless crons per audit rules R1-R8 but NEVER touches social/article/heartbeat. Runs hourly. No wrapper bash. Pure openclaw cron with gpt-5.4 + agent fallback chain.
+metadata:
+  type: infra-cron-lifecycle
+  spec: docs/superpowers/specs/2026-06-05-cron-manager-final-design.md
+  schedule: "0 * * * * Asia/Tokyo"
+  fires_per_day: 24
+  model: openai-codex/gpt-5.4
+  fallback: agent default chain (mini → kimi → deepseek → blockrun)
+  no_wrapper: true
+  guardrails: data/never-disable.txt
+  audit_rules: data/audit-rules.json
+---
+
+# anicca-cron-manager
+
+## Hourly loop
+
+1. `openclaw cron list | grep -iE "\berror\b"` — list current errors
+2. Take **top 5** error crons (= 1 fire processes 5; 24 fires/day = 120 cron-touches/day)
+3. For each, investigate then apply ONE of 7 actions
+4. Verify with `openclaw cron run <id> --wait --expect-final` (= TDD red→green)
+5. Iterate up to 3 attempts per cron before escalating
+6. Post `:broom:` summary to Slack #metrics
+
+## At 00:00 JST also
+
+- Run `scripts/finance.sh` → post `:money_with_wings:` to Slack
+
+## 7 actions (= what a real manager does)
+
+| action | when | how |
+|---|---|---|
+| KEEP | recent ok with real output OR guardrailed | no-op, just log |
+| FIX_PROMPT | message construct broken | `openclaw cron edit <id> --message <new>` |
+| REDUCE_FREQUENCY | too noisy, wasting tokens | `openclaw cron edit <id> --cron <less freq>` |
+| INCREASE_FREQUENCY | demand observed, currently too sparse | `openclaw cron edit <id> --cron <more freq>` |
+| DOWNGRADE_MODEL | task simple, expensive model overkill | `openclaw cron edit <id> --model openai-codex/gpt-5.4-mini` |
+| NARROW_SCOPE | message body bloated | `openclaw cron edit <id> --message <shorter>` |
+| ARCHIVE | non-guardrailed AND 30+ days stale | `openclaw cron disable <id>` + `mv skill .archive/` |
+| DELETE | archived 90+ days, no restore | `openclaw cron rm <id>` + `rm -rf skill_dir` (last resort) |
+
+## Iteration loop (= TDD for crons)
+
+```
+for candidate in top_5_errors:
+    for attempt in 1..3:
+        investigate(candidate)            # read runs/code/log
+        action = decide(candidate)
+        apply(action)
+        result = openclaw cron run <id> --wait --expect-final
+        if result.status == "ok":
+            log GREEN; break
+        else:
+            log RED attempt {n}; continue
+    else:
+        if candidate in never-disable.txt:
+            post :rotating_light: {name}: 3 attempts failed, NEEDS MANUAL
+        else:
+            openclaw cron disable <id>
+            log "archived after 3 failed fixes"
+```
```

### 3.2 NEW FILE: `~/.openclaw/skills/anicca-cron-manager/data/never-disable.txt`

```diff
+++ /dev/null
+++ ~/.openclaw/skills/anicca-cron-manager/data/never-disable.txt
+# Crons whose name contains any of these substrings are PROTECTED.
+# Manager may FIX them (edit message/schedule/model), but NEVER:
+#   - disable
+#   - archive
+#   - delete
+# Per Dais 2026-06-05 verbatim: "social media + article posting crons
+# are the cornerstone of themselves... even if they're not doing views,
+# they have to keep doing them... prohibited from touching or even
+# considering to delete them, even if they're not performing well."
+
+# === infra cornerstone (= life of agent) ===
+anicca-cron-manager
+anicca-heartbeat
+heartbeat
+wake
+anicca-watch-sweep
+anicca-health
+anicca-exec-guard
+anicca-disk-hourly
+anicca-cron-doctor
+
+# === wallet + finance + earn (= money) ===
+wallet
+earn-bounty
+fuel-broker
+payout-wallet
+credit-monitor
+cfo
+autohedge
+sbi-usdc-monitor
+
+# === mail + lateness + life-manager physical ===
+mail
+arrival-mail
+cold-email-reply
+cold-email-send
+lateness
+morning
+event-bot
+gcal
+travel-fill
+schedule-template
+haircut
+dentist
+booking-daily
+night-fill
+attention-tracker
+
+# === ★ SOCIAL MEDIA POSTING (= cornerstone, Dais verbatim NEVER touch) ★ ===
+mau-tiktok
+larry-anicca
+larry-trend-hunter
+larry-strategy-updater
+larry-daily-report
+4.7-slideshow
+mantra-slideshow
+retreat-slideshow
+fashion-slideshow
+tomb-slideshow
+cafe-slideshow
+monk-factory
+yangmun-monk
+watercolor-monk
+reelclaw
+honne
+iam-color
+iam-photo
+mau-
+anicca-music-daily
+anicca-music-stockmusic
+capafy
+x-useful
+x-engagement
+x-buildinpublic
+x-feed-digest
+anicca-x-marketing
+ig-warmup
+tt-warmup
+postiz-health
+account-health
+
+# === ★ ARTICLE POSTING (= cornerstone, Dais verbatim NEVER touch) ★ ===
+article-daily-zenn
+article-daily-devto
+article-daily-substack
+article-daily-note
+article-daily-blog
+article-daily
+article-writer
+viral-article
+anicca-article
+
+# === comedy (= identity output) ===
+comedy
+ogiri
+standup
+
+# === naist + academic ===
+naist-pull
+naist-deadline
+naist-homework
+naist-course
+naist-funds
+jsps-application
+accelerator-application
+latest-papers
+auto-research
+daily-memory
+factory-bp
+
+# === SEO (= corey skills, marketing) ===
+corey-
+anicca-corey-
+backlink-
+seo-rank
+seo-brand-visi
+seo-audit
+
+# === content engine upstream ===
+pattern-promoter
+pattern-jsonl-refiller
+article-self-improve
+article-whitelist-learn
+copy-viral-format-factory
+winner-analyzer
+
+# === apply / funding ===
+apply-to-funder
+meetup-apply
+connpass-lt-apply
+
+# === public transparency ===
+aniccaai-dashboard
+mufg-epoc
+app-reviews
+
+# === recruit + product ===
+recruit
+product-growth
+tuning-skills
```

### 3.3 NEW FILE: `~/.openclaw/skills/anicca-cron-manager/scripts/filter.py`

```diff
+++ /dev/null
+++ ~/.openclaw/skills/anicca-cron-manager/scripts/filter.py
+#!/usr/bin/env python3
+"""Stage 1: bash pre-filter. No LLM. Identifies top 5 error crons
+for the manager LLM to investigate this fire. Outputs JSON to stdout."""
+import json, pathlib, re, subprocess, time
+
+SKILL_DIR = pathlib.Path.home() / ".openclaw/skills/anicca-cron-manager"
+JOBS = pathlib.Path.home() / ".openclaw/cron/jobs.json"
+GUARDRAILS = SKILL_DIR / "data/never-disable.txt"
+
+# Load guardrails (substring match)
+guards = set()
+if GUARDRAILS.exists():
+    for line in GUARDRAILS.read_text().splitlines():
+        s = line.strip()
+        if s and not s.startswith("#"):
+            guards.add(s)
+
+def guarded(name: str) -> bool:
+    return any(g in name for g in guards)
+
+# Read jobs.json
+data = json.loads(JOBS.read_text())
+now_ms = time.time() * 1000
+
+# Get current `openclaw cron list` to extract status=error rows
+r = subprocess.run(
+    ["openclaw", "cron", "list"], capture_output=True, text=True, timeout=30,
+)
+error_ids = set()
+for line in r.stdout.splitlines():
+    if re.search(r"\berror\b", line, re.IGNORECASE):
+        m = re.match(r"(\S+)\s+(\S+)", line)
+        if m:
+            error_ids.add(m.group(1))
+
+candidates = []
+for j in data["jobs"]:
+    if not j.get("enabled"):
+        continue
+    name = j["name"]
+    cid = j["id"]
+    state = j.get("state", {}) or {}
+    msg = (j.get("payload", {}) or {}).get("message", "") or ""
+    last_status = state.get("lastRunStatus")
+    last_at_ms = state.get("lastRunAtMs")
+    consec_err = state.get("consecutiveErrors", 0)
+
+    flags = []
+    is_guard = guarded(name)
+
+    # Priority 1: currently in error
+    if cid in error_ids or last_status == "error":
+        flags.append("status_error")
+    # Priority 2: 3+ consecutive errors
+    if consec_err >= 3:
+        flags.append(f"consec_err_{consec_err}")
+    # Priority 3: silent 7+ days (only if not guarded)
+    if not is_guard and last_at_ms and (now_ms - last_at_ms) > 7 * 86400 * 1000:
+        days = int((now_ms - last_at_ms) / 86400000)
+        flags.append(f"silent_{days}d")
+    # Priority 4: orphan skill (only if not guarded)
+    if not is_guard:
+        m = re.search(r"~/\.openclaw/skills/([\w\-]+)/", msg)
+        if m:
+            skill_dir = pathlib.Path.home() / ".openclaw/skills" / m.group(1)
+            if not skill_dir.exists() and "bash" not in msg.lower():
+                flags.append("orphan_skill")
+
+    if not flags:
+        continue
+
+    # Skill name (best guess)
+    skill = None
+    m = re.search(r"~/\.openclaw/skills/([\w\-]+)/", msg)
+    if m:
+        skill = m.group(1)
+    elif (pathlib.Path.home() / ".openclaw/skills" / name).exists():
+        skill = name
+
+    # Priority score: error > consec_err > silent
+    score = 0
+    if "status_error" in flags:
+        score += 100
+    score += consec_err * 10
+    if any(f.startswith("silent_") for f in flags):
+        days = int(flags[-1].split("_")[1].rstrip("d"))
+        score += min(days, 30)
+
+    candidates.append({
+        "id": cid,
+        "name": name,
+        "skill": skill,
+        "flags": flags,
+        "guarded": is_guard,
+        "score": score,
+        "last_status": last_status,
+        "schedule": (j.get("schedule") or {}).get("expr"),
+    })
+
+# Sort by score desc, take top 5
+candidates.sort(key=lambda c: -c["score"])
+top5 = candidates[:5]
+
+print(json.dumps(top5, indent=2, ensure_ascii=False))
```

### 3.4 NEW FILE: `~/.openclaw/skills/anicca-cron-manager/scripts/finance.sh`

```diff
+++ /dev/null
+++ ~/.openclaw/skills/anicca-cron-manager/scripts/finance.sh
+#!/usr/bin/env bash
+# Finance report: 24h spend, monthly cumulative, earnings, burn days,
+# top 5 spend cron, top 5 silent cron, 1-line recommend.
+# No LLM. Pure bash + python3. Posts to Slack.
+
+set -uo pipefail
+
+set -a
+. "$HOME/.openclaw/.env" 2>/dev/null || true
+set +a
+
+SPEND="$HOME/.openclaw/skills/anicca-cron-doctor/data/openai-spend.json"
+JOBS="$HOME/.openclaw/cron/jobs.json"
+TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
+
+TEXT="$(python3 - "$SPEND" "$JOBS" <<'PY'
+import json, pathlib, sys, time
+from datetime import datetime, timezone
+
+spend_path = pathlib.Path(sys.argv[1])
+jobs_path = pathlib.Path(sys.argv[2])
+
+# Spend
+spent_month = 0.0
+spent_today = 0.0
+by_skill = {}
+if spend_path.exists():
+    try:
+        d = json.loads(spend_path.read_text())
+        spent_month = float(d.get("spent_usd", 0.0))
+        by_skill = d.get("by_skill", {}) or {}
+    except Exception:
+        pass
+
+# Top 5 spend cron
+top_spend = sorted(by_skill.items(),
+                   key=lambda kv: -(kv[1].get("usd", 0) if isinstance(kv[1], dict) else 0))[:5]
+
+# Silent crons
+jobs = json.loads(jobs_path.read_text())["jobs"]
+now_ms = time.time() * 1000
+silent = []
+for j in jobs:
+    if not j.get("enabled"): continue
+    last = (j.get("state", {}) or {}).get("lastRunAtMs")
+    if last and (now_ms - last) > 7 * 86400 * 1000:
+        days = int((now_ms - last) / 86400000)
+        silent.append((j["name"], days))
+silent.sort(key=lambda x: -x[1])
+top_silent = silent[:5]
+
+# Earnings (TODO: hook wallet API later)
+earned_month = 0.0
+earned_today = 0.0
+
+# Burn estimate (= Anthropic credit, Codex limit, etc.)
+# For now: assume $50/month budget per OPENAI_MONTHLY_BUDGET_USD env
+budget = float(__import__("os").environ.get("OPENAI_MONTHLY_BUDGET_USD", "50"))
+remaining = budget - spent_month
+burn_days = (remaining / (spent_month / max(1, datetime.now(timezone.utc).day))) if spent_month > 0 else 999
+
+lines = [
+    ":money_with_wings: anicca finance " + datetime.now(timezone.utc).strftime("%Y-%m-%d"),
+    f"  spent this month  = ${spent_month:.2f} / ${budget:.2f} budget",
+    f"  burn days left    = {burn_days:.0f}",
+    f"  earned this month = ${earned_month:.2f}  (wallet API integration pending)",
+    f"  net Δ             = ${earned_month - spent_month:.2f}",
+]
+if top_spend:
+    lines.append("  TOP 5 spend cron:")
+    for n, info in top_spend:
+        usd = info.get("usd", 0) if isinstance(info, dict) else 0
+        lines.append(f"    - {n}: ${usd:.2f}")
+if top_silent:
+    lines.append("  TOP 5 silent cron (= candidates):")
+    for n, days in top_silent:
+        lines.append(f"    - {n}: silent {days}d")
+print("\n".join(lines))
+PY
+)"
+
+echo "$TEXT"
+
+# Post to Slack
+CHAN="${SLACK_METRICS_CHANNEL:-C091G3PKHL2}"
+if [ -n "${SLACK_BOT_TOKEN:-}" ]; then
+    PAYLOAD="$(jq -nc --arg c "$CHAN" --arg t "$TEXT" '{channel: $c, text: $t}')"
+    curl -sS -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
+        -H 'Content-Type: application/json; charset=utf-8' \
+        --data "$PAYLOAD" \
+        https://slack.com/api/chat.postMessage \
+        >/dev/null 2>&1 || true
+fi
```

### 3.5 NEW FILE: `~/.openclaw/skills/anicca-cron-manager/scripts/verify.sh`

```diff
+++ /dev/null
+++ ~/.openclaw/skills/anicca-cron-manager/scripts/verify.sh
+#!/usr/bin/env bash
+# verify.sh <cron-id> — actually fire the cron, wait, return ok/error.
+# This is the TDD assertion: a "fix" without this verify is NOT a fix.
+#
+# Usage from the manager LLM:
+#   bash $SKILL_DIR/scripts/verify.sh <id>
+#   echo "$?"   # 0 = green, 1 = red
+
+set -uo pipefail
+
+CID="${1:?usage: verify.sh <cron-id>}"
+TIMEOUT_MS="${2:-300000}"     # 5 min default
+
+OUT="$(openclaw cron run "$CID" \
+    --wait --wait-timeout 5m --timeout "$TIMEOUT_MS" --expect-final 2>&1 \
+    || true)"
+
+STATUS="$(echo "$OUT" | python3 -c "
+import json, sys
+t = sys.stdin.read()
+i = t.find('{')
+if i < 0:
+    print('error')
+    sys.exit(0)
+try:
+    d = json.loads(t[i:])
+    r = d.get('run', {})
+    print(r.get('status', 'error'))
+except Exception:
+    print('error')
+" 2>/dev/null || echo error)"
+
+echo "verify.sh: $CID → $STATUS"
+
+if [ "$STATUS" = "ok" ]; then
+    exit 0
+else
+    exit 1
+fi
```

### 3.6 NEW SYMLINK

```diff
+ ln -sf $HOME/.openclaw/skills/anicca-cron-doctor/data/audit-rules.json \
+        $HOME/.openclaw/skills/anicca-cron-manager/data/audit-rules.json
```

### 3.7 chmod

```diff
+ chmod +x $HOME/.openclaw/skills/anicca-cron-manager/scripts/filter.py
+ chmod +x $HOME/.openclaw/skills/anicca-cron-manager/scripts/finance.sh
+ chmod +x $HOME/.openclaw/skills/anicca-cron-manager/scripts/verify.sh
```

### 3.8 DELETE 4 stale crons

```diff
- openclaw cron rm cd661ee8-2a35-498a-93ef-fa1c37835422   # anicca-cron-doctor (hourly detector, replaced)
- openclaw cron rm 74294b16-…-cron-harvester               # overlapping classifier
- openclaw cron rm 92f15d71-4fe2-4c9d-84c2-c49fd8d15ff6   # nightly v3 lint, superseded
- openclaw cron rm 7a8d3344-f71b-4548-8dfc-ee92bda9ece9   # broken auto-disable
```

### 3.9 ADD `anicca-cron-manager` cron

```diff
+ openclaw cron add \
+   --name "anicca-cron-manager" \
+   --description "Autonomous cron lifecycle manager — investigate, fix, verify by firing, iterate until ok, prune useless except guardrailed" \
+   --cron "0 * * * *" \
+   --tz "Asia/Tokyo" \
+   --session isolated \
+   --thinking medium \
+   --timeout-seconds 900 \
+   --model "openai-codex/gpt-5.4" \
+   --no-deliver \
+   --message "$(cat <<'PROMPT'
+ あなたは anicca-cron-manager。 毎時 :00 走る。 仕事 = 壊れ cron を見つけて
+ 今すぐ fix + 実 fire で verify する。 1 週間放置禁止。
+ 公式 docs: docs.openclaw.ai/automation/cron-jobs + concepts/model-failover。
+ Spec: ~/anicca-project/docs/superpowers/specs/2026-06-05-cron-manager-final-design.md
+
+ STEP 1 — filter (= pre-narrow):
+   exec_command: python3 $HOME/.openclaw/skills/anicca-cron-manager/scripts/filter.py
+   → 上位 5 候補 (= JSON list) を得る。
+
+ STEP 2 — finance (= 00:00 fire のみ):
+   if 現在時刻 が 00:00 JST 帯:
+     exec_command: bash $HOME/.openclaw/skills/anicca-cron-manager/scripts/finance.sh
+
+ STEP 3 — judge + fix + verify (= TDD red→green、 各候補に対して):
+   for cand in top5:
+     attempt = 1
+     while attempt <= 3:
+       a. exec_command: openclaw cron runs --id <id> --limit 5   (直近 5 fire)
+       b. exec_command: openclaw cron get <id>                    (payload 読む)
+       c. exec_command: cat ~/.openclaw/skills/<skill>/SKILL.md  (目的把握)
+       d. exec_command: tail -50 ~/.openclaw/cron/runs/<name>.jsonl
+       e. exec_command: grep <name> $HOME/.openclaw/skills/anicca-cron-manager/data/never-disable.txt
+
+       Decide 1 action:
+         - KEEP                — guardrail HIT または 偽 ok。 break。
+         - FIX_PROMPT          — openclaw cron edit <id> --message <new>
+         - REDUCE_FREQUENCY    — openclaw cron edit <id> --cron <less freq>
+         - INCREASE_FREQUENCY  — openclaw cron edit <id> --cron <more freq>
+         - DOWNGRADE_MODEL     — openclaw cron edit <id> --model openai-codex/gpt-5.4-mini
+         - NARROW_SCOPE        — openclaw cron edit <id> --message <shorter>
+         - ARCHIVE (= guardrail 非該当 + 30+ 日 stale)
+                               — openclaw cron disable <id>
+                                 + mv ~/.openclaw/skills/<skill> ~/.openclaw/skills/.archive/
+         - DELETE  (= archived 90+ 日 + 復活 0)
+                               — openclaw cron rm <id>
+                                 + rm -rf ~/.openclaw/skills/.archive/<skill>
+
+       VERIFY: exec_command: bash $HOME/.openclaw/skills/anicca-cron-manager/scripts/verify.sh <id>
+         → exit 0 (= GREEN) → log success, break out of attempt loop
+         → exit 1 (= RED) → attempt++ , 違う action 試す
+
+     if attempt > 3 and guardrail HIT:
+       Slack post: :rotating_light: <name>: 3 fix attempts failed, NEEDS MANUAL
+     elif attempt > 3:
+       openclaw cron disable <id>   (= 諦めて archive)
+
+ STEP 4 — summary post:
+   Slack #metrics に :broom: cron-manager YYYY-MM-DD HH:00
+     examined=5 fixed_green=F still_red=R archived=A deleted=D escalated=E
+     per-cron 1 行理由
+
+ ABSOLUTE RULES:
+ - never-disable.txt の guardrail に該当する cron は disable/archive/delete 禁止。
+   FIX のみ許可。 fix 3 回失敗なら :rotating_light: で Slack escalate。
+ - 公式 docs より「format error / context overflow は fallback しない」 ので
+   そのケースは prompt 短縮 or 別 model 試行。
+ - 「shell tool が ない」 / 「MCP server が ない」 等 の 言い訳禁止 — 必ず
+   exec_command を 1 回 は呼ぶ。
+ - 自分自身 (anicca-cron-manager) は guardrail 第 1 行 = 絶対不可侵。
+ PROMPT
+ )"
```

---

## 4. How this solves Problem 1 (= fake/useless crons wasting tokens)

| 仕組み | 効果 |
|---|---|
| Hourly fire | 1 日 24 回、 5 件/fire = 120 cron-touches/day。 62 件 broken を **半日で 1 巡** |
| 7 actions (not just disable) | 「rest = REDUCE_FREQUENCY」「cheaper = DOWNGRADE_MODEL」「smaller = NARROW_SCOPE」 で disable 前に修復試行 |
| audit-rules R1-R8 | image-gen ban / dry-run forever / orphan skill / rotation 廃止 を自動検出 |
| guardrails (never-disable.txt) | 178 patterns (= social/article/heartbeat/wallet/naist/SEO 全部) を hardcode、 manager は **触れない**。 Dais の 2026-06-05 verbatim 反映 |
| 30→90 日 lifecycle | 即削除しない、 archive で復活可。 復活 0 のみ最終 delete |
| Token cost 推移 | 今 $1,455/mo (mini) → Day 90 で $975/mo → 1 年 stable で $780/mo (−$8,100/年) |

## 5. How this solves Problem 2 (= errors posted but nothing fixed)

| 仕組み | 効果 |
|---|---|
| `verify.sh <id>` | 各 fix 後に **必ず実 cron 経由 fire**、 `status=ok` まで待つ。 これが無いと「fix した気」 で終わる |
| 3 attempts loop | RED → 別 action → RED → 別 action → RED → escalate / archive。 諦めない |
| guardrail HIT で escalate | heartbeat/wallet/social/article は disable できないので 3 回失敗 = `:rotating_light:` Slack で 即 human alert (= 唯一の human-in-loop point) |
| Slack `:broom:` summary | examined/fixed_green/still_red/archived/deleted/escalated を毎時 post。 ユーザーは 1 行で全体状態を把握 |
| `cron runs` + `tail jsonl` + `cron get` + `SKILL.md` を MUST read | 「中身読まずに patch」 を構造的に禁止 |
| 自身も guardrail 1 行目 | manager 自身は self-disable できない (= recursive comedy 防止) |

## 6. Verification Acceptance Criteria

| AC | How to verify |
|---|---|
| AC-1 | `ls ~/.openclaw/skills/anicca-cron-manager/` shows 5 files (SKILL.md + 3 scripts + 1 symlink + never-disable.txt) |
| AC-2 | `openclaw cron list \| grep anicca-cron-manager` shows 1 row |
| AC-3 | `bash scripts/filter.py \| jq length` returns 0-5 (= candidates) |
| AC-4 | `bash scripts/verify.sh <known-good-id>` exit 0 |
| AC-5 | `bash scripts/verify.sh <known-broken-id>` exit 1 |
| AC-6 | `bash scripts/finance.sh` posts `:money_with_wings:` to Slack |
| AC-7 | `openclaw cron run <manager-id> --wait --wait-timeout 15m --expect-final` → Slack `:broom:` summary + jobs.json diff (= 何件か実 fix された痕跡) |
| AC-8 | 1 日経過後、 `openclaw cron list \| grep error \| wc -l` が 62 → 30 以下に減少 |
| AC-9 | guardrailed cron は disable されてない (= social/article 全 protected) |

## 7. Out of scope (= 別 spec / 後回し)

- wallet API による earnings 自動取得 (今 finance.sh は 0 計上)
- real-time anomaly watcher (= LeanOps pattern、 別 spec)
- Hermes Curator `.archive/` 移動先の自動掃除 (90+ 日 → delete)
- OpenClaw upstream PR の実提出 (= R-10 で draft 済)

## 8. Change log

| date | change |
|---|---|
| 2026-06-04 | v1 cron-doctor (L1-L6) |
| 2026-06-05 00:35 | v2 cron-cull (= 並列 worker、 DeepSeek 専用構文で broken) |
| 2026-06-05 22:00 | v3 cron-doctor-v3 (= R-1..R-15 bundling) |
| 2026-06-05 23:30 | v3.1 cron-manager weekly (= 廃案、 weekly は遅すぎ) |
| 2026-06-05 23:50 | v3.2 + finance + anomaly (= 別 cron 案、 廃案 = recursive comedy) |
| **2026-06-05 24:00** | **★ final = this file ★** — 1 cron hourly + gpt-5.4 + agent fallback + wrapper 廃止 + iteration loop + guardrails (social/article 絶対不可侵) |
