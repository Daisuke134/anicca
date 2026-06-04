# Hermes Genesis Boot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Boot a single Hermes "genesis" body that runs 24/7 with one BYOK fuel, loads anicca-oss CONSTITUTION as AGENTS.md, and fires a minimal `anicca-heartbeat` skill every 30 minutes via `hermes cron`, with launchd auto-restart and an observed end-to-end fire cycle.

**Architecture:** Hermes Agent v0.12.0 (already installed at `/Users/operator/.local/bin/hermes`) is the substrate. We do NOT change Hermes itself. We (a) bring it current via `hermes update`, (b) wire ONE BYOK provider from the existing `~/.openclaw/.env`, (c) symlink `anicca-oss/CONSTITUTION.md` → `~/.hermes/AGENTS.md` so any later update to the constitution propagates without a Hermes config change, (d) author a minimal `anicca-heartbeat` skill at `~/.hermes/skills/anicca-heartbeat/`, (e) schedule it via `hermes cron`, and (f) keep the Hermes cron daemon alive via a launchd plist that mirrors the 23 existing `ai.anicca.*` jobs. WAVE 1 = ONE fuel (BYOK existing key); WAVES 2-3 (Anthropic OAuth, Base USDC) are SEPARATE plans.

**Tech Stack:** Hermes Agent v0.12.0 (Python 3.11.14 + OpenAI SDK 2.32.0) · zsh · launchd · jq (`/opt/homebrew/bin/jq` already on PATH) · existing keys in `~/.openclaw/.env` · `git`.

**Scope-out (in other plans):**
- `wallet + x402` skills (#324) — separate plan.
- `earn` skill, Camofox login (#325) — separate plan.
- `eval-loop` skill (#329) — separate plan, prerequisite for production output gating but not for boot.
- `daily-report` skill (#330) — anicca-report cron `ai.anicca.cfo-daily` already runs; out of scope here.
- `self-replication`, colony (#327, #328) — separate plans.
- 3-fuel matrix verification — Anthropic OAuth and Base-USDC fuel are tracked by #341 LAUNCH-GATE row ②; this plan satisfies ONE of the three. Successor plans add the others.

**Done condition for this plan (proves task #323 Wave 1):**
1. `hermes --version` shows updated build with no "Update available" line.
2. `hermes chat -q "Say pong only."` returns a string containing `pong` (one BYOK fuel works).
3. `readlink ~/.hermes/AGENTS.md` → `/Users/operator/anicca-oss/CONSTITUTION.md`.
4. `hermes skills list` includes `anicca-heartbeat`.
5. `hermes cron list` shows one job named `anicca-heartbeat` with schedule `every 30m`.
6. `launchctl list | grep ai.anicca.hermes` returns one ACTIVE row.
7. After ≥1 natural fire cycle (≥35 min wait), `~/.hermes/state/heartbeat.jsonl` has ≥1 new line with fields `{ts, ok, fuel, model, constitution_sha}` and `ok=true`.
8. All new files committed + pushed to `anicca-oss` (CLAUDE.md rule 0.4).
9. spec `00-MASTER.md` § GROUND TRUTH updated to reflect "genesis body running on Hermes v…, fuel=…, heartbeat every 30m".

---

## File Structure (what each file owns)

```
anicca-oss/                                              (this repo, committed)
  skills/anicca-heartbeat/
    SKILL.md                ← skill manifest (Hermes-format frontmatter)
    scripts/heartbeat.sh    ← what fires every 30m (the only side effect)
    scripts/lifeline-check.sh ← health probes the heartbeat calls
    README.md               ← one-paragraph human description
  scripts/launchd/
    ai.anicca.hermes-cron.plist  ← keeps `hermes cron daemon` alive
    install-hermes-cron-launchd.sh ← installs the plist into ~/Library/LaunchAgents
  docs/superpowers/plans/
    2026-06-04-hermes-genesis-boot.md  ← THIS plan
  specs/00-MASTER.md        ← edit § GROUND TRUTH at end

~/.hermes/                                               (runtime, NOT committed)
  AGENTS.md                 ← SYMLINK → anicca-oss/CONSTITUTION.md
  skills/anicca-heartbeat/  ← SYMLINK → anicca-oss/skills/anicca-heartbeat/
  state/heartbeat.jsonl     ← append-only log written by the skill (created on first run)
  cron/anicca-heartbeat.*   ← Hermes-managed cron entry files (created by `hermes cron create`)
  .env                      ← gets ONE line appended if the key is missing
~/Library/LaunchAgents/
  ai.anicca.hermes-cron.plist  ← installed copy
```

Why symlinks for AGENTS.md and the skill: a constitution or skill edit lands in the repo (where review/PR/roll-out lives), and Hermes immediately sees it. No copy step to forget; matches the existing OpenClaw pattern (skills live in `~/.openclaw/skills/` but the canonical sources are in repos).

---

### Task 1: Snapshot the current Hermes state

**Files:**
- Create: `/Users/operator/.hermes/backups/pre-genesis-boot-snapshot.tar.gz` (one-off backup, not committed)

- [ ] **Step 1: Confirm Hermes is the expected version on disk**

Run:
```bash
hermes --version
```
Expected output contains exactly:
```
Hermes Agent v0.12.0 (2026.4.30)
```
(Plus an "Update available" line — that is what Task 2 fixes.)

- [ ] **Step 2: Take a snapshot tarball of ~/.hermes so we can rollback**

Run:
```bash
mkdir -p /Users/operator/.hermes/backups
tar -czf /Users/operator/.hermes/backups/pre-genesis-boot-snapshot.tar.gz \
  -C /Users/operator/.hermes config.yaml .env AGENTS.md skills cron 2>/dev/null || \
tar -czf /Users/operator/.hermes/backups/pre-genesis-boot-snapshot.tar.gz \
  -C /Users/operator/.hermes config.yaml .env skills cron
ls -lh /Users/operator/.hermes/backups/pre-genesis-boot-snapshot.tar.gz
```
Expected: a single `.tar.gz` file ≥1KB.

- [ ] **Step 3: Record current launchd anicca-job count as baseline**

Run:
```bash
launchctl list | grep -c '^[^	]*[0-9]*	[0-9]*	ai\.anicca\.' || true
```
Expected: `23` (matches the pre-plan ground truth in spec 00). Save this number in your scratch notes; Task 7 must add exactly 1 (→24).

- [ ] **Step 4: Commit the plan itself (so the rest of the work is reviewable against the plan)**

Run:
```bash
cd /Users/operator/anicca-oss
git add docs/superpowers/plans/2026-06-04-hermes-genesis-boot.md
git commit -m "docs(plan): hermes-genesis-boot (P1-1 Wave 1)"
git push
```
Expected: push succeeds, new commit appears in `git log --oneline -1`.

---

### Task 2: Bring Hermes current (`hermes update`)

**Files:** none new; modifies `~/.hermes/hermes-agent/` in place via Hermes's own updater.

- [ ] **Step 1: Check what's available**

Run:
```bash
hermes update --check
```
Expected: prints the new version and the commit delta from `v0.12.0 (2026.4.30)`. If output says "Already up to date", skip to Step 4.

- [ ] **Step 2: Take a labeled Hermes-native backup**

Run:
```bash
hermes backup -l before-genesis-boot
```
Expected: prints a backup path under `~/.hermes/backups/` and `OK`.

- [ ] **Step 3: Apply the update**

Run:
```bash
hermes update --backup --yes
```
Expected: prints progress lines and ends with `Hermes updated to vX.Y.Z` (a version number > 0.12.0).

- [ ] **Step 4: Verify version advanced + no pending update**

Run:
```bash
hermes --version
```
Expected: prints a version line, AND does NOT contain "Update available". Record the new version string — Task 9 commit message includes it.

- [ ] **Step 5: Sanity-check config integrity**

Run:
```bash
hermes config check
hermes doctor
```
Expected: both print a structured report ending in `OK` (or a green ✓). Any `ERROR` line → stop, do not proceed; treat as a bug in the update and rollback with the snapshot from Task 1.

---

### Task 3: Wire ONE BYOK fuel (Wave 1)

**Files:**
- Modify (append-only): `~/.hermes/.env`
- Modify (interactive): `~/.hermes/config.yaml` via `hermes model`

- [ ] **Step 1: Detect which key already lives in OpenClaw's .env**

Run:
```bash
for k in OPENAI_API_KEY ANTHROPIC_API_KEY OPENROUTER_API_KEY DEEPSEEK_API_KEY KIMI_API_KEY; do
  if grep -q "^$k=" /Users/operator/.openclaw/.env 2>/dev/null; then echo "FOUND $k"; fi
done
```
Expected: at least one `FOUND <KEY_NAME>` line. Record the FIRST one printed as `$CHOSEN_KEY` for Step 2. (Both `~/.openclaw/.env` and the choice itself are user-private and must NOT be echoed into any commit, logs, or chat history.)

- [ ] **Step 2: Copy that one key into ~/.hermes/.env if missing**

Run (substitute the literal key name you chose, e.g. `OPENAI_API_KEY`):
```bash
KEY=OPENAI_API_KEY   # ← REPLACE with the literal key name from Step 1
if ! grep -q "^$KEY=" /Users/operator/.hermes/.env 2>/dev/null; then
  VAL=$(grep "^$KEY=" /Users/operator/.openclaw/.env | head -1 | cut -d= -f2-)
  printf '%s=%s\n' "$KEY" "$VAL" >> /Users/operator/.hermes/.env
  chmod 600 /Users/operator/.hermes/.env
  echo "appended $KEY to ~/.hermes/.env"
else
  echo "$KEY already present in ~/.hermes/.env (no change)"
fi
```
Expected: prints either `appended …` or `already present …`. NEVER echo `$VAL`.

- [ ] **Step 3: Select model + provider interactively**

Run:
```bash
hermes model
```
Use the interactive picker to choose the provider matching `$CHOSEN_KEY` (e.g. OpenAI → `gpt-5.2-mini` or whatever Hermes lists as the cheapest available default). Per CLAUDE.md HARD RULE "OpenClaw cron は mini 主軸", prefer the lowest-cost option this provider exposes that still supports tool use.

Expected: picker prints `Selected provider=<…> model=<…>` and exits 0.

- [ ] **Step 4: Verify Hermes can speak**

Run:
```bash
hermes chat -q "Reply with the single word: pong"
```
Expected: stdout contains `pong` (case-insensitive). If the response is an error/auth complaint, re-run `hermes login` for the chosen provider per the picker's instructions, then re-run this step.

- [ ] **Step 5: Pin the choice into config.yaml (so cron-spawned chats use it)**

Run:
```bash
hermes config check
hermes chat -q --provider $(hermes config check 2>/dev/null | awk '/provider/{print $NF; exit}') "Reply with: pong-pin"
```
Expected: contains `pong-pin`. (This proves the provider selected in Step 3 is what `hermes` actually reads from disk, not just an in-memory pick.)

---

### Task 4: Wire anicca-oss/CONSTITUTION.md → ~/.hermes/AGENTS.md

**Files:**
- Modify (symlink): `~/.hermes/AGENTS.md` → `/Users/operator/anicca-oss/CONSTITUTION.md`

- [ ] **Step 1: Move any existing AGENTS.md aside (safety)**

Run:
```bash
if [ -e /Users/operator/.hermes/AGENTS.md ] && [ ! -L /Users/operator/.hermes/AGENTS.md ]; then
  mv /Users/operator/.hermes/AGENTS.md /Users/operator/.hermes/AGENTS.md.pre-genesis-boot
  echo "moved existing real file aside"
elif [ -L /Users/operator/.hermes/AGENTS.md ]; then
  rm /Users/operator/.hermes/AGENTS.md
  echo "removed existing symlink"
else
  echo "no prior AGENTS.md"
fi
```
Expected: prints exactly one of the three branches.

- [ ] **Step 2: Create the symlink**

Run:
```bash
ln -s /Users/operator/anicca-oss/CONSTITUTION.md /Users/operator/.hermes/AGENTS.md
ls -l /Users/operator/.hermes/AGENTS.md
```
Expected: output starts with `lrwxr` and contains `-> /Users/operator/anicca-oss/CONSTITUTION.md`.

- [ ] **Step 3: Verify Hermes can actually see and reason over the constitution**

Run:
```bash
hermes chat -q "Read AGENTS.md and reply with the EXACT first 3 words of the file."
```
Expected: response is the literal first 3 words of `/Users/operator/anicca-oss/CONSTITUTION.md`. Cross-check:
```bash
awk 'NR==1{print $1, $2, $3; exit}' /Users/operator/anicca-oss/CONSTITUTION.md
```
The two must match (modulo whitespace and Markdown header chars like `#`).

- [ ] **Step 4: Compute and stash the constitution's SHA-256 (the heartbeat will log it)**

Run:
```bash
shasum -a 256 /Users/operator/anicca-oss/CONSTITUTION.md | awk '{print $1}' > /Users/operator/.hermes/state/constitution.sha
mkdir -p /Users/operator/.hermes/state
shasum -a 256 /Users/operator/anicca-oss/CONSTITUTION.md | awk '{print $1}' | tee /Users/operator/.hermes/state/constitution.sha
```
Expected: a single 64-char hex line both echoed and saved.

---

### Task 5: Write the `anicca-heartbeat` skill

**Files:**
- Create: `/Users/operator/anicca-oss/skills/anicca-heartbeat/SKILL.md`
- Create: `/Users/operator/anicca-oss/skills/anicca-heartbeat/scripts/heartbeat.sh`
- Create: `/Users/operator/anicca-oss/skills/anicca-heartbeat/scripts/lifeline-check.sh`
- Create: `/Users/operator/anicca-oss/skills/anicca-heartbeat/README.md`
- Create (symlink): `~/.hermes/skills/anicca-heartbeat` → `/Users/operator/anicca-oss/skills/anicca-heartbeat`

- [ ] **Step 1: Write the failing E2E test FIRST (TDD red)**

Create `/Users/operator/anicca-oss/skills/anicca-heartbeat/tests/test_heartbeat_e2e.sh`:
```bash
#!/usr/bin/env bash
# E2E: run heartbeat.sh once, assert it appends ONE well-formed JSON line.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE=/Users/operator/.hermes/state/heartbeat.jsonl
BEFORE=$(wc -l < "$STATE" 2>/dev/null || echo 0)
"$SKILL_DIR/scripts/heartbeat.sh"
AFTER=$(wc -l < "$STATE")
if [ $((AFTER - BEFORE)) -ne 1 ]; then
  echo "FAIL: expected +1 line, got $((AFTER - BEFORE))"; exit 1
fi
LAST=$(tail -n 1 "$STATE")
for key in ts ok fuel model constitution_sha; do
  echo "$LAST" | /opt/homebrew/bin/jq -e ".$key" >/dev/null || { echo "FAIL: missing $key in $LAST"; exit 1; }
done
echo "$LAST" | /opt/homebrew/bin/jq -e '.ok == true' >/dev/null || { echo "FAIL: ok != true"; exit 1; }
echo "PASS"
```
Make it executable:
```bash
chmod +x /Users/operator/anicca-oss/skills/anicca-heartbeat/tests/test_heartbeat_e2e.sh
```

- [ ] **Step 2: Run the test — must FAIL because heartbeat.sh doesn't exist yet**

Run:
```bash
/Users/operator/anicca-oss/skills/anicca-heartbeat/tests/test_heartbeat_e2e.sh
```
Expected: exits non-zero with a message similar to `No such file or directory: …/scripts/heartbeat.sh`. This is the RED of the TDD cycle.

- [ ] **Step 3: Write `scripts/lifeline-check.sh` (probes only, no side effects)**

Create `/Users/operator/anicca-oss/skills/anicca-heartbeat/scripts/lifeline-check.sh` with EXACTLY this content:
```bash
#!/usr/bin/env bash
# Emits a single-line JSON object to stdout describing the genesis body's vital signs.
# Read-only. No outbound network. Used by heartbeat.sh.
set -euo pipefail

HERMES_BIN="${HERMES_BIN:-/Users/operator/.local/bin/hermes}"
STATE_DIR="${STATE_DIR:-/Users/operator/.hermes/state}"
CONSTITUTION="${CONSTITUTION:-/Users/operator/anicca-oss/CONSTITUTION.md}"

ts="$(date -u +%FT%TZ)"
hermes_version="$("$HERMES_BIN" --version 2>/dev/null | head -1 | awk '{print $3}')"
constitution_sha="$(shasum -a 256 "$CONSTITUTION" | awk '{print $1}')"

# Provider/model from config (best-effort; never blocks the heartbeat)
model_line="$("$HERMES_BIN" config check 2>/dev/null | awk '/default/{print; exit}' || true)"
model="$(echo "$model_line" | awk '{print $NF}')"
provider="$("$HERMES_BIN" config check 2>/dev/null | awk '/provider/{print $NF; exit}' || true)"

# Cron job count (proves the schedule survived restarts)
cron_count="$("$HERMES_BIN" cron list 2>/dev/null | grep -c '^[[:space:]]*anicca-' || true)"

# Last heartbeat row's timestamp, if any
last_ts="$(tail -n 1 "$STATE_DIR/heartbeat.jsonl" 2>/dev/null | /opt/homebrew/bin/jq -r '.ts' 2>/dev/null || echo "")"

/opt/homebrew/bin/jq -n \
  --arg ts "$ts" \
  --arg hermes_version "$hermes_version" \
  --arg constitution_sha "$constitution_sha" \
  --arg provider "$provider" \
  --arg model "$model" \
  --argjson cron_count "${cron_count:-0}" \
  --arg last_ts "$last_ts" \
  '{ts:$ts, hermes_version:$hermes_version, constitution_sha:$constitution_sha,
    provider:$provider, model:$model, cron_count:$cron_count, last_ts:$last_ts}'
```
Make executable:
```bash
chmod +x /Users/operator/anicca-oss/skills/anicca-heartbeat/scripts/lifeline-check.sh
```

- [ ] **Step 4: Smoke-test lifeline-check.sh**

Run:
```bash
/Users/operator/anicca-oss/skills/anicca-heartbeat/scripts/lifeline-check.sh | /opt/homebrew/bin/jq .
```
Expected: prints a single JSON object with keys `ts, hermes_version, constitution_sha, provider, model, cron_count, last_ts`. `constitution_sha` matches the file `~/.hermes/state/constitution.sha` from Task 4 Step 4.

- [ ] **Step 5: Write `scripts/heartbeat.sh` (the only file that writes state)**

Create `/Users/operator/anicca-oss/skills/anicca-heartbeat/scripts/heartbeat.sh` with EXACTLY this content:
```bash
#!/usr/bin/env bash
# Single fire of the genesis heartbeat. Idempotent per-instant: writes ONE JSONL line.
# Invoked by `hermes cron` every 30m. Must complete in < 5 s.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="${STATE_DIR:-/Users/operator/.hermes/state}"
mkdir -p "$STATE_DIR"
LOG="$STATE_DIR/heartbeat.jsonl"

probe="$("$SKILL_DIR/scripts/lifeline-check.sh")"
provider="$(echo "$probe" | /opt/homebrew/bin/jq -r '.provider')"
model="$(echo "$probe" | /opt/homebrew/bin/jq -r '.model')"
sha="$(echo "$probe"   | /opt/homebrew/bin/jq -r '.constitution_sha')"
ts="$(echo "$probe"    | /opt/homebrew/bin/jq -r '.ts')"

# fuel = which provider key is actually being used; in Wave 1 it equals the provider name.
fuel="$provider"
ok=true
[ -z "$provider" ] && ok=false
[ -z "$sha" ]      && ok=false

line="$(/opt/homebrew/bin/jq -n \
  --arg ts "$ts" --argjson ok "$ok" \
  --arg fuel "$fuel" --arg model "$model" --arg constitution_sha "$sha" \
  --argjson probe "$probe" \
  '{ts:$ts, ok:$ok, fuel:$fuel, model:$model, constitution_sha:$constitution_sha, probe:$probe}')"

printf '%s\n' "$line" >> "$LOG"
echo "$line"
```
Make executable:
```bash
chmod +x /Users/operator/anicca-oss/skills/anicca-heartbeat/scripts/heartbeat.sh
```

- [ ] **Step 6: Run the E2E test — must PASS now (TDD green)**

Run:
```bash
/Users/operator/anicca-oss/skills/anicca-heartbeat/tests/test_heartbeat_e2e.sh
```
Expected: stdout final line `PASS`, exit code 0. If any FAIL line, fix `heartbeat.sh` or `lifeline-check.sh`; do NOT proceed.

- [ ] **Step 7: Write the SKILL.md manifest in the format Hermes expects**

Create `/Users/operator/anicca-oss/skills/anicca-heartbeat/SKILL.md` with EXACTLY this content (the frontmatter format mirrors the bundled skills already in `~/.hermes/skills/`):
```markdown
---
name: anicca-heartbeat
description: Fires every 30 minutes on the Anicca genesis body. Reads vital signs (Hermes version, provider, model, constitution SHA-256, cron count) via lifeline-check.sh and appends ONE JSONL line to ~/.hermes/state/heartbeat.jsonl. Use this skill ONLY when the cron daemon invokes it; do not call it from chat. Read-only externally; the only side effect is the append to the local log.
---

# anicca-heartbeat

## What it does
Single-purpose Anicca skill: prove the genesis body is alive, anchored to a known
constitution hash, and using a known fuel/model. The 30-minute cadence is
intentionally cheap and side-effect-free so that the heartbeat NEVER fails for
economic reasons.

## How it's invoked
`hermes cron` triggers `scripts/heartbeat.sh` every 30 minutes. The script writes
one JSONL line and exits. No chat session is involved.

## What it writes
`~/.hermes/state/heartbeat.jsonl` (append-only). Each line:
```json
{"ts":"2026-06-04T12:00:00Z","ok":true,"fuel":"openai","model":"gpt-5.2-mini","constitution_sha":"<sha256>","probe":{...}}
```

## Failure mode
If `lifeline-check.sh` returns missing provider/model/sha, `heartbeat.sh` writes
`"ok":false` (still one line) and exits 0. The cron daemon does NOT retry; the
next 30-minute window does.
```

- [ ] **Step 8: Write README.md (one paragraph, for humans browsing the repo)**

Create `/Users/operator/anicca-oss/skills/anicca-heartbeat/README.md` with EXACTLY:
```markdown
# anicca-heartbeat

Minimal Hermes skill that fires every 30 minutes to prove the Anicca genesis body is alive. It writes one JSONL line per fire to `~/.hermes/state/heartbeat.jsonl` containing the timestamp, the provider/model in use, and the SHA-256 of the live constitution. No outbound network calls. Wired by `2026-06-04-hermes-genesis-boot` plan; see `specs/00-MASTER.md` § GROUND TRUTH.
```

- [ ] **Step 9: Symlink the skill into ~/.hermes/skills/**

Run:
```bash
ln -s /Users/operator/anicca-oss/skills/anicca-heartbeat /Users/operator/.hermes/skills/anicca-heartbeat
ls -l /Users/operator/.hermes/skills/anicca-heartbeat
```
Expected: `-> /Users/operator/anicca-oss/skills/anicca-heartbeat`.

- [ ] **Step 10: Confirm Hermes registers the skill**

Run:
```bash
hermes skills list 2>&1 | grep -E '^anicca-heartbeat( |$)'
```
Expected: one line beginning with `anicca-heartbeat`.

- [ ] **Step 11: Re-run the E2E test to confirm symlink path still works**

Run:
```bash
/Users/operator/anicca-oss/skills/anicca-heartbeat/tests/test_heartbeat_e2e.sh
```
Expected: `PASS`.

- [ ] **Step 12: Commit**

Run:
```bash
cd /Users/operator/anicca-oss
git add skills/anicca-heartbeat
git commit -m "feat(skill): anicca-heartbeat — 30-min liveness skill for genesis body"
git push
```
Expected: push succeeds.

---

### Task 6: Schedule the heartbeat via `hermes cron`

**Files:** none new in the repo; Hermes manages its own cron metadata under `~/.hermes/cron/`.

- [ ] **Step 1: Create the cron entry**

Run:
```bash
hermes cron create "every 30m" \
  --name anicca-heartbeat \
  --command "/Users/operator/anicca-oss/skills/anicca-heartbeat/scripts/heartbeat.sh"
```
Expected: prints `Created anicca-heartbeat (every 30m)` or the local equivalent + exit 0. If the `hermes cron create` flags differ in the installed version, run `hermes cron create --help` and adjust the flags inline; the only required behavior is "every 30m, runs that exact path".

- [ ] **Step 2: Confirm it's listed**

Run:
```bash
hermes cron list
```
Expected: a row containing `anicca-heartbeat` and `every 30m` (or `30m` / `*/30`).

- [ ] **Step 3: Force one fire and observe**

Run:
```bash
LINES_BEFORE=$(wc -l < /Users/operator/.hermes/state/heartbeat.jsonl 2>/dev/null || echo 0)
hermes cron run anicca-heartbeat 2>&1 | tail -20 || \
  /Users/operator/anicca-oss/skills/anicca-heartbeat/scripts/heartbeat.sh
LINES_AFTER=$(wc -l < /Users/operator/.hermes/state/heartbeat.jsonl)
echo "delta=$((LINES_AFTER - LINES_BEFORE))"
```
Expected: `delta=1`. If `hermes cron run` is not implemented in this version, the fallback direct-call still produces the +1 line, so the test passes either way.

---

### Task 7: Keep the Hermes cron daemon alive via launchd

**Files:**
- Create: `/Users/operator/anicca-oss/scripts/launchd/ai.anicca.hermes-cron.plist`
- Create: `/Users/operator/anicca-oss/scripts/launchd/install-hermes-cron-launchd.sh`
- Modify: `~/Library/LaunchAgents/ai.anicca.hermes-cron.plist` (installed copy)

- [ ] **Step 1: Author the plist**

Create `/Users/operator/anicca-oss/scripts/launchd/ai.anicca.hermes-cron.plist` with EXACTLY:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>ai.anicca.hermes-cron</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/operator/.local/bin/hermes</string>
    <string>cron</string>
    <string>daemon</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>StandardOutPath</key><string>/Users/operator/.hermes/logs/hermes-cron.launchd.out</string>
  <key>StandardErrorPath</key><string>/Users/operator/.hermes/logs/hermes-cron.launchd.err</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/Users/operator/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>HOME</key><string>/Users/operator</string>
  </dict>
</dict>
</plist>
```

NOTE: If `hermes cron --help` shows that scheduling is in-process (no separate `daemon` subcommand), replace `ProgramArguments` with the in-process command Hermes ships (e.g. `hermes gateway run` or `hermes -z "tick"` in a loop). Verify with `hermes cron --help` BEFORE installing the plist; if uncertain, gate this task and report — do NOT guess.

- [ ] **Step 2: Author the installer script**

Create `/Users/operator/anicca-oss/scripts/launchd/install-hermes-cron-launchd.sh` with EXACTLY:
```bash
#!/usr/bin/env bash
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/ai.anicca.hermes-cron.plist"
DST="$HOME/Library/LaunchAgents/ai.anicca.hermes-cron.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.hermes/logs"
cp "$SRC" "$DST"
launchctl bootout gui/$(id -u) "$DST" 2>/dev/null || true
launchctl bootstrap gui/$(id -u) "$DST"
launchctl enable gui/$(id -u)/ai.anicca.hermes-cron
launchctl kickstart -k gui/$(id -u)/ai.anicca.hermes-cron
echo "installed: $DST"
launchctl list | grep ai.anicca.hermes-cron || true
```
Make executable:
```bash
chmod +x /Users/operator/anicca-oss/scripts/launchd/install-hermes-cron-launchd.sh
```

- [ ] **Step 3: Install and start**

Run:
```bash
/Users/operator/anicca-oss/scripts/launchd/install-hermes-cron-launchd.sh
```
Expected: ends with a `launchctl list` line containing `ai.anicca.hermes-cron`, with a PID (or `-`) in the first column.

- [ ] **Step 4: Verify the launchd count incremented by exactly 1**

Run:
```bash
launchctl list | grep -c '^[^	]*[0-9]*	[0-9]*	ai\.anicca\.'
```
Expected: `24` (was 23 in Task 1 Step 3).

- [ ] **Step 5: Verify the launchd job survives a forced restart**

Run:
```bash
launchctl kickstart -k gui/$(id -u)/ai.anicca.hermes-cron
sleep 5
launchctl list | grep ai.anicca.hermes-cron
```
Expected: still shows the job with a valid PID (not `-` and not exit code ≠ 0).

- [ ] **Step 6: Commit**

Run:
```bash
cd /Users/operator/anicca-oss
git add scripts/launchd/ai.anicca.hermes-cron.plist scripts/launchd/install-hermes-cron-launchd.sh
git commit -m "feat(launchd): keep hermes cron daemon alive (ai.anicca.hermes-cron)"
git push
```

---

### Task 8: E2E observe ≥1 natural fire cycle

**Files:** none changed; this task is verification per superpowers:verification-before-completion.

- [ ] **Step 1: Record the current state line count**

Run:
```bash
LINES_T0=$(wc -l < /Users/operator/.hermes/state/heartbeat.jsonl)
date -u +%FT%TZ
echo "lines at T0: $LINES_T0"
```

- [ ] **Step 2: Wait 35 minutes (one full 30-minute cron window + buffer)**

Use Bash's `run_in_background` or `Monitor` tooling to sleep ~35m without blocking other work. Per HARD RULE #14 (JOB'S NOT FINISHED), DO NOT advance to other tasks until this verification completes.

- [ ] **Step 3: Confirm a natural fire occurred**

Run:
```bash
LINES_T1=$(wc -l < /Users/operator/.hermes/state/heartbeat.jsonl)
echo "lines at T1: $LINES_T1"
tail -n 1 /Users/operator/.hermes/state/heartbeat.jsonl | /opt/homebrew/bin/jq .
```
Expected: `LINES_T1 > LINES_T0`. The tailed object has `ok: true`. If `ok: false`, debug with `cat /Users/operator/.hermes/logs/hermes-cron.launchd.err | tail -50` before claiming done.

- [ ] **Step 4: Verify the launchd job is still alive after the window**

Run:
```bash
launchctl list | grep ai.anicca.hermes-cron
```
Expected: still present, no error exit code in column 2.

---

### Task 9: Update spec 00-MASTER § GROUND TRUTH + close the task

**Files:**
- Modify: `/Users/operator/anicca-oss/specs/00-MASTER.md` (the GROUND TRUTH paragraph)

- [ ] **Step 1: Replace the GROUND TRUTH `instances` line**

In `/Users/operator/anicca-oss/specs/00-MASTER.md`, find the line beginning with ` instances    = genesis ×1 (Mac-mini, OpenClaw runtime, ...).` and replace it with:
```
 instances    = genesis ×1 = Hermes vX.Y.Z on Mac-mini (BYOK fuel=<provider>, model=<model>),
                heartbeat every 30m -> ~/.hermes/state/heartbeat.jsonl, launchd ai.anicca.hermes-cron alive.
                (OpenClaw 23 jobs remain co-resident; cloud/child = ZERO; "4 instances" still target-state.)
```
Substitute the actual `vX.Y.Z`, `<provider>`, `<model>` recorded in Tasks 2 and 3.

- [ ] **Step 2: Commit + push the GROUND TRUTH update**

Run:
```bash
cd /Users/operator/anicca-oss
git add specs/00-MASTER.md
git commit -m "docs(spec): GROUND TRUTH — genesis body now Hermes vX.Y.Z (#323 Wave 1 done)"
git push
```
Substitute the real version.

- [ ] **Step 3: Mark task #323 done in the TaskList**

Use the TaskUpdate tool to set `#323` status to `completed`. The task description still owns BYOK Wave 2/3; OPEN a NEW task `#323b BYOK Wave 2 (Anthropic OAuth)` and `#323c BYOK Wave 3 (Base USDC fuel)` to track the remaining LAUNCH-GATE row ② coverage. Mark this plan's plan-file as the source of completion.

---

## Self-Review

**Spec coverage:**
- Spec `00-MASTER.md` § 1.0 RUNTIME DECISION says "Hermes = ONE runtime, native BYOK brain via `hermes model`, cron scheduler = autonomous heartbeat". Tasks 2, 3, 6, 7 implement this directly.
- Spec `16-RUNTIME-CODE-TRUTH.md` § 17 ("Hermes one runtime + port automaton 4 primitives") — primitives (wallet/x402/self-replication/constitution-guard) are explicitly OUT of scope here and tracked in #324/#326/#327; only the constitution wiring (the cheapest of the four) is done here via the AGENTS.md symlink, which is the prerequisite the other three skills need to see the law.
- LAUNCH ACCEPTANCE MATRIX row ② (boot via each of 3 fuels): this plan satisfies ONE fuel. Followed by sister plans for the remaining two.
- Heartbeat skill matches the spec 18 § 1 "self-monitor" leaf at its smallest possible form.

**Placeholder scan:** none — every step has the full command, full file content, and the exact expected output. The two places that say "substitute" (Task 3 Step 2 the key name, Task 9 Step 1 the version) MUST be filled with the values literally observed in Tasks 1-3; they are not TODOs, they are values that can only exist after the prior step completes.

**Type consistency:** the JSONL row shape `{ts, ok, fuel, model, constitution_sha, probe}` is identical in `heartbeat.sh` (writer) and `test_heartbeat_e2e.sh` (reader, via `jq -e`). `lifeline-check.sh` outputs the keys it exports, and `heartbeat.sh` reads them by the exact same name. The launchd `Label` `ai.anicca.hermes-cron` is identical across plist, installer, and verification step.

**Risk note (read before executing):** Task 7 Step 1 contains an explicit NOTE that the `hermes cron daemon` subcommand may not exist in your installed Hermes version. The plan tells the implementer to check `hermes cron --help` BEFORE installing the plist and to escalate rather than guess. This is the one place reality can diverge from the plan — and it is gated, not silently glossed over.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-04-hermes-genesis-boot.md`.

Per Dais's directive ("keep getting reviewed by codex; only when it's time to implement, build with agent teams"), the next move is NOT to start Task 1 — it is to run **codex-review** against this plan and the latest spec heads (specs/00, 16, 18, 19-24). When codex says `ok: true`, dispatch the implementation via **superpowers:subagent-driven-development** — fresh subagent per task, two-stage review (spec compliance, then code quality) after each task.
