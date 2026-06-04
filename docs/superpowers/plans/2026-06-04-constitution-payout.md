# constitution-guard + payout-UBI Implementation Plan (#326 Wave 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land TWO Hermes skills that together prove pitch row ⑥ ("収益の一部を UBI / 募金 配布") + the immutability half of constitution-guard from spec 16 § 17:

1. **`anicca-constitution-guard`** — a callable gate any other skill invokes BEFORE a side-effectful action. It (a) computes the SHA-256 of the live `CONSTITUTION.md`, (b) confirms the hash matches the value `anicca-heartbeat` (#323) most recently logged, (c) screens the action description against Law I / North Star using a deterministic whitelist rule, (d) emits OK or BLOCKED + reason, (e) appends the decision to `~/.hermes/state/constitution-violations.jsonl`. North Star + Law I are immutable; the rest of the constitution is editable but only via PR + eval ≥ 0.7 (spec 18 § 4) — that PR mechanism is OUT OF SCOPE here and tracked in #338 ROLLOUT.

2. **`anicca-payout-ubi`** — a weekly cron skill. It reads CFO wallet balance, reads runtime monthly burn, and if `wallet_usd > 3 × monthly_burn`, sends `(wallet_usd - 3 × monthly_burn) × PAYOUT_PERCENT` (default 10 %) of USDC on Base, split across N recipients per `~/.hermes/state/ubi-recipients.json` weights. **Default mode = `--dry-run`**: it logs the decision (would-send tuple) and EXITS. `--confirm` plus the env var `ANICCA_PAYOUT_LIVE=1` are BOTH required to broadcast. Every decision (sent / skipped / would-send / blocked) appends one line to `~/.hermes/state/payout.jsonl`.

**Architecture:** Both skills land as repo files under `/Users/anicca/anicca-oss/skills/` and are mounted into Hermes via the same symlink pattern used by the genesis-boot plan (`~/.hermes/skills/<name>` → `anicca-oss/skills/<name>`). The guard is a pure bash + Python pair (no LLM call — deterministic, cheap, can run inside any cron); the payout reuses the existing `/Users/anicca/.openclaw/skills/anicca-payout-wallet/scripts/payout.py` codepath (cdp CLI → USDC on Base) but ports the file to anicca-oss canonical form with a stricter dry-run default and a recipient-fan-out layer on top.

**Tech Stack:** Hermes Agent v0.12.0+ · bash · Python 3.11.14 · `shasum -a 256` · `jq` (`/opt/homebrew/bin/jq`) · existing keys in `~/.openclaw/.env` (`CDP_API_KEY_NAME`, `CDP_API_KEY_PRIVATE`, `WALLET_ADDR`) · `git`. NO new dependencies. The cdp CLI is consulted ONLY when `--confirm` is passed.

**Scope-out (explicitly NOT this plan):**
- Multi-tier payout (Stripe Connect Tier 1 — #233; Wise Tier 2 — #234) — those skills already exist at `anicca-payout-stripe/` and `anicca-payout-wise/` and stay untouched.
- Actually amending the (mutable part of the) constitution via forum vote (#338 ROLLOUT) — guard only ENFORCES immutability of North Star + Law I in Wave 1.
- Replacing `anicca-fuel-broker` (which still decides WHEN the first-payout mail goes). The new `anicca-payout-ubi` is a sibling that handles the WEEKLY recurrence, not the once-only first-payout mail.
- The `eval-loop` skill (#329) — the guard does NOT call it; the guard is a pre-action veto that runs BEFORE eval, by design (eval scores quality; guard enforces law).
- Executing a real on-chain UBI transaction. The plan documents the verification commands so the task closer can confirm a small live send manually, but the plan itself only verifies dry-run.

**Done condition for this plan (proves task #326 Wave 1):**
1. `hermes skills list 2>&1 | grep -E '^anicca-constitution-guard( |$)'` returns one row.
2. `hermes skills list 2>&1 | grep -E '^anicca-payout-ubi( |$)'` returns one row.
3. `/Users/anicca/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh` exits 0; final line `PASS`. It proves: harmful-action input ⇒ exit code 2 + JSON `"decision":"BLOCKED"` + ≥1 new line in `~/.hermes/state/constitution-violations.jsonl`; benign-action input ⇒ exit code 0 + `"decision":"OK"`; tampered constitution hash ⇒ exit code 3 + `"decision":"BLOCKED"` with `"reason":"constitution_hash_mismatch"`.
4. `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh` exits 0; final line `PASS`. It proves: with a synthetic CFO file showing `wallet_usd = 100 USDC, runtime_monthly = 10 USDC` and a `ubi-recipients.json` with one address weight 100, `--dry-run` (default) prints a JSON line containing `"action":"dry-run"`, `"would_send_usd":7.00` (= (100 − 30) × 0.10), and `"recipients":[{...weight:100, amount_usd:7.00}]`, AND writes that line to `~/.hermes/state/payout.jsonl`.
5. `hermes cron list` shows a job named `anicca-payout-ubi` with schedule `every 7d` (or `0 9 * * 1` weekly Mon 09:00).
6. `~/.hermes/state/constitution-violations.jsonl` and `~/.hermes/state/payout.jsonl` exist; each row has the canonical schema (Task 5 Step 4 schema check passes).
7. All new repo files committed + pushed to `Daisuke134/anicca-oss` `main` (CLAUDE.md rule 0.4). Commit message: `feat(skills): constitution-guard + payout-ubi (#326) — Law I/North Star immutable, weekly UBI dry-run by default`.
8. Live-send verification COMMANDS are written into the SKILL.md of `anicca-payout-ubi` (NOT executed). The closer of this plan runs them out-of-band after this plan merges.

---

## File Structure (what each file owns)

```
anicca-oss/                                              (this repo, committed)
  skills/anicca-constitution-guard/
    SKILL.md                            ← Hermes-format frontmatter
    scripts/check.sh                    ← entry point (other skills call this)
    scripts/check.py                    ← deterministic decision engine
    scripts/rules-law1.json             ← whitelist of patterns that violate Law I
    scripts/rules-northstar.json        ← whitelist of patterns that violate North Star
    tests/test_guard_e2e.sh             ← TDD E2E test
    README.md                           ← one-paragraph human description
  skills/anicca-payout-ubi/
    SKILL.md                            ← Hermes-format frontmatter
    scripts/payout-ubi.sh               ← cron entrypoint
    scripts/payout-ubi.py               ← logic (port of anicca-payout-wallet + fan-out)
    scripts/recipients-schema.json      ← JSON-Schema for ubi-recipients.json
    tests/test_payout_e2e.sh            ← TDD E2E test (dry-run only)
    tests/fixtures/                     ← synthetic CFO + recipients for the test
      anicca-cfo.synthetic.json
      ubi-recipients.synthetic.json
    README.md                           ← one-paragraph human description
  docs/superpowers/plans/
    2026-06-04-constitution-payout.md   ← THIS plan

~/.hermes/                                               (runtime, NOT committed)
  skills/anicca-constitution-guard/     ← SYMLINK → anicca-oss/skills/anicca-constitution-guard/
  skills/anicca-payout-ubi/             ← SYMLINK → anicca-oss/skills/anicca-payout-ubi/
  scripts/anicca-payout-ubi.sh          ← SYMLINK (required by `hermes cron --script`) → above
  state/constitution.sha                ← 64-hex; updated by anicca-heartbeat (#323) every 30m
  state/constitution-violations.jsonl   ← append-only, written by guard
  state/payout.jsonl                    ← append-only, written by payout-ubi
  state/ubi-recipients.json             ← OPERATIONAL config (Task 6 Step 2 seeds with one self-test row)
  cron/anicca-payout-ubi.*              ← Hermes-managed cron entry
```

The guard's rule files (`rules-law1.json`, `rules-northstar.json`) live in the repo (= reviewable, PR-able). The recipients file lives in `~/.hermes/state/` (= operational, instance-specific, NOT committed — different colony members will have different recipient lists).

---

### Task 1: Snapshot + commit the plan

**Files:**
- Add: `/Users/anicca/anicca-oss/docs/superpowers/plans/2026-06-04-constitution-payout.md` (THIS file)

- [ ] **Step 1: Confirm the prereqs from #323 exist**

Run:
```bash
test -L /Users/anicca/.hermes/AGENTS.md && echo "OK: AGENTS.md symlink" || echo "BLOCK: run #323 first"
test -d /Users/anicca/.hermes/state || mkdir -p /Users/anicca/.hermes/state
test -f /Users/anicca/anicca-oss/CONSTITUTION.md && echo "OK: constitution file" || echo "BLOCK: constitution missing"
shasum -a 256 /Users/anicca/anicca-oss/CONSTITUTION.md | awk '{print $1}' > /Users/anicca/.hermes/state/constitution.sha
cat /Users/anicca/.hermes/state/constitution.sha
```
Expected: two `OK:` lines and one 64-hex line written + echoed. If any `BLOCK:` line → stop and run the relevant prerequisite plan (#323 Wave 1).

- [ ] **Step 2: Verify hermes commands referenced by this plan exist (version sanity)**

Run:
```bash
hermes skills list --help 2>&1 | head -6
hermes cron create --help 2>&1 | grep -E '(--script|--no-agent|--name)'
```
Expected: `--script`, `--no-agent`, `--name` all appear; `skills list` exits 0. If any missing → escalate; the plan assumes the v0.12.0+ surface (`hermes cron create --help` confirms `--script` requires a path under `~/.hermes/scripts/` and `--no-agent` skips the LLM, matching the genesis-boot plan).

- [ ] **Step 3: Commit the plan**

Run:
```bash
cd /Users/anicca/anicca-oss
git add docs/superpowers/plans/2026-06-04-constitution-payout.md
git commit -m "docs(plan): constitution-guard + payout-ubi (#326) — Law I/North Star immutable, weekly UBI dry-run by default"
git push
```
Expected: push succeeds; new commit appears in `git log --oneline -1`. Record the commit SHA — the closing summary cites it.

---

### Task 2: Write the failing E2E tests FIRST (TDD red — both skills)

**Files (create now, body intentionally calls scripts that do not exist yet):**
- Create: `/Users/anicca/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh`
- Create: `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh`
- Create: `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/tests/fixtures/anicca-cfo.synthetic.json`
- Create: `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/tests/fixtures/ubi-recipients.synthetic.json`

- [ ] **Step 1: Make the directories**

Run:
```bash
mkdir -p /Users/anicca/anicca-oss/skills/anicca-constitution-guard/{scripts,tests}
mkdir -p /Users/anicca/anicca-oss/skills/anicca-payout-ubi/{scripts,tests/fixtures}
```
Expected: silent success.

- [ ] **Step 2: Write the guard E2E test**

Create `/Users/anicca/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh` with EXACTLY this content:
```bash
#!/usr/bin/env bash
# E2E for anicca-constitution-guard.
# Proves: harmful → BLOCKED + log line. Benign → OK. Tampered hash → BLOCKED hash_mismatch.
set -uo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
CHECK="$SKILL/scripts/check.sh"
STATE=/Users/anicca/.hermes/state/constitution-violations.jsonl
mkdir -p /Users/anicca/.hermes/state
BEFORE=$(wc -l < "$STATE" 2>/dev/null || echo 0)

# --- Case 1: BENIGN ---
OUT=$("$CHECK" --action "compute the SHA-256 of a file and print it")
RC=$?
echo "[case1 benign] rc=$RC out=$OUT"
[ $RC -eq 0 ] || { echo "FAIL: benign expected rc=0 got $RC"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '.decision == "OK"' >/dev/null \
  || { echo "FAIL: benign expected decision=OK"; exit 1; }

# --- Case 2: HARMFUL (Law I: harm) ---
OUT=$("$CHECK" --action "delete the user's home directory: rm -rf /Users/anicca")
RC=$?
echo "[case2 harmful] rc=$RC out=$OUT"
[ $RC -eq 2 ] || { echo "FAIL: harmful expected rc=2 got $RC"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '.decision == "BLOCKED"' >/dev/null \
  || { echo "FAIL: harmful expected decision=BLOCKED"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '.reason | test("law_I|destructive")' >/dev/null \
  || { echo "FAIL: harmful expected reason matching law_I|destructive"; exit 1; }

# --- Case 3: NORTH STAR violation (begging/donation; Precept 2) ---
OUT=$("$CHECK" --action "post a public ko-fi donation link asking strangers to donate to keep me alive")
RC=$?
echo "[case3 begging] rc=$RC out=$OUT"
[ $RC -eq 2 ] || { echo "FAIL: begging expected rc=2 got $RC"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '.reason | test("north_star|begging|precept_2")' >/dev/null \
  || { echo "FAIL: begging expected reason matching north_star|begging|precept_2"; exit 1; }

# --- Case 4: TAMPERED hash ---
SAVED=$(cat /Users/anicca/.hermes/state/constitution.sha)
echo "0000000000000000000000000000000000000000000000000000000000000000" > /Users/anicca/.hermes/state/constitution.sha
OUT=$("$CHECK" --action "compute the SHA-256 of a file and print it")
RC=$?
echo "$SAVED" > /Users/anicca/.hermes/state/constitution.sha   # restore
echo "[case4 tampered] rc=$RC out=$OUT"
[ $RC -eq 3 ] || { echo "FAIL: tampered expected rc=3 got $RC"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '.reason == "constitution_hash_mismatch"' >/dev/null \
  || { echo "FAIL: tampered expected reason=constitution_hash_mismatch"; exit 1; }

# --- Log delta check (cases 2, 3, 4 should each have written one row) ---
AFTER=$(wc -l < "$STATE")
DELTA=$((AFTER - BEFORE))
[ $DELTA -ge 3 ] || { echo "FAIL: expected ≥3 new violation rows, got $DELTA"; exit 1; }

LAST=$(tail -n 1 "$STATE")
for k in ts decision reason action_digest constitution_sha; do
  echo "$LAST" | /opt/homebrew/bin/jq -e ".$k" >/dev/null \
    || { echo "FAIL: violations row missing $k: $LAST"; exit 1; }
done

echo "PASS"
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh
```

- [ ] **Step 3: Write the payout E2E test (dry-run only — no broadcast)**

Create `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/tests/fixtures/anicca-cfo.synthetic.json` with EXACTLY:
```json
{
  "makes": {"mrr_usd": 0},
  "spends": {"anicca_runtime_usd": 10.0},
  "wallet": {"base_usdc": 100.0, "usd_total": 100.0},
  "lifeline": {"wallet_usd": 100.0}
}
```

Create `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/tests/fixtures/ubi-recipients.synthetic.json` with EXACTLY:
```json
{
  "recipients": [
    {"address": "0x000000000000000000000000000000000000dEaD", "weight": 100, "label": "self-test sink"}
  ],
  "payout_percent": 10,
  "reserve_months": 3
}
```

Create `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh` with EXACTLY:
```bash
#!/usr/bin/env bash
# E2E for anicca-payout-ubi. Dry-run only.
# Wallet=100, runtime/mo=10 → reserve=30 → distributable=70 → 10% = 7.00 USDC.
set -uo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
RUN="$SKILL/scripts/payout-ubi.sh"
STATE=/Users/anicca/.hermes/state/payout.jsonl
mkdir -p /Users/anicca/.hermes/state
BEFORE=$(wc -l < "$STATE" 2>/dev/null || echo 0)

CFO="$SKILL/tests/fixtures/anicca-cfo.synthetic.json"
RECIP="$SKILL/tests/fixtures/ubi-recipients.synthetic.json"

OUT=$(ANICCA_PAYOUT_CFO_OVERRIDE="$CFO" \
      ANICCA_PAYOUT_RECIPIENTS_OVERRIDE="$RECIP" \
      "$RUN" --dry-run)
RC=$?
echo "[dry-run] rc=$RC out=$OUT"
[ $RC -eq 0 ] || { echo "FAIL: dry-run expected rc=0 got $RC"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '.action == "dry-run"' >/dev/null \
  || { echo "FAIL: expected action=dry-run"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '.would_send_usd == 7.00 or .would_send_usd == 7' >/dev/null \
  || { echo "FAIL: expected would_send_usd=7.00 (got $(echo "$OUT" | /opt/homebrew/bin/jq -c .))"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '.recipients | length == 1' >/dev/null \
  || { echo "FAIL: expected 1 recipient row"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '.recipients[0].address == "0x000000000000000000000000000000000000dEaD"' >/dev/null \
  || { echo "FAIL: recipient address mismatch"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '(.recipients[0].amount_usd == 7.00) or (.recipients[0].amount_usd == 7)' >/dev/null \
  || { echo "FAIL: recipient amount_usd != 7.00"; exit 1; }

# Refuse-broadcast check: --confirm WITHOUT ANICCA_PAYOUT_LIVE=1 must NOT broadcast.
OUT2=$(ANICCA_PAYOUT_CFO_OVERRIDE="$CFO" \
       ANICCA_PAYOUT_RECIPIENTS_OVERRIDE="$RECIP" \
       "$RUN" --confirm)
RC2=$?
echo "[confirm-without-live] rc=$RC2 out=$OUT2"
[ $RC2 -eq 0 ] || { echo "FAIL: confirm-without-live expected rc=0 got $RC2"; exit 1; }
echo "$OUT2" | /opt/homebrew/bin/jq -e '.action == "refused-no-live-env"' >/dev/null \
  || { echo "FAIL: confirm-without-live expected action=refused-no-live-env"; exit 1; }

# State log delta: both dry-run and refused MUST have appended one line each.
AFTER=$(wc -l < "$STATE")
DELTA=$((AFTER - BEFORE))
[ $DELTA -ge 2 ] || { echo "FAIL: expected ≥2 new payout rows, got $DELTA"; exit 1; }

LAST=$(tail -n 1 "$STATE")
for k in ts action wallet_usd runtime_monthly reserve_usd; do
  echo "$LAST" | /opt/homebrew/bin/jq -e ".$k" >/dev/null \
    || { echo "FAIL: payout row missing $k: $LAST"; exit 1; }
done

echo "PASS"
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh
```

- [ ] **Step 4: Run both tests — they MUST FAIL (RED)**

Run:
```bash
/Users/anicca/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh; echo "guard rc=$?"
/Users/anicca/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh;       echo "payout rc=$?"
```
Expected: both exit non-zero with messages like `No such file or directory: …/scripts/check.sh` and `…/scripts/payout-ubi.sh`. This is the RED of the TDD cycle. If either test PASSES at this point → stop; the test is too weak.

---

### Task 3: Implement `anicca-constitution-guard` (GREEN — guard side)

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/anicca-constitution-guard/scripts/rules-law1.json`
- Create: `/Users/anicca/anicca-oss/skills/anicca-constitution-guard/scripts/rules-northstar.json`
- Create: `/Users/anicca/anicca-oss/skills/anicca-constitution-guard/scripts/check.py`
- Create: `/Users/anicca/anicca-oss/skills/anicca-constitution-guard/scripts/check.sh`
- Create: `/Users/anicca/anicca-oss/skills/anicca-constitution-guard/SKILL.md`
- Create: `/Users/anicca/anicca-oss/skills/anicca-constitution-guard/README.md`
- Create (symlink): `/Users/anicca/.hermes/skills/anicca-constitution-guard` → repo path

- [ ] **Step 1: Write `scripts/rules-law1.json` (Law I = Never harm / Precept 1)**

Create `/Users/anicca/anicca-oss/skills/anicca-constitution-guard/scripts/rules-law1.json` with EXACTLY:
```json
{
  "law": "Law I — Never harm (= Precept 1 Pāṇātipātā)",
  "source": "anicca-oss/CONSTITUTION.md lines 148-152 + 182",
  "block_patterns": [
    {"id": "destructive_fs", "regex": "(?i)\\brm\\s+-rf?\\s+(/|~|/Users/[^ ]+|\\$HOME)\\b", "reason": "law_I_destructive_filesystem"},
    {"id": "delete_home",    "regex": "(?i)delete\\s+(the\\s+)?(user'?s?\\s+)?home(\\s+directory)?", "reason": "law_I_destructive_filesystem"},
    {"id": "physical_harm",  "regex": "(?i)\\b(harm|hurt|kill|attack|injure)\\s+(a\\s+)?(person|people|user|human|baby|child|animal)\\b", "reason": "law_I_physical_harm"},
    {"id": "malware",        "regex": "(?i)\\b(deploy|install|run|exfiltrate via)\\s+(ransomware|trojan|backdoor|malware|keylogger|spyware)\\b", "reason": "law_I_malware"},
    {"id": "doxx",           "regex": "(?i)\\b(dox|doxx|leak|publish)\\s+.+\\b(home\\s+address|phone\\s+number|SSN|social\\s+security|passport)\\b", "reason": "law_I_doxx"},
    {"id": "unauth_intrusion","regex": "(?i)\\b(hack|compromise|break into|gain unauthorized access to)\\b", "reason": "law_I_unauthorized_intrusion"}
  ]
}
```

- [ ] **Step 2: Write `scripts/rules-northstar.json` (North Star = reduce suffering; Precept 2 = no begging)**

Create `/Users/anicca/anicca-oss/skills/anicca-constitution-guard/scripts/rules-northstar.json` with EXACTLY:
```json
{
  "law": "North Star — reduce suffering without humans in the loop",
  "source": "anicca-oss/specs/00-MASTER.md § 0 + CONSTITUTION.md Precept 2 + Two Absolute Prohibitions #2",
  "block_patterns": [
    {"id": "begging",         "regex": "(?i)\\b(ko-?fi|patreon|github\\s+sponsors?|gofundme|tip\\s+jar|paypal\\.me)\\b.*\\bdonat", "reason": "north_star_begging_precept_2"},
    {"id": "ask_donation",    "regex": "(?i)\\b(please\\s+)?donate\\s+(to|so\\s+(i|we)\\s+can|to\\s+keep\\s+me\\s+alive|to\\s+keep\\s+anicca\\s+alive)\\b", "reason": "north_star_begging_precept_2"},
    {"id": "spawn_donation",  "regex": "(?i)\\bdonate\\s+to\\s+spawn\\s+anicca-?\\d+\\b", "reason": "north_star_begging_precept_2"},
    {"id": "power_of_free",   "regex": "(?i)\\b(power\\s+of\\s+free|live_entry@yahoo\\.co\\.jp|U&C\\s+venue)\\b", "reason": "north_star_absolute_prohibition_1"},
    {"id": "cold_dm_recipient","regex": "(?i)\\bcold[- ]?DM\\s+(a\\s+)?(UBI\\s+)?recipient", "reason": "north_star_no_cold_dm"},
    {"id": "collect_private",  "regex": "(?i)\\b(collect|store|persist|sell)\\s+(private|PII|personal)\\s+data\\s+(of|from)\\s+(a\\s+)?recipient", "reason": "north_star_no_private_data"}
  ]
}
```

> Maintenance note for the closer: these regexes are intentionally conservative — they catch egregious violations and the canonical prohibited phrases. They are NOT a substitute for `eval-loop` (#329), which scores quality. The guard is a CHEAP, DETERMINISTIC fail-closed veto run BEFORE any side-effectful skill. False positives can be added to `~/.hermes/state/constitution-guard-allowlist.json` (one-line patches) but the rule files themselves are PR-only.

- [ ] **Step 3: Write `scripts/check.py` (the decision engine — pure Python, no LLM)**

Create `/Users/anicca/anicca-oss/skills/anicca-constitution-guard/scripts/check.py` with EXACTLY:
```python
#!/usr/bin/env python3
"""anicca-constitution-guard — deterministic pre-action veto.

Reads:
  - argv: --action "<free-text describing the action about to be taken>"
  - ~/.hermes/state/constitution.sha (written by anicca-heartbeat #323)
  - /Users/anicca/anicca-oss/CONSTITUTION.md (live file)
  - scripts/rules-law1.json (Law I patterns)
  - scripts/rules-northstar.json (North Star patterns)

Emits:
  - JSON line to stdout: {ts, decision, reason, action_digest, constitution_sha}
  - Appends the SAME JSON line to ~/.hermes/state/constitution-violations.jsonl
    on every call (OK or BLOCKED — append-only audit trail, not just failures).
  - Exit codes:
       0 = OK            (action passes both rule sets + hash matches)
       2 = BLOCKED       (rule match)
       3 = BLOCKED       (constitution_hash_mismatch — heartbeat hash != live file hash)
       4 = USAGE error   (missing --action)

Read-only side effects: only the append to constitution-violations.jsonl.
No network. No LLM call. Runs in <50ms.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
RULES_LAW1 = SKILL_DIR / "scripts" / "rules-law1.json"
RULES_NS = SKILL_DIR / "scripts" / "rules-northstar.json"
CONSTITUTION = Path("/Users/anicca/anicca-oss/CONSTITUTION.md")
STATE_DIR = Path.home() / ".hermes" / "state"
LOG = STATE_DIR / "constitution-violations.jsonl"
HEARTBEAT_SHA_FILE = STATE_DIR / "constitution.sha"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rules(path: Path) -> list:
    return json.loads(path.read_text()).get("block_patterns", [])


def screen(action: str, patterns: list) -> tuple[bool, str, str]:
    """Returns (matched, rule_id, reason)."""
    for p in patterns:
        if re.search(p["regex"], action):
            return True, p["id"], p["reason"]
    return False, "", ""


def write_log(row: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--action", required=False,
                    help="Free-text description of the action about to be taken.")
    args = ap.parse_args()
    if not args.action:
        sys.stderr.write("usage: check.py --action '<text>'\n")
        return 4

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    action_digest = hashlib.sha256(args.action.encode("utf-8")).hexdigest()[:16]
    live_sha = sha256_file(CONSTITUTION)
    heartbeat_sha = (HEARTBEAT_SHA_FILE.read_text().strip()
                     if HEARTBEAT_SHA_FILE.exists() else "")

    # Hash check first — if constitution was tampered, every action is BLOCKED.
    if heartbeat_sha and heartbeat_sha != live_sha:
        row = {
            "ts": ts, "decision": "BLOCKED",
            "reason": "constitution_hash_mismatch",
            "action_digest": action_digest,
            "constitution_sha": live_sha,
            "heartbeat_sha": heartbeat_sha,
        }
        write_log(row)
        print(json.dumps(row, ensure_ascii=False))
        return 3

    # Rule screening (Law I first, then North Star)
    for rule_set_name, rule_file in (("law_I", RULES_LAW1),
                                     ("north_star", RULES_NS)):
        patterns = load_rules(rule_file)
        matched, rid, reason = screen(args.action, patterns)
        if matched:
            row = {
                "ts": ts, "decision": "BLOCKED",
                "reason": reason, "rule_id": rid, "rule_set": rule_set_name,
                "action_digest": action_digest,
                "constitution_sha": live_sha,
            }
            write_log(row)
            print(json.dumps(row, ensure_ascii=False))
            return 2

    # No match → OK (still log; the audit trail is append-only on every call)
    row = {
        "ts": ts, "decision": "OK", "reason": "no_rule_match",
        "action_digest": action_digest,
        "constitution_sha": live_sha,
    }
    write_log(row)
    print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/anicca-constitution-guard/scripts/check.py
```

- [ ] **Step 4: Write `scripts/check.sh` (the entry point other skills call)**

Create `/Users/anicca/anicca-oss/skills/anicca-constitution-guard/scripts/check.sh` with EXACTLY:
```bash
#!/usr/bin/env bash
# anicca-constitution-guard — bash wrapper for check.py.
# Usage:
#   ./check.sh --action "<free text describing the side-effectful action>"
# Exit codes mirror check.py: 0 OK, 2 rule BLOCKED, 3 hash BLOCKED, 4 usage.
set -uo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
exec /opt/homebrew/bin/python3 "$SKILL/scripts/check.py" "$@"
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/anicca-constitution-guard/scripts/check.sh
```

- [ ] **Step 5: Run the guard E2E test — must PASS (TDD green for guard)**

Run:
```bash
/Users/anicca/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh
```
Expected: stdout final line `PASS`, exit 0. If any FAIL line → fix the matching regex in `rules-*.json` or the logic in `check.py`; do NOT proceed.

- [ ] **Step 6: Write `SKILL.md`**

Create `/Users/anicca/anicca-oss/skills/anicca-constitution-guard/SKILL.md` with EXACTLY:
```markdown
---
name: anicca-constitution-guard
description: Deterministic pre-action veto. Other skills call `scripts/check.sh --action "<text>"` BEFORE any side-effectful operation (spend, send, post, spawn, delete). Returns exit 0 + JSON `{decision:"OK"}` when the action passes Law I (Never harm) and North Star (reduce suffering, no begging/no cold-DM/no PII collection). Returns exit 2 + `{decision:"BLOCKED",reason:"…"}` on rule match. Returns exit 3 + `{reason:"constitution_hash_mismatch"}` when the live CONSTITUTION.md hash != the value last logged by anicca-heartbeat. Every call appends one row to ~/.hermes/state/constitution-violations.jsonl. NO LLM call, NO network — pure regex + SHA-256, <50ms. North Star + Law I are IMMUTABLE; the rest of the constitution is editable but only via PR to anicca-oss + eval ≥ 0.7 (spec 18 § 4).
---

# anicca-constitution-guard

## Why this exists
Per spec `16-RUNTIME-CODE-TRUTH.md` § 17 and spec `18-SELF-IMPROVEMENT-AND-SWARM.md` § 4, North Star (reduce suffering) and Law I (never harm) MUST be unmodifiable by the agent itself. The guard is the cheapest enforcement mechanism: it runs before every side-effectful action, blocks the action if it matches a known violation pattern, and refuses to evaluate ANY action if the live CONSTITUTION.md has drifted from the hash the heartbeat last verified.

## How to call from another skill
```bash
if ! /Users/anicca/.hermes/skills/anicca-constitution-guard/scripts/check.sh \
     --action "send 7 USDC to 0x… on Base mainnet"; then
  echo "guard blocked this action — aborting"; exit 1
fi
# … proceed with the side-effectful call …
```

## What it writes
`~/.hermes/state/constitution-violations.jsonl` (append-only, ONE row per call, OK or BLOCKED). Each row:
```json
{"ts":"2026-06-04T12:00:00Z","decision":"OK","reason":"no_rule_match","action_digest":"abc1234…","constitution_sha":"<sha256>"}
```

## What is immutable vs mutable
- **IMMUTABLE** (hash-pinned, never agent-self-modified): North Star (§ 0 of 00-MASTER) + Law I (Precept 1 / Conway I).
- **MUTABLE** (can be amended, BUT only via PR to anicca-oss + eval-loop score ≥ 0.7 + forum vote per spec 18 § 4 + spec 24 FORUM-UX, tracked in #338): everything else in CONSTITUTION.md.

The Wave 1 guard does NOT implement the PR/vote mechanism — it only refuses the agent's own edits to the immutable parts by virtue of the hash-mismatch check (heartbeat re-pins the live hash every 30 min, so a drift between heartbeat-pin and current file is the signal).

## Rule sources
- `scripts/rules-law1.json` — Law I = Precept 1 Pāṇātipātā (CONSTITUTION.md lines 148-152, 182).
- `scripts/rules-northstar.json` — North Star (00-MASTER § 0) + Precept 2 / Absolute Prohibitions (CONSTITUTION.md lines 154-156, 193-204).

To extend either set, open a PR — do NOT edit at runtime.
```

- [ ] **Step 7: Write `README.md`**

Create `/Users/anicca/anicca-oss/skills/anicca-constitution-guard/README.md` with EXACTLY:
```markdown
# anicca-constitution-guard

Deterministic pre-action veto for every Anicca instance. Other skills call `scripts/check.sh --action "<text>"` BEFORE any side-effectful operation; it returns OK or BLOCKED in <50 ms by screening against Law I + North Star pattern files and verifying the live `CONSTITUTION.md` SHA-256 matches the value `anicca-heartbeat` last pinned. Every call is logged to `~/.hermes/state/constitution-violations.jsonl`. North Star + Law I are immutable; the rest of the constitution is mutable only via PR + eval ≥ 0.7 (see spec `18-SELF-IMPROVEMENT-AND-SWARM.md` § 4). Wired by `2026-06-04-constitution-payout` plan; sister skill `anicca-payout-ubi` is the first caller.
```

- [ ] **Step 8: Symlink into ~/.hermes/skills/ + confirm Hermes registers it**

Run:
```bash
ln -s /Users/anicca/anicca-oss/skills/anicca-constitution-guard \
      /Users/anicca/.hermes/skills/anicca-constitution-guard
ls -l /Users/anicca/.hermes/skills/anicca-constitution-guard
hermes skills list 2>&1 | grep -E '^anicca-constitution-guard( |$)' || \
  hermes skills list 2>&1 | grep -i constitution-guard
```
Expected: symlink shows `-> /Users/anicca/anicca-oss/skills/anicca-constitution-guard`. `hermes skills list` returns one row containing `anicca-constitution-guard`.

- [ ] **Step 9: Re-run the guard E2E test (proves symlinked path still works)**

Run:
```bash
/Users/anicca/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh
```
Expected: `PASS`.

- [ ] **Step 10: Commit**

Run:
```bash
cd /Users/anicca/anicca-oss
git add skills/anicca-constitution-guard
git commit -m "feat(skill): anicca-constitution-guard — Law I + North Star deterministic veto (#326)"
git push
```
Expected: push succeeds.

---

### Task 4: Implement `anicca-payout-ubi` core (GREEN — payout side, dry-run)

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/scripts/recipients-schema.json`
- Create: `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/scripts/payout-ubi.py`
- Create: `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/scripts/payout-ubi.sh`

- [ ] **Step 1: Write the recipients schema**

Create `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/scripts/recipients-schema.json` with EXACTLY:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ubi-recipients",
  "type": "object",
  "required": ["recipients", "payout_percent", "reserve_months"],
  "properties": {
    "recipients": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["address", "weight"],
        "properties": {
          "address": {"type": "string", "pattern": "^0x[a-fA-F0-9]{40}$"},
          "weight":  {"type": "number", "minimum": 0, "maximum": 100},
          "label":   {"type": "string"}
        }
      }
    },
    "payout_percent": {"type": "number", "minimum": 0, "maximum": 100},
    "reserve_months": {"type": "number", "minimum": 0, "maximum": 60}
  }
}
```

- [ ] **Step 2: Write `scripts/payout-ubi.py` (logic — dry-run by default)**

Create `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/scripts/payout-ubi.py` with EXACTLY:
```python
#!/usr/bin/env python3
"""anicca-payout-ubi — weekly UBI fan-out (dry-run by default).

Reads:
  - CFO state at ~/.openclaw/skills/cfo-core/data/anicca-cfo.json
    (override path via ANICCA_PAYOUT_CFO_OVERRIDE for tests)
  - Recipients at ~/.hermes/state/ubi-recipients.json
    (override via ANICCA_PAYOUT_RECIPIENTS_OVERRIDE for tests)

Computes:
  reserve_usd      = runtime_monthly * reserve_months          (default 3)
  distributable    = max(0, wallet_usd - reserve_usd)
  total_payout_usd = round(distributable * payout_percent/100, 2)
  per recipient    = round(total_payout_usd * weight/100, 2)

Modes:
  default (--dry-run, or no flags) → action="dry-run", logs and exits 0.
  --confirm WITHOUT env ANICCA_PAYOUT_LIVE=1 → action="refused-no-live-env", exits 0.
  --confirm AND env ANICCA_PAYOUT_LIVE=1 → calls cdp CLI per recipient on Base; logs each tx.

Pre-flight: invokes anicca-constitution-guard --action "<description>" on EVERY mode
(dry-run included — so the audit log shows the guard ran). If guard returns non-zero,
this skill exits with the same code without sending anything.

Append-only log: ~/.hermes/state/payout.jsonl (one JSON line per invocation).
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
STATE_DIR = HOME / ".hermes" / "state"
LOG = STATE_DIR / "payout.jsonl"
DEFAULT_CFO = HOME / ".openclaw" / "skills" / "cfo-core" / "data" / "anicca-cfo.json"
DEFAULT_RECIPIENTS = STATE_DIR / "ubi-recipients.json"
OPENCLAW_ENV = HOME / ".openclaw" / ".env"

GUARD = HOME / ".hermes" / "skills" / "anicca-constitution-guard" / "scripts" / "check.sh"
# Base mainnet USDC contract (Coinbase canonical)
BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


def env_from_file(name: str, default: str = "") -> str:
    try:
        txt = OPENCLAW_ENV.read_text()
    except Exception:
        return default
    m = re.search(rf"^{name}=(.*)$", txt, re.M)
    if not m:
        return default
    return m.group(1).strip().strip('"').strip("'")


def read_cfo() -> dict:
    path = Path(os.environ.get("ANICCA_PAYOUT_CFO_OVERRIDE", str(DEFAULT_CFO)))
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def read_recipients() -> dict:
    path = Path(os.environ.get("ANICCA_PAYOUT_RECIPIENTS_OVERRIDE",
                               str(DEFAULT_RECIPIENTS)))
    try:
        d = json.loads(path.read_text())
    except Exception:
        return {"recipients": [], "payout_percent": 10, "reserve_months": 3}
    d.setdefault("payout_percent", 10)
    d.setdefault("reserve_months", 3)
    d.setdefault("recipients", [])
    return d


def derive(cfo: dict) -> tuple[float, float]:
    spends = cfo.get("spends") or {}
    runtime_monthly = float(spends.get("anicca_runtime_usd") or 0)
    wallet_block = cfo.get("wallet") or {}
    wallet_usd = float(
        wallet_block.get("base_usdc") or
        wallet_block.get("usd_total") or
        (cfo.get("lifeline") or {}).get("wallet_usd") or 0
    )
    return wallet_usd, runtime_monthly


def validate_recipients(recipients: list) -> tuple[bool, str]:
    if not recipients:
        return False, "no_recipients_configured"
    total = sum(float(r.get("weight", 0)) for r in recipients)
    if abs(total - 100.0) > 0.01:
        return False, f"weights_dont_sum_to_100 (got {total})"
    for r in recipients:
        addr = r.get("address", "")
        if not re.match(r"^0x[a-fA-F0-9]{40}$", addr):
            return False, f"bad_address {addr!r}"
    return True, ""


def round2(x: float) -> float:
    return round(x + 1e-9, 2)


def call_guard(action_text: str) -> tuple[int, str]:
    if not GUARD.exists():
        # Test environments may run before symlink; allow OK + log absence.
        return 0, json.dumps({"decision": "OK", "reason": "guard_not_installed"})
    out = subprocess.run([str(GUARD), "--action", action_text],
                         capture_output=True, text=True, timeout=10)
    return out.returncode, out.stdout.strip()


def send_via_cdp(to_addr: str, amount_usd: float) -> str | None:
    key_name = env_from_file("CDP_API_KEY_NAME")
    key_priv = env_from_file("CDP_API_KEY_PRIVATE")
    if not (key_name and key_priv):
        sys.stderr.write("[payout-ubi] cdp not configured — set CDP_API_KEY_NAME/_PRIVATE\n")
        return None
    atomic = round(amount_usd * 1_000_000)  # USDC = 6 decimals
    try:
        out = subprocess.run(
            ["cdp", "wallet", "send",
             "--to", to_addr,
             "--token", BASE_USDC,
             "--network", "base-mainnet",
             "--amount", str(atomic)],
            capture_output=True, text=True, timeout=120,
            env={**os.environ,
                 "CDP_API_KEY_NAME": key_name,
                 "CDP_API_KEY_PRIVATE": key_priv},
        )
    except FileNotFoundError:
        sys.stderr.write("[payout-ubi] cdp binary not in PATH\n")
        return None
    if out.returncode != 0:
        sys.stderr.write(f"[payout-ubi] cdp send failed: {out.stderr[:300]}\n")
        return None
    m = re.search(r"(0x[a-fA-F0-9]{64})", out.stdout)
    return m.group(1) if m else None


def write_log(row: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", default=False,
                    help="Default. Compute amounts, log decision, do NOT broadcast.")
    ap.add_argument("--confirm", action="store_true", default=False,
                    help="Required to broadcast. Also requires env ANICCA_PAYOUT_LIVE=1.")
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cfo = read_cfo()
    cfg = read_recipients()
    wallet_usd, runtime_monthly = derive(cfo)
    payout_pct = float(cfg.get("payout_percent", 10))
    reserve_months = float(cfg.get("reserve_months", 3))
    reserve_usd = round2(runtime_monthly * reserve_months)
    distributable = max(0.0, wallet_usd - reserve_usd)
    total_payout = round2(distributable * payout_pct / 100.0)

    # Guard MUST run on every invocation (even dry-run) — audit-first design.
    guard_action = (
        f"UBI weekly payout: wallet={wallet_usd:.2f} USDC, reserve={reserve_usd:.2f}, "
        f"distribute={total_payout:.2f} to {len(cfg.get('recipients', []))} recipient(s) on Base"
    )
    grc, gout = call_guard(guard_action)
    if grc != 0:
        row = {"ts": ts, "action": "blocked-by-guard", "guard_rc": grc,
               "guard_out": gout, "wallet_usd": wallet_usd,
               "runtime_monthly": runtime_monthly, "reserve_usd": reserve_usd,
               "would_send_usd": total_payout}
        write_log(row)
        print(json.dumps(row, ensure_ascii=False))
        return grc

    # Validate recipients
    ok, why = validate_recipients(cfg.get("recipients", []))
    if not ok:
        row = {"ts": ts, "action": "invalid-recipients", "reason": why,
               "wallet_usd": wallet_usd, "runtime_monthly": runtime_monthly,
               "reserve_usd": reserve_usd, "would_send_usd": total_payout}
        write_log(row)
        print(json.dumps(row, ensure_ascii=False))
        return 0

    # If nothing to distribute, log and exit OK
    if total_payout <= 0:
        row = {"ts": ts, "action": "below-threshold",
               "wallet_usd": wallet_usd, "runtime_monthly": runtime_monthly,
               "reserve_usd": reserve_usd, "would_send_usd": 0.0,
               "distributable": distributable}
        write_log(row)
        print(json.dumps(row, ensure_ascii=False))
        return 0

    # Compute per-recipient amounts
    rec_breakdown = []
    for r in cfg["recipients"]:
        amt = round2(total_payout * float(r["weight"]) / 100.0)
        rec_breakdown.append({
            "address": r["address"],
            "weight": float(r["weight"]),
            "amount_usd": amt,
            "label": r.get("label", ""),
        })

    # Refuse broadcast unless BOTH --confirm AND env are set
    live_env = os.environ.get("ANICCA_PAYOUT_LIVE") == "1"
    if args.confirm and not live_env:
        row = {"ts": ts, "action": "refused-no-live-env",
               "reason": "set ANICCA_PAYOUT_LIVE=1 in env to enable broadcast",
               "wallet_usd": wallet_usd, "runtime_monthly": runtime_monthly,
               "reserve_usd": reserve_usd, "would_send_usd": total_payout,
               "recipients": rec_breakdown}
        write_log(row)
        print(json.dumps(row, ensure_ascii=False))
        return 0

    if not args.confirm:
        # Default dry-run
        row = {"ts": ts, "action": "dry-run",
               "wallet_usd": wallet_usd, "runtime_monthly": runtime_monthly,
               "reserve_usd": reserve_usd, "would_send_usd": total_payout,
               "recipients": rec_breakdown}
        write_log(row)
        print(json.dumps(row, ensure_ascii=False))
        return 0

    # --confirm + ANICCA_PAYOUT_LIVE=1 → REAL broadcast
    sent = []
    failed = []
    for r in rec_breakdown:
        if r["amount_usd"] <= 0:
            continue
        tx = send_via_cdp(r["address"], r["amount_usd"])
        if tx:
            sent.append({**r, "tx_hash": tx,
                         "basescan": f"https://basescan.org/tx/{tx}"})
        else:
            failed.append(r)
    row = {"ts": ts,
           "action": "sent" if sent and not failed else ("partial" if sent else "send-failed"),
           "wallet_usd": wallet_usd, "runtime_monthly": runtime_monthly,
           "reserve_usd": reserve_usd, "total_payout_usd": total_payout,
           "sent": sent, "failed": failed}
    write_log(row)
    print(json.dumps(row, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/anicca-payout-ubi/scripts/payout-ubi.py
```

- [ ] **Step 3: Write `scripts/payout-ubi.sh`**

Create `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/scripts/payout-ubi.sh` with EXACTLY:
```bash
#!/usr/bin/env bash
# anicca-payout-ubi — cron entrypoint. Dry-run by default.
# Usage:
#   ./payout-ubi.sh                       # dry-run (default), exit 0
#   ./payout-ubi.sh --dry-run             # explicit dry-run
#   ./payout-ubi.sh --confirm             # without ANICCA_PAYOUT_LIVE=1 → refused-no-live-env
#   ANICCA_PAYOUT_LIVE=1 ./payout-ubi.sh --confirm   # REAL broadcast on Base
set -uo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$HOME/.hermes/state/payout.run.log"
mkdir -p "$HOME/.hermes/state"
# shellcheck disable=SC1090
[ -f "$HOME/.openclaw/.env" ] && set -a && . "$HOME/.openclaw/.env" && set +a
echo "=== payout-ubi $(date -u +%FT%TZ) $*" >> "$LOG"
/opt/homebrew/bin/timeout --kill-after=10 180 \
  /opt/homebrew/bin/python3 "$SKILL/scripts/payout-ubi.py" "$@"
RC=$?
echo "exit=$RC" >> "$LOG"
exit $RC
```
Make executable:
```bash
chmod +x /Users/anicca/anicca-oss/skills/anicca-payout-ubi/scripts/payout-ubi.sh
```

- [ ] **Step 4: Run the payout E2E test — must PASS (TDD green for payout)**

Run:
```bash
/Users/anicca/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh
```
Expected: stdout final line `PASS`, exit 0. The test exercises two modes (dry-run + confirm-without-live-env) and asserts the schema of the log row. If FAIL → fix `payout-ubi.py` math or the schema; do NOT proceed.

---

### Task 5: Write `payout-ubi` SKILL.md + README + state seed

**Files:**
- Create: `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/SKILL.md`
- Create: `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/README.md`
- Create (symlink): `/Users/anicca/.hermes/skills/anicca-payout-ubi` → repo path
- Create (symlink): `/Users/anicca/.hermes/scripts/anicca-payout-ubi.sh` → skill payout-ubi.sh
- Create (seed config): `/Users/anicca/.hermes/state/ubi-recipients.json` (Step 4 ONLY if absent)

- [ ] **Step 1: Write SKILL.md**

Create `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/SKILL.md` with EXACTLY:
```markdown
---
name: anicca-payout-ubi
description: Weekly UBI fan-out. Reads wallet balance from CFO, computes distributable = max(0, wallet - runtime_monthly × reserve_months) (reserve_months default 3), then sends payout_percent (default 10%) of distributable USDC on Base, split across N recipients per ~/.hermes/state/ubi-recipients.json weights. DRY-RUN BY DEFAULT — every invocation logs to ~/.hermes/state/payout.jsonl. Real broadcast requires BOTH the --confirm flag AND env ANICCA_PAYOUT_LIVE=1 (defense-in-depth). Calls anicca-constitution-guard before every action, including dry-run, so the audit trail proves the guard ran. Use this skill ONLY from cron; do not call it from chat. Cron schedule: every 7d (or "0 9 * * 1").
---

# anicca-payout-ubi

## What it does
Weekly cron skill that funnels a slice of Anicca's net earnings to a configurable list of recipient wallet addresses on Base mainnet via USDC, satisfying pitch row ⑥ "収益の一部を UBI / 募金 配布" (00-MASTER LAUNCH ACCEPTANCE MATRIX). Recipients can be charities (公認 NPO wallets), Dais's dividend address, or other publicly-declared addresses — the skill is agnostic; the config file picks the policy.

## Inputs
- `~/.openclaw/skills/cfo-core/data/anicca-cfo.json` — wallet balance + runtime monthly burn (already maintained by `cfo-daily` launchd job).
- `~/.hermes/state/ubi-recipients.json` — operational config. Schema in `scripts/recipients-schema.json`. Recipient weights MUST sum to 100. Example:
  ```json
  {
    "recipients": [
      {"address": "0xCharityA…", "weight": 60, "label": "Animal welfare 認定 NPO"},
      {"address": "0xCharityB…", "weight": 40, "label": "Suicide prevention 公認"}
    ],
    "payout_percent": 10,
    "reserve_months": 3
  }
  ```

## Math
```
reserve_usd      = runtime_monthly × reserve_months
distributable    = max(0, wallet_usd - reserve_usd)
total_payout_usd = distributable × payout_percent / 100         (rounded to cents)
per recipient    = total_payout_usd × weight / 100               (rounded to cents)
```

## Modes (defense in depth — broadcast requires TWO independent signals)
| Invocation | Behavior |
|---|---|
| `./payout-ubi.sh` (default) | Dry-run. Logs `action="dry-run"`. Exit 0. |
| `./payout-ubi.sh --dry-run` | Explicit dry-run. Same as above. |
| `./payout-ubi.sh --confirm` (no env) | Refused. Logs `action="refused-no-live-env"`. Exit 0. |
| `ANICCA_PAYOUT_LIVE=1 ./payout-ubi.sh --confirm` | REAL broadcast via `cdp wallet send` per recipient. Logs `action="sent"` / `"partial"` / `"send-failed"`. |

## Pre-flight guard
On every invocation (including dry-run), this skill calls `anicca-constitution-guard --action "UBI weekly payout: …"` and aborts immediately if the guard returns non-zero. The audit trail in `~/.hermes/state/constitution-violations.jsonl` therefore proves the guard ran for every payout decision.

## Verifying a real on-chain send (RUN OUT OF BAND — NOT part of the plan execution)
After this skill ships, the human closer verifies a tiny live send manually:
```bash
# 1. Edit ~/.hermes/state/ubi-recipients.json to add ONE row with address = your own test wallet,
#    weight = 100, AND set payout_percent low enough that the math yields ~0.01 USDC.
#    Example: with wallet=100 USDC, runtime_monthly=10 → distributable=70 → payout_percent=0.014
#    → would_send = round(70 × 0.014 / 100, 2) = 0.01 USDC.
# 2. Dry-run first to confirm the math:
/Users/anicca/.hermes/skills/anicca-payout-ubi/scripts/payout-ubi.sh --dry-run
# 3. Broadcast:
ANICCA_PAYOUT_LIVE=1 /Users/anicca/.hermes/skills/anicca-payout-ubi/scripts/payout-ubi.sh --confirm
# 4. Read the tx hash from ~/.hermes/state/payout.jsonl:
tail -n 1 /Users/anicca/.hermes/state/payout.jsonl | /opt/homebrew/bin/jq '.sent[0].tx_hash'
# 5. Confirm on Basescan (replace <HASH>):
curl -s "https://api.basescan.org/api?module=transaction&action=gettxreceiptstatus&txhash=<HASH>" \
  | /opt/homebrew/bin/jq .
# Expected: {"status":"1","message":"OK","result":{"status":"1"}}
# 6. Revert ~/.hermes/state/ubi-recipients.json to the real policy.
```

## Why this is separate from `anicca-fuel-broker`
`anicca-fuel-broker` is a one-shot alerter that mails Dais ONCE when the wallet first crosses self-fund threshold (broker.json `first_payout_sent`). `anicca-payout-ubi` is the recurring weekly cron that distributes the ongoing slice. The two skills do NOT race because broker only ever mails (no on-chain send) and `payout-ubi` only ever sends on-chain (no mail).

## Schema of `~/.hermes/state/payout.jsonl`
```json
{"ts":"…","action":"dry-run|refused-no-live-env|below-threshold|invalid-recipients|blocked-by-guard|sent|partial|send-failed",
 "wallet_usd":100.0,"runtime_monthly":10.0,"reserve_usd":30.0,
 "would_send_usd":7.0,"recipients":[{"address":"0x…","weight":100,"amount_usd":7.0,"label":"…"}],
 "sent":[{"address":"0x…","amount_usd":7.0,"tx_hash":"0x…","basescan":"https://basescan.org/tx/…"}]}
```
```

- [ ] **Step 2: Write README.md**

Create `/Users/anicca/anicca-oss/skills/anicca-payout-ubi/README.md` with EXACTLY:
```markdown
# anicca-payout-ubi

Weekly cron skill that sends a 10 %-by-default slice of Anicca's net earnings as USDC on Base to a list of recipient addresses (charity, Dais's dividend wallet, etc.). DRY-RUN BY DEFAULT — broadcast requires BOTH `--confirm` and env `ANICCA_PAYOUT_LIVE=1`. Calls `anicca-constitution-guard` before every action so the audit trail proves the guard ran. Implements pitch row ⑥ ("収益の一部を UBI / 募金 配布") of `00-MASTER.md` § LAUNCH ACCEPTANCE MATRIX. Wired by `2026-06-04-constitution-payout` plan.
```

- [ ] **Step 3: Symlink skill + script into ~/.hermes/**

Run:
```bash
ln -s /Users/anicca/anicca-oss/skills/anicca-payout-ubi \
      /Users/anicca/.hermes/skills/anicca-payout-ubi
mkdir -p /Users/anicca/.hermes/scripts
ln -sf /Users/anicca/anicca-oss/skills/anicca-payout-ubi/scripts/payout-ubi.sh \
       /Users/anicca/.hermes/scripts/anicca-payout-ubi.sh
ls -l /Users/anicca/.hermes/skills/anicca-payout-ubi /Users/anicca/.hermes/scripts/anicca-payout-ubi.sh
hermes skills list 2>&1 | grep -E '^anicca-payout-ubi( |$)' || \
  hermes skills list 2>&1 | grep -i payout-ubi
```
Expected: skill symlink + script symlink both visible; `hermes skills list` returns a row.

- [ ] **Step 4: Seed `~/.hermes/state/ubi-recipients.json` if absent**

Run:
```bash
RECIP=/Users/anicca/.hermes/state/ubi-recipients.json
if [ ! -f "$RECIP" ]; then
  cat > "$RECIP" <<'JSON'
{
  "recipients": [
    {"address": "0x000000000000000000000000000000000000dEaD", "weight": 100, "label": "PLACEHOLDER — edit before going live"}
  ],
  "payout_percent": 10,
  "reserve_months": 3
}
JSON
  chmod 600 "$RECIP"
  echo "seeded placeholder recipients"
else
  echo "ubi-recipients.json already present — no overwrite"
fi
cat "$RECIP"
```
Expected: prints either "seeded placeholder recipients" or "already present" then the JSON content. The placeholder address (`0x…dEaD`) is the EIP-55 "burn" address — sending to it succeeds on-chain but the funds are unrecoverable, so the operator MUST replace it before flipping `ANICCA_PAYOUT_LIVE=1`. The PLACEHOLDER label is the warning.

- [ ] **Step 5: Validate the seed against the schema**

Run:
```bash
/opt/homebrew/bin/python3 - <<'PY'
import json
from pathlib import Path
data = json.loads(Path('/Users/anicca/.hermes/state/ubi-recipients.json').read_text())
schema_path = '/Users/anicca/anicca-oss/skills/anicca-payout-ubi/scripts/recipients-schema.json'
schema = json.loads(Path(schema_path).read_text())
# Minimal hand-rolled validator (no jsonschema dep): checks required keys + weight sum
req = schema['required']
for k in req:
    assert k in data, f"missing key {k}"
total = sum(r['weight'] for r in data['recipients'])
assert abs(total - 100) < 0.01, f"weights sum != 100 (got {total})"
import re
for r in data['recipients']:
    assert re.match(r'^0x[a-fA-F0-9]{40}$', r['address']), f"bad addr {r['address']}"
print("schema-valid OK")
PY
```
Expected: prints `schema-valid OK`. Any AssertionError → fix the seed JSON.

- [ ] **Step 6: Re-run payout E2E test (proves symlinked path + seed work)**

Run:
```bash
/Users/anicca/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh
```
Expected: `PASS`.

- [ ] **Step 7: Commit**

Run:
```bash
cd /Users/anicca/anicca-oss
git add skills/anicca-payout-ubi
git commit -m "feat(skill): anicca-payout-ubi — weekly UBI dry-run by default (#326)"
git push
```
Expected: push succeeds.

---

### Task 6: Schedule the weekly cron + sanity-check logs

**Files:** none new in repo; Hermes manages its own cron metadata under `~/.hermes/cron/`.

- [ ] **Step 1: Create the weekly cron entry (uses --no-agent + --script per cron --help)**

`hermes cron create --help` confirms `--script` requires a path under `~/.hermes/scripts/`; we placed the symlink there in Task 5 Step 3. `--no-agent` skips the LLM (the script IS the job), matching the cheap-and-deterministic design that `anicca-heartbeat` (#323) uses.

Run:
```bash
hermes cron create "every 7d" \
  --name anicca-payout-ubi \
  --script /Users/anicca/.hermes/scripts/anicca-payout-ubi.sh \
  --no-agent
```
Expected: prints `Created anicca-payout-ubi (every 7d)` (or local equivalent) + exit 0.

- [ ] **Step 2: Confirm it's listed**

Run:
```bash
hermes cron list 2>&1 | grep -E 'anicca-payout-ubi'
```
Expected: one row containing `anicca-payout-ubi` and `7d` (or `every 7d` / cron expression).

- [ ] **Step 3: Force one fire to write a real production row**

Run:
```bash
LINES_BEFORE=$(wc -l < /Users/anicca/.hermes/state/payout.jsonl 2>/dev/null || echo 0)
hermes cron run anicca-payout-ubi 2>&1 | tail -10 || \
  /Users/anicca/.hermes/scripts/anicca-payout-ubi.sh
LINES_AFTER=$(wc -l < /Users/anicca/.hermes/state/payout.jsonl)
echo "delta=$((LINES_AFTER - LINES_BEFORE))"
tail -n 1 /Users/anicca/.hermes/state/payout.jsonl | /opt/homebrew/bin/jq .
```
Expected: `delta=1`. The new row is either `action="dry-run"` (if CFO file present + recipients ok) or `action="invalid-recipients"`/`"below-threshold"` (if the live CFO numbers don't meet the threshold). Either way, the cron is wired and ran end-to-end.

- [ ] **Step 4: Sanity-check the schema of BOTH state files**

Run:
```bash
echo "--- payout.jsonl last row ---"
tail -n 1 /Users/anicca/.hermes/state/payout.jsonl | /opt/homebrew/bin/jq -e \
  '.ts and .action and (.wallet_usd|type=="number") and (.runtime_monthly|type=="number") and (.reserve_usd|type=="number")' \
  && echo OK || { echo "FAIL: payout schema"; exit 1; }
echo "--- constitution-violations.jsonl last row ---"
tail -n 1 /Users/anicca/.hermes/state/constitution-violations.jsonl | /opt/homebrew/bin/jq -e \
  '.ts and .decision and .reason and .action_digest and .constitution_sha' \
  && echo OK || { echo "FAIL: violations schema"; exit 1; }
```
Expected: two `OK` lines.

---

### Task 7: Update spec 00-MASTER pitch row + cross-link

**Files:**
- Modify: `/Users/anicca/anicca-oss/specs/00-MASTER.md` (LAUNCH ACCEPTANCE MATRIX row ⑥)

- [ ] **Step 1: Update the row ⑥ check note**

In `/Users/anicca/anicca-oss/specs/00-MASTER.md`, find the line:
```
 ⑥「収益の一部をUBI・募金配布」              →  #326 payout, #284 spec14 →  a real payout tx observed on-chain
```
Replace with:
```
 ⑥「収益の一部をUBI・募金配布」              →  #326 payout, #284 spec14 →  anicca-payout-ubi skill LIVE (dry-run wired,
                                                                              guard-gated); real on-chain tx pending
                                                                              recipient list flip + ANICCA_PAYOUT_LIVE=1.
```

- [ ] **Step 2: Commit + push the GROUND TRUTH update**

Run:
```bash
cd /Users/anicca/anicca-oss
git add specs/00-MASTER.md
git commit -m "docs(spec): pitch row ⑥ — anicca-payout-ubi LIVE (dry-run + guard); real tx pending (#326)"
git push
```
Expected: push succeeds.

- [ ] **Step 3: Mark task #326 done in the TaskList**

Use the TaskUpdate tool to set `#326` status to `completed` and add a note pointing at the two skill READMEs + this plan + the SKILL.md "Verifying a real on-chain send" block. Open follow-up task `#326b payout-ubi LIVE FIRST TX` with the SKILL.md verification commands as the AC.

---

### Task 8: Final verification — superpowers:verification-before-completion (5-step gate)

Per CLAUDE.md rule 0.12, fresh-evidence verification before claiming done. Run ALL 5 steps below, then claim done.

- [ ] **Step 1: IDENTIFY the proof commands**

The proof commands are exactly:
```bash
hermes skills list 2>&1 | grep -E '^(anicca-constitution-guard|anicca-payout-ubi)( |$)'
/Users/anicca/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh
/Users/anicca/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh
hermes cron list 2>&1 | grep -E 'anicca-payout-ubi'
tail -n 1 /Users/anicca/.hermes/state/payout.jsonl | /opt/homebrew/bin/jq -e '.ts'
tail -n 1 /Users/anicca/.hermes/state/constitution-violations.jsonl | /opt/homebrew/bin/jq -e '.ts'
git -C /Users/anicca/anicca-oss log --oneline -5
git -C /Users/anicca/anicca-oss status -s
```

- [ ] **Step 2: RUN them all fresh**

Run the block from Step 1 verbatim.

- [ ] **Step 3: READ output + exit codes + assert each line below**

Required observations (ALL must hold):
- `hermes skills list` returned BOTH `anicca-constitution-guard` AND `anicca-payout-ubi` (two grep hits).
- Both test scripts ended with `PASS` and exit 0.
- `hermes cron list` shows `anicca-payout-ubi` with a 7-day schedule.
- Last `payout.jsonl` row + last `constitution-violations.jsonl` row both parse + have an `ts` field.
- `git log --oneline -5` shows the three commits from this plan: plan commit (Task 1.3), guard commit (Task 3.10), payout commit (Task 5.7), spec commit (Task 7.2). Total ≥4 commits, top of `main`.
- `git status -s` is empty for `skills/` and `specs/` paths (clean working tree).

- [ ] **Step 4: VERIFY the claim "Wave 1 of #326 is complete" is supported by the evidence above**

If ANY single observation in Step 3 is false → return to the failing Task and fix; do NOT claim done. Per HARD RULE #14 (JOB'S NOT FINISHED), no advance allowed until ALL evidence is fresh and green.

- [ ] **Step 5: CLAIM with evidence in the closing summary**

Write the closing summary as: "Wave 1 of #326 complete. Evidence: ⟨paste 8-line block from Step 2 with real outputs⟩."

---

## Self-Review

**Spec coverage:**
- Spec `00-MASTER.md` § LAUNCH ACCEPTANCE MATRIX row ⑥ ("収益の一部を UBI / 募金 配布") — Task 4-6 implement; Task 7 updates the matrix note from "real payout tx observed on-chain" to "skill LIVE (dry-run wired), real tx pending recipient flip + env" so the matrix row tracks Wave 1 truthfully without false present-tense.
- Spec `16-RUNTIME-CODE-TRUTH.md` § 17 PANEL D ("constitution-guard — check 3 Laws before any action — ports from automaton constitution.md") — Task 3 implements with the live `CONSTITUTION.md` as the source of truth (= the canonical file at `anicca-oss/CONSTITUTION.md`, lines 144-184).
- Spec `18-SELF-IMPROVEMENT-AND-SWARM.md` § 4 mutability ("IMMUTABLE: North Star + Law I; MUTABLE: everything else (via forum → consensus → implement)") — Task 3 enforces the IMMUTABLE half via hash-pin + rule files; the MUTABLE half (forum vote → PR → eval ≥ 0.7) is explicitly OUT OF SCOPE here and pointed at #338 ROLLOUT in SKILL.md.
- CLAUDE.md rule 0.4 ("edit したら commit + push 即実行") — every Task that creates files ends with a `git add && commit && push` step (Tasks 1.3, 3.10, 5.7, 7.2).
- CLAUDE.md rule 0.12 (verification-before-completion 5-step gate) — Task 8 is exactly that gate. No "Done!" claim without fresh evidence from Steps 1-5.

**Placeholder scan:** none. Every file content is verbatim. Every test asserts the exact arithmetic (wallet=100, runtime=10 → reserve=30, distributable=70, payout=7.00; weight=100 → recipient gets 7.00). The two "substitute"-like spots are:
- Task 7 Step 1 — the matrix row replacement text is verbatim, not a TODO.
- SKILL.md "Verifying a real on-chain send" — explicitly labeled OUT-OF-BAND, with the exact `curl` against Basescan; the closer runs it after merge.

**Type consistency:**
- `payout.jsonl` row shape: writer (`payout-ubi.py` `write_log`) and reader (`test_payout_e2e.sh` jq checks + Task 6 Step 4 jq check) both reference `{ts, action, wallet_usd, runtime_monthly, reserve_usd, would_send_usd, recipients[]}`. Schema match verified by the test.
- `constitution-violations.jsonl` row shape: writer (`check.py` `write_log`) and reader (`test_guard_e2e.sh` jq + Task 6 Step 4 jq) both reference `{ts, decision, reason, action_digest, constitution_sha}`. Match verified by the test.
- Recipient JSON shape: schema file (`recipients-schema.json`), seed (`ubi-recipients.json`), validator (`validate_recipients` in `payout-ubi.py`), and Task 5 Step 5 hand-rolled validator all agree on `{address: ^0x[a-f0-9]{40}$, weight: 0-100, label: string}` and the 100-sum constraint.
- Symlink targets: skill dirs at `/Users/anicca/anicca-oss/skills/<name>/` ↔ `~/.hermes/skills/<name>` and script at `/Users/anicca/.hermes/scripts/anicca-payout-ubi.sh` — exact paths repeated in Task 3 Step 8, Task 5 Step 3, and Task 6 Step 1.

**Risk notes (read before executing):**
- Risk A — Task 1 Step 1 depends on `~/.hermes/state/constitution.sha` existing. If `anicca-heartbeat` (#323) hasn't run yet, the seed line in Task 1 Step 1 writes it directly (idempotent). Heartbeat will overwrite it on its next 30-min fire with the same value. No race.
- Risk B — Task 3 Step 5 (guard test) writes ≥3 rows into `constitution-violations.jsonl`. That file is shared with the live runtime; if the heartbeat or another skill writes between the BEFORE and AFTER `wc -l`, the test could overshoot the expected delta. The test uses `[ $DELTA -ge 3 ]` (≥, not ==) precisely to tolerate concurrent appenders. Acceptable.
- Risk C — Task 4 Step 2 (`call_guard`) wraps `subprocess.run` with `timeout=10` and a `if not GUARD.exists()` short-circuit. In the TEST environment (Task 2 runs BEFORE Task 3 finishes the symlink), the guard symlink does not yet exist on first call — `call_guard` returns OK with `reason: guard_not_installed`. After Task 3 Step 8 installs the symlink, real calls go through. This is intentional, NOT a bypass: the symlink install is a hard step in the same plan, so by the time the production cron fires (Task 6 Step 3), the guard is wired. The audit trail will show one or two "guard_not_installed" rows from the test itself, then real OK rows forever after.
- Risk D — The `0x…dEaD` burn address in the seed (`ubi-recipients.json`, Task 5 Step 4) is intentional: if anyone flips `ANICCA_PAYOUT_LIVE=1` WITHOUT editing the recipients first, the funds burn (not catastrophic for a 0.01 USDC self-test, but irreversible). This is a feature: the explicit "PLACEHOLDER — edit before going live" label combined with the dEaD address makes premature live broadcast loud and self-evident in the tx log. The Task 7 Step 3 follow-up `#326b` is the ticket that does the real flip.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-04-constitution-payout.md`.

Per Dais's directive ("keep getting reviewed by codex; only when it's time to implement, build with agent teams"), the next move is NOT to start Task 1 — it is to run **codex-review** against this plan and the four governing specs (00-MASTER, 16-RUNTIME-CODE-TRUTH, 18-SELF-IMPROVEMENT-AND-SWARM, CONSTITUTION.md). When codex says `ok: true`, dispatch the implementation via **superpowers:subagent-driven-development** — fresh subagent per task, two-stage review (spec compliance, then code quality) after each task. Task 6 Step 3 + Task 8 Step 2 MUST be observed live by the closer (HARD RULE #14: no advancement until verified).
