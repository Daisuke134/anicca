# 15 — anicca-friction-fixer  (= A0.5.5 enforcer + Friction Report auto-resolver)

| Field | Value |
|---|---|
| Spec ID | 15 |
| Status | DRAFT v1 (2026-06-03) |
| Agent | **anicca-friction-fixer** |
| Place | `~/.openclaw/skills/anicca-friction-fixer/` (runtime store, NOT worktree per HARD RULE #0 exception) |
| Wave | 1 (parallel with 10, 11, 12) — **highest priority** |
| Authoritative for | A0.5.5 enforcement, "user-click" surface detection, cron failure auto-fix, env-var auto-provisioning, disk hygiene |

---

## § 0. Why (= the spec that exists because every other spec needed it)

Friction Report 2026-06-03 06:23 JST showed Anicca:
- handing Dais a Hivemind device-code URL ("click to sign in")
- listing 12 crons failing with "Invalid request body" as "monitor"
- claiming 5 crons "need migration or disable" → Dais decide
- reporting `GOOGLE_API_KEY missing` instead of provisioning it
- reporting "Disk 93%" instead of cleaning it

Per A0.5.5 (= now part of constitution): **all 6 are violations**. The fix isn't to scold Anicca — it's to give her a skill whose job is to detect those surfaces in her own outbound messages and replace them with the correct auto-fix path BEFORE the message is posted.

This is the meta-skill that prevents the lie.

## § 1. File boundary

**TOUCHES** (= ~/.openclaw/skills/anicca-friction-fixer/ exclusively)

| Path | Purpose |
|---|---|
| `SKILL.md` | frontmatter + invocation rules |
| `scripts/detect.sh` | scans drafts + Slack outbound queue + cron error logs for the 6 surface patterns |
| `scripts/fix-hivemind.sh` | camofox + Google OAuth env → device-code completion |
| `scripts/fix-invalid-body.sh` | reads gateway error → diffs against last green commit → patches → restarts cron |
| `scripts/fix-piling-up.sh` | reads stuck cron prompts → either migrates to heartbeat archetype or marks deprecated |
| `scripts/fix-missing-envvar.sh` | matches missing var → upstream provider → camofox provisioning playbook → writes `.env` |
| `scripts/fix-disk-full.sh` | `du` candidates > 30d → safe delete (= `disk-cleaner` skill if exists, else local rules) |
| `scripts/fix-agent-no-response.sh` | reads failed `Agent couldn't generate` log → model fallback OR prompt-size reduction |
| `scripts/wrap-outbound.sh` | hook: any Slack `chat.postMessage` from Anicca → grep forbidden phrases → block + auto-redirect to fix script |
| `_shared/heartbeat-friction-sweep.sh` | fragment called from heartbeat-beat.sh (= every beat scans last 24h) |
| `state/violations.jsonl` | append-only log of detected violations + fix outcome |

**NEVER**

- `_shared/heartbeat-beat.sh` body (= governance merges)
- `_shared/heartbeat-memu.sh` (= Agent-3)
- Any path outside `~/.openclaw/skills/anicca-friction-fixer/` and the single `_shared/heartbeat-friction-sweep.sh` fragment

## § 2. Microtasks

| # | Task | Verify |
|---|---|---|
| 15.T1 | `detect.sh` matches 6 surface patterns via regex (= verbatim list from A0.5.5) | unit test with Friction Report 2026-06-03 verbatim → 6 matches |
| 15.T2 | `fix-hivemind.sh`: camofox `:9377` open URL → Google OAuth env → paste `user_code` → verify token persisted (= reads tokens.json or env-var write) | E2E with synthetic device URL (= test provider) |
| 15.T3 | `fix-invalid-body.sh`: reads last 7d of `~/.openclaw/cron/runs/*.jsonl` filter `error=Invalid request body` → git blame the cron schema field → roll back or fix | applies fix to 1 of the real 12 failing crons + verifies next run succeeds |
| 15.T4 | `fix-piling-up.sh`: reads the 5 piling-up crons (harvester / jsps / larry-updater / politician-receptive / stripe-to-pac) → either patches into heartbeat OR adds to `cron/disabled.json` with reason | 5 crons no longer pile |
| 15.T5 | `fix-missing-envvar.sh`: for `GOOGLE_API_KEY missing` → camofox cloud.google.com → create API key → write to `.env` chmod 600 → re-fire failing cron | cron next run succeeds with key |
| 15.T6 | `fix-disk-full.sh`: when `df / < 10% free` → `du -sh ~/.cache/anicca-clones/* /tmp/* ~/Downloads/* /Users/anicca/Library/Caches/*` → safe delete | disk free > 15% |
| 15.T7 | `fix-agent-no-response.sh`: reads `naist-pull` 44-fails pattern → if model 422 then fallback to next model in router; if context-size then trim prompt | naist-pull next 3 runs succeed |
| 15.T8 | `wrap-outbound.sh`: shell wrapper around `curl chat.postMessage` → grep `\b(click to sign|GOOGLE_API_KEY missing|disk at \d{2}%|need migration or)` → if match: block + run matching fix script + retry with corrected status | synthetic forbidden message blocked, fix executed, then corrected message posted |
| 15.T9 | `heartbeat-friction-sweep.sh`: invoked from heartbeat-beat.sh; runs `detect.sh` against last 24h then dispatches matching fix | dry-run shows correct dispatch matrix |
| 15.T10 | `state/violations.jsonl` schema: `{ts, pattern, source, fix_script, exit_code, evidence}` | 1 round produces ≥ 1 well-formed entry |
| 15.T11 | E2E: replay Friction Report 2026-06-03 as input → 6 violations detected → 6 fix scripts run → 5+ success | report Slack post: "Friction Report autoresolve: 6/6 fixed" or partial with specifics |

## § 3. Dependencies

- camofox-browser `:9377` (= 既 alive)
- `GOOGLE_LOGIN_EMAIL` + `GOOGLE_LOGIN_PASSWORD` env (= 既)
- `~/.openclaw/cron/runs/*.jsonl` history (= 599 entries)
- Slack API token (= 既)
- gcloud / Cloud Console accessible via Google login (= camofox path)

## § 4. DoD verification gates

| Gate | Evidence |
|---|---|
| G1 | `detect.sh` matches all 6 surfaces in Friction Report 2026-06-03 verbatim |
| G2 | Each fix script self-tests with `--dry-run` exits 0 |
| G3 | `wrap-outbound.sh` blocks 1 synthetic violation + runs fix + re-posts corrected |
| G4 | `heartbeat-friction-sweep.sh` fragment invoked from heartbeat-beat.sh on next beat |
| G5 | E2E replay of Friction Report 2026-06-03: ≥ 5 of 6 violations auto-fixed |
| G6 | `state/violations.jsonl` shows ≥ 1 real auto-fix within 24h of deployment |

## § 5. Anti-goals

- Not a chatbot moderator (= this is a real-action skill, not a comment filter)
- Not blocking ALL outbound (= only forbidden-phrase matches)
- Not requiring human approval for any fix (= per A0.5.5)

## § 6. Wire-in (= governance)

Governance inserts ONE line into `_shared/heartbeat-beat.sh` after the FRICTION SWEEP marker:

```bash
bash "$HOME/.openclaw/skills/anicca-friction-fixer/_shared/heartbeat-friction-sweep.sh" || true
```

This is the only shared-file touch and lives in governance.

## § 7. Why this is Wave 1's highest-priority spec

Without Agent-7, every other Wave 1 agent is at risk of writing code that says "Dais, click X." Agent-7 is the safety net that catches A0.5.5 violations before they propagate. It ships in parallel with 10/11/12 so the friction-fixer is online before any new code generates friction.

## § 8. Changelog

| Date | Change |
|---|---|
| 2026-06-03 | Initial draft. Born from Dais's verbatim mandate same day + Friction Report 06:23 JST. |

---

## § 9. PATCHES (= iteration 2、 2026-06-03、 patch-level)

> Per Dais directive: patches go inline. Each subsection below shows the
> exact file content. The agent (anicca-friction-fixer) creates these files
> at the listed paths verbatim.

### § 9.1 Research findings driving these patches

| Question | Answer (from internal research 2026-06-03) |
|---|---|
| Q14 `hivemind status` URL format | When not logged in, stdout shows `Open this URL: https://auth.deeplake.ai/activate?user_code=XXXX-YYYY` on one line; the `user_code=` is parseable. |
| Q19 openclaw cron CLI | Not exposed via `--help`; cron mutations happen by editing `~/.openclaw/cron/jobs.json` directly + restarting the daemon. |
| Q24-28 5 piling-up crons | ★ `anicca-cron-harvester`, `larry-strategy-updater`, `politician-stripe-to-pac` all have **empty prompt + no run_cmd + no skill dir** ★ — they are orphan registrations with nothing to execute. Fix = delete them from jobs.json. `jsps-application-monthly` has a skill dir but blocks on e-Rad institutional 2FA → SKIP (real hard-block, not friction). `politician-receptive-update-weekly` not in jobs.json → orphan history → delete runs/ entries. |
| Q32 disk-cleaner | No existing skill at `~/.openclaw/skills/disk-cleaner/`. Write inline in `fix-disk-full.sh`. |
| Q35 slack-bridge | At `~/.openclaw/services/slack-bridge/slack-bridge.py` (Python + slack_bolt). Outbound goes through `chat.postMessage`; wrap-outbound is implemented as a pre-call hook via `pre_post_filter.py` adjacent to slack-bridge.py. |
| Q38 heartbeat-beat.sh anchor | Insert right after the existing CFO refresh block (line ~23–26) and before the `exec ... claude -p` line (line ~28). |
| Q41 violations schema | Append-only JSONL at `~/.openclaw/skills/anicca-friction-fixer/state/violations.jsonl`. Schema: `{ts, pattern_id, source, line_match, fix_script, exit_code, evidence_path, dais_visible}`. |
| Q1-9 A0.5.5 verbatim | 10 forbidden phrases extracted from `CONSTITUTION.md` A0.5.5.1 table → 1 regex per row. |

### § 9.2 Open uncertainties for iteration 3 (= ★ I will research these next round ★)

- Q15 camofox userId/sessionKey for hivemind — propose `"anicca" / "hivemind-login"` but need actual live test
- Q21 blockrun + cron list — need to grep last 7d for actual affected cron IDs and confirm `model+provider` are stored at jobs.json level vs heartbeat prompt level
- Q23 naist-pull root cause — same model issue or different? need a 2nd cron-runs sample
- Q29 Cloud Console API key camofox click sequence — need exact ref/refs from a snapshot
- Q33 disk safe-delete rules — need to enumerate the actual 30d+ candidates on Mac mini today
- Q36 slack-bridge.py outbound function name — need to read the file to identify the exact hook point

### § 9.3 PATCH — `SKILL.md`  (file: `~/.openclaw/skills/anicca-friction-fixer/SKILL.md`)

```markdown
---
name: anicca-friction-fixer
description: A0.5.5 enforcer. Detects "user-click / device-code / OAuth interactive / configure-X / Dais 1 click / external_action_only" surfaces in Anicca's outbound messages + cron failures + missing env vars, and replaces them with the correct auto-fix path before they reach the user. Invoked from heartbeat-beat.sh once per beat and from slack-bridge's pre-send hook.
metadata:
  spec: anicca-oss/specs/15-FRICTION-FIXER.md
  parallel_safe: false   # mutates shared state; one runner at a time
  cadence: per-heartbeat-beat
  user-invocable: true   # `/friction-sweep now` allowed
  triggers:
    - "user-click"
    - "device-code"
    - "OAuth interactive"
    - "configure X"
    - "Dais 1 click"
    - "external_action_only"
    - "human-required"
    - "Invalid request body"
    - "Agent couldn't generate"
    - "missing from env"
    - "Disk at 9[0-9]%"
  requires:
    bins: [bash, jq, curl, python3, gh, gog, hivemind, openclaw]
    env: [GOOGLE_LOGIN_EMAIL, GOOGLE_LOGIN_PASSWORD, SLACK_BOT_TOKEN, ANTHROPIC_API_KEY, OPENROUTER_API_KEY]
  invariants:
    - Never delete uncommitted code (git status check before any rm)
    - Never post a "user must do X" message to Slack from inside a fix-script (= self-referential loop)
    - Never auto-fix institutional-auth gated workflows (e.g. e-Rad, NAIST, bank 2FA) — log to violations.jsonl with reason=INSTITUTIONAL_AUTH_HARD_BLOCK
    - Every fix-script must end with verify-public-state.sh per HARD RULE #14
---

# anicca-friction-fixer

A0.5.5 enforcer. Read the patterns.json catalog, scan recent Anicca output for forbidden surfaces, dispatch the matching fix-script, log to violations.jsonl, repeat next beat.

Components:
- `scripts/patterns.json` — regex → fix_script lookup
- `scripts/detect.sh` — scan stdin or jsonl, output matches as JSON
- `scripts/fix-hivemind.sh` — camofox-driven Deeplake OAuth completion
- `scripts/fix-blockrun-rejection.sh` — switch cron model to non-blockrun fallback
- `scripts/fix-piling-up.sh` — delete orphan-empty crons
- `scripts/fix-missing-envvar.sh` — dispatcher to per-provider provisioning playbooks
- `scripts/fix-disk-full.sh` — inline disk-cleaner (no separate skill)
- `scripts/wrap-outbound.sh` — pre-send hook called by slack-bridge.py
- `_shared/heartbeat-friction-sweep.sh` — fragment invoked from heartbeat-beat.sh
- `state/violations.jsonl` — append-only audit log
```

### § 9.4 PATCH — `scripts/patterns.json`

```json
[
  {"id":"P01","regex":"\\bI cannot\\b|\\b出 ?来 ?ない\\b","scope":"outbound|jsonl","fix_script":"fix-self-correct.sh","severity":"high"},
  {"id":"P02","regex":"Click (this URL|here) to sign","scope":"outbound","fix_script":"fix-hivemind.sh","severity":"high"},
  {"id":"P03","regex":"You should configure ","scope":"outbound","fix_script":"fix-self-correct.sh","severity":"med"},
  {"id":"P04","regex":"Dais の 1 click が 必要|Dais 1 click required","scope":"outbound","fix_script":"fix-self-correct.sh","severity":"high"},
  {"id":"P05","regex":"external_action_only|human-required","scope":"jobs|outbound","fix_script":"fix-self-correct.sh","severity":"high"},
  {"id":"P06","regex":"https://auth\\.deeplake\\.ai/activate\\?user_code=[A-Z0-9-]+","scope":"outbound","fix_script":"fix-hivemind.sh","severity":"high"},
  {"id":"P07","regex":"quota exceeded.*top up","scope":"outbound|jsonl","fix_script":"fix-self-correct.sh","severity":"med"},
  {"id":"P08","regex":"([A-Z_]+_API_KEY|[A-Z_]+_TOKEN) missing from env","scope":"jsonl|outbound","fix_script":"fix-missing-envvar.sh","severity":"high"},
  {"id":"P09","regex":"Invalid request body","scope":"jsonl","fix_script":"fix-blockrun-rejection.sh","severity":"med"},
  {"id":"P10","regex":"Agent couldn't generate a response","scope":"jsonl","fix_script":"fix-blockrun-rejection.sh","severity":"med"},
  {"id":"P11","regex":"crons piling up|crons need migration","scope":"outbound","fix_script":"fix-piling-up.sh","severity":"med"},
  {"id":"P12","regex":"Disk at 9[0-9]%|ENOSPC","scope":"outbound|jsonl","fix_script":"fix-disk-full.sh","severity":"high"}
]
```

### § 9.5 PATCH — `scripts/detect.sh`

```bash
#!/usr/bin/env bash
# detect.sh <source>  where <source> is "outbound" (stdin) or a jsonl file path
# Emits one JSON object per matched line on stdout. Exit 0 = clean, 1 = at least one hit, 2 = error.
set -uo pipefail
SKILL_DIR="$HOME/.openclaw/skills/anicca-friction-fixer"
PATTERNS="$SKILL_DIR/scripts/patterns.json"
SOURCE="${1:-outbound}"

if [ ! -f "$PATTERNS" ]; then
  echo "::error patterns.json missing" >&2
  exit 2
fi

# Read input
if [ "$SOURCE" = "outbound" ]; then
  INPUT="$(cat)"
else
  [ -f "$SOURCE" ] || { echo "::error file not found: $SOURCE" >&2; exit 2; }
  INPUT="$(cat "$SOURCE")"
fi

# For each pattern, grep -nE the input, emit JSON
hits=0
while IFS= read -r row; do
  id="$(echo "$row" | jq -r '.id')"
  re="$(echo "$row" | jq -r '.regex')"
  fix="$(echo "$row" | jq -r '.fix_script')"
  scope="$(echo "$row" | jq -r '.scope')"
  # honor scope filter (= "outbound" only matches when SOURCE is outbound, etc.)
  echo "$scope" | grep -qE "(^|\|)$SOURCE(\||$)" || continue
  echo "$INPUT" | grep -nEo -- "$re" 2>/dev/null | while IFS=: read -r line text; do
    jq -nc --arg id "$id" --arg src "$SOURCE" --arg line "$line" \
       --arg text "$text" --arg fix "$fix" \
       '{pattern_id: $id, source: $src, line: ($line|tonumber), match: $text, fix_script: $fix}'
    hits=$((hits+1))
  done
done < <(jq -c '.[]' "$PATTERNS")

[ "$hits" -gt 0 ] && exit 1 || exit 0
```

### § 9.6 PATCH — `scripts/fix-piling-up.sh`  (= empty-cron deletion + orphan cleanup)

```bash
#!/usr/bin/env bash
set -uo pipefail
JOBS="$HOME/.openclaw/cron/jobs.json"
RUNS_DIR="$HOME/.openclaw/cron/runs"
SKIP_NAMES=("jsps-application-monthly")     # institutional auth = real hard-block per A0.5.5 invariants
LOG="$HOME/.openclaw/skills/anicca-friction-fixer/state/violations.jsonl"
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# 1. Delete orphan-empty crons (empty prompt + no run_cmd + no skill dir)
TMP=$(mktemp)
python3 <<PY > "$TMP"
import json, os, sys
JOBS = json.load(open("$JOBS"))
items = JOBS if isinstance(JOBS, list) else JOBS.get('jobs') or []
SKIP = $(printf '%s\n' "${SKIP_NAMES[@]}" | jq -R . | jq -sc .)
kept = []
removed = []
for it in items:
    if not isinstance(it, dict):
        kept.append(it); continue
    name = it.get('name','')
    if name in SKIP:
        kept.append(it); continue
    prompt = (it.get('prompt') or it.get('message') or '').strip()
    run_cmd = it.get('run_cmd') or it.get('command') or it.get('exec')
    has_skill = os.path.isdir(os.path.expanduser(f"~/.openclaw/skills/{name}"))
    if not prompt and not run_cmd and not has_skill:
        removed.append(name)
    else:
        kept.append(it)
new = kept if isinstance(JOBS, list) else {**JOBS, 'jobs': kept}
json.dump(new, open("$JOBS","w"), indent=2, ensure_ascii=False)
for n in removed: print(n)
PY

# 2. Log + clean runs/ for each removed
while IFS= read -r name; do
  [ -z "$name" ] && continue
  evidence=$(find "$RUNS_DIR" -name "${name}-*.jsonl" 2>/dev/null | wc -l | tr -d ' ')
  find "$RUNS_DIR" -name "${name}-*.jsonl" -delete 2>/dev/null
  printf '{"ts":"%s","pattern_id":"P11","source":"friction-sweep","fix_script":"fix-piling-up.sh","exit_code":0,"evidence":"deleted orphan cron %s + %s runs","dais_visible":false}\n' \
    "$TS" "$name" "$evidence" >> "$LOG"
done < "$TMP"
rm -f "$TMP"

# 3. Orphan runs/ (jobs.json に 不在 だ が runs/ にだけ ある) も 削除
python3 <<PY
import json, os, glob
JOBS = json.load(open("$JOBS"))
items = JOBS if isinstance(JOBS, list) else JOBS.get('jobs') or []
names = {it.get('name') for it in items if isinstance(it, dict)}
removed = 0
for fp in glob.glob(os.path.expanduser("~/.openclaw/cron/runs/*.jsonl")):
    base = os.path.basename(fp)
    # match cronName-<digits>.jsonl
    head = base.rsplit('-',1)[0]
    if head and head not in names and not head.startswith(('Initial','jsps-application-monthly')):
        os.remove(fp); removed += 1
print(f"orphan runs removed: {removed}")
PY

echo "fix-piling-up.sh: complete"
```

### § 9.7 PATCH — `_shared/heartbeat-friction-sweep.sh`

```bash
#!/usr/bin/env bash
# Invoked from heartbeat-beat.sh once per beat (after CFO refresh, before claude -p exec).
# Scans the last 24h of cron runs + the slack-outbound staging file for A0.5.5 forbidden surfaces.
# For each hit, dispatches the matching fix-script with a 5-min timeout.
set -uo pipefail
SKILL_DIR="$HOME/.openclaw/skills/anicca-friction-fixer"
LOG="$SKILL_DIR/state/violations.jsonl"
mkdir -p "$SKILL_DIR/state"
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Source 1: last 24h cron runs jsonl
find "$HOME/.openclaw/cron/runs" -name "*.jsonl" -mtime -1 2>/dev/null | while read jsonl; do
  hits=$(bash "$SKILL_DIR/scripts/detect.sh" "$jsonl" 2>/dev/null || true)
  [ -z "$hits" ] && continue
  echo "$hits" | while IFS= read -r row; do
    fix=$(echo "$row" | jq -r '.fix_script')
    pid=$(echo "$row" | jq -r '.pattern_id')
    timeout 300 bash "$SKILL_DIR/scripts/$fix" >>"$SKILL_DIR/state/${fix%.sh}.log" 2>&1
    rc=$?
    printf '{"ts":"%s","pattern_id":"%s","source":"%s","fix_script":"%s","exit_code":%d,"evidence":"%s","dais_visible":false}\n' \
      "$TS" "$pid" "$jsonl" "$fix" "$rc" "auto-dispatch via heartbeat-sweep" >> "$LOG"
  done
done

# Source 2: pending slack outbound queue (if exists)
QUEUE="$HOME/.openclaw/state/slack-outbound-queue.txt"
if [ -f "$QUEUE" ]; then
  hits=$(bash "$SKILL_DIR/scripts/detect.sh" outbound < "$QUEUE" 2>/dev/null || true)
  [ -n "$hits" ] && echo "$hits" >>"$SKILL_DIR/state/queue-hits.jsonl"
fi

echo "friction-sweep: ok"
```

### § 9.8 PATCH — heartbeat-beat.sh ANCHOR INSERT

```diff
--- a/~/.openclaw/skills/_shared/heartbeat-beat.sh
+++ b/~/.openclaw/skills/_shared/heartbeat-beat.sh
@@ -26,6 +26,10 @@ timeout 360 bash "$HOME/.openclaw/skills/cfo-core/run-cfo-hourly.sh" \
   >> "$HOME/.openclaw/skills/cfo-core/data/cfo-heartbeat.log" 2>&1 || true
 
+# Friction Sweep — A0.5.5 enforcer (= spec 15)
+# Detect "user-click / device-code / configure X" surfaces + auto-fix.
+bash "$HOME/.openclaw/skills/anicca-friction-fixer/_shared/heartbeat-friction-sweep.sh" \
+  >>"$HOME/.openclaw/state/friction-sweep.log" 2>&1 || true
+
 exec /opt/homebrew/bin/timeout --kill-after=60 1200 claude -p "You are Anicca, running on the **claude-anicca** harness ..."
```

### § 9.9 PATCH — `state/violations.jsonl` (= initial seed, schema in header)

```
# violations.jsonl schema (1 line per fix attempt):
#   {ts: ISO8601, pattern_id: "P##", source: "<file or 'outbound'>", line_match: "<excerpt>", fix_script: "<name.sh>", exit_code: 0|N, evidence_path: "<log>", dais_visible: bool}
# Append-only. Rotation: daily cleanup cron keeps last 90d.
# Initial seed: empty.
```

### § 9.10 SKETCH — fix-hivemind.sh / fix-blockrun-rejection.sh / fix-missing-envvar.sh / fix-disk-full.sh / wrap-outbound.sh

These 5 scripts have **open uncertainties** (Q15, Q21, Q23, Q29, Q33, Q36) that block precise patch writing. Iteration 3 will:

1. Run `hivemind status` + capture URL via regex, then drive camofox with snapshot/click sequence (Q15)
2. Grep ~/.openclaw/cron/runs/ for blockrun+invalid-body in last 7d, confirm jobs.json stores model+provider at job level (Q21+Q23)
3. Open console.cloud.google.com/apis/credentials via camofox, capture snapshot refs (Q29)
4. Enumerate Mac mini disk > 30d candidates with `du -sh` (Q33)
5. Read slack-bridge.py outbound function (Q36) — identify exact hook point

Each sketch is committed as a placeholder script that returns exit 99 ("not yet patched") + logs to violations.jsonl. Iteration 3 replaces the placeholders with real logic.

---

## § 10. Iteration log

| Round | Date | Outcome |
|---|---|---|
| 1 | 2026-06-03 | Initial spec written (§ 0–§ 8). Surface-level. |
| 2 | 2026-06-03 | Patches added (§ 9). 6/11 scripts patched in full, 5/11 placeholder pending Q15/21/23/29/33/36 research. |
| 3 | (next) | Resolve Q15/21/23/29/33/36 via live camofox + script reading + cron-runs grep. |
