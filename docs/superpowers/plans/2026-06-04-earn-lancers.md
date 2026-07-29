# Earn Lancers — #325 Wave 1 dry-run scaffolding (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Codex round 2 (2026-06-04) verdict applied — version v2.** Scope of this plan = SCAFFOLDING ONLY. `#325` (= LAUNCH MATRIX row ④) is **NOT** closed by this plan. Real-submit + CFO bank evidence live in the follow-on Wave 2 plan (see Task 13 below). Per HARD RULE #-2: zero human-in-the-loop language ("Dais reviews / eyeball / tap 2FA / pull the trigger" all removed); the agent drives camofox + Google login env autonomously; the ONLY hard-block path is a real CAPTCHA element rendering or a financial broadcast attempt. Runtime state lives under `~/.hermes/state/`, never `/tmp`.

**Goal (revised — scaffolding only):** Port the proven in-house Lancers earner (= the only existing skill that already submitted real ¥1万 proposals through `propose_confirm → propose_finish`) into the Hermes skills format at `anicca-oss/skills/anicca-earn-lancers/`, wire it to ONE daily Hermes cron, drive Camofox (`:9377`) with Google-login-canonical session for the apply flow autonomously, and prove a `--dry-run` end-to-end with 3 scored gigs WITHOUT submitting. **This plan does NOT close `#325`** — closing `#325` requires real submitted proposals + CFO bank deposit evidence, both produced by the Wave 2 follow-on plan (Task 13).

**Architecture:** `anicca-earn-bounty` (already in `anicca-oss/skills/`) is the structural template — `SKILL.md` + `scripts/{run,scan,select,solve,submit}.sh` + `state/` + `data/` + `.gitignore`. We mirror that layout exactly. The actual apply logic ports verbatim from `~/.openclaw/skills/_archive/hybrid-v1/cfo-earner-lancers/scripts/run.sh` (= "Vue hidden-field set" pattern that proved out on JID `5550526/5550727/5550692` and got URLs `https://www.lancers.jp/work/propose_finish/<JID>`). Camofox is consumed strictly through its REST `:9377` per `~/.openclaw/skills/camofox-browser/SKILL.md` — no playwright, no Selenium. Login is Google OAuth via Camofox (HARD RULE: camofox > cloak > agent-browser); the Lancers session is the alias account `user+anicca@example.com` with `LANCERS_PASSWORD` (the one HARD-RULE-documented Google-login exception, already in `~/.openclaw/.env`). Hermes cron is invoked via `hermes cron create` with `--no-agent --script` (= cheap, no LLM per fire) per `hermes cron create --help` v0.12.0 — the scoring/templating LLM is invoked *inside* the script via `hermes chat -q` with `--model` pinned to a mini model (HARD RULE "OpenClaw cron は mini 主軸").

**Tech Stack:** Hermes Agent v0.12.0+ (already booted by sister plan `2026-06-04-hermes-genesis-boot.md`) · Camofox REST `http://localhost:9377` (process already running, verified `/health` → `ok:true browserConnected:true`) · `bash` · `curl` · `jq` (`/opt/homebrew/bin/jq`) · `python3` (stdlib only — `json`, `urllib.parse`, `re`) · `git` · `~/.openclaw/.env` (read-only, never echoed) · existing in-house code (port-from path: `~/.openclaw/skills/_archive/hybrid-v1/cfo-earner-lancers/scripts/run.sh`, 246 lines, the proven version).

**Scope-out (other plans):**
- New earn channels Coconala (`anicca-coconala-earner`) and CrowdWorks (`anicca-crowdworks-earner`) → **Wave 2** (separate plans, same template once this Wave 1 lands).
- Bounty + x402 (Algora / OnlyDust / x402 facilitator) → **#324** (`anicca-earn-bounty` already in repo).
- Capafy publish lane → **#43** (separate skill).
- New bank wiring / payout rails → covered by `anicca-payout-*` skills already in `anicca-oss/skills/`. Incoming Lancers payments hit the existing OpenClaw bank, which CFO already scrapes (`cfo-bank` skill, LIVE since 2026-05-28). **This plan does NOT touch payout/CFO.**
- Hermes runtime, BYOK fuel, gateway / launchd, AGENTS.md symlink → done by `2026-06-04-hermes-genesis-boot.md`. This plan ASSUMES that body is alive.
- eKYC / selfie upload / withdraw → out of scope here; Lancers releases reward to the bank tied to the Lancers account, then CFO surfaces it. eKYC is a one-time HARD-RULE-#18 physical exception covered by the future `anicca-earn-lancers/scripts/ekyc.sh` task (NOT in Wave 1).

**Done condition for this plan (Wave 1 scaffolding only — `#325` stays OPEN):**
1. `hermes skills list 2>&1 | grep -E '^anicca-earn-lancers( |$)'` → exactly one row.
2. `hermes cron list 2>&1 | grep anicca-earn-lancers` → exactly one row, schedule `0 10 * * *` (daily 10:00 JST = quiet hour, Lancers traffic low → less competition).
3. `bash skills/anicca-earn-lancers/scripts/run.sh --dry-run` prints a single JSON envelope with `mode:"dry-run"`, `candidates: [<3 objects>]`, each object has `{jid, url, title_truncated, budget_jpy, effort_estimate, score, generated_message}`, and NO `applied` rows. Exit 0. NO HTTP call to `/work/propose_start/*/submit` is made (verified by grep against the camofox `evaluate` payload).
4. `bash skills/anicca-earn-lancers/scripts/run.sh --dry-run` also writes `~/.hermes/state/earn-lancers-dry-run-latest.json` (overwritable, OUTSIDE the repo per X4) and does NOT touch `~/.hermes/state/earn-lancers-runs.jsonl`.
5. The E2E test `tests/test_earn_lancers_dry_run.sh` passes (RED → GREEN → REFACTOR completed).
6. Wave 2 follow-on plan exists at `docs/superpowers/plans/2026-06-04-earn-lancers-wave2-realsubmit.md` (created in Task 13) describing the EXACT autonomous-agent steps to submit one ¥1k-cap proposal (`--max-apply 1 --max-budget-jpy 1000 --confirm`), watch CFO/bank, and only close `#325` when the cash lands. The Wave 2 plan is committed but NOT executed by this plan.
7. `specs/00-MASTER.md` § LAUNCH ACCEPTANCE MATRIX row ④「平均月収 x円（コスト約 y円）」 has a sub-bullet noting "Lancers channel: anicca-earn-lancers Wave 1 scaffold live (cron daily 10:00 JST, dry-run only). Row ④ does NOT advance from this plan — advancement requires Wave 2 real-submit + CFO deposit evidence."
8. All new files committed + pushed to `anicca-oss` (CLAUDE.md rule 0.4).
9. `#325` is NOT marked completed. It remains OPEN with a comment "Wave 1 scaffolding done; awaiting Wave 2 real-submit + CFO bank evidence".

---

## File Structure (what each file owns)

```
anicca-oss/                                              (this repo, committed)
  skills/anicca-earn-lancers/
    SKILL.md                       ← Hermes frontmatter + how-it-runs
    .gitignore                     ← keep only state/.keep + data/.keep in repo
    state/.keep                    ← repo placeholder ONLY; runtime state lives under ~/.hermes/state/
    data/.keep                     ← repo placeholder ONLY; runtime logs live under ~/.hermes/state/
    scripts/run.sh                 ← orchestrator: parses flags, calls scan/select/apply, writes ~/.hermes/state/
    scripts/scan.sh                ← Camofox search → JID list (read-only)
    scripts/select.sh              ← LLM-score top 3 by (budget vs effort) via `hermes chat -q --model`
    scripts/apply.sh               ← Camofox apply (--dry-run = stop before evaluate(); --confirm = submit)
    scripts/login-check.sh         ← Camofox `/sessions/anicca/cookies` probe; if no Lancers cookie → autonomous Google-OAuth via GOOGLE_LOGIN_EMAIL/PASSWORD (+ optional Authy TOTP env)
    scripts/_lib.sh                ← shared helpers (camofox curl wrappers, slack_post, redact)
    tests/test_earn_lancers_dry_run.sh   ← E2E: dry-run produces a 3-candidate JSON envelope
    tests/fixtures/sample-snapshot.json  ← canned camofox snapshot for offline-of-Lancers unit tests
    README.md                      ← one-paragraph human description
  docs/superpowers/plans/
    2026-06-04-earn-lancers.md     ← THIS plan (Wave 1 scaffolding)
    2026-06-04-earn-lancers-wave2-realsubmit.md ← Wave 2 follow-on (real submit + CFO verify)
  specs/00-MASTER.md               ← add sub-bullet to § LAUNCH MATRIX row ④ (scaffold-only note)

~/.hermes/                                               (runtime, NOT committed — X4)
  skills/anicca-earn-lancers/                  ← SYMLINK → anicca-oss/skills/anicca-earn-lancers/
  scripts/anicca-earn-lancers.sh               ← SYMLINK → anicca-oss/skills/anicca-earn-lancers/scripts/run.sh
                                                 (Hermes cron requires the script to live under ~/.hermes/scripts/)
  state/earn-lancers-dry-run-latest.json       ← last dry-run envelope (overwritable) — canonical runtime path
  state/earn-lancers-runs.jsonl                ← append-only LIVE submit log (1 row per apply attempt, written by apply.sh)
  state/earn-lancers-cron-fire.log             ← transient cron-fire stdout/stderr (Task 10 Step 4) — never `/tmp`
  cron/anicca-earn-lancers.*                   ← managed by `hermes cron create`

~/.openclaw/.env                                         (read-only, NEVER echoed)
  GOOGLE_LOGIN_EMAIL=…             ← canonical Google identity (HARD RULE)
  GOOGLE_LOGIN_PASSWORD=…
  LANCERS_EMAIL=user+anicca@example.com   ← documented HARD-RULE exception
  LANCERS_USERNAME=…
  LANCERS_PASSWORD=…
```

Why symlinks for the skill + run.sh: identical to the genesis-boot pattern. The canonical source lives in the repo (where review/PR lands); Hermes reads it instantly via the symlink — no copy step to forget.

Why `_lib.sh`: the camofox curl wrappers (`cf_open`, `cf_navigate`, `cf_snapshot`, `cf_evaluate`) repeat 4× across scan/select/apply. Extracting them keeps each step file ≤200 lines (CLAUDE.md coding-style.md: "200-400 lines typical, 800 max").

---

### Task 0: Preflight (cross-plan X5 — camofox + hermes + env presence)

**Files:** none new. Read-only checks.

- [ ] **Step 1: Camofox health (X5)**

Run:
```bash
curl -sS --max-time 5 http://localhost:9377/health \
  | /opt/homebrew/bin/jq -e '.ok == true and .browserConnected == true' >/dev/null \
  && echo CAMOFOX_OK
```
Expected: `CAMOFOX_OK`. If non-zero → `bash ~/.openclaw/skills/camofox-browser/scripts/start.sh` then re-check. Camofox is non-negotiable (camofox > cloak > agent-browser per HARD RULE).

- [ ] **Step 2: Hermes binary presence (X1 + X5)**

Run:
```bash
command -v hermes && hermes --version
```
Expected: a path printed and a version line ≥ `0.12.0`. Do NOT run `hermes update` (X1 — pin v0.12.0).

- [ ] **Step 3: Env presence check — GOOGLE_LOGIN_EMAIL / GOOGLE_LOGIN_PASSWORD / LANCERS_PASSWORD (X5)**

Run:
```bash
for k in GOOGLE_LOGIN_EMAIL GOOGLE_LOGIN_PASSWORD LANCERS_PASSWORD; do
  if grep -q "^$k=" /Users/operator/.openclaw/.env 2>/dev/null; then echo "FOUND $k"; else echo "MISSING $k"; fi
done
```
Expected: 3× `FOUND …`. Any `MISSING …` → STOP. Do NOT proceed: the autonomous flow needs all three (HARD RULE: Google login canonical, Lancers documented exception).

- [ ] **Step 4: Authy / TOTP env (optional — only if a Google 2FA challenge actually renders)**

Run:
```bash
grep -q "^GOOGLE_TOTP_SECRET=" /Users/operator/.openclaw/.env 2>/dev/null \
  && echo "TOTP_AVAILABLE" || echo "TOTP_ABSENT (gog-gmail auto-read fallback will be used)"
```
Expected: either line is acceptable. If absent, `login-check.sh` auto-reads the 2FA code from `user@example.com` via the existing gog-gmail MCP (no human in loop). If a real CAPTCHA element renders (= `iframe[src*="recaptcha"]` or `iframe[src*="hcaptcha"]` in the snapshot) — and ONLY then — record the exact rendered HTML and stop; that is the only HARD RULE #-2 genuine hard-block.

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
  if grep -q "^$k=" /Users/operator/.openclaw/.env 2>/dev/null; then echo "FOUND $k"; else echo "MISSING $k"; fi
done
```
Expected: 5× `FOUND …`. Any `MISSING …` → STOP, fix the env file first; do not proceed (HARD RULE: Google login canonical).

- [ ] **Step 4: Confirm the in-house port-from source is readable**

Run:
```bash
test -r /Users/operator/.openclaw/skills/_archive/hybrid-v1/cfo-earner-lancers/scripts/run.sh && \
  wc -l /Users/operator/.openclaw/skills/_archive/hybrid-v1/cfo-earner-lancers/scripts/run.sh
test -r /Users/operator/.openclaw/skills/cfo-earner-lancers/data/apply-log.jsonl && \
  /opt/homebrew/bin/jq -r '.jid' /Users/operator/.openclaw/skills/cfo-earner-lancers/data/apply-log.jsonl
```
Expected: 246-line port-from file readable, and 4 JIDs printed (`5550526`, `5550727`, `5550692`, `5550661`) — these are the proven-pattern receipts. Record them in scratch notes as the ground truth that the port-from logic worked.

- [ ] **Step 5: Commit the plan itself so the rest is reviewable against it**

Run:
```bash
cd /Users/operator/anicca-oss
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
mkdir -p /Users/operator/anicca-oss/skills/anicca-earn-lancers/tests/fixtures
```

Create `/Users/operator/anicca-oss/skills/anicca-earn-lancers/tests/fixtures/sample-snapshot.json` with EXACTLY this content (canned camofox snapshot — 5 candidate JIDs, varying budgets, so the scorer has real input to rank):
```json
{
  "url": "https://www.lancers.jp/work/search?keyword=AI&open=1",
  "snapshot": "ref=e1 [link] AI 動画制作 (1本) /work/detail/5560001 — 予算 ¥10,000\nref=e2 [link] ChatGPT プロンプト 改善 /work/detail/5560002 — 予算 ¥3,000\nref=e3 [link] Python スクレイピング /work/detail/5560003 — 予算 ¥50,000 大規模\nref=e4 [link] LINE Bot 作成 /work/detail/5560004 — 予算 ¥8,000\nref=e5 [link] 動画 字幕 100本 一括 /work/detail/5560005 — 予算 ¥200,000\nref=e6 [link] AI 関連 /work/detail/5560006"
}
```

- [ ] **Step 2: Write the failing test**

Create `/Users/operator/anicca-oss/skills/anicca-earn-lancers/tests/test_earn_lancers_dry_run.sh` with EXACTLY this content:
```bash
#!/usr/bin/env bash
# E2E: `run.sh --dry-run --offline-fixture <path>` MUST produce a JSON envelope on stdout
# with mode=dry-run and exactly 3 scored candidates, and MUST NOT touch the runs jsonl.

set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FIXTURE="$SKILL_DIR/tests/fixtures/sample-snapshot.json"
STATE_DIR="${HERMES_STATE_DIR:-$HOME/.hermes/state}"
LOG="$STATE_DIR/earn-lancers-runs.jsonl"
DRY_LATEST="$STATE_DIR/earn-lancers-dry-run-latest.json"

# Capture log size before
mkdir -p "$STATE_DIR"
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

# Assertion 6: runs log untouched (~/.hermes/state/earn-lancers-runs.jsonl)
LOG_AFTER=$(wc -c < "$LOG" 2>/dev/null || echo 0)
[ "$LOG_BEFORE" = "$LOG_AFTER" ] || { echo "FAIL: $LOG mutated (before=$LOG_BEFORE after=$LOG_AFTER)"; exit 1; }

# Assertion 7: ~/.hermes/state/earn-lancers-dry-run-latest.json written
test -s "$DRY_LATEST" || { echo "FAIL: $DRY_LATEST not written"; exit 1; }

# Assertion 8: NO call would hit the submit URL (grep the dry-run-latest for forbidden URL substring)
if /opt/homebrew/bin/jq -r '.candidates[] | .url' "$DRY_LATEST" | grep -q 'propose_finish'; then
  echo "FAIL: candidate URLs leaked propose_finish path (= submit-side URL)"; exit 1
fi

echo "PASS"
```

Make executable:
```bash
chmod +x /Users/operator/anicca-oss/skills/anicca-earn-lancers/tests/test_earn_lancers_dry_run.sh
```

- [ ] **Step 3: Run the test — must FAIL because nothing exists (TDD RED)**

Run:
```bash
/Users/operator/anicca-oss/skills/anicca-earn-lancers/tests/test_earn_lancers_dry_run.sh
```
Expected: non-zero exit with `No such file or directory: …/scripts/run.sh` (or shell complaining about missing executable). This RED is the entry contract for Tasks 3-6.

---

### Task 3: Write the shared `_lib.sh` (camofox wrappers, redact, slack)

**Files:**
- Create: `skills/anicca-earn-lancers/scripts/_lib.sh`

- [ ] **Step 1: Create the directory**

Run:
```bash
mkdir -p /Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts
mkdir -p /Users/operator/anicca-oss/skills/anicca-earn-lancers/state
mkdir -p /Users/operator/anicca-oss/skills/anicca-earn-lancers/data
```

- [ ] **Step 2: Write `_lib.sh` with EXACTLY this content**

Create `/Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/_lib.sh`:
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
chmod 644 /Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/_lib.sh
```

- [ ] **Step 3: Smoke `_lib.sh` directly**

Run:
```bash
( source /Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/_lib.sh; \
  cf_health && echo HEALTH_OK; \
  echo "redacted=$(redact 'hello LANCERS_PASSWORD_OK world')" )
```
Expected: `HEALTH_OK` followed by `redacted=hello LANCERS_PASSWORD_OK world` (no actual secret was in the string, so it passes through unchanged — but this proves the redact function loaded). No values from `~/.openclaw/.env` are ever printed.

---

### Task 4: Write `scan.sh` (Camofox search → JID list, --offline-fixture support)

**Files:**
- Create: `skills/anicca-earn-lancers/scripts/scan.sh`

- [ ] **Step 1: Write `scan.sh` with EXACTLY this content**

Create `/Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/scan.sh`:
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
chmod +x /Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/scan.sh
```

- [ ] **Step 2: Smoke `scan.sh --offline-fixture`**

Run:
```bash
/Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/scan.sh \
  --offline-fixture /Users/operator/anicca-oss/skills/anicca-earn-lancers/tests/fixtures/sample-snapshot.json
```
Expected: 6 JIDs printed, one per line, in order: `5560001`, `5560002`, `5560003`, `5560004`, `5560005`, `5560006`. Exit 0.

---

### Task 5: Write `select.sh` (LLM-score top 3 by budget vs effort, via mini model)

**Files:**
- Create: `skills/anicca-earn-lancers/scripts/select.sh`

- [ ] **Step 1: Write `select.sh` with EXACTLY this content**

Create `/Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/select.sh`:
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
chmod +x /Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/select.sh
```

- [ ] **Step 2: Smoke `select.sh --offline-fixture` against the 6-JID fixture**

Run:
```bash
/Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/scan.sh \
  --offline-fixture /Users/operator/anicca-oss/skills/anicca-earn-lancers/tests/fixtures/sample-snapshot.json \
| /Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/select.sh \
  --offline-fixture /Users/operator/anicca-oss/skills/anicca-earn-lancers/tests/fixtures/sample-snapshot.json \
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

Create `/Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/apply.sh`:
```bash
#!/usr/bin/env bash
# apply.sh — generate the proposal message and (if --confirm) submit it.
# stdin: JSON array of candidate objects from select.sh
# stdout: JSON array of {jid, url, generated_message, status} per candidate.
#
# Modes:
#   --dry-run         → DO NOT call cf_evaluate, DO NOT touch the runs log,
#                       generated_message stops at the proposal text, status="dry-run".
#   --confirm         → execute the proven 2-stage submit
#                       (propose_start → propose_confirm → propose_finish).
#                       Append one JSONL row per candidate to
#                       ~/.hermes/state/earn-lancers-runs.jsonl (HERMES_STATE_DIR overridable).
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
STATE_DIR="${HERMES_STATE_DIR:-$HOME/.hermes/state}"
APPLY_LOG="$STATE_DIR/earn-lancers-runs.jsonl"
mkdir -p "$STATE_DIR"

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
chmod +x /Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/apply.sh
```

- [ ] **Step 2: Smoke `apply.sh --dry-run` against the select output**

Run:
```bash
/Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/scan.sh \
  --offline-fixture /Users/operator/anicca-oss/skills/anicca-earn-lancers/tests/fixtures/sample-snapshot.json \
| /Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/select.sh \
  --offline-fixture /Users/operator/anicca-oss/skills/anicca-earn-lancers/tests/fixtures/sample-snapshot.json \
| /Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/apply.sh --dry-run \
| /opt/homebrew/bin/jq '[.[] | .status]'
```
Expected: `["dry-run","dry-run","dry-run"]`. And `wc -l ~/.hermes/state/earn-lancers-runs.jsonl 2>/dev/null` must show 0 (= no log write in dry-run; the runs log lives under `~/.hermes/state/`, not in the repo per X4).

---

### Task 7: Write `login-check.sh` (Camofox cookie probe + Google OAuth fallback)

**Files:**
- Create: `skills/anicca-earn-lancers/scripts/login-check.sh`

- [ ] **Step 1: Write `login-check.sh` with EXACTLY this content**

Create `/Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/login-check.sh`:
```bash
#!/usr/bin/env bash
# login-check.sh — verify the camofox session has a Lancers cookie; if not, the
# agent runs the FULL Google-OAuth flow autonomously via Camofox using
# GOOGLE_LOGIN_EMAIL/PASSWORD (HARD RULE #-2: Anicca does everything).
#
# 2FA handling — fully autonomous:
#   (a) If a TOTP challenge renders, use GOOGLE_TOTP_SECRET (Authy/OTP env) to
#       compute the 6-digit code with `oathtool --totp -b "$GOOGLE_TOTP_SECRET"`
#       and type it; OR
#   (b) read the latest 2-step verification email at user@example.com
#       via the gog-gmail MCP and type the code.
# No "Dais reviews", no "tap on phone", no human eyeball — the agent drives.
#
# HARD-BLOCK (only): a real CAPTCHA element renders in the snapshot
# (iframe with src containing "recaptcha" / "hcaptcha" / "turnstile") OR the
# page asks for a financial broadcast. Record the verbatim snapshot subset
# at ~/.hermes/state/earn-lancers-login-hardblock.json and exit non-0.
# The earn task stays OPEN (do NOT close it).

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
#    → 2-step verification handled autonomously by 3b/3c below (TOTP env OR gog-gmail auto-read).
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

# 3b. CAPTCHA / hard-block detector (HARD RULE #-2 genuine hard-block ONLY)
SNAP=$(cf_snapshot "$TAB")
if printf '%s' "$SNAP" | grep -Eq 'iframe[^>]*src=[^>]*(recaptcha|hcaptcha|turnstile)'; then
  HARDBLOCK_PATH="$HOME/.hermes/state/earn-lancers-login-hardblock.json"
  mkdir -p "$(dirname "$HARDBLOCK_PATH")"
  printf '%s' "$SNAP" > "$HARDBLOCK_PATH"
  err "real CAPTCHA element rendered — verbatim snapshot saved to $HARDBLOCK_PATH (#325 stays OPEN)"
  cf_close "$TAB"
  exit 9
fi

# 3c. Autonomous 2FA handling (no human in loop)
#  - TOTP path (if GOOGLE_TOTP_SECRET present)
if printf '%s' "$SNAP" | grep -Eq '2-step|two-step|verification code|認証コード'; then
  if [ -n "${GOOGLE_TOTP_SECRET:-}" ] && command -v oathtool >/dev/null 2>&1; then
    CODE=$(oathtool --totp -b "$GOOGLE_TOTP_SECRET" 2>/dev/null || true)
    if [ -n "$CODE" ]; then
      TOTP_REF=$(printf '%s' "$SNAP" | "$PYTHON" -c '
import json,sys,re
d=json.load(sys.stdin); s=d.get("snapshot","")
m=re.search(r"ref=(\S+).*(?:totpPin|code|verification|認証コード)", s, re.I)
print(m.group(1) if m else "")
')
      if [ -n "$TOTP_REF" ]; then
        curl -sS -X POST "$CAMOFOX/tabs/$TAB/type" \
          -H 'Content-Type: application/json' \
          -d "$("$JQ" -n --arg r "$TOTP_REF" --arg t "$CODE" \
                          --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                          '{ref:$r, text:$t, userId:$uid, sessionKey:$sk}')" >/dev/null
        sleep 1
        curl -sS -X POST "$CAMOFOX/tabs/$TAB/press" \
          -H 'Content-Type: application/json' \
          -d "$("$JQ" -n --arg k "Enter" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                          '{key:$k, userId:$uid, sessionKey:$sk}')" >/dev/null
        sleep 8
      fi
    fi
  fi
  #  - gog-gmail auto-read fallback path (no TOTP env)
  #  Polls user@example.com for "Google" subject in the last 60s via
  #  `hermes chat -q --skill gog-gmail "fetch latest Google 2-step code"`.
  #  The mini model returns the 6-digit code, which we then type.
  if [ -z "${GOOGLE_TOTP_SECRET:-}" ]; then
    GCODE=$(hermes chat -q --model "${LANCERS_SCORE_MODEL:-gpt-5.2-mini}" \
      "Read the most recent email in user@example.com (last 90s) with subject containing 'Google' or '確認コード' or '2-step verification'. Reply with ONLY the 6-digit verification code, no prose. If none found, reply NONE." 2>/dev/null | tr -d ' \n\r' || true)
    if printf '%s' "$GCODE" | grep -Eq '^[0-9]{6}$'; then
      SNAP2=$(cf_snapshot "$TAB")
      G_REF=$(printf '%s' "$SNAP2" | "$PYTHON" -c '
import json,sys,re
d=json.load(sys.stdin); s=d.get("snapshot","")
m=re.search(r"ref=(\S+).*(?:code|verification|認証コード)", s, re.I)
print(m.group(1) if m else "")
')
      if [ -n "$G_REF" ]; then
        curl -sS -X POST "$CAMOFOX/tabs/$TAB/type" \
          -H 'Content-Type: application/json' \
          -d "$("$JQ" -n --arg r "$G_REF" --arg t "$GCODE" \
                          --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                          '{ref:$r, text:$t, userId:$uid, sessionKey:$sk}')" >/dev/null
        sleep 1
        curl -sS -X POST "$CAMOFOX/tabs/$TAB/press" \
          -H 'Content-Type: application/json' \
          -d "$("$JQ" -n --arg k "Enter" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                          '{key:$k, userId:$uid, sessionKey:$sk}')" >/dev/null
        sleep 8
      fi
    fi
  fi
fi

# 4. Re-probe cookies
COOKIES_JSON=$(curl -sS "$CAMOFOX/sessions/$USER_ID/cookies?sessionKey=$SESSION_KEY" 2>/dev/null || echo '[]')
HAS=$(printf '%s' "$COOKIES_JSON" | "$JQ" '[.[] | select(.domain | test("lancers.jp"))] | length')
cf_close "$TAB"
if [ "${HAS:-0}" -gt 0 ]; then
  ok "lancers cookie obtained (n=$HAS)"
  exit 0
fi
err "login flow ran but no lancers cookie — autonomous 2FA path did not converge (TOTP missing + gog-gmail empty), record state and retry next beat"
HARDBLOCK_PATH="$HOME/.hermes/state/earn-lancers-login-hardblock.json"
mkdir -p "$(dirname "$HARDBLOCK_PATH")"
printf '%s' "$SNAP" > "$HARDBLOCK_PATH"
exit 6
```

Make executable:
```bash
chmod +x /Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/login-check.sh
```

- [ ] **Step 2: Document expected exit codes**

| Exit | Meaning |
|------|---------|
| 0    | Camofox session has a Lancers cookie (live ready) |
| 3    | Camofox not running |
| 4    | Google-login button missing on Lancers login page (page redesign — needs script update) |
| 5    | Google email field ref not found (OAuth UI redesign) |
| 6    | Autonomous 2FA path (TOTP env + gog-gmail auto-read) did not converge this beat — verbatim Camofox snapshot saved to `~/.hermes/state/earn-lancers-login-hardblock.json`. Earn task stays OPEN. Next beat retries automatically (cron). |
| 9    | Real CAPTCHA / hCaptcha / Turnstile iframe rendered in snapshot — verbatim subset saved to `~/.hermes/state/earn-lancers-login-hardblock.json` (HARD RULE #-2 genuine hard-block). Earn task stays OPEN. |

(No live execution in this step — that happens in Task 9. This step writes the file and prints the table; the table is the contract that Task 9 checks against.)

---

### Task 8: Write `run.sh` (orchestrator), SKILL.md, README, .gitignore — TDD GREEN

**Files:**
- Create: `skills/anicca-earn-lancers/scripts/run.sh`
- Create: `skills/anicca-earn-lancers/SKILL.md`
- Create: `skills/anicca-earn-lancers/README.md`
- Create: `skills/anicca-earn-lancers/.gitignore`

- [ ] **Step 1: Write `run.sh` with EXACTLY this content**

Create `/Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/run.sh`:
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
STATE_DIR="${HERMES_STATE_DIR:-$HOME/.hermes/state}"

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
  mkdir -p "$STATE_DIR"
  printf '%s' "$ENV" > "$STATE_DIR/earn-lancers-dry-run-latest.json"
fi

echo "$ENV"

# Step 6: optional Slack ping (HARD RULE #8: external report, never primary)
APPLIED_N=$(echo "$ENV" | "$JQ" '[.candidates[] | select(.status == "applied")] | length')
DRYRUN_N=$(echo "$ENV" | "$JQ" '[.candidates[] | select(.status == "dry-run")] | length')
slack_post "🟢 earn-lancers $MODE applied=$APPLIED_N dry-run=$DRYRUN_N"
```

Make executable:
```bash
chmod +x /Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/run.sh
```

- [ ] **Step 2: Run the E2E test — must PASS now (TDD GREEN)**

Run:
```bash
/Users/operator/anicca-oss/skills/anicca-earn-lancers/tests/test_earn_lancers_dry_run.sh
```
Expected: stdout final line `PASS`, exit code 0. If FAIL: fix the script that produced the failing assertion — do NOT proceed to commit.

- [ ] **Step 3: Write `SKILL.md`**

Create `/Users/operator/anicca-oss/skills/anicca-earn-lancers/SKILL.md` with EXACTLY:
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
| `state/.keep`            | repo placeholder; runtime state lives at `~/.hermes/state/` (X4) |
| `data/.keep`             | repo placeholder; runtime logs live at `~/.hermes/state/` (X4) |
| `~/.hermes/state/earn-lancers-dry-run-latest.json` | last dry-run envelope (overwritable) — runtime |
| `~/.hermes/state/earn-lancers-runs.jsonl` | append-only LIVE submit log — runtime |
| `~/.hermes/state/earn-lancers-cron-fire.log` | transient cron-fire stdout/stderr — runtime |

## Invocation
```bash
# Default (safe)
bash scripts/run.sh --dry-run

# LIVE (Wave 2 only — see docs/superpowers/plans/2026-06-04-earn-lancers-wave2-realsubmit.md)
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
- Wave 1 done = scaffold only. `#325` (LAUNCH MATRIX row ④) is NOT closed by this skill alone.
- After a Wave 2 LIVE submit, `tail -1 ~/.hermes/state/earn-lancers-runs.jsonl | jq '.status == "applied"'` must be `true`, the Lancers dashboard URL must show the proposal, AND `cfo-bank` must surface the incoming deposit before `#325` can move.
```

- [ ] **Step 4: Write `README.md`**

Create `/Users/operator/anicca-oss/skills/anicca-earn-lancers/README.md` with EXACTLY:
```markdown
# anicca-earn-lancers

Hermes skill (Wave 1 = scaffolding only) that scans Lancers (lancers.jp) for AI / 動画 / Python gigs daily, ranks the top 3 by budget vs effort with a mini-model scorer, and (in `--confirm` mode) submits a proposal through the proven 2-stage Vue-hidden-field path verified in the in-house archive (JIDs 5550526 / 5550727 / 5550692 received `propose_finish` confirmation URLs). Default mode is `--dry-run` — the daily cron writes only `~/.hermes/state/earn-lancers-dry-run-latest.json` and never submits. LIVE submission is gated by an explicit `--confirm` flag plus `--max-apply` and `--max-budget-jpy` safety caps and lives in the Wave 2 follow-on plan (`docs/superpowers/plans/2026-06-04-earn-lancers-wave2-realsubmit.md`). Closing `#325` (LAUNCH MATRIX row ④) requires Wave 2 real-submit + CFO bank deposit evidence — Wave 1 does NOT close `#325`.
```

- [ ] **Step 5: Write `.gitignore`**

Create `/Users/operator/anicca-oss/skills/anicca-earn-lancers/.gitignore` with EXACTLY (X4 — only `.keep` files belong in the repo; all runtime state lives under `~/.hermes/state/`):
```
state/*
data/*
!state/.keep
!data/.keep
```

Then create the keep files so the directories exist in the repo:
```bash
mkdir -p /Users/operator/anicca-oss/skills/anicca-earn-lancers/state \
         /Users/operator/anicca-oss/skills/anicca-earn-lancers/data
touch /Users/operator/anicca-oss/skills/anicca-earn-lancers/state/.keep \
      /Users/operator/anicca-oss/skills/anicca-earn-lancers/data/.keep
```

- [ ] **Step 6: Re-run the E2E test one more time after writing SKILL.md (no regression)**

Run:
```bash
/Users/operator/anicca-oss/skills/anicca-earn-lancers/tests/test_earn_lancers_dry_run.sh
```
Expected: `PASS`.

- [ ] **Step 7: Commit**

Run:
```bash
cd /Users/operator/anicca-oss
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
mkdir -p /Users/operator/.hermes/skills /Users/operator/.hermes/scripts
ln -sf /Users/operator/anicca-oss/skills/anicca-earn-lancers \
       /Users/operator/.hermes/skills/anicca-earn-lancers
ln -sf /Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/run.sh \
       /Users/operator/.hermes/scripts/anicca-earn-lancers.sh
ls -l /Users/operator/.hermes/skills/anicca-earn-lancers \
      /Users/operator/.hermes/scripts/anicca-earn-lancers.sh
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
test -L /Users/operator/.hermes/scripts/anicca-earn-lancers.sh && \
  readlink /Users/operator/.hermes/scripts/anicca-earn-lancers.sh
```
Expected: the symlink target → `/Users/operator/anicca-oss/skills/anicca-earn-lancers/scripts/run.sh`.

- [ ] **Step 2: Create the cron entry**

Per `hermes cron create --help` (verified v0.12.0): the supported flags are
`--name`, `--script`, `--no-agent`, `--schedule`, `--repeat`, `--workdir`, `--deliver`, `--skill`.
We use `--no-agent` (the script IS the job — no LLM fire per beat, matches HARD RULE "OpenClaw cron は mini 主軸").

Run:
```bash
hermes cron create "0 10 * * *" \
  --name anicca-earn-lancers \
  --script /Users/operator/.hermes/scripts/anicca-earn-lancers.sh \
  --no-agent
```
Expected: prints `Created anicca-earn-lancers (0 10 * * *)` (or local equivalent), exit 0.

Note: the script defaults to `--dry-run` (= no submit). LIVE switch is NOT done via cron in Wave 1 — it requires the Wave 2 plan (`docs/superpowers/plans/2026-06-04-earn-lancers-wave2-realsubmit.md`) which runs ONE autonomous capped real-submit manually via the agent (not via cron). Task 11's ops note documents Wave 1 retry semantics only.

- [ ] **Step 3: Confirm registration**

Run:
```bash
hermes cron list 2>&1 | grep anicca-earn-lancers
```
Expected: one row containing `anicca-earn-lancers` and the schedule. (This is DONE condition #2.)

- [ ] **Step 4: Force-fire the cron once and confirm the contract (logs to ~/.hermes/state, NEVER /tmp)**

Run:
```bash
mkdir -p ~/.hermes/state
hermes cron run anicca-earn-lancers 2>&1 | tail -20 \
  | tee ~/.hermes/state/earn-lancers-cron-fire.log
test -s ~/.hermes/state/earn-lancers-dry-run-latest.json
/opt/homebrew/bin/jq '.mode' ~/.hermes/state/earn-lancers-dry-run-latest.json
```
Expected:
- `~/.hermes/state/earn-lancers-cron-fire.log` contains a JSON envelope with `"mode":"dry-run"`
- `~/.hermes/state/earn-lancers-dry-run-latest.json` exists
- `jq '.mode'` prints `"dry-run"`

If `hermes cron run` is not implemented, the equivalent direct call is:
```bash
bash /Users/operator/.hermes/scripts/anicca-earn-lancers.sh --dry-run
```
This falls through to live Camofox (no `--offline-fixture`). `login-check.sh` runs autonomously per Task 7 (Google login env + TOTP / gog-gmail auto-read — NO human tap). Recognized non-success exits:
- exit 6 → autonomous 2FA path did not converge this beat; verbatim Camofox snapshot saved to `~/.hermes/state/earn-lancers-login-hardblock.json`. The next cron fire retries automatically. Earn task stays OPEN.
- exit 9 → real CAPTCHA iframe rendered (HARD RULE #-2 genuine hard-block); verbatim snapshot saved to the same hardblock file. Earn task stays OPEN.
- exit 7 → `login-check` aborted; inspect `~/.hermes/state/earn-lancers-login-hardblock.json` to diagnose and patch on the next beat.

In all cases above the cron is allowed to keep retrying — no human eyeballing, no "ping Dais" step, no `/tmp` writes.

---

### Task 11: Write the Wave 1 autonomous-operation note (NOT a "human reads before pulling trigger" runbook)

> Codex round 2: the previous "smoke runbook with human eyeballing" is removed. Wave 1 is autonomous + dry-run-only. The autonomous real-submit lives in Wave 2 (Task 13). This task only documents the kill-switch + retry semantics for the daily dry-run cron.

**Files:**
- Create: `docs/superpowers/runbooks/2026-06-04-earn-lancers-ops.md`

- [ ] **Step 1: Create the directory**

Run:
```bash
mkdir -p /Users/operator/anicca-oss/docs/superpowers/runbooks
```

- [ ] **Step 2: Write the ops note with EXACTLY this content**

Create `/Users/operator/anicca-oss/docs/superpowers/runbooks/2026-06-04-earn-lancers-ops.md`:
```markdown
# anicca-earn-lancers Wave 1 — autonomous ops note

Wave 1 is dry-run-only and runs autonomously. No human reads, eyeballs, or taps anything. This note exists ONLY to document the kill-switch path and the exit-code semantics that the autonomous loop honors. Real-submit / `--confirm` lives in the Wave 2 plan: `docs/superpowers/plans/2026-06-04-earn-lancers-wave2-realsubmit.md`.

## Daily beat

`hermes cron` fires `~/.hermes/scripts/anicca-earn-lancers.sh` at `0 10 * * *` JST. The script runs `login-check.sh → scan.sh → select.sh → apply.sh --dry-run` and writes:
- `~/.hermes/state/earn-lancers-dry-run-latest.json` — latest envelope.
- `~/.hermes/state/earn-lancers-cron-fire.log` — last fire's stdout/stderr.

## Login = autonomous (no human, no 2FA tap-on-phone, no "Dais reviews")

`login-check.sh` does everything itself:
1. Probe Camofox `/sessions/anicca/cookies` for a `lancers.jp` cookie. If present → done.
2. Otherwise open `https://www.lancers.jp/user/login` and click "Googleでログイン".
3. Type `GOOGLE_LOGIN_EMAIL`, Enter, type `GOOGLE_LOGIN_PASSWORD`, Enter.
4. If a 2-step challenge appears:
   - `GOOGLE_TOTP_SECRET` present → `oathtool --totp -b "$GOOGLE_TOTP_SECRET"` → type code.
   - Else → `hermes chat -q --model <mini>` reads the latest 2-step email at `user@example.com` and returns the 6-digit code → type code.
5. Re-probe cookie. If present → exit 0.

## Hard-block (only — HARD RULE #-2)

A genuine hard-block is recognized only when:
- a real CAPTCHA iframe (`recaptcha`, `hcaptcha`, `turnstile`) renders in the Camofox snapshot, OR
- the page asks for a financial broadcast (= money send / withdraw signature).

When this happens the script saves the verbatim subset of the Camofox snapshot to `~/.hermes/state/earn-lancers-login-hardblock.json` and exits non-0. The earn task stays OPEN. The next cron beat retries automatically. No human is asked to "tap" or "review" — the loop self-heals on the next beat.

## Kill switch

```bash
hermes cron pause anicca-earn-lancers
```

This freezes the daily cron until `hermes cron resume anicca-earn-lancers`. Use only if a Wave 2 real-submit beat lands a clearly out-of-niche proposal or Lancers serves a TOS warning.

## What advances `#325` (LAUNCH MATRIX row ④)

Wave 1 (this plan) does NOT advance row ④. Advancement requires the Wave 2 plan's exit conditions:
1. ≥1 row in `~/.hermes/state/earn-lancers-runs.jsonl` with `status:"applied"` AND a verified `finish_url` (Camofox-confirmed the proposal page renders).
2. CFO `cfo-bank` shows the incoming Lancers deposit on Dais's bank account (`anicca_runtime` income classification).
3. Wave 2 plan's Task closing-condition is met and `#325` is then closed by the Wave 2 plan, not by this one.
```

- [ ] **Step 3: Commit the ops note**

Run:
```bash
cd /Users/operator/anicca-oss
git add docs/superpowers/runbooks/2026-06-04-earn-lancers-ops.md
git commit -m "docs(ops): earn-lancers Wave 1 autonomous ops note (no human in loop, kill switch, hard-block semantics)"
git push
```

---

### Task 12: Update `specs/00-MASTER.md` § LAUNCH MATRIX row ④ (scaffold-only sub-bullet — `#325` stays OPEN)

**Files:**
- Modify: `specs/00-MASTER.md` (LAUNCH ACCEPTANCE MATRIX row ④ sub-bullet)

- [ ] **Step 1: Add the sub-bullet (scaffold-only — does NOT close row ④)**

In `/Users/operator/anicca-oss/specs/00-MASTER.md`, locate the row:
```
 ④「平均月収 x円（コスト約 y円）」            →  #325 earn, #332 battle,  →  CFO dashboard real monthly x>y;
                                                 CFO (live)                  if not 黒字 → write honest/drop
```

Append (after that row, before row ⑤a) a sub-bullet:
```
   ↳ ④a Lancers channel scaffold (Wave 1) = anicca-earn-lancers skill registered,
        cron `0 10 * * *` JST in dry-run mode only. Row ④ does NOT advance here —
        advancement requires Wave 2 (anicca-earn-lancers-wave2-realsubmit) producing
        ≥1 real `applied` row + CFO bank deposit evidence.
        (Coconala + CrowdWorks join as ④b/④c in Wave 2 follow-ons.)
```

- [ ] **Step 2: Commit + push**

Run:
```bash
cd /Users/operator/anicca-oss
git add specs/00-MASTER.md
git commit -m "docs(spec): 00-MASTER row ④ — anicca-earn-lancers Wave 1 scaffold (no row close, #325 still open)"
git push
```

- [ ] **Step 3: Do NOT mark `#325` completed. Leave it OPEN.**

`#325` (`Wave 1 dry-run scaffolding`) is updated with a comment but NOT closed. Use the TaskUpdate tool to leave `#325` in `in_progress` with the comment:
> "Wave 1 scaffolding done (dry-run E2E green, cron registered, autonomous login). Closing blocked on Wave 2 real-submit + CFO bank evidence per `docs/superpowers/plans/2026-06-04-earn-lancers-wave2-realsubmit.md`."

Open follow-up tasks (do NOT execute them in this plan):
- `#325-wave2` — Wave 2 real-submit + CFO row ④ verify (the plan from Task 13 below).
- `#325b` — Wave 2 Coconala (`anicca-coconala-earner`) port using this skill as template.
- `#325c` — Wave 2 CrowdWorks (`anicca-crowdworks-earner`) port using this skill as template.

---

### Task 13: Write the Wave 2 follow-on plan (real submit + CFO row ④ verify)

> Codex round 2 X2 + P3-no-real-earn-proof: real money proof lives in this separate Wave 2 plan, not in Wave 1. The Wave 1 implementer commits the Wave 2 plan file but does NOT execute it. `#325` can ONLY be closed by Wave 2's exit condition.

**Files:**
- Create: `docs/superpowers/plans/2026-06-04-earn-lancers-wave2-realsubmit.md`

- [ ] **Step 1: Create the Wave 2 plan file with EXACTLY this content**

Create `/Users/operator/anicca-oss/docs/superpowers/plans/2026-06-04-earn-lancers-wave2-realsubmit.md`:
````markdown
# Earn Lancers Wave 2 — real-submit + CFO row ④ verify

> Follow-on to `2026-06-04-earn-lancers.md` (Wave 1 scaffolding). This plan executes ONE real Lancers proposal under the documented safety cap (`--max-apply 1 --max-budget-jpy 1000`), watches CFO/bank for the deposit, and is the ONLY plan permitted to close `#325`. Fully autonomous per HARD RULE #-2 — agent drives camofox + Google login env; the only allowed hard-block is a real CAPTCHA element or financial-broadcast prompt. No human eyeballing.

**Prereq:** Wave 1 (`2026-06-04-earn-lancers.md`) all Tasks 0–12 green. Skill registered. Dry-run E2E green. `~/.hermes/state/earn-lancers-dry-run-latest.json` exists.

**Done condition (the ONLY way `#325` closes):**
1. `~/.hermes/state/earn-lancers-runs.jsonl` has ≥1 row with `status:"applied"` AND `finish_url` containing `propose_finish`.
2. Camofox re-fetches the `finish_url` and the snapshot contains the proposal body text — agent verifies this autonomously, no human eyeball.
3. `cfo-bank` (already LIVE) records an incoming Lancers deposit on Dais's bank within 30 days of the `applied` row (Lancers payout SLA). Verified by running `bash ~/.openclaw/skills/cfo-bank/scripts/scan.sh` and grepping the output for `Lancers` / `ランサーズ`.
4. ONLY when (1)+(2)+(3) all true: TaskUpdate closes `#325` with the row from `~/.hermes/state/earn-lancers-runs.jsonl` and the CFO deposit line as the receipt.

## Task A: Preflight (X5)

- [ ] A.1 `curl -sS http://localhost:9377/health | jq -e '.ok and .browserConnected'` → exit 0.
- [ ] A.2 `command -v hermes && hermes --version` → ≥ 0.12.0 (X1 — do NOT update).
- [ ] A.3 Env presence: `GOOGLE_LOGIN_EMAIL`, `GOOGLE_LOGIN_PASSWORD`, `LANCERS_PASSWORD` all `FOUND` per Wave 1 Task 0 Step 3.
- [ ] A.4 `bash ~/.hermes/scripts/anicca-earn-lancers.sh --dry-run` → exit 0, `~/.hermes/state/earn-lancers-dry-run-latest.json` updated.
- [ ] A.5 `bash skills/anicca-earn-lancers/scripts/login-check.sh` → exit 0 (autonomous, no human). If exit 6/9 → diagnose `~/.hermes/state/earn-lancers-login-hardblock.json`, patch, retry. Do NOT proceed until exit 0.

## Task B: Execute ONE real proposal (autonomous, capped)

- [ ] B.1 Run, exactly once:
```bash
bash /Users/operator/.hermes/scripts/anicca-earn-lancers.sh \
  --confirm \
  --max-apply 1 \
  --max-budget-jpy 1000 \
  2>&1 | tee -a ~/.hermes/state/earn-lancers-cron-fire.log
```
Expected: stdout JSON envelope `.candidates[0].status == "applied"` and `.candidates[0].finish_url` matches `propose_finish`. If `.status` is anything else (`skip:REDIRECT` / `skip:BLOCKED` / `final_click_failed`), the candidate pool that day did not meet the ¥1k floor; re-run the next day's beat — do NOT raise the cap.

- [ ] B.2 Read back the last row autonomously:
```bash
ROW=$(tail -1 ~/.hermes/state/earn-lancers-runs.jsonl)
echo "$ROW" | /opt/homebrew/bin/jq -e '.status == "applied" and (.finish_url | test("propose_finish"))' >/dev/null \
  && echo SUBMIT_OK || { echo SUBMIT_NOT_YET; exit 0; }
```
Expected: `SUBMIT_OK`. If `SUBMIT_NOT_YET`: NOT a failure — the autonomous loop is allowed to keep trying daily until B.1 produces `applied`. Do NOT close `#325`.

- [ ] B.3 Autonomous verification of the proposal page (no human):
```bash
FURL=$(echo "$ROW" | /opt/homebrew/bin/jq -r '.finish_url')
TAB=$(curl -sS -X POST http://localhost:9377/tabs -H 'Content-Type: application/json' \
  -d "$(/opt/homebrew/bin/jq -n --arg u "$FURL" --arg uid anicca --arg sk default \
        '{url:$u, userId:$uid, sessionKey:$sk}')" | /opt/homebrew/bin/jq -r .tabId)
sleep 5
SNAP=$(curl -sS "http://localhost:9377/tabs/$TAB/snapshot?userId=anicca&sessionKey=default")
curl -sS -X DELETE "http://localhost:9377/tabs/$TAB?userId=anicca&sessionKey=default" >/dev/null
printf '%s' "$SNAP" | /opt/homebrew/bin/jq -e '.snapshot | test("提案|Proposal|finish")' >/dev/null \
  && echo PROPOSAL_VISIBLE || { echo PROPOSAL_NOT_RENDERED; exit 0; }
```
Expected: `PROPOSAL_VISIBLE`. If `PROPOSAL_NOT_RENDERED`: write `~/.hermes/state/earn-lancers-wave2-hardblock-<ts>.json` with the snapshot subset and do NOT close `#325`; loop retries on the next beat.

## Task C: CFO bank deposit verify (the row ④ gate)

- [ ] C.1 Up to 30 days after Task B SUBMIT_OK, run on each weekday:
```bash
bash ~/.openclaw/skills/cfo-bank/scripts/scan.sh
grep -Ei 'Lancers|ランサーズ' ~/.openclaw/skills/cfo-bank/data/bank-latest.jsonl \
  && echo CFO_DEPOSIT_VISIBLE || echo CFO_DEPOSIT_PENDING
```
Expected eventually: `CFO_DEPOSIT_VISIBLE`. While `CFO_DEPOSIT_PENDING`: do NOT close `#325`. The autonomous loop keeps trying daily Wave 1 dry-runs in parallel — no human poke required.

## Task D: Close `#325` (only here, only when C.1 shows CFO_DEPOSIT_VISIBLE)

- [ ] D.1 TaskUpdate sets `#325` to `completed` with a comment containing: `(a)` the submitted `finish_url` from Task B.2; `(b)` the verified-rendered confirmation from Task B.3; `(c)` the CFO bank line from Task C.1 (amount + date).
- [ ] D.2 Update `specs/00-MASTER.md` row ④ sub-bullet ④a from "scaffold (Wave 1)" to "Wave 2 LIVE — one real proposal applied + CFO deposit verified <YYYY-MM-DD>"; commit + push.

That is the only flow allowed to advance row ④ on the Lancers channel.
````

- [ ] **Step 2: Commit the Wave 2 plan**

Run:
```bash
cd /Users/operator/anicca-oss
git add docs/superpowers/plans/2026-06-04-earn-lancers-wave2-realsubmit.md
git commit -m "docs(plan): earn-lancers Wave 2 — autonomous real-submit + CFO row ④ verify (only path to close #325)"
git push
```

---

## Self-Review

**Spec coverage:**
- `specs/00-MASTER.md` § LAUNCH ACCEPTANCE MATRIX row ④「平均月収 x円」 = directly addressed (Task 12 adds the sub-bullet linking this skill to the row).
- `specs/16-RUNTIME-CODE-TRUTH.md` § 17 ("ONE RUNTIME = Hermes ... Camofox or Nous-Portal browser ... earn = Camofox → Lancers/Coconala gig apply+deliver") = the file structure and `_lib.sh` enforce "Camofox via REST :9377, no second browser". Hermes cron `--no-agent` + `hermes chat --model gpt-5.2-mini` inside the script keep the substrate decision intact.
- CLAUDE.md HARD RULE #-2 "no human-loop excuses": ZERO human touchpoints in Wave 1 or Wave 2. `login-check.sh` runs Google login autonomously via `GOOGLE_LOGIN_EMAIL`+`GOOGLE_LOGIN_PASSWORD` env, with autonomous 2FA via `GOOGLE_TOTP_SECRET` (if present) OR `hermes chat -q --model <mini>` reading the gog-gmail mailbox. The ONLY recognized hard-block is a real CAPTCHA iframe (`recaptcha`/`hcaptcha`/`turnstile`) or a financial-broadcast prompt — both record the verbatim snapshot to `~/.hermes/state/earn-lancers-login-hardblock.json` without closing the earn task. No "Dais reviews", no "tap on phone", no "eyeball before pulling trigger" language remains anywhere in this plan or its child runbook/Wave 2 plan (codex round 2 X3).
- HARD RULE browser order (camofox > cloak > agent-browser): the skill imports ONLY `:9377` (camofox). `cloakbrowser` / `agent-browser` are not referenced anywhere in the new files.
- HARD RULE "Google login forever, `user@example.com` canonical, Lancers uses `user+anicca@example.com` + `LANCERS_PASSWORD`": `_lib.sh` reads env vars by their canonical names; `login-check.sh` Step 1 uses Google OAuth as the first path and only falls back to LANCERS_EMAIL+PASSWORD if the Google button is missing. No password is hard-coded; `redact()` masks values in any log line.
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
- Task 10 Step 4 (force-fire) depends on the Camofox session having a Lancers cookie. If not yet present, the autonomous `login-check.sh` will mint one via the Google login env + TOTP / gog-gmail flow. Recognized non-zero exits (6 = autonomous 2FA didn't converge this beat; 9 = real CAPTCHA iframe rendered) save the verbatim Camofox snapshot under `~/.hermes/state/earn-lancers-login-hardblock.json` and let the next cron beat retry — no human is asked to act. The daily cron in Wave 1 is dry-run only; it never submits, so silent retry is bounded by definition.

---

## Execution Handoff

Plan v2 (codex round 2 fixes applied) saved to `docs/superpowers/plans/2026-06-04-earn-lancers.md`. Wave 2 follow-on plan saved alongside as `docs/superpowers/plans/2026-06-04-earn-lancers-wave2-realsubmit.md`.

Per Dais's directive ("keep getting reviewed by codex; only when it's time to implement, build with agent teams"), the next move is NOT to start Task 0 — it is to re-run **codex-review** against this plan + the new Wave 2 plan + specs 00 / 16 / 18 + the parent plan `2026-06-04-hermes-genesis-boot.md`. When codex says `ok: true`, dispatch the implementation via **superpowers:subagent-driven-development** — fresh subagent per task, two-stage review (spec compliance → code quality) after each task. The flow is fully autonomous end-to-end — no human eyeball anywhere; `#325` closes only inside the Wave 2 plan after CFO bank evidence lands.
