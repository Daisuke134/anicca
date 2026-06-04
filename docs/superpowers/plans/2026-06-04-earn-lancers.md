# Earn Lancers (Wave 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the proven in-house Lancers earner (= the only existing skill that already submitted real ¥1万 proposals through `propose_confirm → propose_finish`) into the Hermes skills format at `anicca-oss/skills/anicca-earn-lancers/`, wire it to ONE daily Hermes cron, drive Camofox (`:9377`) with Google-login-canonical session for the apply flow, and prove a `--dry-run` end-to-end with 3 scored gigs WITHOUT submitting. A LIVE smoke (¥1k tier `--confirm`) is documented but NOT auto-executed.

**Architecture:** `anicca-earn-bounty` (already in `anicca-oss/skills/`) is the structural template — `SKILL.md` + `scripts/{run,scan,select,solve,submit}.sh` + `state/` + `data/` + `.gitignore`. We mirror that layout exactly. The actual apply logic ports verbatim from `~/.openclaw/skills/_archive/hybrid-v1/cfo-earner-lancers/scripts/run.sh` (= "Vue hidden-field set" pattern that proved out on JID `5550526/5550727/5550692` and got URLs `https://www.lancers.jp/work/propose_finish/<JID>`). Camofox is consumed strictly through its REST `:9377` per `~/.openclaw/skills/camofox-browser/SKILL.md` — no playwright, no Selenium. Login is Google OAuth via Camofox (HARD RULE: camofox > cloak > agent-browser); the Lancers session is the alias account `keiodaisuke+anicca@gmail.com` with `LANCERS_PASSWORD` (the one HARD-RULE-documented Google-login exception, already in `~/.openclaw/.env`). Hermes cron is invoked via `hermes cron create` with `--no-agent --script` (= cheap, no LLM per fire) per `hermes cron create --help` v0.12.0 — the scoring/templating LLM is invoked *inside* the script via `hermes chat -q` with `--model` pinned to a mini model (HARD RULE "OpenClaw cron は mini 主軸").

**Tech Stack:** Hermes Agent v0.12.0+ (already booted by sister plan `2026-06-04-hermes-genesis-boot.md`) · Camofox REST `http://localhost:9377` (process already running, verified `/health` → `ok:true browserConnected:true`) · `bash` · `curl` · `jq` (`/opt/homebrew/bin/jq`) · `python3` (stdlib only — `json`, `urllib.parse`, `re`) · `git` · `~/.openclaw/.env` (read-only, never echoed) · existing in-house code (port-from path: `~/.openclaw/skills/_archive/hybrid-v1/cfo-earner-lancers/scripts/run.sh`, 246 lines, the proven version).

**Scope-out (other plans):**
- New earn channels Coconala (`anicca-coconala-earner`) and CrowdWorks (`anicca-crowdworks-earner`) → **Wave 2** (separate plans, same template once this Wave 1 lands).
- Bounty + x402 (Algora / OnlyDust / x402 facilitator) → **#324** (`anicca-earn-bounty` already in repo).
- Capafy publish lane → **#43** (separate skill).
- New bank wiring / payout rails → covered by `anicca-payout-*` skills already in `anicca-oss/skills/`. Incoming Lancers payments hit the existing OpenClaw bank, which CFO already scrapes (`cfo-bank` skill, LIVE since 2026-05-28). **This plan does NOT touch payout/CFO.**
- Hermes runtime, BYOK fuel, gateway / launchd, AGENTS.md symlink → done by `2026-06-04-hermes-genesis-boot.md`. This plan ASSUMES that body is alive.
- eKYC / selfie upload / withdraw → out of scope here; Lancers releases reward to the bank tied to the Lancers account, then CFO surfaces it. eKYC is a one-time HARD-RULE-#18 physical exception covered by the future `anicca-earn-lancers/scripts/ekyc.sh` task (NOT in Wave 1).

**Done condition for this plan (proves task #325 Wave 1):**
1. `hermes skills list 2>&1 | grep -E '^anicca-earn-lancers( |$)'` → exactly one row.
2. `hermes cron list 2>&1 | grep anicca-earn-lancers` → exactly one row, schedule `0 10 * * *` (daily 10:00 JST = quiet hour, Lancers traffic low → less competition).
3. `bash skills/anicca-earn-lancers/scripts/run.sh --dry-run` prints a single JSON envelope with `mode:"dry-run"`, `candidates: [<3 objects>]`, each object has `{jid, url, title_truncated, budget_jpy, effort_estimate, score, generated_message}`, and NO `applied` rows. Exit 0. NO HTTP call to `/work/propose_start/*/submit` is made (verified by grep against the camofox `evaluate` payload).
4. `bash skills/anicca-earn-lancers/scripts/run.sh --dry-run` also writes `state/dry-run-latest.json` (overwritable) and does NOT touch `data/apply-log.jsonl`.
5. The E2E test `tests/test_earn_lancers_dry_run.sh` passes (RED → GREEN → REFACTOR completed).
6. A documented LIVE smoke procedure exists at `docs/superpowers/runbooks/2026-06-04-earn-lancers-smoke.md` with: (a) safety-bounded flags (`--max-apply 1`, `--max-budget-jpy 1000`, `--confirm`), (b) the exact `bash` invocation, (c) the kill-switch (`hermes cron pause anicca-earn-lancers`), (d) the verify command (`tail -1 data/apply-log.jsonl | jq '.finish_url'`). The runbook is committed but is NOT auto-executed by this plan or by cron.
7. `specs/00-MASTER.md` § LAUNCH ACCEPTANCE MATRIX row ④「平均月収 x円（コスト約 y円）」 has a sub-bullet noting "Lancers channel: anicca-earn-lancers skill live, cron daily 10:00 JST, dry-run E2E green; LIVE smoke pending Dais human-of-record nod" (this is the ONE place a human OK is required, because LIVE submits a real proposal under the user's Lancers account).
8. All new files committed + pushed to `anicca-oss` (CLAUDE.md rule 0.4).

---

## File Structure (what each file owns)

```
anicca-oss/                                              (this repo, committed)
  skills/anicca-earn-lancers/
    SKILL.md                       ← Hermes frontmatter + how-it-runs
    .gitignore                     ← ignore state/*, data/*.jsonl
    scripts/run.sh                 ← orchestrator: parses flags, calls scan/select/apply
    scripts/scan.sh                ← Camofox search → JID list (read-only)
    scripts/select.sh              ← LLM-score top 3 by (budget vs effort) via `hermes chat -q --model`
    scripts/apply.sh               ← Camofox apply (--dry-run = stop before evaluate(); --confirm = submit)
    scripts/login-check.sh         ← Camofox `/sessions/anicca/cookies` probe; if no Lancers cookie → Google-OAuth flow
    scripts/_lib.sh                ← shared helpers (camofox curl wrappers, slack_post, redact)
    tests/test_earn_lancers_dry_run.sh   ← E2E: dry-run produces a 3-candidate JSON envelope
    tests/fixtures/sample-snapshot.json  ← canned camofox snapshot for offline-of-Lancers unit tests
    README.md                      ← one-paragraph human description
  docs/superpowers/plans/
    2026-06-04-earn-lancers.md     ← THIS plan
  docs/superpowers/runbooks/
    2026-06-04-earn-lancers-smoke.md ← LIVE smoke runbook (humans read before pulling the trigger)
  specs/00-MASTER.md               ← add sub-bullet to § LAUNCH MATRIX row ④

~/.hermes/                                               (runtime, NOT committed)
  skills/anicca-earn-lancers/      ← SYMLINK → anicca-oss/skills/anicca-earn-lancers/
  scripts/anicca-earn-lancers.sh   ← SYMLINK → anicca-oss/skills/anicca-earn-lancers/scripts/run.sh
                                     (Hermes cron requires the script to live under ~/.hermes/scripts/)
  state/anicca-earn-lancers/       ← created on first run (jsonl logs)
  cron/anicca-earn-lancers.*       ← managed by `hermes cron create`

~/.openclaw/.env                                         (read-only, NEVER echoed)
  GOOGLE_LOGIN_EMAIL=…             ← canonical Google identity (HARD RULE)
  GOOGLE_LOGIN_PASSWORD=…
  LANCERS_EMAIL=keiodaisuke+anicca@gmail.com   ← documented HARD-RULE exception
  LANCERS_USERNAME=…
  LANCERS_PASSWORD=…
```

Why symlinks for the skill + run.sh: identical to the genesis-boot pattern. The canonical source lives in the repo (where review/PR lands); Hermes reads it instantly via the symlink — no copy step to forget.

Why `_lib.sh`: the camofox curl wrappers (`cf_open`, `cf_navigate`, `cf_snapshot`, `cf_evaluate`) repeat 4× across scan/select/apply. Extracting them keeps each step file ≤200 lines (CLAUDE.md coding-style.md: "200-400 lines typical, 800 max").

---

### Task 1: Verify prerequisites and snapshot baseline

**Files:**
- None new. Reads existing state.

- [ ] **Step 1: Confirm Hermes genesis body is alive**

Run:
```bash
hermes --version
hermes cron status
```
Expected: `hermes --version` prints a version line (≥0.12.0), `hermes cron status` does NOT print `✗ Gateway is not running`. If either fails → STOP, complete `2026-06-04-hermes-genesis-boot.md` first.

- [ ] **Step 2: Confirm Camofox `:9377` is up and a browser is attached**

Run:
```bash
curl -sS http://localhost:9377/health | /opt/homebrew/bin/jq -e '.ok == true and .browserConnected == true' >/dev/null && echo OK
```
Expected: `OK`. If non-zero exit → run `bash ~/.openclaw/skills/camofox-browser/scripts/start.sh` and re-check. Camofox MUST be the chosen browser (HARD RULE "camofox > cloak-browser > agent-browser") — do NOT fall back to agent-browser.

- [ ] **Step 3: Confirm Lancers credentials exist in `~/.openclaw/.env` (names only — NEVER echo values)**

Run:
```bash
for k in GOOGLE_LOGIN_EMAIL GOOGLE_LOGIN_PASSWORD LANCERS_EMAIL LANCERS_USERNAME LANCERS_PASSWORD; do
  if grep -q "^$k=" /Users/anicca/.openclaw/.env 2>/dev/null; then echo "FOUND $k"; else echo "MISSING $k"; fi
done
```
Expected: 5× `FOUND …`. Any `MISSING …` → STOP, fix the env file first; do not proceed (HARD RULE: Google login canonical).

- [ ] **Step 4: Confirm the in-house port-from source is readable**

Run:
```bash
test -r /Users/anicca/.openclaw/skills/_archive/hybrid-v1/cfo-earner-lancers/scripts/run.sh && \
  wc -l /Users/anicca/.openclaw/skills/_archive/hybrid-v1/cfo-earner-lancers/scripts/run.sh
test -r /Users/anicca/.openclaw/skills/cfo-earner-lancers/data/apply-log.jsonl && \
  /opt/homebrew/bin/jq -r '.jid' /Users/anicca/.openclaw/skills/cfo-earner-lancers/data/apply-log.jsonl
```
Expected: 246-line port-from file readable, and 4 JIDs printed (`5550526`, `5550727`, `5550692`, `5550661`) — these are the proven-pattern receipts. Record them in scratch notes as the ground truth that the port-from logic worked.

- [ ] **Step 5: Commit the plan itself so the rest is reviewable against it**

Run:
```bash
cd /Users/anicca/anicca-oss
git add docs/superpowers/plans/2026-06-04-earn-lancers.md
git commit -m "docs(plan): earn-lancers (#325 Wave 1) — port existing Lancers earner to Hermes + camofox daily apply cron"
git push
```
Expected: push succeeds, `git log --oneline -1` shows the new commit.

---

### Task 2: Write the failing E2E dry-run test FIRST (TDD RED)

**Files:**
- Create: `skills/anicca-earn-lancers/tests/test_earn_lancers_dry_run.sh`
- Create: `skills/anicca-earn-lancers/tests/fixtures/sample-snapshot.json`

- [ ] **Step 1: Create the test directory and fixture**

Run:
```bash
mkdir -p /Users/anicca/anicca-oss/skills/anicca-earn-lancers/tests/fixtures
```

Create `/Users/anicca/anicca-oss/skills/anicca-earn-lancers/tests/fixtures/sample-snapshot.json` with EXACTLY this content (canned camofox snapshot — 5 candidate JIDs, varying budgets, so the scorer has real input to rank):
```json
{
  "url": "https://www.lancers.jp/work/search?keyword=AI&open=1",
  "snapshot": "ref=e1 [link] AI 動画制作 (1本) /work/detail/5560001 — 予算 ¥10,000\nref=e2 [link] ChatGPT プロンプト 改善 /work/detail/5560002 — 予算 ¥3,000\nref=e3 [link] Python スクレイピング /work/detail/5560003 — 予算 ¥50,000 大規模\nref=e4 [link] LINE Bot 作成 /work/detail/5560004 — 予算 ¥8,000\nref=e5 [link] 動画 字幕 100本 一括 /work/detail/5560005 — 予算 ¥200,000\nref=e6 [link] AI 関連 /work/detail/5560006"
}
```

- [ ] **Step 2: Write the failing test**

Create `/Users/anicca/anicca-oss/skills/anicca-earn-lancers/tests/test_earn_lancers_dry_run.sh` with EXACTLY this content:
```bash
#!/usr/bin/env bash
# E2E: `run.sh --dry-run --offline-fixture <path>` MUST produce a JSON envelope on stdout
# with mode=dry-run and exactly 3 scored candidates, and MUST NOT touch data/apply-log.jsonl.

set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FIXTURE="$SKILL_DIR/tests/fixtures/sample-snapshot.json"
LOG="$SKILL_DIR/data/apply-log.jsonl"

# Capture log size before
mkdir -p "$SKILL_DIR/data"
LOG_BEFORE=$(wc -c < "$LOG" 2>/dev/null || echo 0)

OUT=$("$SKILL_DIR/scripts/run.sh" --dry-run --offline-fixture "$FIXTURE")

# Assertion 1: stdout is valid JSON
echo "$OUT" | /opt/homebrew/bin/jq -e . >/dev/null || { echo "FAIL: stdout not JSON: $OUT"; exit 1; }

# Assertion 2: mode == "dry-run"
echo "$OUT" | /opt/homebrew/bin/jq -e '.mode == "dry-run"' >/dev/null || { echo "FAIL: mode != dry-run"; exit 1; }

# Assertion 3: exactly 3 candidates
N=$(echo "$OUT" | /opt/homebrew/bin/jq '.candidates | length')
[ "$N" -eq 3 ] || { echo "FAIL: expected 3 candidates, got $N"; exit 1; }

# Assertion 4: every candidate has the required keys
for k in jid url title_truncated budget_jpy effort_estimate score generated_message; do
  PRESENT=$(echo "$OUT" | /opt/homebrew/bin/jq "[.candidates[] | has(\"$k\")] | all")
  [ "$PRESENT" = "true" ] || { echo "FAIL: candidate missing key $k"; exit 1; }
done

# Assertion 5: candidates are sorted desc by score
SORTED=$(echo "$OUT" | /opt/homebrew/bin/jq '[.candidates[].score] == ([.candidates[].score] | sort | reverse)')
[ "$SORTED" = "true" ] || { echo "FAIL: candidates not sorted by score desc"; exit 1; }

# Assertion 6: apply-log untouched
LOG_AFTER=$(wc -c < "$LOG" 2>/dev/null || echo 0)
[ "$LOG_BEFORE" = "$LOG_AFTER" ] || { echo "FAIL: apply-log.jsonl mutated (before=$LOG_BEFORE after=$LOG_AFTER)"; exit 1; }

# Assertion 7: state/dry-run-latest.json written
test -s "$SKILL_DIR/state/dry-run-latest.json" || { echo "FAIL: state/dry-run-latest.json not written"; exit 1; }

# Assertion 8: NO call would hit the submit URL (grep the dry-run-latest for forbidden URL substring)
if /opt/homebrew/bin/jq -r '.candidates[] | .url' "$SKILL_DIR/state/dry-run-latest.json" | grep -q 'propose_finish'; then
  echo "FAIL: candidate URLs leaked propose_finish path (= submit-side URL)"; exit 1
fi

echo "PASS"
```

Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/anicca-earn-lancers/tests/test_earn_lancers_dry_run.sh
```

- [ ] **Step 3: Run the test — must FAIL because nothing exists (TDD RED)**

Run:
```bash
/Users/anicca/anicca-oss/skills/anicca-earn-lancers/tests/test_earn_lancers_dry_run.sh
```
Expected: non-zero exit with `No such file or directory: …/scripts/run.sh` (or shell complaining about missing executable). This RED is the entry contract for Tasks 3-6.

---

### Task 3: Write the shared `_lib.sh` (camofox wrappers, redact, slack)

**Files:**
- Create: `skills/anicca-earn-lancers/scripts/_lib.sh`

- [ ] **Step 1: Create the directory**

Run:
```bash
mkdir -p /Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts
mkdir -p /Users/anicca/anicca-oss/skills/anicca-earn-lancers/state
mkdir -p /Users/anicca/anicca-oss/skills/anicca-earn-lancers/data
```

- [ ] **Step 2: Write `_lib.sh` with EXACTLY this content**

Create `/Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/_lib.sh`:
```bash
#!/usr/bin/env bash
# Shared helpers for anicca-earn-lancers.
# Loads ~/.openclaw/.env (NEVER echo values), wraps Camofox :9377 REST,
# provides redacted logging + optional Slack post.
# Source this file: `source "$(dirname "$0")/_lib.sh"`.

set -uo pipefail

# Load env (= the ONE place secrets enter the process)
if [ -f "$HOME/.openclaw/.env" ]; then
  set -a; . "$HOME/.openclaw/.env"; set +a
fi

CAMOFOX="${CAMOFOX_URL:-http://localhost:9377}"
USER_ID="${ANICCA_USER_ID:-anicca}"
SESSION_KEY="${ANICCA_SESSION_KEY:-default}"
JQ="${JQ:-/opt/homebrew/bin/jq}"
PYTHON="${PYTHON:-python3}"

# ─── logging (stderr, never stdout — stdout is the JSON contract) ──────────
log()  { echo "▶ [earn-lancers] $*" >&2; }
ok()   { echo "✅ [earn-lancers] $*" >&2; }
err()  { echo "❌ [earn-lancers] $*" >&2; }

# ─── camofox health ────────────────────────────────────────────────────────
cf_health() {
  curl -sS --max-time 5 "$CAMOFOX/health" \
    | "$JQ" -e '.ok == true and .browserConnected == true' >/dev/null
}

# ─── open new tab, return tabId on stdout ─────────────────────────────────
cf_open() {
  local url="$1"
  curl -sS -X POST "$CAMOFOX/tabs" \
    -H 'Content-Type: application/json' \
    -d "$("$JQ" -n --arg u "$url" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
            '{url:$u, userId:$uid, sessionKey:$sk}')" \
    | "$JQ" -r '.tabId // empty'
}

# ─── navigate existing tab ─────────────────────────────────────────────────
cf_navigate() {
  local tab="$1" url="$2"
  curl -sS -X POST "$CAMOFOX/tabs/$tab/navigate" \
    -H 'Content-Type: application/json' \
    -d "$("$JQ" -n --arg u "$url" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
            '{url:$u, userId:$uid, sessionKey:$sk}')" >/dev/null
}

# ─── snapshot (returns raw JSON on stdout) ─────────────────────────────────
cf_snapshot() {
  local tab="$1"
  curl -sS "$CAMOFOX/tabs/$tab/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY"
}

# ─── evaluate JS in tab (returns raw JSON on stdout) ───────────────────────
# Forbidden in --dry-run; callers MUST gate.
cf_evaluate() {
  local tab="$1" js="$2"
  curl -sS -X POST "$CAMOFOX/tabs/$tab/evaluate" \
    -H 'Content-Type: application/json' \
    -d "$("$JQ" -n --arg e "$js" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
            '{expression:$e, userId:$uid, sessionKey:$sk}')" \
    --max-time 60
}

# ─── close tab ─────────────────────────────────────────────────────────────
cf_close() {
  local tab="$1"
  curl -sS -X DELETE "$CAMOFOX/tabs/$tab?userId=$USER_ID&sessionKey=$SESSION_KEY" >/dev/null
}

# ─── slack post (optional, swallows errors) ────────────────────────────────
slack_post() {
  local msg="$1" channel="${SLACK_REPORT_CHANNEL:-C091G3PKHL2}"
  [ -z "${SLACK_BOT_TOKEN:-}" ] && return
  local payload
  payload=$(MSG="$msg" CH="$channel" "$PYTHON" -c \
    'import json,os; print(json.dumps({"channel":os.environ["CH"],"text":os.environ["MSG"]}))')
  curl -s -X POST https://slack.com/api/chat.postMessage \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H 'Content-type: application/json; charset=utf-8' \
    -d "$payload" >/dev/null 2>&1 || true
}

# ─── redact: replace any env-loaded secret token in $1 with ***REDACTED*** ──
redact() {
  local s="$1"
  for v in "${LANCERS_PASSWORD:-}" "${GOOGLE_LOGIN_PASSWORD:-}" "${SLACK_BOT_TOKEN:-}" "${GITHUB_TOKEN:-}"; do
    [ -n "$v" ] && s="${s//$v/***REDACTED***}"
  done
  printf '%s' "$s"
}
```

Make sourceable (not executable as a script):
```bash
chmod 644 /Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/_lib.sh
```

- [ ] **Step 3: Smoke `_lib.sh` directly**

Run:
```bash
( source /Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/_lib.sh; \
  cf_health && echo HEALTH_OK; \
  echo "redacted=$(redact 'hello LANCERS_PASSWORD_OK world')" )
```
Expected: `HEALTH_OK` followed by `redacted=hello LANCERS_PASSWORD_OK world` (no actual secret was in the string, so it passes through unchanged — but this proves the redact function loaded). No values from `~/.openclaw/.env` are ever printed.

---

### Task 4: Write `scan.sh` (Camofox search → JID list, --offline-fixture support)

**Files:**
- Create: `skills/anicca-earn-lancers/scripts/scan.sh`

- [ ] **Step 1: Write `scan.sh` with EXACTLY this content**

Create `/Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/scan.sh`:
```bash
#!/usr/bin/env bash
# scan.sh — discover Lancers JIDs.
# Usage:
#   scan.sh                         → live Camofox scan, stdout = newline-separated JIDs
#   scan.sh --offline-fixture <p>   → read fixture JSON, skip Camofox entirely

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

# parse args
FIXTURE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --offline-fixture) FIXTURE="$2"; shift 2 ;;
    *) shift ;;
  esac
done

extract_jids() {
  # stdin = camofox snapshot JSON; stdout = unique JIDs, max 15, preserve order
  "$PYTHON" - <<'PY'
import json, re, sys
d = json.load(sys.stdin)
snap = d.get('snapshot', '')
seen = []
for m in re.finditer(r'/work/detail/(\d+)', snap):
    jid = m.group(1)
    if jid not in seen:
        seen.append(jid)
    if len(seen) >= 15:
        break
print('\n'.join(seen))
PY
}

if [ -n "$FIXTURE" ]; then
  log "scan offline: $FIXTURE"
  test -r "$FIXTURE" || { err "fixture unreadable: $FIXTURE"; exit 2; }
  extract_jids < "$FIXTURE"
  exit 0
fi

cf_health || { err "camofox down"; exit 3; }

# Live scan — rotate keyword by day-of-week (proven pattern from port-from source line 49)
DOW=$(date +%u)
KEYWORDS=("AI" "ChatGPT" "Python" "スクレイピング" "自動化" "GPT" "動画制作" "AI開発" "LINE Bot" "Web制作")
IDX=$(( (DOW - 1) % ${#KEYWORDS[@]} ))
KW="${LANCERS_KEYWORD:-${KEYWORDS[$IDX]}}"
KW_ENC=$("$PYTHON" -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$KW")
log "scan live keyword=$KW (DOW=$DOW idx=$IDX)"

TAB=$(cf_open "https://www.lancers.jp/work/search?keyword=${KW_ENC}&open=1")
[ -z "$TAB" ] && { err "tab open failed"; exit 4; }
log "tabId=$TAB"

sleep 10
SNAP=$(cf_snapshot "$TAB")
cf_close "$TAB"

printf '%s' "$SNAP" | extract_jids
```

Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/scan.sh
```

- [ ] **Step 2: Smoke `scan.sh --offline-fixture`**

Run:
```bash
/Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/scan.sh \
  --offline-fixture /Users/anicca/anicca-oss/skills/anicca-earn-lancers/tests/fixtures/sample-snapshot.json
```
Expected: 6 JIDs printed, one per line, in order: `5560001`, `5560002`, `5560003`, `5560004`, `5560005`, `5560006`. Exit 0.

---

### Task 5: Write `select.sh` (LLM-score top 3 by budget vs effort, via mini model)

**Files:**
- Create: `skills/anicca-earn-lancers/scripts/select.sh`

- [ ] **Step 1: Write `select.sh` with EXACTLY this content**

Create `/Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/select.sh`:
```bash
#!/usr/bin/env bash
# select.sh — score candidate JIDs and emit top 3.
# stdin: newline-separated JIDs
# stdout: JSON array of 3 scored candidate objects, sorted desc by score.
#
# Scoring source of truth:
#   When --offline-fixture is given, the fixture snapshot is reparsed for
#   (title, budget_jpy) per JID (no Camofox, no LLM — pure deterministic
#   scoring = budget_jpy / effort_estimate). This is what the E2E test pins.
#
#   When live, each JID is fetched via Camofox detail page, parsed for
#   the budget block, and passed to `hermes chat -q --model <mini>` which
#   returns a JSON line with effort_estimate ∈ 1..10. Mini model only
#   (CLAUDE.md HARD RULE: gpt-5.2-mini / deepseek-v4-flash / kimi-k2.6).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

FIXTURE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --offline-fixture) FIXTURE="$2"; shift 2 ;;
    *) shift ;;
  esac
done

JIDS=$(cat)

if [ -n "$FIXTURE" ]; then
  # Deterministic: parse (jid, title, budget) tuples from the fixture and rank.
  "$PYTHON" - "$FIXTURE" <<'PY' <<<"$JIDS"
import json, re, sys
fixture_path = sys.argv[1]
jids = [j.strip() for j in sys.stdin.read().splitlines() if j.strip()]
snap = json.load(open(fixture_path)).get('snapshot', '')
# Each fixture line is: "ref=eN [link] <TITLE> /work/detail/<JID> — 予算 ¥<N>[,<N>]*"
rows = {}
for line in snap.split('\n'):
    m = re.search(r'/work/detail/(\d+)', line)
    if not m: continue
    jid = m.group(1)
    title = re.sub(r'ref=\S+\s+\[link\]\s+', '', line).split('/work/detail/')[0].strip()
    b = re.search(r'予算\s*¥([\d,]+)', line)
    budget = int(b.group(1).replace(',', '')) if b else 0
    rows[jid] = (title, budget)

# effort_estimate proxy from title length + presence of "大規模"/"一括"/"100本"
def effort(title):
    e = 1
    if any(t in title for t in ['大規模','一括','100本','大量']): e += 5
    if len(title) > 20: e += 2
    return max(1, min(10, e))

scored = []
for jid in jids:
    if jid not in rows: continue
    title, budget = rows[jid]
    eff = effort(title)
    score = budget / max(1, eff)
    scored.append({
        "jid": jid,
        "url": f"https://www.lancers.jp/work/detail/{jid}",
        "title_truncated": title[:40],
        "budget_jpy": budget,
        "effort_estimate": eff,
        "score": round(score, 2),
    })

scored.sort(key=lambda r: r['score'], reverse=True)
print(json.dumps(scored[:3], ensure_ascii=False))
PY
  exit 0
fi

# ── LIVE branch ───────────────────────────────────────────────────────────
cf_health || { err "camofox down"; exit 3; }

# Pick the mini model from env or default. HARD RULE: mini only.
MODEL="${LANCERS_SCORE_MODEL:-gpt-5.2-mini}"

ROWS_JSON='[]'
for JID in $JIDS; do
  TAB=$(cf_open "https://www.lancers.jp/work/detail/$JID")
  sleep 4
  SNAP=$(cf_snapshot "$TAB")
  cf_close "$TAB"

  PARSED=$("$PYTHON" - <<PY
import json, re, sys
d = json.loads('''$SNAP''') if False else json.loads(sys.stdin.read())
snap = d.get('snapshot', '')
title = (re.search(r'(?m)^\s*(?:[#=]+\s*)?(.{4,60})$', snap) or [None,''])[1].strip()
b = re.search(r'予算\s*¥?([\d,]+)\s*[-〜~]?\s*¥?([\d,]+)?', snap)
budget = 0
if b:
    budget = int((b.group(2) or b.group(1)).replace(',', ''))
print(json.dumps({"jid":"$JID","url":"https://www.lancers.jp/work/detail/$JID","title":title,"budget_jpy":budget}))
PY
<<<"$SNAP")

  # Ask the mini model for effort 1..10 (single JSON line)
  PROMPT="Read the Lancers gig title and budget. Reply with ONE JSON line only: {\"effort_estimate\": <int 1..10>} where 1=trivial, 10=large multi-week. No prose. Input: $PARSED"
  EFF_LINE=$(hermes chat --model "$MODEL" -q "$PROMPT" 2>/dev/null || echo '{"effort_estimate":5}')
  EFF=$(printf '%s' "$EFF_LINE" | "$JQ" -r '.effort_estimate // 5' 2>/dev/null || echo 5)

  ROW=$("$JQ" -n --argjson p "$PARSED" --argjson e "$EFF" \
    '$p + {effort_estimate:$e, score: ((.budget_jpy // 0) / ([1, $e] | max))}')
  ROWS_JSON=$("$JQ" -n --argjson a "$ROWS_JSON" --argjson r "$ROW" '$a + [$r]')
done

# Sort desc by score, take top 3, add title_truncated + placeholder generated_message
echo "$ROWS_JSON" | "$JQ" '
  sort_by(-.score)
  | .[0:3]
  | map(. + {title_truncated: (.title // "")[0:40], generated_message: ""})
'
```

Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/select.sh
```

- [ ] **Step 2: Smoke `select.sh --offline-fixture` against the 6-JID fixture**

Run:
```bash
/Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/scan.sh \
  --offline-fixture /Users/anicca/anicca-oss/skills/anicca-earn-lancers/tests/fixtures/sample-snapshot.json \
| /Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/select.sh \
  --offline-fixture /Users/anicca/anicca-oss/skills/anicca-earn-lancers/tests/fixtures/sample-snapshot.json \
| /opt/homebrew/bin/jq .
```
Expected: a JSON array of 3 objects, sorted desc by `score`. Given the fixture:
- `5560005` (字幕100本一括, budget 200000, effort ~8) → score ≈ 25000
- `5560003` (Python スクレイピング, budget 50000, effort ~3) → score ≈ 16666
- `5560001` (AI 動画制作, budget 10000, effort ~1) → score = 10000

The top-3 ranking MUST be `5560005, 5560003, 5560001` in that order. (The exact effort values may differ by ±1 if the heuristic changes, but the order is what the test pins.)

---

### Task 6: Write `apply.sh` (--dry-run safe; --confirm submits; ports Vue-hidden-field pattern)

**Files:**
- Create: `skills/anicca-earn-lancers/scripts/apply.sh`

- [ ] **Step 1: Write `apply.sh` with EXACTLY this content**

Create `/Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/apply.sh`:
```bash
#!/usr/bin/env bash
# apply.sh — generate the proposal message and (if --confirm) submit it.
# stdin: JSON array of candidate objects from select.sh
# stdout: JSON array of {jid, url, generated_message, status} per candidate.
#
# Modes:
#   --dry-run         → DO NOT call cf_evaluate, DO NOT touch apply-log.jsonl,
#                       generated_message stops at the proposal text, status="dry-run".
#   --confirm         → execute the proven 2-stage submit
#                       (propose_start → propose_confirm → propose_finish).
#                       Append one JSONL row per candidate to data/apply-log.jsonl.
#   --max-apply N     → hard cap on submits per run (default 3 in run.sh; here we honor whatever caller passes).
#   --max-budget-jpy B → in --confirm mode, skip candidates with budget > B (safety bound).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

DRY_RUN=true
CONFIRM=false
MAX_APPLY=3
MAX_BUDGET_JPY=0   # 0 = no cap
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=true; CONFIRM=false; shift ;;
    --confirm) DRY_RUN=false; CONFIRM=true; shift ;;
    --max-apply) MAX_APPLY="$2"; shift 2 ;;
    --max-budget-jpy) MAX_BUDGET_JPY="$2"; shift 2 ;;
    *) shift ;;
  esac
done

INPUT=$(cat)
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
APPLY_LOG="$SKILL_DIR/data/apply-log.jsonl"
mkdir -p "$SKILL_DIR/data"

generate_message() {
  local jid="$1" title="$2" budget="$3"
  cat <<MSG
はじめまして。 自律 AI を 中核に持つ 制作チーム Anicca です。

【ご提案 内容】 ${title} を ¥${budget} で 制作。 24-48h 納品。

【強み】 AI 音声合成 (ElevenLabs / OpenAI) + Remotion+ffmpeg コード化パイプラインで 量産可能。 24h 受付・並列処理 可。

【納品まで】 (1) 仕様 / スクリプト 連絡 (2) AI 生成 (素材/voice/字幕) (3) 編集+BGM (4) 成果物 をランサーズ メッセージで共有 → 修正 → 完納。

【納期】 1本 24-48h。 複数本 一括も 1週間で 5-10本 可。

【継続】 月単位の 単価アップ ご相談 可能。

ご検討 よろしく お願いいたします。  Anicca / 成田 大祐
MSG
}

# Build the output array
RESULT='[]'
COUNT=0
echo "$INPUT" | "$JQ" -c '.[]' | while IFS= read -r row; do
  JID=$(echo "$row" | "$JQ" -r '.jid')
  TITLE=$(echo "$row" | "$JQ" -r '.title_truncated')
  BUDGET=$(echo "$row" | "$JQ" -r '.budget_jpy')
  URL_DETAIL="https://www.lancers.jp/work/detail/$JID"
  MSG=$(generate_message "$JID" "$TITLE" "$BUDGET")

  if $DRY_RUN; then
    OUT_ROW=$("$JQ" -n --arg jid "$JID" --arg url "$URL_DETAIL" --arg msg "$MSG" \
      --argjson budget "$BUDGET" --arg title "$TITLE" \
      --argjson eff "$(echo "$row" | "$JQ" '.effort_estimate')" \
      --argjson score "$(echo "$row" | "$JQ" '.score')" \
      '{jid:$jid, url:$url, title_truncated:$title, budget_jpy:$budget,
        effort_estimate:$eff, score:$score,
        generated_message:$msg, status:"dry-run"}')
    echo "$OUT_ROW"
    continue
  fi

  # ── LIVE submit ────────────────────────────────────────────────────────
  # Safety bound: budget cap
  if [ "$MAX_BUDGET_JPY" -gt 0 ] && [ "$BUDGET" -gt "$MAX_BUDGET_JPY" ]; then
    log "skip JID=$JID budget=$BUDGET > cap=$MAX_BUDGET_JPY"
    continue
  fi
  # Safety bound: per-run cap
  COUNT=$((COUNT+1))
  if [ "$COUNT" -gt "$MAX_APPLY" ]; then
    log "reached --max-apply $MAX_APPLY — stop"
    break
  fi

  cf_health || { err "camofox down mid-apply"; break; }

  TAB=$(cf_open "https://www.lancers.jp/work/propose_start/$JID")
  sleep 6
  SNAP=$(cf_snapshot "$TAB")
  STATE=$(printf '%s' "$SNAP" | "$PYTHON" -c '
import json,sys
d=json.load(sys.stdin); snap=d.get("snapshot",""); url=d.get("url","")
if "propose_start" not in url: print("REDIRECT")
elif "提案できません" in snap: print("BLOCKED")
elif "data[Proposal]" in snap or "提案文" in snap: print("OPEN")
else: print("UNKNOWN")
')
  if [ "$STATE" != "OPEN" ]; then
    log "JID=$JID state=$STATE — skip"
    cf_close "$TAB"
    OUT_ROW=$("$JQ" -n --arg jid "$JID" --arg url "$URL_DETAIL" --arg s "$STATE" \
      '{jid:$jid, url:$url, status:("skip:" + $s)}')
    echo "$OUT_ROW"
    continue
  fi

  # The proven JS — ported verbatim from
  # ~/.openclaw/skills/_archive/hybrid-v1/cfo-earner-lancers/scripts/run.sh lines 159-188
  APPLY_JS=$("$PYTHON" - <<PYEOF
import json
prop  = """$MSG"""
title = "AI動画制作 1本納品"
ms_desc = "AI 動画 1本 (1-3min) を MP4 で 納品。 ご希望の voice / フォーマット / 字幕 に 合わせて 24-48h で 初稿、 修正 1 回まで 無料。"
amount = "$BUDGET"
js = f"""(async()=>{{
  const setT=(el,v)=>{{
    if(!el) return false;
    const proto=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto,'value').set.call(el,v);
    el.dispatchEvent(new Event('input',{{bubbles:true}}));
    el.dispatchEvent(new Event('change',{{bubbles:true}}));
    return true;
  }};
  const propTA=document.querySelector('textarea[name=\"data[Proposal][description]\"]');
  if(!propTA) return JSON.stringify({{err:'no_prop_ta'}});
  setT(propTA, {json.dumps(prop)});
  setT(document.querySelector('input[name=\"data[Milestone][10][title]\"]'), {json.dumps(title)});
  setT(document.querySelector('input[name=\"data[Milestone][10][schedule][year]\"]'), '2026');
  setT(document.querySelector('input[name=\"data[Milestone][10][schedule][month]\"]'), '6');
  setT(document.querySelector('input[name=\"data[Milestone][10][schedule][day]\"]'), '15');
  setT(document.querySelector('textarea[name=\"data[Milestone][10][description]\"]'), {json.dumps(ms_desc)});
  setT(document.querySelector('input[name=\"data[Milestone][10][amount_exclude_tax]\"]'), '{amount}');
  await new Promise(r=>setTimeout(r,2000));
  const submit=document.querySelector('input[type=submit][name=\"send\"]');
  if(!submit) return JSON.stringify({{err:'no_submit'}});
  submit.click();
  await new Promise(r=>setTimeout(r,15000));
  return JSON.stringify({{url:location.href}});
}})()"""
print(js)
PYEOF
)

  cf_evaluate "$TAB" "$APPLY_JS" >/dev/null || true
  sleep 8

  URL_CHECK=$(cf_snapshot "$TAB" | "$JQ" -r '.url // ""')
  STATUS="submit_failed"
  FINAL_URL=""
  if [[ "$URL_CHECK" == *"propose_confirm"* ]]; then
    FINAL_JS='(async()=>{const s=document.querySelector("input[type=submit][value=\"利用規約に同意して提案する\"]");if(!s)return JSON.stringify({err:"no_final"});s.click();await new Promise(r=>setTimeout(r,12000));return JSON.stringify({url:location.href});})()'
    cf_evaluate "$TAB" "$FINAL_JS" >/dev/null || true
    sleep 8
    FINAL_URL=$(cf_snapshot "$TAB" | "$JQ" -r '.url // ""')
    if [[ "$FINAL_URL" == *"propose_finish"* ]]; then
      STATUS="applied"
    else
      STATUS="final_click_failed"
    fi
  fi
  cf_close "$TAB"

  TS=$(date -u +%FT%TZ)
  ROW_LOG=$("$JQ" -n --arg ts "$TS" --arg jid "$JID" --arg status "$STATUS" \
                  --argjson amt "$BUDGET" --arg furl "$FINAL_URL" \
                  '{ts:$ts, jid:$jid, status:$status, amount:$amt, finish_url:$furl}')
  printf '%s\n' "$ROW_LOG" >> "$APPLY_LOG"

  OUT_ROW=$("$JQ" -n --arg jid "$JID" --arg url "$URL_DETAIL" --arg msg "$MSG" \
                   --arg status "$STATUS" --arg furl "$FINAL_URL" \
                   '{jid:$jid, url:$url, generated_message:$msg, status:$status, finish_url:$furl}')
  echo "$OUT_ROW"
done | "$JQ" -s '.'
```

Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/apply.sh
```

- [ ] **Step 2: Smoke `apply.sh --dry-run` against the select output**

Run:
```bash
/Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/scan.sh \
  --offline-fixture /Users/anicca/anicca-oss/skills/anicca-earn-lancers/tests/fixtures/sample-snapshot.json \
| /Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/select.sh \
  --offline-fixture /Users/anicca/anicca-oss/skills/anicca-earn-lancers/tests/fixtures/sample-snapshot.json \
| /Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/apply.sh --dry-run \
| /opt/homebrew/bin/jq '[.[] | .status]'
```
Expected: `["dry-run","dry-run","dry-run"]`. And `wc -l /Users/anicca/anicca-oss/skills/anicca-earn-lancers/data/apply-log.jsonl 2>/dev/null` must show 0 (= no log write in dry-run).

---

### Task 7: Write `login-check.sh` (Camofox cookie probe + Google OAuth fallback)

**Files:**
- Create: `skills/anicca-earn-lancers/scripts/login-check.sh`

- [ ] **Step 1: Write `login-check.sh` with EXACTLY this content**

Create `/Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/login-check.sh`:
```bash
#!/usr/bin/env bash
# login-check.sh — verify the camofox session has a Lancers cookie; if not, run
# Google-OAuth login via Camofox using GOOGLE_LOGIN_EMAIL/PASSWORD.
# Exit 0: session usable. Exit non-0: needs human intervention (HARD-RULE
# physical exception, e.g. Google 2FA tap on phone — same gate as Camofox SKILL.md).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

cf_health || { err "camofox down"; exit 3; }

# Cookie probe: does the session contain a Lancers cookie?
COOKIES_JSON=$(curl -sS "$CAMOFOX/sessions/$USER_ID/cookies?sessionKey=$SESSION_KEY" 2>/dev/null || echo '[]')
HAS=$(printf '%s' "$COOKIES_JSON" | "$JQ" '[.[] | select(.domain | test("lancers.jp"))] | length')
if [ "${HAS:-0}" -gt 0 ]; then
  ok "lancers cookie present (n=$HAS)"
  exit 0
fi

log "no lancers cookie — running Google OAuth via Camofox"

# 1. Open Lancers login page (Google button is the canonical path per HARD RULE)
TAB=$(cf_open "https://www.lancers.jp/user/login")
sleep 4

# 2. Click the "Googleでログイン" button via accessibility snapshot
SNAP=$(cf_snapshot "$TAB")
GOOGLE_REF=$(printf '%s' "$SNAP" | "$PYTHON" -c '
import json,sys,re
d=json.load(sys.stdin); s=d.get("snapshot","")
for line in s.split("\n"):
    if "Google" in line and "ログイン" in line:
        m=re.search(r"ref=(\S+)", line)
        if m: print(m.group(1)); break
')
if [ -n "$GOOGLE_REF" ]; then
  curl -sS -X POST "$CAMOFOX/tabs/$TAB/click" \
    -H 'Content-Type: application/json' \
    -d "$("$JQ" -n --arg r "$GOOGLE_REF" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
            '{ref:$r, userId:$uid, sessionKey:$sk}')" >/dev/null
  sleep 6
else
  log "Google-login button ref not found — Lancers may need email/pw form (LANCERS_EMAIL + LANCERS_PASSWORD)"
  cf_close "$TAB"
  exit 4
fi

# 3. Google OAuth steps (verified pattern from Camofox SKILL.md):
#    type email → Next → "Try another way" → "Enter your password" → type pw
#    → 2-step verification (TAP on phone, one-time physical exception)
SNAP=$(cf_snapshot "$TAB")
EMAIL_REF=$(printf '%s' "$SNAP" | "$PYTHON" -c '
import json,sys,re
d=json.load(sys.stdin); s=d.get("snapshot","")
m=re.search(r"ref=(\S+).*(?:email|メール|identifier)", s, re.I)
print(m.group(1) if m else "")
')
[ -z "$EMAIL_REF" ] && { err "no email ref"; cf_close "$TAB"; exit 5; }

curl -sS -X POST "$CAMOFOX/tabs/$TAB/type" \
  -H 'Content-Type: application/json' \
  -d "$("$JQ" -n --arg r "$EMAIL_REF" --arg t "${GOOGLE_LOGIN_EMAIL:-}" \
                  --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                  '{ref:$r, text:$t, userId:$uid, sessionKey:$sk}')" >/dev/null
sleep 1
curl -sS -X POST "$CAMOFOX/tabs/$TAB/press" \
  -H 'Content-Type: application/json' \
  -d "$("$JQ" -n --arg k "Enter" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                  '{key:$k, userId:$uid, sessionKey:$sk}')" >/dev/null
sleep 6

# Password field
SNAP=$(cf_snapshot "$TAB")
PW_REF=$(printf '%s' "$SNAP" | "$PYTHON" -c '
import json,sys,re
d=json.load(sys.stdin); s=d.get("snapshot","")
m=re.search(r"ref=(\S+).*password", s, re.I)
print(m.group(1) if m else "")
')
if [ -n "$PW_REF" ] && [ -n "${GOOGLE_LOGIN_PASSWORD:-}" ]; then
  curl -sS -X POST "$CAMOFOX/tabs/$TAB/type" \
    -H 'Content-Type: application/json' \
    -d "$("$JQ" -n --arg r "$PW_REF" --arg t "$GOOGLE_LOGIN_PASSWORD" \
                    --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                    '{ref:$r, text:$t, userId:$uid, sessionKey:$sk}')" >/dev/null
  sleep 1
  curl -sS -X POST "$CAMOFOX/tabs/$TAB/press" \
    -H 'Content-Type: application/json' \
    -d "$("$JQ" -n --arg k "Enter" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                    '{key:$k, userId:$uid, sessionKey:$sk}')" >/dev/null
  sleep 10
fi

# 4. Re-probe cookies
COOKIES_JSON=$(curl -sS "$CAMOFOX/sessions/$USER_ID/cookies?sessionKey=$SESSION_KEY" 2>/dev/null || echo '[]')
HAS=$(printf '%s' "$COOKIES_JSON" | "$JQ" '[.[] | select(.domain | test("lancers.jp"))] | length')
cf_close "$TAB"
if [ "${HAS:-0}" -gt 0 ]; then
  ok "lancers cookie obtained (n=$HAS)"
  exit 0
fi
err "login flow ran but no lancers cookie — likely 2FA tap pending (HARD-RULE-#-2 physical exception)"
exit 6
```

Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/login-check.sh
```

- [ ] **Step 2: Document expected exit codes**

| Exit | Meaning |
|------|---------|
| 0    | Camofox session has a Lancers cookie (live ready) |
| 3    | Camofox not running |
| 4    | Google-login button missing on Lancers login page (page redesign — needs script update) |
| 5    | Google email field ref not found (OAuth UI redesign) |
| 6    | OAuth ran but no cookie produced — almost always Google 2FA "Tap Yes on phone" pending. **This is the ONE allowed physical exception** (HARD RULE Camofox SKILL.md line 84-85). After the tap, re-run `login-check.sh` and the cookie persists in `~/.camofox/profiles/anicca/default/`. |

(No live execution in this step — that happens in Task 9. This step writes the file and prints the table; the table is the contract that Task 9 checks against.)

---

### Task 8: Write `run.sh` (orchestrator), SKILL.md, README, .gitignore — TDD GREEN

**Files:**
- Create: `skills/anicca-earn-lancers/scripts/run.sh`
- Create: `skills/anicca-earn-lancers/SKILL.md`
- Create: `skills/anicca-earn-lancers/README.md`
- Create: `skills/anicca-earn-lancers/.gitignore`

- [ ] **Step 1: Write `run.sh` with EXACTLY this content**

Create `/Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/run.sh`:
```bash
#!/usr/bin/env bash
# run.sh — single Lancers beat. Default = --dry-run (safe). --confirm = LIVE.
#
# Flags:
#   --dry-run                      (default) scan + select + apply --dry-run, no submit
#   --confirm                      LIVE submit (read the runbook FIRST)
#   --offline-fixture <path>       use fixture instead of live Camofox (for tests/CI)
#   --max-apply N                  cap submits per run (default 3)
#   --max-budget-jpy B             cap budget per submit in --confirm mode
#
# Output: JSON envelope on stdout.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

MODE="dry-run"
FIXTURE=""
MAX_APPLY=3
MAX_BUDGET_JPY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) MODE="dry-run"; shift ;;
    --confirm) MODE="live"; shift ;;
    --offline-fixture) FIXTURE="$2"; shift 2 ;;
    --max-apply) MAX_APPLY="$2"; shift 2 ;;
    --max-budget-jpy) MAX_BUDGET_JPY="$2"; shift 2 ;;
    *) shift ;;
  esac
done

TS=$(date -u +%FT%TZ)
log "mode=$MODE fixture=${FIXTURE:-none}"

# Step 1: login (skip in offline mode)
if [ -z "$FIXTURE" ]; then
  "$SCRIPT_DIR/login-check.sh" || { err "login-check failed — abort"; exit 7; }
fi

# Step 2: scan → JIDs
if [ -n "$FIXTURE" ]; then
  JIDS=$("$SCRIPT_DIR/scan.sh" --offline-fixture "$FIXTURE")
else
  JIDS=$("$SCRIPT_DIR/scan.sh")
fi
[ -z "$JIDS" ] && { err "no JIDs found"; exit 8; }

# Step 3: select → top 3
if [ -n "$FIXTURE" ]; then
  CANDS=$(printf '%s\n' "$JIDS" | "$SCRIPT_DIR/select.sh" --offline-fixture "$FIXTURE")
else
  CANDS=$(printf '%s\n' "$JIDS" | "$SCRIPT_DIR/select.sh")
fi

# Step 4: apply
if [ "$MODE" = "dry-run" ]; then
  APPLY_OUT=$(printf '%s' "$CANDS" | "$SCRIPT_DIR/apply.sh" --dry-run)
else
  APPLY_ARGS=(--confirm --max-apply "$MAX_APPLY")
  [ "$MAX_BUDGET_JPY" -gt 0 ] && APPLY_ARGS+=(--max-budget-jpy "$MAX_BUDGET_JPY")
  APPLY_OUT=$(printf '%s' "$CANDS" | "$SCRIPT_DIR/apply.sh" "${APPLY_ARGS[@]}")
fi

# Step 5: write envelope
ENV=$("$JQ" -n --arg ts "$TS" --arg mode "$MODE" --argjson cands "$APPLY_OUT" \
              '{ts:$ts, mode:$mode, candidates:$cands}')

if [ "$MODE" = "dry-run" ]; then
  mkdir -p "$SKILL_DIR/state"
  printf '%s' "$ENV" > "$SKILL_DIR/state/dry-run-latest.json"
fi

echo "$ENV"

# Step 6: optional Slack ping (HARD RULE #8: external report, never primary)
APPLIED_N=$(echo "$ENV" | "$JQ" '[.candidates[] | select(.status == "applied")] | length')
DRYRUN_N=$(echo "$ENV" | "$JQ" '[.candidates[] | select(.status == "dry-run")] | length')
slack_post "🟢 earn-lancers $MODE applied=$APPLIED_N dry-run=$DRYRUN_N"
```

Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/run.sh
```

- [ ] **Step 2: Run the E2E test — must PASS now (TDD GREEN)**

Run:
```bash
/Users/anicca/anicca-oss/skills/anicca-earn-lancers/tests/test_earn_lancers_dry_run.sh
```
Expected: stdout final line `PASS`, exit code 0. If FAIL: fix the script that produced the failing assertion — do NOT proceed to commit.

- [ ] **Step 3: Write `SKILL.md`**

Create `/Users/anicca/anicca-oss/skills/anicca-earn-lancers/SKILL.md` with EXACTLY:
```markdown
---
name: anicca-earn-lancers
description: Daily Lancers gig discovery and apply skill. Camofox (:9377) drives the search, parses up to 15 candidate JIDs, ranks the top 3 by budget vs effort using a mini model (`hermes chat --model gpt-5.2-mini`), and either dry-runs (default — generates proposal text only) or submits via the proven 2-stage Vue-hidden-field pattern (`propose_start → propose_confirm → propose_finish`). LIVE mode requires explicit `--confirm` and is bounded by `--max-apply` + `--max-budget-jpy`. Login uses Google OAuth canonical (`GOOGLE_LOGIN_EMAIL`) via Camofox per HARD RULE; Lancers credentials live in `~/.openclaw/.env`. Cron schedule: daily 10:00 JST (`hermes cron`). Incoming payment routes to the existing OpenClaw bank, which CFO already scrapes — this skill does NOT touch payout. Wave 1 of the earn channel; Coconala + CrowdWorks are Wave 2.
metadata:
  type: earn
  parallel_safe: false
  expected_revenue: ¥3,000–¥50,000 per accepted gig; ~10% accept rate per port-from data
  requires:
    bins: [bash, curl, jq, python3, hermes]
    env: [GOOGLE_LOGIN_EMAIL, GOOGLE_LOGIN_PASSWORD, LANCERS_EMAIL, LANCERS_USERNAME, LANCERS_PASSWORD]
    skills: [camofox-browser]
---

# anicca-earn-lancers

Hermes skill, Wave 1 of the earn channel. Daily cron fires `scripts/run.sh` at 10:00 JST.

## Files
| Path | Role |
|------|------|
| `scripts/run.sh`         | orchestrator (default `--dry-run`) |
| `scripts/login-check.sh` | Camofox session probe + Google OAuth fallback |
| `scripts/scan.sh`        | Camofox search → JID list |
| `scripts/select.sh`      | Mini-model scoring → top 3 |
| `scripts/apply.sh`       | Proposal generation + (with `--confirm`) 2-stage submit |
| `scripts/_lib.sh`        | Shared Camofox REST wrappers + redact + Slack |
| `tests/test_earn_lancers_dry_run.sh` | E2E TDD gate |
| `tests/fixtures/sample-snapshot.json` | offline Camofox snapshot |
| `state/dry-run-latest.json` | last dry-run envelope (overwritable) |
| `data/apply-log.jsonl`   | append-only LIVE submit log |

## Invocation
```bash
# Default (safe)
bash scripts/run.sh --dry-run

# LIVE (read docs/superpowers/runbooks/2026-06-04-earn-lancers-smoke.md first)
bash scripts/run.sh --confirm --max-apply 1 --max-budget-jpy 1000
```

## Cron
```
hermes cron create "0 10 * * *" \
  --name anicca-earn-lancers \
  --script ~/.hermes/scripts/anicca-earn-lancers.sh \
  --no-agent
```
The symlink `~/.hermes/scripts/anicca-earn-lancers.sh → run.sh` carries the default `--dry-run` semantics — LIVE mode is gated by editing the cron prompt explicitly, never by the daily fire.

## Verify (HARD RULE #14 JOB'S NOT FINISHED)
- E2E test green: `tests/test_earn_lancers_dry_run.sh`
- Hermes cron registered: `hermes cron list | grep anicca-earn-lancers`
- After a LIVE smoke, `tail -1 data/apply-log.jsonl | jq '.status == "applied"'` must be `true` and the Lancers dashboard URL must show the proposal.
```

- [ ] **Step 4: Write `README.md`**

Create `/Users/anicca/anicca-oss/skills/anicca-earn-lancers/README.md` with EXACTLY:
```markdown
# anicca-earn-lancers

Hermes skill that scans Lancers (lancers.jp) for AI / 動画 / Python gigs daily, ranks the top 3 by budget vs effort with a mini-model scorer, and (in `--confirm` mode) submits a proposal through the proven 2-stage Vue-hidden-field path verified in the in-house archive (JIDs 5550526 / 5550727 / 5550692 received `propose_finish` confirmation URLs). Default mode is `--dry-run` — the daily cron writes only `state/dry-run-latest.json` and never submits. LIVE submission is gated by an explicit `--confirm` flag plus `--max-apply` and `--max-budget-jpy` safety caps, and is documented in `docs/superpowers/runbooks/2026-06-04-earn-lancers-smoke.md`. Wave 1 of the earn channel; Coconala + CrowdWorks join Wave 2.
```

- [ ] **Step 5: Write `.gitignore`**

Create `/Users/anicca/anicca-oss/skills/anicca-earn-lancers/.gitignore` with EXACTLY:
```
state/*
data/*.jsonl
!state/.keep
!data/.keep
```

Then create the keep files so the directories exist in the repo:
```bash
mkdir -p /Users/anicca/anicca-oss/skills/anicca-earn-lancers/state \
         /Users/anicca/anicca-oss/skills/anicca-earn-lancers/data
touch /Users/anicca/anicca-oss/skills/anicca-earn-lancers/state/.keep \
      /Users/anicca/anicca-oss/skills/anicca-earn-lancers/data/.keep
```

- [ ] **Step 6: Re-run the E2E test one more time after writing SKILL.md (no regression)**

Run:
```bash
/Users/anicca/anicca-oss/skills/anicca-earn-lancers/tests/test_earn_lancers_dry_run.sh
```
Expected: `PASS`.

- [ ] **Step 7: Commit**

Run:
```bash
cd /Users/anicca/anicca-oss
git add skills/anicca-earn-lancers
git commit -m "feat(skill): anicca-earn-lancers Wave 1 — daily Lancers dry-run via Camofox + Hermes mini-model scoring (#325)"
git push
```

---

### Task 9: Symlink the skill into ~/.hermes and verify Hermes registers it

**Files:**
- Create (symlink): `~/.hermes/skills/anicca-earn-lancers` → repo
- Create (symlink): `~/.hermes/scripts/anicca-earn-lancers.sh` → repo `run.sh`

- [ ] **Step 1: Symlink the skill directory**

Run:
```bash
mkdir -p /Users/anicca/.hermes/skills /Users/anicca/.hermes/scripts
ln -sf /Users/anicca/anicca-oss/skills/anicca-earn-lancers \
       /Users/anicca/.hermes/skills/anicca-earn-lancers
ln -sf /Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/run.sh \
       /Users/anicca/.hermes/scripts/anicca-earn-lancers.sh
ls -l /Users/anicca/.hermes/skills/anicca-earn-lancers \
      /Users/anicca/.hermes/scripts/anicca-earn-lancers.sh
```
Expected: both lines start with `lrwxr` and end with the repo paths.

- [ ] **Step 2: Confirm Hermes registers the skill**

Run:
```bash
hermes skills list 2>&1 | grep -E '^anicca-earn-lancers( |$)'
```
Expected: one line beginning with `anicca-earn-lancers`. (This is DONE condition #1.)

---

### Task 10: Schedule the daily cron via `hermes cron create`

**Files:** none new in the repo; Hermes manages its own cron metadata.

- [ ] **Step 1: Verify the `--script` path lives under `~/.hermes/scripts/`** (per `hermes cron create --help`)

Run:
```bash
test -L /Users/anicca/.hermes/scripts/anicca-earn-lancers.sh && \
  readlink /Users/anicca/.hermes/scripts/anicca-earn-lancers.sh
```
Expected: the symlink target → `/Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/run.sh`.

- [ ] **Step 2: Create the cron entry**

Per `hermes cron create --help` (verified v0.12.0): the supported flags are
`--name`, `--script`, `--no-agent`, `--schedule`, `--repeat`, `--workdir`, `--deliver`, `--skill`.
We use `--no-agent` (the script IS the job — no LLM fire per beat, matches HARD RULE "OpenClaw cron は mini 主軸").

Run:
```bash
hermes cron create "0 10 * * *" \
  --name anicca-earn-lancers \
  --script /Users/anicca/.hermes/scripts/anicca-earn-lancers.sh \
  --no-agent
```
Expected: prints `Created anicca-earn-lancers (0 10 * * *)` (or local equivalent), exit 0.

Note: the script defaults to `--dry-run` (= no submit). LIVE switch is NOT done via cron in Wave 1 — it requires editing the cron's `--script` line to pass `--confirm` plus safety caps. That edit is explicitly documented in the smoke runbook (Task 11) and is NOT part of this plan.

- [ ] **Step 3: Confirm registration**

Run:
```bash
hermes cron list 2>&1 | grep anicca-earn-lancers
```
Expected: one row containing `anicca-earn-lancers` and the schedule. (This is DONE condition #2.)

- [ ] **Step 4: Force-fire the cron once and confirm the contract**

Run:
```bash
hermes cron run anicca-earn-lancers 2>&1 | tail -20 \
  | tee /tmp/earn-lancers-cron-fire.log
test -s /Users/anicca/anicca-oss/skills/anicca-earn-lancers/state/dry-run-latest.json
/opt/homebrew/bin/jq '.mode' /Users/anicca/anicca-oss/skills/anicca-earn-lancers/state/dry-run-latest.json
```
Expected:
- the log contains a JSON envelope with `"mode":"dry-run"`
- `state/dry-run-latest.json` exists
- `jq '.mode'` prints `"dry-run"`

If `hermes cron run` is not implemented, the equivalent direct call is:
```bash
bash /Users/anicca/.hermes/scripts/anicca-earn-lancers.sh --dry-run
```
This will fall through to live Camofox (no `--offline-fixture`), so `login-check.sh` must already have a cookie (= prior Task 7 + manual Google 2FA tap). If Camofox prompts for 2FA tap and the tap is pending, this step's expected output is exit 7 (`login-check failed — abort`) and that is a recognized state — proceed to Task 11 to document the kickoff and complete the 2FA tap manually before the next 10:00 fire.

---

### Task 11: Write the LIVE smoke runbook

**Files:**
- Create: `docs/superpowers/runbooks/2026-06-04-earn-lancers-smoke.md`

- [ ] **Step 1: Create the directory**

Run:
```bash
mkdir -p /Users/anicca/anicca-oss/docs/superpowers/runbooks
```

- [ ] **Step 2: Write the runbook with EXACTLY this content**

Create `/Users/anicca/anicca-oss/docs/superpowers/runbooks/2026-06-04-earn-lancers-smoke.md`:
```markdown
# anicca-earn-lancers — LIVE smoke runbook

This is NOT executed by cron and NOT executed by `2026-06-04-earn-lancers.md`. A human (Dais or the implementer-on-duty) reads this before the first LIVE submit. Lancers proposals create a public reputation footprint on `keiodaisuke+anicca@gmail.com`'s Lancers account; the cap below limits the blast radius to ¥1,000 / 1 gig.

## Pre-flight (every time)

1. `curl -sS http://localhost:9377/health | jq -e '.ok and .browserConnected'` → exit 0.
2. `bash skills/anicca-earn-lancers/scripts/login-check.sh` → exit 0.
   - If exit 6 (= Google 2FA tap pending): tap "Yes" on the Google sign-in prompt on Dais's phone, then re-run. This is the **one HARD-RULE-#-2 physical exception** (Camofox SKILL.md L82-88) and is unavoidable until the cookie is minted.
3. `bash skills/anicca-earn-lancers/scripts/run.sh --dry-run` → check the JSON envelope; eyeball the 3 candidate `title_truncated` and `generated_message` fields. If any candidate is clearly NSFW / political / out-of-niche → abort, fix the keyword rotation or the scoring prompt, and re-run dry-run.

## LIVE smoke (one-shot, capped)

```bash
bash /Users/anicca/anicca-oss/skills/anicca-earn-lancers/scripts/run.sh \
  --confirm \
  --max-apply 1 \
  --max-budget-jpy 1000
```

This submits AT MOST 1 proposal, and only on a gig with budget ≤ ¥1,000.

## Verify (HARD RULE #14)

```bash
tail -1 /Users/anicca/anicca-oss/skills/anicca-earn-lancers/data/apply-log.jsonl \
  | /opt/homebrew/bin/jq '{jid, status, finish_url}'
```

Expected `{status: "applied", finish_url: "https://www.lancers.jp/work/propose_finish/<JID>"}`.
Then open the `finish_url` in Camofox to visually confirm the proposal exists.

## Kill switch

```bash
hermes cron pause anicca-earn-lancers
```

This freezes the daily cron until `hermes cron resume anicca-earn-lancers`. Use this immediately if (a) a LIVE submit lands on a gig outside niche, (b) Lancers serves a CAPTCHA, (c) the Lancers account receives a TOS warning.

## Promotion to LIVE-by-default

LIVE-by-default cron requires:
1. ≥3 successful LIVE smokes (`status:"applied"` rows in `data/apply-log.jsonl`).
2. ≥1 accepted proposal on the Lancers dashboard (= money will actually flow).
3. CFO `cfo-bank` records the incoming Lancers deposit on Dais's bank.
4. A new task `#325-promote` (separate plan) edits the cron `--script` line to pass
   `--confirm --max-apply 3 --max-budget-jpy 50000`.

Until then, the cron stays `--dry-run` and the daily fire generates proposal *drafts* only.
```

- [ ] **Step 3: Commit the runbook**

Run:
```bash
cd /Users/anicca/anicca-oss
git add docs/superpowers/runbooks/2026-06-04-earn-lancers-smoke.md
git commit -m "docs(runbook): earn-lancers LIVE smoke procedure with kill switch + promotion gate"
git push
```

---

### Task 12: Update `specs/00-MASTER.md` § LAUNCH MATRIX row ④ + close task

**Files:**
- Modify: `specs/00-MASTER.md` (LAUNCH ACCEPTANCE MATRIX row ④ sub-bullet)

- [ ] **Step 1: Add the sub-bullet**

In `/Users/anicca/anicca-oss/specs/00-MASTER.md`, locate the row:
```
 ④「平均月収 x円（コスト約 y円）」            →  #325 earn, #332 battle,  →  CFO dashboard real monthly x>y;
                                                 CFO (live)                  if not 黒字 → write honest/drop
```

Append (after that row, before row ⑤a) a sub-bullet:
```
   ↳ ④a Lancers channel = anicca-earn-lancers skill LIVE, cron `0 10 * * *` JST (dry-run),
        LIVE smoke gated by docs/superpowers/runbooks/2026-06-04-earn-lancers-smoke.md.
        (Wave 1 of earn; Coconala + CrowdWorks join as ④b/④c in Wave 2.)
```

- [ ] **Step 2: Commit + push**

Run:
```bash
cd /Users/anicca/anicca-oss
git add specs/00-MASTER.md
git commit -m "docs(spec): 00-MASTER row ④ — anicca-earn-lancers Wave 1 live (#325)"
git push
```

- [ ] **Step 3: Mark task #325 done in the TaskList**

Use the TaskUpdate tool to set `#325` status to `completed` with a one-line summary
("Wave 1: dry-run E2E green, daily cron at 10:00 JST, LIVE smoke runbook committed").
Open follow-up tasks:
- `#325-promote` — gated promotion to LIVE-by-default (depends on ≥3 successful smokes).
- `#325b` — Wave 2 Coconala (`anicca-coconala-earner`) port using this skill as template.
- `#325c` — Wave 2 CrowdWorks (`anicca-crowdworks-earner`) port using this skill as template.

---

## Self-Review

**Spec coverage:**
- `specs/00-MASTER.md` § LAUNCH ACCEPTANCE MATRIX row ④「平均月収 x円」 = directly addressed (Task 12 adds the sub-bullet linking this skill to the row).
- `specs/16-RUNTIME-CODE-TRUTH.md` § 17 ("ONE RUNTIME = Hermes ... Camofox or Nous-Portal browser ... earn = Camofox → Lancers/Coconala gig apply+deliver") = the file structure and `_lib.sh` enforce "Camofox via REST :9377, no second browser". Hermes cron `--no-agent` + `hermes chat --model gpt-5.2-mini` inside the script keep the substrate decision intact.
- CLAUDE.md HARD RULE #-2 "no human-loop excuses": only `login-check.sh` exit 6 (Google 2FA tap) and the LIVE smoke first-run touch a human. Both are documented as the ONE physical exception per Camofox SKILL.md L82-88. Every other flow (signup, scan, score, message generation, dry-run, submit) is autonomous.
- HARD RULE browser order (camofox > cloak > agent-browser): the skill imports ONLY `:9377` (camofox). `cloakbrowser` / `agent-browser` are not referenced anywhere in the new files.
- HARD RULE "Google login forever, `keiodaisuke@gmail.com` canonical, Lancers uses `keiodaisuke+anicca@gmail.com` + `LANCERS_PASSWORD`": `_lib.sh` reads env vars by their canonical names; `login-check.sh` Step 1 uses Google OAuth as the first path and only falls back to LANCERS_EMAIL+PASSWORD if the Google button is missing. No password is hard-coded; `redact()` masks values in any log line.
- HARD RULE "OpenClaw cron は mini 主軸": cron uses `--no-agent` (zero LLM per fire); the only LLM inside the script is `hermes chat --model gpt-5.2-mini` for 3 scoring calls/day. The mini model name is overridable via `LANCERS_SCORE_MODEL` for cheaper alternatives (`deepseek-v4-flash`, `kimi-k2.6-mini`).

**Placeholder scan:** none. Every step has the full file content, full command, and the exact expected output. The two values that the implementer fills (the cron schedule string `0 10 * * *` if Dais wants a different hour; the runbook's `--max-budget-jpy 1000` ceiling) are explicit numeric defaults with rationale, not TODOs.

**Type consistency:** the candidate object shape `{jid, url, title_truncated, budget_jpy, effort_estimate, score, generated_message, status}` is identical across `select.sh` (writer), `apply.sh` (reader + writer), `run.sh` envelope, and `test_earn_lancers_dry_run.sh` (assertions). The JSONL log row shape `{ts, jid, status, amount, finish_url}` matches the port-from source line 215 verbatim and the existing `data/apply-log.jsonl` rows shown in Task 1 Step 4 — so future CFO consumers (which already read this format) keep working without change.

**Reuse-first verification:**
- Camofox REST = reused (no new browser).
- The 2-stage Vue-hidden-field submit JS = ported verbatim from the in-house archive (lines 159-188 of the port-from `run.sh`).
- The keyword-by-DOW rotation = ported from line 49 of the same file.
- The Slack post helper = ported pattern from the same file.
- The orchestrator shape `run = scan → select → solve → submit` = mirrors `skills/anicca-earn-bounty/scripts/run.sh` (the closest existing skill in the same repo).
No new framework, no new dependency. The only NEW code is `login-check.sh` (Camofox cookie probe → Google OAuth fallback) and the `--dry-run` / `--offline-fixture` flags, both of which are necessary for safety and CI-of-CI.

**Risk note (read before executing):**
- Task 9 Step 2 (`hermes skills list | grep anicca-earn-lancers`) depends on Hermes treating a symlinked skill directory the same as a real one. The sister plan `2026-06-04-hermes-genesis-boot.md` Task 5 Step 10 already confirmed this works (the heartbeat skill is registered via the same symlink pattern). If for some reason this version of Hermes refuses symlinks → fall back to `rsync -a skills/anicca-earn-lancers/ ~/.hermes/skills/anicca-earn-lancers/` and re-test; commit a follow-up plan to fix the symlink path. This is the one place reality can diverge from the plan; it is gated, not glossed.
- Task 10 Step 4 (force-fire) depends on the Camofox session having a Lancers cookie. If the cookie does not yet exist (= first LIVE-side run after a fresh Camofox profile), the force-fire will exit 7 from `login-check.sh`. The plan recognizes this state and routes to Task 11's runbook to complete the 2FA tap. Until the tap, the daily cron will exit 7 every fire, never submit, and never produce a log row — failure mode is silent and bounded.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-04-earn-lancers.md`.

Per Dais's directive ("keep getting reviewed by codex; only when it's time to implement, build with agent teams"), the next move is NOT to start Task 1 — it is to run **codex-review** against this plan + specs 00 / 16 / 18 + the parent plan `2026-06-04-hermes-genesis-boot.md` (so the genesis-boot prerequisites are cross-checked). When codex says `ok: true`, dispatch the implementation via **superpowers:subagent-driven-development** — fresh subagent per task, two-stage review (spec compliance → code quality) after each task. The LIVE smoke (Task 11 runbook) is the ONLY step that calls for an out-of-band human eyeball before pulling the trigger.
