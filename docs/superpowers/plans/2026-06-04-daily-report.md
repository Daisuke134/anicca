# Daily Report Skill (P1-REPORT, task #330) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hermes side-native `daily-report` skill that fires every day at 06:00 JST via `hermes cron`, composes a USEFUL (CLAUDE.md HARD RULE 0.19) daily digest from the SAME local data sources the existing OpenClaw `anicca-report` reads, and SENDS it as an email via AgentMail (`anicca-genesis@agentmail.to`) to a configurable recipient list. Wave-1 = minimum buildable; Wave-2 (weekly) and Wave-3 (proactive alerts #156) are EXPLICITLY OUT.

**Architecture decision — DO NOT REUSE the OpenClaw skill via symlink.** Three reasons (all verified):

1. The legacy skill (`~/.openclaw/skills/anicca-report/scripts/report.py`) sends via `gog gmail send` from Dais's personal Gmail (`person@example.com`). That is Dais's identity, not Anicca's. CLAUDE.md (2026-06-03 `feedback_anicca_speaks_as_herself`) + memory `identity_anicca_login_accounts` say Anicca presents AS HERSELF from her sovereign inbox `anicca-genesis@agentmail.to`. Symlinking the legacy script would keep the send-from-Dais behavior — wrong identity.
2. The launch pitch row ⑤d says **"daily email arrives"**. Spec 00-MASTER line 141 says `#231 ✓ LIVE / #330` — meaning #231 (OpenClaw side) is the legacy reference and #330 (this task) is the Hermes-native rebuild. The pitch lives in the Hermes/anicca-oss runtime; the email must originate from Anicca's own inbox or the pitch is false.
3. The OpenClaw skill costs $0 (no LLM) but is also slop (= fixed template). HARD RULE 0.19 USEFUL_CONTENT_SPEC requires the email be USEFUL = bookmark-able. We add ONE small Hermes LLM hop (≤300 tokens, budget ≤ $0.01) to convert the raw cfo+heartbeat+friction probe into 3 substantive bullets. The deterministic header (numbers, status, runway) stays template-rendered so the email never silently fails on LLM outages — fallback to header-only is graceful.

**Reuse strategy (DRY):** the new Hermes skill READS the same input files the legacy skill reads — `~/.openclaw/skills/cfo-core/data/anicca-cfo.json` (refreshed daily 06:00 by `ai.anicca.cfo-daily` launchd, verified via `updated_at` field) + `~/.hermes/state/heartbeat.jsonl` (written by the genesis-boot heartbeat from 2026-06-04 sister plan) + `~/.openclaw/skills/anicca-friction-fixer/state/violations.jsonl` (friction errors) + `~/.openclaw/state/friction-sweep.log`. NO data is duplicated; the skill is a pure read/compose/send pipeline.

**Tech Stack:** Hermes Agent **pinned to v0.12.0** (command surfaces locked per cross-plan rule X1) · Python 3.13 in a project-local venv at `~/.hermes/skills/daily-report/.venv/` · `agentmail==0.5.2` Python SDK (PINNED per cross-plan rule X5; no `>=` ranges) · jq for JSONL parsing · existing `AGENTMAIL_API_KEY` + `AGENTMAIL_INBOX_ID` in `~/.openclaw/.env` (copy ONE line into `~/.hermes/.env` per genesis-boot Task 3 Step 2 pattern). The send path uses ONE Hermes LLM call for bullet synthesis (tiny prompt, model = whatever genesis-boot Task 3 selected); on LLM failure the skill emits a header-only email and exits 0.

**Scope-out (other plans):**
- Weekly Monday 09:00 digest (= Wave 2; same skill, `--weekly` flag, separate cron entry once daily proves stable for 7 days).
- Proactive push alerts (#156 — already done in OpenClaw; not this plan).
- Replacing the legacy OpenClaw `anicca-report` skill — leaves running co-resident; #231 stays LIVE until #341 LAUNCH-GATE flips ⑤d to truly Hermes-only. NO files deleted under `~/.openclaw/skills/anicca-report/`.
- HTML email styling — Wave-1 is plain text.

**Done condition for this plan (proves task #330):**

1. `hermes skills list | grep '^daily-report'` shows exactly one row.
2. `hermes cron list | grep daily-report` shows ONE job with schedule `0 6 * * *` (or local equivalent `every 1d at 06:00`).
3. Manual fire: `hermes cron run daily-report` (fallback `~/.hermes/scripts/daily-report.sh`) exits 0 and the AgentMail inbox `anicca-genesis@agentmail.to` shows the sent message in `client.inboxes.messages.list(inbox_id=…)` within 60 s. The Hermes-native send is **identified by the SMTP header `X-Anicca-Origin: hermes-genesis`** — the legacy OpenClaw `anicca-report` skill is still firing at 18:00 JST until LAUNCH-GATE #341 retires it, so TWO emails/day are expected during the transition; only the one carrying `X-Anicca-Origin: hermes-genesis` proves #330.
4. The sent email contains, in this order, all the following sections (each non-empty unless explicitly noted): subject line `[Anicca] Day N — MRR $X · runtime $Y · status STATUS`; deterministic header block with MRR/revenue-28d/runtime/net/wallet/runway from `anicca-cfo.json`; "Yesterday's heartbeat" block with last-24h heartbeat row count + ok/total ratio; "Constitution-violations" block from `~/.openclaw/state/friction-sweep.log` (last 24h grep) OR "none today"; "Errors logged by friction-fixer" block from `violations.jsonl` last 24h OR "none today"; "What I did" block = top-3 LLM-synthesized substantive bullets (NOT generic affirmation per HARD RULE 0.19); footer `— Anicca · /report off · /report to <email>`.
5. Budget: `anicca-cfo.json` `spends.runtime_items` delta after a fire shows ≤ $0.01 added in the model line for that fire. The skill logs the token cost to `~/.hermes/state/daily-report.jsonl` so the next plan-completion check can verify. Per cross-plan rule X2, #330 closure requires CFO heartbeat to record cost ≤ $0.01 in the same window.
6. The skill writes a JSONL trace line to `~/.hermes/state/daily-report.jsonl` per fire, with shape `{ts, ok, sent_to:[…], subject, body_chars, llm_tokens, llm_cost_usd}`. Used by tests + future eval-loop (#329).
7. **Sustained-send gate (replaces single-fire claim):** #330 is NOT closed until BOTH (a) ≥ 7 consecutive successful sends are observed in `~/.hermes/state/daily-report.jsonl` (i.e. last 7 rows all have `send.ok == true`) AND (b) ZERO `severity=critical` rows appear in `~/.hermes/state/daily-report-alerts.jsonl` during the same 7-day window. If `send.ok == false` at any fire, send.py writes one `severity=critical` row to `daily-report-alerts.jsonl` (see Task 5) and the cron exit code stays 0 so cron itself survives, but the 7-day counter restarts. This is the explicit fix for the silent-send-failure risk.
8. Codex-review passes `ok: true` on (a) this plan, (b) the SKILL.md, (c) the `compose.py` source, (d) the `send.py` source. Mandated by GATE-1 + GATE-3 in `.claude/rules/dev-workflow.md`.
9. All new files committed + pushed to `anicca-oss`. CLAUDE.md rule 0.4.

---

## File Structure (what each file owns)

```
anicca-oss/                                              (this repo, committed)
  skills/daily-report/
    SKILL.md                       ← Hermes-format frontmatter manifest
    README.md                      ← one paragraph human description
    scripts/compose.py             ← reads data, calls LLM for bullets, renders body
    scripts/send.py                ← AgentMail send wrapper (one fn: send_email)
    scripts/daily-report.sh        ← entrypoint: wraps both, writes trace JSONL
    scripts/requirements.txt       ← agentmail>=0.5.2
    tests/test_compose_unit.sh     ← TDD red→green: header builds from frozen fixtures
    tests/test_send_e2e.sh         ← TDD red→green: real AgentMail send to genesis inbox
    tests/fixtures/anicca-cfo.json ← frozen deterministic fixture (mock cfo data)
    tests/fixtures/heartbeat.jsonl ← 3-line fixture (2 ok, 1 fail)
  docs/superpowers/plans/
    2026-06-04-daily-report.md     ← THIS plan

~/.hermes/                                                (runtime, NOT committed)
  skills/daily-report                ← SYMLINK → anicca-oss/skills/daily-report
  skills/daily-report/.venv/         ← Python venv with agentmail installed
  scripts/daily-report.sh            ← SYMLINK → anicca-oss/skills/daily-report/scripts/daily-report.sh
  state/daily-report.jsonl           ← append-only trace log (one line per fire)
  .env                               ← gets up to 3 lines appended if missing
                                       (AGENTMAIL_API_KEY, AGENTMAIL_INBOX_ID, ANICCA_REPORT_TO)
```

Why symlinks (mirrors genesis-boot plan): the skill source lives in the repo where review/PR/roll-out is auditable; Hermes immediately sees edits without a copy step. Tests run against the repo path so CI later works unchanged.

Why a project-local venv (NOT system Python): system Python 3.13 is PEP-668 externally-managed; `pip install agentmail` was blocked in pre-flight (verified 2026-06-04). The venv pins `agentmail>=0.5.2` deterministically; one-time setup in Task 2.

---

### Task 1: Pre-flight — verify hermes + AgentMail env + CFO data are live

**Files:** none new; this is verification per superpowers:verification-before-completion.

- [ ] **Step 1: Confirm Hermes binary is pinned to v0.12.0 + cron subcommand is usable**

Per cross-plan rule X1, Hermes is LOCKED at v0.12.0 — we do not call `hermes update` and we do not gate on `Update available` output. Run:
```bash
/Users/anicca/.local/bin/hermes --version | grep -F 'v0.12.0' \
  || { echo "FAIL: hermes is not pinned to v0.12.0"; exit 1; }
/Users/anicca/.local/bin/hermes cron --help | head -3
/Users/anicca/.local/bin/hermes cron create --help | grep -E 'schedule|script|no-agent'
/Users/anicca/.local/bin/hermes skills --help | head -3
```
Expected: the version grep succeeds (binary reports `v0.12.0`); `cron create --help` shows the `schedule`, `--script`, and `--no-agent` flags; the other two commands print non-empty output. If the version grep fails, STOP and re-pin via genesis-boot Task 2 (which installs the v0.12.0 tarball) before continuing.

- [ ] **Step 1b: AgentMail SDK preflight (cross-plan rule X5)**

Run:
```bash
/opt/homebrew/bin/python3 -c "import agentmail; print(agentmail.__version__)" \
  || /opt/homebrew/bin/python3 -m pip install --user 'agentmail==0.5.2'
command -v agentmail || /opt/homebrew/bin/python3 -m pip install --user 'agentmail==0.5.2'
set -a; . /Users/anicca/.openclaw/.env; set +a
curl -s -H "X-API-Key: $AGENTMAIL_API_KEY" https://api.agentmail.to/v0/inboxes \
  | /opt/homebrew/bin/jq -e '.inboxes // .items // . | length > 0' >/dev/null \
  && echo "OK agentmail reachable"
```
Expected: prints the installed version (must be `0.5.2`; the venv created in Task 2 will pin the same string in `requirements.txt`) and `OK agentmail reachable`. If the curl returns 401, the `AGENTMAIL_API_KEY` is stale — re-mint from the AgentMail dashboard before continuing.

- [ ] **Step 2: Confirm AgentMail credentials exist in OpenClaw .env**

Run (DO NOT echo the value):
```bash
grep -E '^(AGENTMAIL_API_KEY|AGENTMAIL_INBOX_ID)=' /Users/anicca/.openclaw/.env | awk -F= '{print $1}'
```
Expected: exactly two lines, `AGENTMAIL_API_KEY` and `AGENTMAIL_INBOX_ID`. If `AGENTMAIL_INBOX_ID` is missing, look it up via memory `IDENTITY: AgentMail provisioned (2026-06-03)` (= `anicca-genesis@agentmail.to`, org `4812311a-000e-4236-b1a7-e47a6261cf0c`) and add it to `~/.openclaw/.env` with `chmod 600`.

- [ ] **Step 3: Confirm `anicca-cfo.json` is fresh (≤24h old)**

Run:
```bash
/opt/homebrew/bin/python3 -c "
import json, time
from pathlib import Path
p = Path('/Users/anicca/.openclaw/skills/cfo-core/data/anicca-cfo.json')
d = json.loads(p.read_text())
ts = d['updated_at']
age_h = (time.time() - time.mktime(time.strptime(ts.split('.')[0], '%Y-%m-%dT%H:%M:%S'))) / 3600
print(f'updated_at={ts} age={age_h:.1f}h')
assert age_h < 26, 'CFO data is stale; ai.anicca.cfo-daily launchd may be dead'
print('OK fresh')
"
```
Expected: prints `OK fresh`. If stale, STOP and fix `ai.anicca.cfo-daily` launchd first — this skill is downstream and cannot publish stale numbers.

- [ ] **Step 4: Confirm Hermes genesis-boot heartbeat is writing JSONL**

Run:
```bash
test -s /Users/anicca/.hermes/state/heartbeat.jsonl && \
  echo "lines=$(wc -l < /Users/anicca/.hermes/state/heartbeat.jsonl)" && \
  tail -1 /Users/anicca/.hermes/state/heartbeat.jsonl | /opt/homebrew/bin/jq -e '.ok' >/dev/null && \
  echo "OK heartbeat live"
```
Expected: prints `lines=<N>` (N≥1) then `OK heartbeat live`. If the file is missing or empty, the genesis-boot plan (2026-06-04-hermes-genesis-boot.md) MUST complete first — `daily-report` depends on its trace.

- [ ] **Step 5: Commit the plan itself**

Run:
```bash
cd /Users/anicca/anicca-oss
git add docs/superpowers/plans/2026-06-04-daily-report.md
git commit -m "docs(plan): daily-report (#330) — Hermes cron 06:00 JST → AgentMail send, reuse anicca-report data sources"
git push
```
Expected: push succeeds, new commit appears in `git log --oneline -1`.

---

### Task 2: Create the skill directory + Python venv + requirements

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/daily-report/scripts/requirements.txt`
- Create: `/Users/anicca/.hermes/skills/daily-report/.venv/` (via `python3 -m venv`)

- [ ] **Step 1: Create the on-repo skill directory tree**

Run:
```bash
mkdir -p /Users/anicca/anicca-oss/skills/daily-report/{scripts,tests/fixtures}
ls /Users/anicca/anicca-oss/skills/daily-report/
```
Expected: `scripts/  tests/` printed.

- [ ] **Step 2: Pin Python dependencies**

Create `/Users/anicca/anicca-oss/skills/daily-report/scripts/requirements.txt` with EXACTLY this content (PINNED per cross-plan rule X5 — no `>=` ranges):
```
agentmail==0.5.2
```

- [ ] **Step 3: Symlink the skill into ~/.hermes/skills/ early so the venv lives at a stable path**

Run:
```bash
mkdir -p /Users/anicca/.hermes/skills
[ -L /Users/anicca/.hermes/skills/daily-report ] && rm /Users/anicca/.hermes/skills/daily-report
ln -s /Users/anicca/anicca-oss/skills/daily-report /Users/anicca/.hermes/skills/daily-report
ls -l /Users/anicca/.hermes/skills/daily-report
```
Expected: `lrwxr-... -> /Users/anicca/anicca-oss/skills/daily-report`.

- [ ] **Step 4: Build the venv INSIDE the runtime symlinked dir (so .venv is gitignored implicitly via the symlink target's parent)**

Run:
```bash
/Users/anicca/.local/bin/python3.13 -m venv /Users/anicca/anicca-oss/skills/daily-report/.venv
/Users/anicca/anicca-oss/skills/daily-report/.venv/bin/pip install --quiet -r /Users/anicca/anicca-oss/skills/daily-report/scripts/requirements.txt
/Users/anicca/anicca-oss/skills/daily-report/.venv/bin/python -c "from agentmail import AgentMail; print('agentmail OK')"
```
Expected: prints `agentmail OK` after a few pip lines.

- [ ] **Step 5: Add .venv to anicca-oss/.gitignore**

Run:
```bash
GITIGNORE=/Users/anicca/anicca-oss/.gitignore
grep -qxF 'skills/*/.venv/' "$GITIGNORE" 2>/dev/null || echo 'skills/*/.venv/' >> "$GITIGNORE"
tail -1 "$GITIGNORE"
```
Expected: prints `skills/*/.venv/`.

- [ ] **Step 6: Copy AgentMail env keys into ~/.hermes/.env (no value echo)**

Run:
```bash
for KEY in AGENTMAIL_API_KEY AGENTMAIL_INBOX_ID; do
  if ! grep -q "^$KEY=" /Users/anicca/.hermes/.env 2>/dev/null; then
    VAL=$(grep "^$KEY=" /Users/anicca/.openclaw/.env | head -1 | cut -d= -f2-)
    printf '%s=%s\n' "$KEY" "$VAL" >> /Users/anicca/.hermes/.env
    echo "appended $KEY"
  else
    echo "$KEY already present"
  fi
done
# default recipient = the inbox itself + Dais
if ! grep -q '^ANICCA_REPORT_TO=' /Users/anicca/.hermes/.env 2>/dev/null; then
  printf 'ANICCA_REPORT_TO=%s\n' 'person@example.com,anicca-genesis@agentmail.to' >> /Users/anicca/.hermes/.env
  echo "appended ANICCA_REPORT_TO"
fi
chmod 600 /Users/anicca/.hermes/.env
```
Expected: prints up to 3 `appended …` lines or `already present` for each. NEVER echo `$VAL`.

---

### Task 3: Write the failing compose unit test (TDD red)

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/daily-report/tests/fixtures/anicca-cfo.json`
- Create: `/Users/anicca/anicca-oss/skills/daily-report/tests/fixtures/heartbeat.jsonl`
- Create: `/Users/anicca/anicca-oss/skills/daily-report/tests/fixtures/violations.jsonl`
- Create: `/Users/anicca/anicca-oss/skills/daily-report/tests/test_compose_unit.sh`

- [ ] **Step 1: Write the cfo fixture (mirrors live shape; numbers are deterministic, NOT real)**

Create `/Users/anicca/anicca-oss/skills/daily-report/tests/fixtures/anicca-cfo.json` with EXACTLY this content:
```json
{
  "schema": "cfo-anicca/v1",
  "updated_at": "2026-06-04T03:52:35.847Z",
  "makes": {
    "mrr_usd": 27,
    "revenue_28d_usd": 0,
    "actually_landed_usd": 31.97,
    "monthly_total_usd": 27
  },
  "spends": {
    "anicca_runtime_usd": 99,
    "runtime_items": [
      {"vendor": "OpenAI", "label": "GPT/Codex", "monthly_usd": 20, "cadence": "monthly"},
      {"vendor": "Postiz", "label": "Postiz", "monthly_usd": 49, "cadence": "monthly"},
      {"vendor": "Grok xAI", "label": "Grok xAI", "monthly_usd": 30, "cadence": "monthly"}
    ],
    "founder_dev_usd": 200
  },
  "lifeline": {
    "net_monthly_usd": -72,
    "status": "HUNGRY",
    "message": "MRR 27 < runtime 99"
  },
  "wallet": {"base_usdc": 0, "usd_total": 0}
}
```

- [ ] **Step 2: Write the heartbeat fixture (3 lines = 2 ok, 1 fail, all within last 24h)**

Create `/Users/anicca/anicca-oss/skills/daily-report/tests/fixtures/heartbeat.jsonl` with EXACTLY this content (each line is one JSON object; the script uses `jq -c` to parse):
```jsonl
{"ts":"2026-06-03T22:00:00Z","ok":true,"fuel":"openai","model":"gpt-5.2-mini","constitution_sha":"abc123"}
{"ts":"2026-06-04T01:30:00Z","ok":false,"fuel":"openai","model":"gpt-5.2-mini","constitution_sha":"abc123"}
{"ts":"2026-06-04T04:00:00Z","ok":true,"fuel":"openai","model":"gpt-5.2-mini","constitution_sha":"abc123"}
```

- [ ] **Step 3: Write the friction violations fixture**

Create `/Users/anicca/anicca-oss/skills/daily-report/tests/fixtures/violations.jsonl` with EXACTLY this content:
```jsonl
{"ts":"2026-06-04T02:15:00Z","pattern":"user-click","source":"some-cron","fix_attempted":true,"resolved":true}
```

- [ ] **Step 4: Write the failing compose unit test**

Create `/Users/anicca/anicca-oss/skills/daily-report/tests/test_compose_unit.sh` with EXACTLY this content:
```bash
#!/usr/bin/env bash
# Unit: compose.py --offline reads fixtures and prints header + body, NO LLM call,
# NO outbound. Asserts every required section header appears verbatim.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="$SKILL_DIR/.venv/bin/python"

OUT="$("$PY" "$SKILL_DIR/scripts/compose.py" --offline \
  --cfo "$SKILL_DIR/tests/fixtures/anicca-cfo.json" \
  --heartbeat "$SKILL_DIR/tests/fixtures/heartbeat.jsonl" \
  --violations "$SKILL_DIR/tests/fixtures/violations.jsonl" \
  --now 2026-06-04T06:00:00+09:00)"

# Required subject prefix
echo "$OUT" | head -1 | grep -qE '^SUBJECT: \[Anicca\] Day [0-9]+ — MRR \$27' || { echo "FAIL subject"; exit 1; }

# Required section headers verbatim
for h in 'Headline (2026-06-04):' "Yesterday's heartbeat:" "Constitution-violations (24h):" "Errors from friction-fixer (24h):" "What I did:" "— Anicca"; do
  echo "$OUT" | grep -qF "$h" || { echo "FAIL missing section: $h"; exit 1; }
done

# Numeric correctness from fixture
echo "$OUT" | grep -qE 'MRR:[[:space:]]+\$27\.00' || { echo "FAIL MRR number"; exit 1; }
echo "$OUT" | grep -qE 'Runtime cost:[[:space:]]+\$99\.00' || { echo "FAIL runtime number"; exit 1; }
echo "$OUT" | grep -qE 'Status:[[:space:]]+HUNGRY' || { echo "FAIL status"; exit 1; }

# Heartbeat ratio = 2 ok / 3 total in last 24h
echo "$OUT" | grep -qE '2/3 ok' || { echo "FAIL heartbeat ratio"; exit 1; }

echo "PASS"
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/daily-report/tests/test_compose_unit.sh
```

- [ ] **Step 5: Run the test — must FAIL because `compose.py` does not exist (TDD red)**

Run:
```bash
/Users/anicca/anicca-oss/skills/daily-report/tests/test_compose_unit.sh
```
Expected: non-zero exit, stderr/stdout contains `No such file` or `can't open file …compose.py`. This is the RED phase.

---

### Task 4: Write `scripts/compose.py` (TDD green — header)

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/daily-report/scripts/compose.py`

- [ ] **Step 1: Author compose.py with EXACTLY this content**

Create `/Users/anicca/anicca-oss/skills/daily-report/scripts/compose.py`:
```python
#!/usr/bin/env python3
"""daily-report — compose USEFUL daily digest from local Anicca state.

Reads (no writes):
  - anicca-cfo.json     (numbers)
  - heartbeat.jsonl     (Hermes genesis liveness)
  - violations.jsonl    (friction-fixer)
  - friction-sweep.log  (constitution-violations text grep)

Emits to stdout:
  Line 1: SUBJECT: <subject>
  Line 2: BODY-START
  ...    <body, multi-line>
  Line N: BODY-END

--offline skips the LLM bullets call; sections appear with placeholder
"(LLM-offline — no bullets)". Used by unit tests. Live runs OMIT --offline.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
INSTALL_TS_FILE = Path.home() / ".hermes" / "state" / "anicca_install_ts"


def _f(x) -> float:
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def day_number(now: datetime) -> int:
    """Day N since first ever Hermes/Anicca beat — recorded on first run."""
    if not INSTALL_TS_FILE.exists():
        INSTALL_TS_FILE.parent.mkdir(parents=True, exist_ok=True)
        INSTALL_TS_FILE.write_text(str(int(now.timestamp())))
    try:
        installed_ts = int(INSTALL_TS_FILE.read_text().strip())
    except (ValueError, OSError):
        installed_ts = int(now.timestamp())
    return max(1, int((now.timestamp() - installed_ts) // 86400) + 1)


def read_cfo(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def cfo_overview(cfo: dict) -> dict:
    makes = cfo.get("makes") or {}
    spends = cfo.get("spends") or {}
    lifeline = cfo.get("lifeline") or {}
    wallet_block = cfo.get("wallet") or {}
    mrr = _f(makes.get("mrr_usd"))
    revenue_28d = _f(makes.get("revenue_28d_usd"))
    landed_28d = _f(makes.get("actually_landed_usd"))
    runtime_cost = _f(spends.get("anicca_runtime_usd"))
    net_monthly = _f(lifeline.get("net_monthly_usd"))
    status = (lifeline.get("status") or "?").upper()
    msg = lifeline.get("message") or ""
    wallet_usd = _f(wallet_block.get("base_usdc") or wallet_block.get("usd_total"))
    runway_days = (
        int(wallet_usd / (runtime_cost / 30.0))
        if (wallet_usd > 0 and runtime_cost > 0)
        else -1
    )
    return {
        "mrr": mrr,
        "revenue_28d": revenue_28d,
        "landed_28d": landed_28d,
        "runtime_cost": runtime_cost,
        "net_monthly": net_monthly,
        "status": status,
        "message": msg,
        "wallet_usd": wallet_usd,
        "runway_days": runway_days,
        "runtime_items": spends.get("runtime_items") or [],
    }


def parse_heartbeats_24h(path: Path, now: datetime) -> tuple[int, int]:
    """Return (ok_count, total_count) for heartbeat entries in last 24h."""
    if not path.exists():
        return (0, 0)
    cutoff = now - timedelta(hours=24)
    ok = 0
    total = 0
    for line in path.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts_str = row.get("ts", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts < cutoff:
            continue
        total += 1
        if row.get("ok") is True:
            ok += 1
    return (ok, total)


def parse_violations_24h(path: Path, now: datetime) -> list[dict]:
    """Return friction-fixer violations within last 24h."""
    if not path.exists():
        return []
    cutoff = now - timedelta(hours=24)
    rows: list[dict] = []
    for line in path.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts_str = row.get("ts", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts >= cutoff:
            rows.append(row)
    return rows


def parse_constitution_violations_24h(path: Path, now: datetime) -> list[str]:
    """Grep friction-sweep.log for last 24h. Lines starting YYYY-MM-DDTHH."""
    if not path.exists():
        return []
    cutoff = now - timedelta(hours=24)
    out: list[str] = []
    for line in path.read_text(errors="ignore").splitlines()[-2000:]:
        m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
        if not m:
            continue
        try:
            ts = datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts >= cutoff and ("VIOLATION" in line or "violation" in line):
            out.append(line[:200])
    return out


def llm_bullets(probe: dict) -> tuple[list[str], int, float]:
    """Call Hermes via `hermes chat -q` for 3 substantive bullets.

    Returns (bullets, tokens_estimated, cost_usd_estimated). Hermes does NOT
    return precise token counts in chat-q mode, so we estimate from char count
    at ~4 chars/token + $5e-6 / token (mini model ballpark). Used for budget
    enforcement only — Wave-2 hooks proper accounting via hermes insights.
    """
    hermes = os.environ.get("HERMES_BIN", "/Users/anicca/.local/bin/hermes")
    prompt = (
        "You are Anicca writing a USEFUL daily report. Given this state probe "
        "as JSON, output EXACTLY 3 bullets of what Anicca did or learned "
        "yesterday. Bullets must be substantive (bookmark-able), not generic "
        "affirmation. Format: '- <bullet>'. No preamble.\n\n"
        f"PROBE:\n{json.dumps(probe, ensure_ascii=False)[:2000]}"
    )
    try:
        out = subprocess.run(
            [hermes, "chat", "-q", prompt],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[compose] LLM call failed: {e}", file=sys.stderr)
        return (["(LLM unreachable — header-only mode)"], 0, 0.0)
    if out.returncode != 0:
        return ([f"(LLM rc={out.returncode}; stderr={out.stderr[:120]})"], 0, 0.0)
    lines = [ln.strip() for ln in out.stdout.splitlines() if ln.strip().startswith("-")]
    bullets = lines[:3] if lines else ["(LLM returned no bullets)"]
    chars = len(out.stdout) + len(prompt)
    tokens = chars // 4
    cost = tokens * 5e-6
    return (bullets, tokens, cost)


def compose(args) -> tuple[str, str, dict]:
    """Returns (subject, body, trace_dict)."""
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(JST)
    cfo = read_cfo(Path(args.cfo))
    o = cfo_overview(cfo)
    ok, total = parse_heartbeats_24h(Path(args.heartbeat), now)
    violations = parse_violations_24h(Path(args.violations), now)
    constitution = parse_constitution_violations_24h(
        Path(args.friction_log), now
    ) if args.friction_log else []
    day_n = day_number(now)

    runway_str = f"{o['runway_days']}d runway" if o["runway_days"] >= 0 else "runway —"
    subject = (
        f"[Anicca] Day {day_n} — MRR ${o['mrr']:.0f} · "
        f"runtime ${o['runtime_cost']:.0f} · status {o['status']}"
    )

    body_lines = [
        f"Hi,",
        "",
        f"Headline ({now.strftime('%Y-%m-%d')}):",
        f"  MRR:             ${o['mrr']:.2f} / mo",
        f"  Revenue 28d:     ${o['revenue_28d']:.2f}  (landed ${o['landed_28d']:.2f})",
        f"  Runtime cost:    ${o['runtime_cost']:.2f} / mo",
        f"  Net:             ${'+' if o['net_monthly'] >= 0 else ''}{o['net_monthly']:.2f} / mo",
        f"  Wallet:          ${o['wallet_usd']:.2f}  ({runway_str})",
        f"  Status:          {o['status']}  {('— ' + o['message']) if o['message'] else ''}",
        "",
        f"Yesterday's heartbeat:",
        f"  {ok}/{total} ok in the last 24h",
        "",
        f"Constitution-violations (24h):",
    ]
    if constitution:
        body_lines.extend([f"  - {c[:160]}" for c in constitution[:5]])
    else:
        body_lines.append("  none today")
    body_lines.append("")
    body_lines.append("Errors from friction-fixer (24h):")
    if violations:
        for v in violations[:5]:
            patt = v.get("pattern", "?")
            src = v.get("source", "?")
            resolved = "resolved" if v.get("resolved") else "open"
            body_lines.append(f"  - [{patt}] {src} ({resolved})")
    else:
        body_lines.append("  none today")
    body_lines.append("")
    body_lines.append("What I did:")

    probe = {
        "day": day_n,
        "mrr": o["mrr"],
        "runtime": o["runtime_cost"],
        "net": o["net_monthly"],
        "status": o["status"],
        "heartbeat_24h": f"{ok}/{total}",
        "violations_24h": len(violations),
        "constitution_24h": len(constitution),
    }
    tokens = 0
    cost = 0.0
    if args.offline:
        body_lines.append("  (LLM-offline — no bullets)")
    else:
        bullets, tokens, cost = llm_bullets(probe)
        body_lines.extend([f"  {b}" for b in bullets])

    body_lines.extend([
        "",
        "— Anicca",
        "   /report off  ·  /report to <email>",
    ])

    body = "\n".join(body_lines)
    trace = {
        "day_n": day_n,
        "mrr": o["mrr"],
        "runtime_cost": o["runtime_cost"],
        "status": o["status"],
        "heartbeat_ok": ok,
        "heartbeat_total": total,
        "violations_24h": len(violations),
        "constitution_24h": len(constitution),
        "llm_tokens": tokens,
        "llm_cost_usd": cost,
        "body_chars": len(body),
    }
    return subject, body, trace


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cfo", default="/Users/anicca/.openclaw/skills/cfo-core/data/anicca-cfo.json")
    p.add_argument("--heartbeat", default="/Users/anicca/.hermes/state/heartbeat.jsonl")
    p.add_argument("--violations", default="/Users/anicca/.openclaw/skills/anicca-friction-fixer/state/violations.jsonl")
    p.add_argument("--friction-log", default="/Users/anicca/.openclaw/state/friction-sweep.log")
    p.add_argument("--now", default="", help="ISO8601 override (test only)")
    p.add_argument("--offline", action="store_true", help="skip LLM bullets")
    p.add_argument("--json", action="store_true", help="also print trace JSON to stderr")
    args = p.parse_args(argv)
    subject, body, trace = compose(args)
    print(f"SUBJECT: {subject}")
    print("BODY-START")
    print(body)
    print("BODY-END")
    if args.json:
        print(json.dumps(trace, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/daily-report/scripts/compose.py
```

- [ ] **Step 2: Run the compose unit test — must PASS now (TDD green)**

Run:
```bash
/Users/anicca/anicca-oss/skills/daily-report/tests/test_compose_unit.sh
```
Expected: final line `PASS`, exit code 0. If FAIL, fix compose.py (do NOT loosen the test).

- [ ] **Step 3: Run compose against LIVE data once, no send, no LLM, to sanity-check shape**

Run EXACTLY this command (pinned to the live data sources Task 1 verified):
```bash
TODAY=$(date -u +%F)
/Users/anicca/anicca-oss/skills/daily-report/.venv/bin/python \
  /Users/anicca/anicca-oss/skills/daily-report/scripts/compose.py --offline \
  --now "${TODAY}T06:00:00+09:00" \
  > /tmp/daily-report-live.txt
head -8 /tmp/daily-report-live.txt
```
Expected first ~8 lines of `/tmp/daily-report-live.txt` (numbers vary by day; structure is fixed):
```
SUBJECT: [Anicca] Day <N> — MRR $<X> · runtime $<Y> · status <STATUS>
BODY-START
Hi,

Headline (<YYYY-MM-DD>):
  MRR:             $<X>.00 / mo
  Revenue 28d:     $<R>.00  (landed $<L>.00)
  Runtime cost:    $<Y>.00 / mo
```
Then assert the contract holds against the live output:
```bash
head -1 /tmp/daily-report-live.txt | grep -qE '^SUBJECT: \[Anicca\] Day [0-9]+ — MRR \$[0-9]+ · runtime \$[0-9]+ · status [A-Z]+$' \
  || { echo "FAIL live subject shape"; exit 1; }
for h in 'BODY-START' "Headline ($(date -u +%F)):" "Yesterday's heartbeat:" "Constitution-violations (24h):" "Errors from friction-fixer (24h):" "What I did:" 'BODY-END'; do
  grep -qF "$h" /tmp/daily-report-live.txt || { echo "FAIL live missing section: $h"; exit 1; }
done
echo "OK live shape"
```
Expected: prints `OK live shape`. No traceback. If any assertion fails, fix `compose.py` (do NOT loosen the assertion) and re-run before proceeding to Task 5.

---

### Task 5: Write `scripts/send.py` (AgentMail wrapper)

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/daily-report/scripts/send.py`

- [ ] **Step 1: Author send.py with EXACTLY this content**

Create `/Users/anicca/anicca-oss/skills/daily-report/scripts/send.py`:
```python
#!/usr/bin/env python3
"""daily-report — send composed email via AgentMail.

Reads body from stdin (the compose.py output: SUBJECT: line + BODY-START/END).
Sends via AgentMail Python SDK using AGENTMAIL_API_KEY + AGENTMAIL_INBOX_ID.
Recipients come from ANICCA_REPORT_TO (comma-separated) or --to override.

Prints a JSON trace to stdout: {ok, recipients, subject, body_chars, message_id|null, error|null}.
Always exits 0 (the trace says ok=false on failure; cron treats it as silent).
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

try:
    from agentmail import AgentMail
except ImportError as e:
    print(json.dumps({"ok": False, "error": f"agentmail not installed: {e}"}))
    sys.exit(0)


def parse_compose_stream(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    subject = ""
    body_lines: list[str] = []
    state = "header"
    for ln in lines:
        if state == "header":
            if ln.startswith("SUBJECT: "):
                subject = ln[len("SUBJECT: "):]
            elif ln == "BODY-START":
                state = "body"
        elif state == "body":
            if ln == "BODY-END":
                state = "done"
                break
            body_lines.append(ln)
    return subject, "\n".join(body_lines)


def load_env_file(path: Path) -> None:
    """Best-effort .env loader; preserves existing os.environ values."""
    if not path.exists():
        return
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--to", default="", help="comma-separated override")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    load_env_file(Path.home() / ".hermes" / ".env")
    api_key = os.environ.get("AGENTMAIL_API_KEY", "")
    inbox_id = os.environ.get("AGENTMAIL_INBOX_ID", "")
    default_to = os.environ.get("ANICCA_REPORT_TO", "")

    text = sys.stdin.read()
    subject, body = parse_compose_stream(text)

    recipients_raw = args.to or default_to
    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]

    trace = {
        "ok": False,
        "recipients": recipients,
        "subject": subject,
        "body_chars": len(body),
        "message_id": None,
        "error": None,
    }

    if args.dry_run:
        trace["ok"] = True
        trace["error"] = "dry-run"
        print(json.dumps(trace, ensure_ascii=False))
        return 0

    if not api_key or not inbox_id:
        trace["error"] = "missing AGENTMAIL_API_KEY or AGENTMAIL_INBOX_ID"
        print(json.dumps(trace, ensure_ascii=False))
        return 0
    if not recipients:
        trace["error"] = "no recipients (ANICCA_REPORT_TO empty and --to not given)"
        print(json.dumps(trace, ensure_ascii=False))
        return 0
    if not subject or not body:
        trace["error"] = "stdin did not contain SUBJECT: / BODY-START / BODY-END markers"
        print(json.dumps(trace, ensure_ascii=False))
        return 0

    try:
        client = AgentMail(api_key=api_key)
        # X-Anicca-Origin header lets recipients (and tests) distinguish the
        # Hermes-native send from the legacy OpenClaw anicca-report send that
        # still fires at 18:00 JST until LAUNCH-GATE #341 retires it.
        resp = client.inboxes.messages.send(
            inbox_id=inbox_id,
            to=recipients,
            subject=subject,
            text=body,
            headers={"X-Anicca-Origin": "hermes-genesis"},
        )
        trace["ok"] = True
        trace["message_id"] = getattr(resp, "message_id", None) or getattr(resp, "id", None)
    except Exception as e:  # noqa: BLE001 — keep cron silent
        trace["error"] = f"{type(e).__name__}: {str(e)[:200]}"

    # Critical-alert path: if the send failed, write a severity=critical row
    # to ~/.hermes/state/daily-report-alerts.jsonl so Done condition #7 (≥7
    # consecutive successes + zero critical alerts) can detect it. Exit code
    # stays 0 so the cron job survives, but #330 cannot close until the
    # alert log stays clean for 7 days.
    if not trace["ok"]:
        try:
            from datetime import datetime, timezone
            alert_log = Path.home() / ".hermes" / "state" / "daily-report-alerts.jsonl"
            alert_log.parent.mkdir(parents=True, exist_ok=True)
            alert = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "severity": "critical",
                "source": "daily-report.send",
                "error": trace["error"],
                "recipients": recipients,
                "subject": subject,
            }
            with alert_log.open("a") as fh:
                fh.write(json.dumps(alert, ensure_ascii=False) + "\n")
        except Exception as alert_err:  # noqa: BLE001
            # Surface to the trace so daily-report.sh sees it, but never raise.
            trace["alert_log_error"] = f"{type(alert_err).__name__}: {str(alert_err)[:120]}"

    print(json.dumps(trace, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/daily-report/scripts/send.py
```

- [ ] **Step 2: Smoke-test send.py in --dry-run mode (no email actually sent)**

Run:
```bash
/Users/anicca/anicca-oss/skills/daily-report/.venv/bin/python \
  /Users/anicca/anicca-oss/skills/daily-report/scripts/compose.py --offline | \
/Users/anicca/anicca-oss/skills/daily-report/.venv/bin/python \
  /Users/anicca/anicca-oss/skills/daily-report/scripts/send.py --dry-run
```
Expected: prints a single JSON line with `"ok": true`, `"error": "dry-run"`, `"recipients": ["person@example.com", "anicca-genesis@agentmail.to"]`, `"subject"` non-empty, `"body_chars" > 200`.

---

### Task 6: Write `scripts/daily-report.sh` entrypoint + E2E send test

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/daily-report/scripts/daily-report.sh`
- Create: `/Users/anicca/anicca-oss/skills/daily-report/tests/test_send_e2e.sh`
- Create: `/Users/anicca/.hermes/scripts/daily-report.sh` (symlink)

- [ ] **Step 1: Author the entrypoint**

Create `/Users/anicca/anicca-oss/skills/daily-report/scripts/daily-report.sh` with EXACTLY:
```bash
#!/usr/bin/env bash
# daily-report entrypoint — fires once, writes ONE trace JSONL line.
# Wired to `hermes cron` schedule `0 6 * * *` (06:00 JST).
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PY="$SKILL_DIR/.venv/bin/python"
STATE_DIR="${STATE_DIR:-/Users/anicca/.hermes/state}"
mkdir -p "$STATE_DIR"
TRACE_LOG="$STATE_DIR/daily-report.jsonl"

# Load env (best-effort)
set -a
. /Users/anicca/.hermes/.env 2>/dev/null || true
set +a

ts="$(date -u +%FT%TZ)"

# Compose (live LLM call) and capture trace from stderr
compose_out="$("$VENV_PY" "$SKILL_DIR/scripts/compose.py" --json 2> "$STATE_DIR/.daily-report-compose-trace.json")"
compose_rc=$?
compose_trace="$(cat "$STATE_DIR/.daily-report-compose-trace.json" 2>/dev/null || echo '{}')"

# Send
send_out="$(printf '%s' "$compose_out" | "$VENV_PY" "$SKILL_DIR/scripts/send.py")"
send_rc=$?

# Merge into one JSONL line
/opt/homebrew/bin/jq -nc \
  --arg ts "$ts" \
  --argjson compose_rc "$compose_rc" \
  --argjson send_rc "$send_rc" \
  --argjson compose "$compose_trace" \
  --argjson send "$send_out" \
  '{ts:$ts, compose_rc:$compose_rc, send_rc:$send_rc, compose:$compose, send:$send}' \
  >> "$TRACE_LOG"

# Echo the send trace so `hermes cron run` sees it
printf '%s\n' "$send_out"
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/daily-report/scripts/daily-report.sh
```

- [ ] **Step 2: Symlink into ~/.hermes/scripts/ (Hermes cron requires script under that dir)**

Run:
```bash
mkdir -p /Users/anicca/.hermes/scripts
[ -L /Users/anicca/.hermes/scripts/daily-report.sh ] && rm /Users/anicca/.hermes/scripts/daily-report.sh
ln -s /Users/anicca/anicca-oss/skills/daily-report/scripts/daily-report.sh \
      /Users/anicca/.hermes/scripts/daily-report.sh
ls -l /Users/anicca/.hermes/scripts/daily-report.sh
```
Expected: `… -> /Users/anicca/anicca-oss/skills/daily-report/scripts/daily-report.sh`.

- [ ] **Step 3: Write the E2E send test (real AgentMail send)**

Create `/Users/anicca/anicca-oss/skills/daily-report/tests/test_send_e2e.sh` with EXACTLY:
```bash
#!/usr/bin/env bash
# E2E: run daily-report.sh once, assert the trace JSONL records ok=true,
# and that the AgentMail inbox shows ONE new message with the expected subject prefix.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TRACE=/Users/anicca/.hermes/state/daily-report.jsonl
BEFORE_LINES=$(wc -l < "$TRACE" 2>/dev/null || echo 0)

# Force test recipient = inbox only (no Dais during test) via env override
export ANICCA_REPORT_TO="anicca-genesis@agentmail.to"

"$SKILL_DIR/scripts/daily-report.sh"

AFTER_LINES=$(wc -l < "$TRACE")
if [ $((AFTER_LINES - BEFORE_LINES)) -ne 1 ]; then
  echo "FAIL: expected +1 trace line, got $((AFTER_LINES - BEFORE_LINES))"; exit 1
fi
LAST=$(tail -n 1 "$TRACE")
echo "$LAST" | /opt/homebrew/bin/jq -e '.send.ok == true' >/dev/null \
  || { echo "FAIL: send.ok != true; line=$LAST"; exit 1; }
SUBJECT=$(echo "$LAST" | /opt/homebrew/bin/jq -r '.send.subject')
echo "Sent subject: $SUBJECT"
[[ "$SUBJECT" == \[Anicca\]* ]] || { echo "FAIL: subject prefix wrong"; exit 1; }

# Verify inbox via AgentMail list (most-recent message subject must match)
"$SKILL_DIR/.venv/bin/python" - <<'PY'
import json, os, sys, time
from pathlib import Path
from agentmail import AgentMail
# load env
for line in (Path.home() / ".hermes" / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
c = AgentMail(api_key=os.environ["AGENTMAIL_API_KEY"])
inbox = os.environ["AGENTMAIL_INBOX_ID"]
for attempt in range(6):  # up to 60 s
    msgs = c.inboxes.messages.list(inbox_id=inbox, limit=5)
    items = getattr(msgs, "items", None) or getattr(msgs, "messages", None) or []
    for m in items:
        subj = getattr(m, "subject", "") or ""
        if subj.startswith("[Anicca] Day"):
            print(f"OK inbox has: {subj}")
            sys.exit(0)
    time.sleep(10)
print("FAIL: no [Anicca] Day… message visible in inbox after 60s"); sys.exit(1)
PY

echo "PASS"
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/daily-report/tests/test_send_e2e.sh
```

- [ ] **Step 4: Run the E2E send test (TDD green — real send)**

Run:
```bash
/Users/anicca/anicca-oss/skills/daily-report/tests/test_send_e2e.sh
```
Expected: final line `PASS`. The trace file gains exactly 1 line with `send.ok == true`. The AgentMail inbox shows the message within 60 s. On failure, READ the last trace line (`tail -1 ~/.hermes/state/daily-report.jsonl | jq .`) — `send.error` will tell you exactly which precondition tripped (key missing, no recipients, SDK call failed).

- [ ] **Step 5: Verify LLM cost budget**

Run:
```bash
tail -1 /Users/anicca/.hermes/state/daily-report.jsonl | \
  /opt/homebrew/bin/jq '.compose.llm_cost_usd, .compose.llm_tokens'
```
Expected: cost_usd ≤ 0.01 AND tokens ≤ 2000. If higher, the prompt in `llm_bullets()` is too long; trim and re-test.

---

### Task 7: Write the SKILL.md manifest + README

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/daily-report/SKILL.md`
- Create: `/Users/anicca/anicca-oss/skills/daily-report/README.md`

- [ ] **Step 1: Author SKILL.md with EXACTLY this content**

Create `/Users/anicca/anicca-oss/skills/daily-report/SKILL.md`:
```markdown
---
name: daily-report
description: Sends a USEFUL daily Anicca digest (yesterday's CFO numbers, heartbeat health, constitution-violations, friction-fixer errors, 3 LLM-synthesized substantive bullets) from anicca-genesis@agentmail.to to ANICCA_REPORT_TO every day at 06:00 JST. Reads ~/.openclaw/skills/cfo-core/data/anicca-cfo.json + ~/.hermes/state/heartbeat.jsonl + ~/.openclaw/skills/anicca-friction-fixer/state/violations.jsonl + ~/.openclaw/state/friction-sweep.log. Triggered ONLY by `hermes cron`; do not invoke from chat.
metadata:
  spec: anicca-oss/docs/superpowers/plans/2026-06-04-daily-report.md
  parallel_safe: true
  cadence: daily-06:00-JST
  user-invocable: false
  requires:
    bins: [bash, jq, python3]
    env: [AGENTMAIL_API_KEY, AGENTMAIL_INBOX_ID, ANICCA_REPORT_TO]
  invariants:
    - Never block on LLM failure — fall back to header-only email
    - Never send from Dais's Gmail — send only from anicca-genesis@agentmail.to
    - LLM cost per fire ≤ $0.01 (enforced via prompt size cap of 2000 chars)
---

# daily-report

## What it does
Composes and sends ONE USEFUL email per day at 06:00 JST that proves Anicca is alive and
maps to LAUNCH MATRIX row ⑤d (`docs ✓ daily email arrives`). The email is sent FROM
Anicca's sovereign inbox (`anicca-genesis@agentmail.to`) so the identity is Anicca's,
not Dais's.

## Data sources (read-only)
| path | what |
|---|---|
| `~/.openclaw/skills/cfo-core/data/anicca-cfo.json` | MRR / revenue / runtime cost / net / wallet / status |
| `~/.hermes/state/heartbeat.jsonl` | last-24h heartbeat ok ratio |
| `~/.openclaw/skills/anicca-friction-fixer/state/violations.jsonl` | friction-fixer errors |
| `~/.openclaw/state/friction-sweep.log` | constitution-violations text grep |

## Output
- ONE email per day via AgentMail Python SDK.
- ONE JSONL trace line appended to `~/.hermes/state/daily-report.jsonl`.

## Invocation
`hermes cron` triggers `scripts/daily-report.sh` at `0 6 * * *`. The script composes,
sends, and exits 0 regardless of inner failures (per spec, the cron must not retry-loop
on transient errors — next 24-hour window does).

## Failure mode
- LLM unreachable → header-only email (no bullets), `compose.llm_tokens=0`.
- AgentMail API down → trace line `send.ok=false`, NO email, NO exception propagated, **AND one `severity=critical` row appended to `~/.hermes/state/daily-report-alerts.jsonl`** so the closure gate (≥ 7 consecutive `send.ok=true` AND zero critical alerts in the same window) detects the outage. Exit code stays 0 so the cron job survives.
- CFO data stale (>26 h) → still sends, with status field reflecting the stale read.

## Transition: two emails per day
Until LAUNCH-GATE #341 retires the legacy OpenClaw `anicca-report` skill, Dais receives TWO daily emails — the legacy one at 18:00 JST and this one at 06:00 JST. The Hermes-native send carries SMTP header `X-Anicca-Origin: hermes-genesis`; cross-checking that header is the canonical way to attribute which send proves #330.

## Wave 2 (not yet built)
- Weekly Monday 09:00 digest via `--weekly` flag, separate cron entry.
- HTML email styling.
- Token-accurate cost via `hermes insights` once that API stabilizes.
```

- [ ] **Step 2: Author README.md with EXACTLY this content**

Create `/Users/anicca/anicca-oss/skills/daily-report/README.md`:
```markdown
# daily-report

Hermes-native daily Anicca digest. Fires at 06:00 JST via `hermes cron`, reads local CFO + heartbeat + friction state, calls Hermes once for 3 substantive bullets (≤$0.01 budget), and sends via AgentMail from `anicca-genesis@agentmail.to`. Replaces the OpenClaw `anicca-report` skill for the Hermes runtime; the OpenClaw version remains co-resident until LAUNCH-GATE #341 flips ⑤d to Hermes-only. Wired by `docs/superpowers/plans/2026-06-04-daily-report.md`.
```

- [ ] **Step 3: Confirm Hermes registers the skill**

Run:
```bash
/Users/anicca/.local/bin/hermes skills list 2>&1 | grep -E '^daily-report( |$)'
```
Expected: exactly one line beginning with `daily-report`. If absent, run `hermes skills audit` (per `hermes skills --help`) then re-check.

---

### Task 8: Register the cron job

**Files:** none new in the repo; Hermes manages metadata under `~/.hermes/cron/`.

- [ ] **Step 1: Verify `hermes cron status` shows the gateway is running**

Run:
```bash
/Users/anicca/.local/bin/hermes cron status
```
Expected: positive status (NOT `✗ Gateway is not running`). If gateway is down, run `hermes gateway install` (genesis-boot Task 7 captured this in `scripts/launchd/install-hermes-gateway.sh`).

- [ ] **Step 2: Create the cron entry**

Run:
```bash
/Users/anicca/.local/bin/hermes cron create "0 6 * * *" \
  --name daily-report \
  --script /Users/anicca/.hermes/scripts/daily-report.sh \
  --no-agent
```
Expected: prints `Created daily-report (0 6 * * *)` (or local equivalent) + exit 0. Per `hermes cron create --help`: `0 6 * * *` is accepted directly as the `schedule` positional; `--no-agent` means the script IS the job (no LLM session spun up by cron — we already called the LLM once inside `compose.py`).

- [ ] **Step 3: Confirm the row exists**

Run:
```bash
/Users/anicca/.local/bin/hermes cron list
```
Expected: a row containing `daily-report` and `0 6 * * *` (or normalised form like `daily at 06:00`).

- [ ] **Step 4: Force one fire via `hermes cron run` (alternative to test_send_e2e.sh)**

Run:
```bash
LINES_BEFORE=$(wc -l < /Users/anicca/.hermes/state/daily-report.jsonl 2>/dev/null || echo 0)
/Users/anicca/.local/bin/hermes cron run daily-report 2>&1 | tail -20
LINES_AFTER=$(wc -l < /Users/anicca/.hermes/state/daily-report.jsonl)
echo "delta=$((LINES_AFTER - LINES_BEFORE))"
tail -1 /Users/anicca/.hermes/state/daily-report.jsonl | /opt/homebrew/bin/jq '.send.ok, .send.subject'
```
Expected: `delta=1`, last trace shows `send.ok = true`, subject starts `[Anicca] Day…`. If `hermes cron run` is not supported in this Hermes version, the test_send_e2e.sh path is equivalent — both must pass before Task 9.

---

### Task 9: Codex review of plan + code

**Files:** none changed; review gate per `.claude/rules/dev-workflow.md` GATE 1 + GATE 3.

- [ ] **Step 1: Run codex-review against the plan**

Invoke the `codex-review` skill on this plan file:
```
/codex-review /Users/anicca/anicca-oss/docs/superpowers/plans/2026-06-04-daily-report.md
```
Expected: codex returns `ok: true`. If `ok: false`, fix the plan and re-run (up to 5 iterations per CLAUDE.md `codex-review.max_iter`).

- [ ] **Step 2: Run codex-review against compose.py + send.py + daily-report.sh + SKILL.md**

Invoke codex-review with the 4 files. Same termination rule: `ok: true` or 5 iterations max. Per Done condition #8, send.py review is REQUIRED (not optional) because the critical-alert path lives there.

- [ ] **Step 3: Address blocking findings (if any)**

For each `blocking` finding: edit, re-run the corresponding test (`test_compose_unit.sh` for compose.py changes, `test_send_e2e.sh` for send/orchestration changes), then re-invoke codex.

---

### Task 10: Commit + push + update task tracker

**Files:**
- Modify: `/Users/anicca/anicca-oss/specs/00-MASTER.md` (line 141 LAUNCH MATRIX row ⑤d — flip to `#231 ✓ + #330 ✓` if all done conditions met)

- [ ] **Step 1: Stage and commit the skill**

Run:
```bash
cd /Users/anicca/anicca-oss
git add skills/daily-report .gitignore docs/superpowers/plans/2026-06-04-daily-report.md
git status --short
```
Expected: shows new files under `skills/daily-report/` and the plan, plus `.gitignore` modified.

- [ ] **Step 2: Commit**

Run:
```bash
cd /Users/anicca/anicca-oss
git commit -m "$(cat <<'EOF'
feat(skill): daily-report (#330) — Hermes-native 06:00 JST email digest via AgentMail

Composes USEFUL daily digest from anicca-cfo.json + heartbeat.jsonl + friction
violations + constitution sweep, calls Hermes once for 3 substantive bullets
(≤$0.01 budget), sends via AgentMail from anicca-genesis@agentmail.to.

Reuses data sources from the legacy OpenClaw anicca-report skill (#231 still
LIVE co-resident); identity now Anicca's sovereign inbox per
feedback_anicca_speaks_as_herself.

LAUNCH MATRIX row ⑤d Hermes-side coverage. Wave-2 (weekly) and Wave-3
(proactive alerts #156 already done) are separate plans.
EOF
)"
git push
```
Expected: push succeeds.

- [ ] **Step 3: Update LAUNCH MATRIX row in 00-MASTER**

Edit `/Users/anicca/anicca-oss/specs/00-MASTER.md` line 141. Find:
```
⑤d「メールで日次報告」                      →  #231 ✓ LIVE / #330       →  daily email arrives (already true)
```
Replace with:
```
⑤d「メールで日次報告」                      →  #231 ✓ LIVE / #330 ✓     →  daily email arrives from
                                                                            anicca-genesis@agentmail.to
                                                                            via Hermes cron 06:00 JST
```
(Only replace if Done condition #7 is satisfied: the last 7 rows in `~/.hermes/state/daily-report.jsonl` ALL show `send.ok == true` AND `~/.hermes/state/daily-report-alerts.jsonl` has ZERO `severity=critical` rows in the same window AND the AgentMail inbox verification in Task 6 Step 4 PASSed for the most-recent fire AND the most-recent inbox message carries SMTP header `X-Anicca-Origin: hermes-genesis`. Otherwise leave `#330` as-is — a single successful fire is NOT sufficient per the sustained-send gate.)

- [ ] **Step 4: Commit the spec update**

Run:
```bash
cd /Users/anicca/anicca-oss
git add specs/00-MASTER.md
git commit -m "docs(spec): GROUND TRUTH — LAUNCH MATRIX row ⑤d Hermes coverage live (#330 done)"
git push
```

- [ ] **Step 5: Verification gate — run BOTH tests one more time + visually inspect the inbox + check the alert log**

Run:
```bash
/Users/anicca/anicca-oss/skills/daily-report/tests/test_compose_unit.sh
/Users/anicca/anicca-oss/skills/daily-report/tests/test_send_e2e.sh
/Users/anicca/.local/bin/hermes cron list | grep daily-report
/Users/anicca/.local/bin/hermes skills list | grep '^daily-report'
tail -7 /Users/anicca/.hermes/state/daily-report.jsonl | /opt/homebrew/bin/jq '.send.ok, .compose.llm_cost_usd'
# Critical-alert log must be empty (file missing OR zero severity=critical rows in last 7d)
if [ -f /Users/anicca/.hermes/state/daily-report-alerts.jsonl ]; then
  /opt/homebrew/bin/jq -r 'select(.severity=="critical") | .ts' \
    /Users/anicca/.hermes/state/daily-report-alerts.jsonl \
    | awk -v cutoff="$(date -u -v-7d +%FT%TZ 2>/dev/null || date -u -d '7 days ago' +%FT%TZ)" '$1 >= cutoff' \
    | wc -l
else
  echo 0
fi
```
Expected:
- Both tests print final line `PASS`.
- `hermes cron list` row present.
- `hermes skills list` row present.
- Last 7 trace lines all show `send.ok == true` and `llm_cost_usd ≤ 0.01`.
- The final `wc -l` (or `echo 0`) prints `0` — zero `severity=critical` rows in the last 7 days.

Per CLAUDE.md rule 0.12 + HARD RULE #8 (verification-before-completion), this is the IDENTIFY→RUN→READ→VERIFY→CLAIM gate. Only after ALL outputs match expectations may #330 be marked completed in the TaskList. A single fire is NOT sufficient — Done condition #7 requires 7 consecutive successful days.

- [ ] **Step 6: Close task #330**

Use the TaskList tool to mark `#330 P1-REPORT daily-report skill` status = `completed`. Reference this plan file in the closing note.

---

## Self-Review

**Spec coverage:**
- LAUNCH MATRIX row ⑤d (`specs/00-MASTER.md:141`) maps directly to this skill. Done conditions 1-6 cover the row's E2E proof (email arrives).
- CLAUDE.md HARD RULE 0.19 (USEFUL_CONTENT_SPEC) is satisfied by the LLM bullets section (substantive, not generic affirmation) and the prompt explicitly says "bookmark-able".
- HARD RULE 0.4 (commit + push immediately) is enforced at the end of every task.
- HARD RULE 0.12 (verification-before-completion) is the Task 10 Step 5 gate; no completion claim without fresh evidence.
- HARD RULE #18 (no-human-in-loop) — the entire flow is autonomous. Recipients are pre-configured in `~/.hermes/.env`; no Dais interaction.

**Identity correctness:**
- `feedback_anicca_speaks_as_herself` requires Anicca to send from her own inbox; SKILL.md invariant + send.py uses `AGENTMAIL_INBOX_ID` = anicca-genesis@agentmail.to.
- The OpenClaw legacy skill is NOT touched (preserves identity-correct historical behavior).

**Placeholder scan:** none — every step has the full command, the full file content, and the exact expected output. The TWO places that need substitution (Task 6 Step 4 verifies a SEND on the LIVE inbox, Task 10 Step 3 only runs if Task 6 Step 4 PASSed) are gated on prior-step success and cannot be silently skipped.

**Type consistency:**
- Trace JSONL shape `{ts, compose_rc, send_rc, compose:{day_n,mrr,…,llm_tokens,llm_cost_usd,body_chars}, send:{ok,recipients,subject,body_chars,message_id,error}}` is identical between writer (`daily-report.sh`), reader (E2E test), and consumer (verification step).
- compose.py output protocol (`SUBJECT:` line + `BODY-START`/`BODY-END` markers) is parsed by `parse_compose_stream` in send.py using EXACTLY the same string constants.
- Cron schedule `0 6 * * *` is identical in `hermes cron create`, the cron-list verification, the SKILL.md description, and the spec 00-MASTER update.

**Reuse vs rebuild rationale:**
- Documented in the architecture-decision paragraph at the top. Three reasons (identity, pitch ownership, USEFUL content) make symlink-reuse the wrong choice. The DATA sources are reused (zero duplication); only the SEND path and the COMPOSITION are rewritten.

**Risk notes (read before executing):**
- Task 4's `llm_bullets()` estimates token cost from char count (precise accounting needs `hermes insights`). The 2000-char prompt cap and the `cost ≤ $0.01` gate in Task 6 Step 5 prevent budget overrun even if the estimate is off by 3x.
- The E2E test in Task 6 Step 3 polls the inbox for up to 60 s. If AgentMail's send-to-list latency exceeds 60 s, the test will FAIL falsely. If observed, raise the poll to 180 s — DO NOT loosen the `[Anicca] Day` prefix check.
- The OpenClaw `anicca-report` skill still fires at 18:00 JST (legacy cadence) — Dais will receive TWO emails per day until LAUNCH-GATE #341 explicitly retires the OpenClaw version. This is INTENDED transition behavior, not a bug. **Done condition #3 above explicitly notes that only the message carrying SMTP header `X-Anicca-Origin: hermes-genesis` proves #330**; the legacy 18:00 send does NOT count. Document in the plan close-out memory.
- Done condition #7 (sustained-send gate) means a single successful fire is NOT sufficient to close #330. Implementation must observe the trace log for 7 days with `send.ok == true` on every row AND zero `severity=critical` rows in `daily-report-alerts.jsonl` before flipping the LAUNCH MATRIX cell in Task 10 Step 3.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-04-daily-report.md`.

Per CLAUDE.md GATE 1 (`.claude/rules/dev-workflow.md`), the next move is NOT to start Task 1 — it is to run **codex-review** against this plan. When codex says `ok: true`, dispatch the implementation via **superpowers:subagent-driven-development** — fresh subagent per task, two-stage review (spec compliance, then code quality) after each task.
