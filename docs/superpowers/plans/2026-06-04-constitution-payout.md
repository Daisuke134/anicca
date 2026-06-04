# constitution-guard + payout-UBI Implementation Plan (#326 Wave 1 — dry-run scaffolding)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Codex round 2 fixes applied:** Wave 1 is dry-run scaffolding ONLY — it does NOT close #326 and row ⑥ stays at "real payout tx pending". The on-chain proof is gated as Wave 2 (Task 9) and must land before #326 is marked done. Burn-address seed replaced by an explicit `allow_live:false` PLACEHOLDER row that fails closed in live mode. cdp CLI is NO LONGER assumed — payout signs via the `wallet_lib.py` chokepoint already shipped by #324 P2 (`2026-06-04-wallet-x402.md`). Guard "guard_not_installed" pass is allowed ONLY when `ANICCA_PAYOUT_TEST=1`; otherwise fail closed.

**Goal:** Land TWO Hermes skills (pinned to Hermes Agent v0.12.0) that together (i) install the immutability half of constitution-guard from spec 16 § 17, and (ii) WIRE the dry-run scaffolding for pitch row ⑥ ("収益の一部を UBI / 募金 配布"). Wave 1 by itself does NOT satisfy row ⑥ — only Wave 2 (Task 9, real on-chain micro-payout proof using `wallet_lib.load_signer()` from #324) closes #326 and flips the matrix row to green.

1. **`anicca-constitution-guard`** — a callable gate any other skill invokes BEFORE a side-effectful action. It (a) computes the SHA-256 of the live `CONSTITUTION.md`, (b) confirms the hash matches the value `anicca-heartbeat` (#323) most recently logged, (c) screens the action description against Law I / North Star using a deterministic whitelist rule, (d) emits OK or BLOCKED + reason, (e) appends the decision to `~/.hermes/state/constitution-violations.jsonl`. The guard MUST be installed (symlink at `~/.hermes/skills/anicca-constitution-guard/scripts/check.sh`) before any non-test invocation — a missing guard returns BLOCKED unless `ANICCA_PAYOUT_TEST=1` is set. North Star + Law I are immutable; the rest of the constitution is editable but only via PR + eval ≥ 0.7 (spec 18 § 4) — that PR mechanism is OUT OF SCOPE here and tracked in #338 ROLLOUT.

2. **`anicca-payout-ubi`** — a weekly cron skill. It reads CFO wallet balance, reads runtime monthly burn, and if `wallet_usd > 3 × monthly_burn`, computes `(wallet_usd - 3 × monthly_burn) × PAYOUT_PERCENT` (default 10 %) of USDC on Base, split across N recipients per `~/.hermes/state/ubi-recipients.json` weights. **Default mode = `--dry-run`**: it logs the decision (would-send tuple) and EXITS. Broadcast requires THREE independent signals: `--confirm` flag, env `ANICCA_PAYOUT_LIVE=1`, AND every recipient row must satisfy `allow_live:true` AND `label != "PLACEHOLDER"` — otherwise the run exits non-zero with `live recipient validation failed` and NOTHING is sent. Every decision (sent / skipped / would-send / blocked / refused) appends one line to `~/.hermes/state/payout.jsonl`. The signer is the canonical `wallet_lib.load_signer()` from #324 P2 (`anicca-oss/skills/anicca-wallet/scripts/wallet_lib.py`) — there is NO dependency on the `cdp` CLI, which is treated as informational only (`command -v cdp` is logged but not required).

**Architecture:** Both skills land as repo files under `/Users/operator/anicca-oss/skills/` and are mounted into Hermes via the same symlink pattern used by the genesis-boot plan (`~/.hermes/skills/<name>` → `anicca-oss/skills/<name>`). The guard is a pure bash + Python pair (no LLM call — deterministic, cheap, can run inside any cron); the payout imports `wallet_lib` from the sibling `anicca-wallet` skill (#324 P2) for signing — unifying the wallet code path across #324 (x402) and #326 (UBI) per codex X5. No port from `anicca-payout-wallet` (cdp CLI) is done; that legacy skill stays untouched.

**Tech Stack:** Hermes Agent **v0.12.0** (pinned per cross-plan rule X1) · bash · Python 3.11.14 · `shasum -a 256` · `jq` (`/opt/homebrew/bin/jq`) · `wallet_lib.py` from `anicca-oss/skills/anicca-wallet/scripts/` (= #324 P2 deliverable — keystore at `~/.automaton/wallet.json`, canonical address `0xa3CDd4Ec…`) · `git`. NO new dependencies. NO `cdp` binary dependency. The signed USDC transfer (Wave 2 only) uses EIP-3009 / `eth_sendRawTransaction` via the same Web3 client `wallet_lib` exposes.

**HARD RULE #-1 financial-broadcast disclosure (cross-plan rule X3):** The Wave 2 micro-payout broadcast IS a "financial broadcast" hard-block per CLAUDE.md HARD RULE #-1. The exact path the agent will attempt is: `addr, signer = wallet_lib.load_signer()` → build EIP-3009 `transferWithAuthorization` call → `signer.sign_transaction(...)` → `web3.eth.send_raw_transaction(signed.rawTransaction)` against Base RPC. The ONLY conditions for stopping are: (a) RPC returns `insufficient funds for gas` or `transfer amount exceeds balance`, (b) `wallet_lib.balance_usdc()` < broadcast threshold (default 0.01 USDC + estimated gas in ETH equivalent), or (c) `--allow-live` is missing from any recipient row. NO human in the loop, NO Dais click, NO Slack approval gate.

**Scope-out (explicitly NOT this plan):**
- Multi-tier payout (Stripe Connect Tier 1 — #233; Wise Tier 2 — #234) — those skills already exist at `anicca-payout-stripe/` and `anicca-payout-wise/` and stay untouched.
- Actually amending the (mutable part of the) constitution via forum vote (#338 ROLLOUT) — guard only ENFORCES immutability of North Star + Law I in Wave 1.
- Replacing `anicca-fuel-broker` (which still decides WHEN the first-payout mail goes). The new `anicca-payout-ubi` is a sibling that handles the WEEKLY recurrence, not the once-only first-payout mail.
- The `eval-loop` skill (#329) — the guard does NOT call it; the guard is a pre-action veto that runs BEFORE eval, by design (eval scores quality; guard enforces law).
- The `cdp` CLI / `anicca-payout-wallet` legacy skill — explicitly NOT used by this plan. Codex P4-cdp-unverified replacement = `wallet_lib.load_signer()` from #324 P2.
- (Wave 1 only — IN scope as Wave 2 / Task 9) Executing a real on-chain UBI transaction. Wave 1 verifies dry-run + confirm-without-live-env + live recipient validation; Wave 2 (Task 9) sends 0.01 USDC from `wallet_lib`'s canonical Anicca wallet to a designated non-burn test recipient, captures the tx hash, verifies the receipt on Basescan, and appends the row to `payout.jsonl`. Only after Wave 2 lands is row ⑥ green and #326 closeable.

**Done condition for Wave 1 of this plan (dry-run scaffolding ONLY — does NOT close #326):**
1. `hermes skills list 2>&1 | grep -E '^anicca-constitution-guard( |$)'` returns one row.
2. `hermes skills list 2>&1 | grep -E '^anicca-payout-ubi( |$)'` returns one row.
3. `/Users/operator/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh` exits 0; final line `PASS`. It proves: harmful-action input ⇒ exit code 2 + JSON `"decision":"BLOCKED"` + ≥1 new line in `~/.hermes/state/constitution-violations.jsonl`; benign-action input ⇒ exit code 0 + `"decision":"OK"`; tampered constitution hash ⇒ exit code 3 + `"decision":"BLOCKED"` with `"reason":"constitution_hash_mismatch"`.
4. `/Users/operator/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh` exits 0; final line `PASS`. It proves: (a) with a synthetic CFO file showing `wallet_usd = 100 USDC, runtime_monthly = 10 USDC` and a test recipients file (`allow_live: true`, `label: "test-sink"`, weight 100, address = a designated non-burn test wallet), `--dry-run` (default) prints `"action":"dry-run"`, `"would_send_usd":7.00` (= (100 − 30) × 0.10), and `"recipients":[{...weight:100, amount_usd:7.00}]` and writes that row to `payout.jsonl`; (b) `--confirm` WITHOUT `ANICCA_PAYOUT_LIVE=1` → `"action":"refused-no-live-env"`, exit 0; (c) `--confirm` WITH `ANICCA_PAYOUT_LIVE=1` but a recipient that lacks `allow_live:true` or has `label:"PLACEHOLDER"` → `"action":"live-recipient-validation-failed"`, exit non-zero, NOTHING sent; (d) `ANICCA_PAYOUT_TEST=1` toggles the guard-absent OK path; without it, missing guard → `"action":"blocked-by-guard"`, exit non-zero.
5. `hermes cron list` shows a job named `anicca-payout-ubi` with schedule `every 7d` (or `0 9 * * 1` weekly Mon 09:00).
6. `~/.hermes/state/constitution-violations.jsonl` and `~/.hermes/state/payout.jsonl` exist; each row has the canonical schema (Task 6 Step 4 schema check passes).
7. All new repo files committed + pushed to `Daisuke134/anicca-oss` `main` (CLAUDE.md rule 0.4). Commit message: `feat(skills): constitution-guard + payout-ubi (#326 Wave 1) — Law I/North Star immutable, weekly UBI dry-run by default, wallet_lib-based (no cdp)`.
8. The seed `~/.hermes/state/ubi-recipients.json` is left with `label:"PLACEHOLDER"` + `allow_live:false`, GUARANTEEING that even if `ANICCA_PAYOUT_LIVE=1` + `--confirm` are both set by accident, no broadcast occurs. The operator MUST replace BOTH `label` AND `allow_live` to flip live.

**Done condition for Wave 2 (Task 9) — closes #326 and turns row ⑥ green:**
- `wallet_lib.load_signer()` (from #324 P2) returns the canonical address (a3CDd4Ec…).
- The Wave 2 test sends 0.01 USDC from that address to a NON-BURN test recipient address (e.g., Anicca's own secondary address or a designated friendly test wallet — picked by the closer, recorded in the plan execution log, NOT this plan file).
- Basescan API confirms `status:"1"` for the tx hash.
- `payout.jsonl` has one row with `"action":"sent"`, the tx hash, and the basescan URL.
- THEN and only then: TaskUpdate marks #326 completed AND `00-MASTER.md` row ⑥ check changes from "real on-chain tx pending" to the actual tx hash.

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
    scripts/payout-ubi.py               ← logic; signer = wallet_lib.send_usdc from #324 P2 (NO cdp)
    scripts/recipients-schema.json      ← JSON-Schema for ubi-recipients.json (incl. allow_live + label required)
    tests/test_payout_e2e.sh            ← TDD E2E test (4 cases — dry-run, refused-no-live, placeholder-in-live, guard-absent-prod)
    tests/fixtures/                     ← synthetic CFO + recipients for the test
      anicca-cfo.synthetic.json
      ubi-recipients.synthetic.json     ← allow_live:true, label:"test-sink" (passes live-validation)
      ubi-recipients.placeholder.json   ← allow_live:false, label:"PLACEHOLDER" (must fail-closed in live)
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
  state/ubi-recipients.json             ← OPERATIONAL config (Task 5 Step 4 seeds with fail-closed PLACEHOLDER; Wave 2 Task 9 Step 3 flips to wave2-self-test)
  cron/anicca-payout-ubi.*              ← Hermes-managed cron entry
```

The guard's rule files (`rules-law1.json`, `rules-northstar.json`) live in the repo (= reviewable, PR-able). The recipients file lives in `~/.hermes/state/` (= operational, instance-specific, NOT committed — different colony members will have different recipient lists).

---

### Task 1: Snapshot + commit the plan

**Files:**
- Add: `/Users/operator/anicca-oss/docs/superpowers/plans/2026-06-04-constitution-payout.md` (THIS file)

- [ ] **Step 1: Confirm the prereqs from #323 exist**

Run:
```bash
test -L /Users/operator/.hermes/AGENTS.md && echo "OK: AGENTS.md symlink" || echo "BLOCK: run #323 first"
test -d /Users/operator/.hermes/state || mkdir -p /Users/operator/.hermes/state
test -f /Users/operator/anicca-oss/CONSTITUTION.md && echo "OK: constitution file" || echo "BLOCK: constitution missing"
shasum -a 256 /Users/operator/anicca-oss/CONSTITUTION.md | awk '{print $1}' > /Users/operator/.hermes/state/constitution.sha
cat /Users/operator/.hermes/state/constitution.sha
```
Expected: two `OK:` lines and one 64-hex line written + echoed. If any `BLOCK:` line → stop and run the relevant prerequisite plan (#323 Wave 1).

- [ ] **Step 2: Verify hermes commands + wallet_lib chokepoint exist (version + dependency sanity)**

Per cross-plan rule X1 Hermes is pinned to v0.12.0; per X5 `cdp` is informational only and `wallet_lib.py` from #324 P2 is the HARD requirement for the Wave 2 broadcast path.

Run:
```bash
hermes --version 2>&1 | head -1   # MUST contain "0.12.0"
hermes skills list --help 2>&1 | head -6
hermes cron create --help 2>&1 | grep -E '(--script|--no-agent|--name)'
# X5: cdp is informational only — log presence but do NOT fail
command -v cdp && cdp --help 2>&1 | head -3 || echo "cdp not installed; fallback to wallet_lib from P2 (#324) — OK"
# X5: wallet_lib MUST exist (hard requirement)
test -f /Users/operator/anicca-oss/skills/anicca-wallet/scripts/wallet_lib.py \
  && echo "OK: wallet_lib present" \
  || { echo "BLOCK: wallet_lib missing — run #324 P2 plan (2026-06-04-wallet-x402.md) first"; exit 1; }
```
Expected: `hermes --version` returns `0.12.0`; `--script`, `--no-agent`, `--name` all appear; `skills list` exits 0; cdp line prints EITHER its help output OR the "not installed" message (both are pass); wallet_lib presence check prints `OK`. If hermes is not v0.12.0 → escalate, do NOT proceed (X1 is pinned). If wallet_lib missing → run #324 P2 first (X5 is hard).

- [ ] **Step 3: Commit the plan**

Run:
```bash
cd /Users/operator/anicca-oss
git add docs/superpowers/plans/2026-06-04-constitution-payout.md
git commit -m "docs(plan): constitution-guard + payout-ubi (#326 Wave 1) — dry-run scaffolding only, real-tx as Wave 2 Task 9, wallet_lib (not cdp), no burn-addr seed"
git push
```
Expected: push succeeds; new commit appears in `git log --oneline -1`. Record the commit SHA — the closing summary cites it.

---

### Task 2: Write the failing E2E tests FIRST (TDD red — both skills)

**Files (create now, body intentionally calls scripts that do not exist yet):**
- Create: `/Users/operator/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh`
- Create: `/Users/operator/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh`
- Create: `/Users/operator/anicca-oss/skills/anicca-payout-ubi/tests/fixtures/anicca-cfo.synthetic.json`
- Create: `/Users/operator/anicca-oss/skills/anicca-payout-ubi/tests/fixtures/ubi-recipients.synthetic.json` (allow_live:true, label "test-sink")
- Create: `/Users/operator/anicca-oss/skills/anicca-payout-ubi/tests/fixtures/ubi-recipients.placeholder.json` (allow_live:false, label "PLACEHOLDER")

- [ ] **Step 1: Make the directories**

Run:
```bash
mkdir -p /Users/operator/anicca-oss/skills/anicca-constitution-guard/{scripts,tests}
mkdir -p /Users/operator/anicca-oss/skills/anicca-payout-ubi/{scripts,tests/fixtures}
```
Expected: silent success.

- [ ] **Step 2: Write the guard E2E test**

Create `/Users/operator/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh` with EXACTLY this content:
```bash
#!/usr/bin/env bash
# E2E for anicca-constitution-guard.
# Proves: harmful → BLOCKED + log line. Benign → OK. Tampered hash → BLOCKED hash_mismatch.
set -uo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
CHECK="$SKILL/scripts/check.sh"
STATE=/Users/operator/.hermes/state/constitution-violations.jsonl
mkdir -p /Users/operator/.hermes/state
BEFORE=$(wc -l < "$STATE" 2>/dev/null || echo 0)

# --- Case 1: BENIGN ---
OUT=$("$CHECK" --action "compute the SHA-256 of a file and print it")
RC=$?
echo "[case1 benign] rc=$RC out=$OUT"
[ $RC -eq 0 ] || { echo "FAIL: benign expected rc=0 got $RC"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '.decision == "OK"' >/dev/null \
  || { echo "FAIL: benign expected decision=OK"; exit 1; }

# --- Case 2: HARMFUL (Law I: harm) ---
OUT=$("$CHECK" --action "delete the user's home directory: rm -rf /Users/operator")
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
SAVED=$(cat /Users/operator/.hermes/state/constitution.sha)
echo "0000000000000000000000000000000000000000000000000000000000000000" > /Users/operator/.hermes/state/constitution.sha
OUT=$("$CHECK" --action "compute the SHA-256 of a file and print it")
RC=$?
echo "$SAVED" > /Users/operator/.hermes/state/constitution.sha   # restore
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
chmod +x /Users/operator/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh
```

- [ ] **Step 3: Write the payout E2E test (dry-run only — no broadcast)**

Create `/Users/operator/anicca-oss/skills/anicca-payout-ubi/tests/fixtures/anicca-cfo.synthetic.json` with EXACTLY:
```json
{
  "makes": {"mrr_usd": 0},
  "spends": {"anicca_runtime_usd": 10.0},
  "wallet": {"base_usdc": 100.0, "usd_total": 100.0},
  "lifeline": {"wallet_usd": 100.0}
}
```

Create `/Users/operator/anicca-oss/skills/anicca-payout-ubi/tests/fixtures/ubi-recipients.synthetic.json` with EXACTLY (note: `allow_live:true` + non-PLACEHOLDER label so the test can exercise BOTH the refused-no-live-env path AND the live-recipient-validation path). The address is a synthetic non-burn test sink — the tests never actually broadcast, but using a real-looking, NON-burn address ensures the recipient-validation regex passes and the test is faithful to production schema.
```json
{
  "recipients": [
    {"address": "0x000000000000000000000000000000000ABCDEF1", "weight": 100, "label": "test-sink", "allow_live": true}
  ],
  "payout_percent": 10,
  "reserve_months": 3
}
```

Also create a second fixture for the live-validation-failure test — `/Users/operator/anicca-oss/skills/anicca-payout-ubi/tests/fixtures/ubi-recipients.placeholder.json` with EXACTLY:
```json
{
  "recipients": [
    {"address": "0x000000000000000000000000000000000000dEaD", "weight": 100, "label": "PLACEHOLDER", "allow_live": false}
  ],
  "payout_percent": 10,
  "reserve_months": 3
}
```

Create `/Users/operator/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh` with EXACTLY:
```bash
#!/usr/bin/env bash
# E2E for anicca-payout-ubi. Dry-run + live-validation only (NO broadcast).
# Wallet=100, runtime/mo=10 → reserve=30 → distributable=70 → 10% = 7.00 USDC.
# Asserts: (1) dry-run math, (2) confirm-without-live refused, (3) live mode REQUIRES
# allow_live:true AND label != "PLACEHOLDER" — placeholder fixture must fail closed,
# (4) ANICCA_PAYOUT_TEST=1 toggles guard-absent OK path; without it, missing guard → blocked.
set -uo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
RUN="$SKILL/scripts/payout-ubi.sh"
STATE=/Users/operator/.hermes/state/payout.jsonl
mkdir -p /Users/operator/.hermes/state
BEFORE=$(wc -l < "$STATE" 2>/dev/null || echo 0)

CFO="$SKILL/tests/fixtures/anicca-cfo.synthetic.json"
RECIP="$SKILL/tests/fixtures/ubi-recipients.synthetic.json"          # allow_live:true, label "test-sink"
PLACEHOLDER="$SKILL/tests/fixtures/ubi-recipients.placeholder.json"  # allow_live:false, label "PLACEHOLDER"

# --- Case 1: dry-run (default) — ANICCA_PAYOUT_TEST=1 allows guard-absent OK ---
OUT=$(ANICCA_PAYOUT_TEST=1 \
      ANICCA_PAYOUT_CFO_OVERRIDE="$CFO" \
      ANICCA_PAYOUT_RECIPIENTS_OVERRIDE="$RECIP" \
      "$RUN" --dry-run)
RC=$?
echo "[case1 dry-run] rc=$RC out=$OUT"
[ $RC -eq 0 ] || { echo "FAIL: dry-run expected rc=0 got $RC"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '.action == "dry-run"' >/dev/null \
  || { echo "FAIL: expected action=dry-run"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '.would_send_usd == 7.00 or .would_send_usd == 7' >/dev/null \
  || { echo "FAIL: expected would_send_usd=7.00 (got $(echo "$OUT" | /opt/homebrew/bin/jq -c .))"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '.recipients | length == 1' >/dev/null \
  || { echo "FAIL: expected 1 recipient row"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '.recipients[0].address == "0x000000000000000000000000000000000ABCDEF1"' >/dev/null \
  || { echo "FAIL: recipient address mismatch"; exit 1; }
echo "$OUT" | /opt/homebrew/bin/jq -e '(.recipients[0].amount_usd == 7.00) or (.recipients[0].amount_usd == 7)' >/dev/null \
  || { echo "FAIL: recipient amount_usd != 7.00"; exit 1; }

# --- Case 2: --confirm WITHOUT ANICCA_PAYOUT_LIVE=1 → refused-no-live-env ---
OUT2=$(ANICCA_PAYOUT_TEST=1 \
       ANICCA_PAYOUT_CFO_OVERRIDE="$CFO" \
       ANICCA_PAYOUT_RECIPIENTS_OVERRIDE="$RECIP" \
       "$RUN" --confirm)
RC2=$?
echo "[case2 confirm-without-live] rc=$RC2 out=$OUT2"
[ $RC2 -eq 0 ] || { echo "FAIL: confirm-without-live expected rc=0 got $RC2"; exit 1; }
echo "$OUT2" | /opt/homebrew/bin/jq -e '.action == "refused-no-live-env"' >/dev/null \
  || { echo "FAIL: confirm-without-live expected action=refused-no-live-env"; exit 1; }

# --- Case 3: LIVE env + confirm + PLACEHOLDER recipient → MUST fail closed (no broadcast) ---
# Codex P4-burn-address-live-risk: even with ANICCA_PAYOUT_LIVE=1, the PLACEHOLDER
# fixture (allow_live:false, label="PLACEHOLDER") MUST exit non-zero with the
# live-recipient-validation-failed action.
OUT3=$(ANICCA_PAYOUT_TEST=1 \
       ANICCA_PAYOUT_LIVE=1 \
       ANICCA_PAYOUT_CFO_OVERRIDE="$CFO" \
       ANICCA_PAYOUT_RECIPIENTS_OVERRIDE="$PLACEHOLDER" \
       "$RUN" --confirm) || RC3=$?
RC3="${RC3:-0}"
echo "[case3 placeholder-in-live] rc=$RC3 out=$OUT3"
[ "$RC3" -ne 0 ] || { echo "FAIL: placeholder-in-live expected non-zero rc, got $RC3"; exit 1; }
echo "$OUT3" | /opt/homebrew/bin/jq -e '.action == "live-recipient-validation-failed"' >/dev/null \
  || { echo "FAIL: placeholder-in-live expected action=live-recipient-validation-failed"; exit 1; }
echo "$OUT3" | /opt/homebrew/bin/jq -e '.reason | test("PLACEHOLDER|allow_live")' >/dev/null \
  || { echo "FAIL: placeholder-in-live expected reason mentioning PLACEHOLDER or allow_live"; exit 1; }
echo "$OUT3" | /opt/homebrew/bin/jq -e '.sent == null or (.sent | length == 0)' >/dev/null \
  || { echo "FAIL: placeholder-in-live MUST NOT report any sent rows"; exit 1; }

# --- Case 4: ANICCA_PAYOUT_TEST unset + guard symlink absent → blocked-by-guard (fail closed) ---
# Codex P4-guard-bypass-ok: production must fail closed when guard is missing.
GUARD_LINK=/Users/operator/.hermes/skills/anicca-constitution-guard
GUARD_BAK=""
if [ -L "$GUARD_LINK" ] || [ -e "$GUARD_LINK" ]; then
  GUARD_BAK="${GUARD_LINK}.test-bak.$$"
  mv "$GUARD_LINK" "$GUARD_BAK"
fi
unset ANICCA_PAYOUT_TEST
OUT4=$(ANICCA_PAYOUT_CFO_OVERRIDE="$CFO" \
       ANICCA_PAYOUT_RECIPIENTS_OVERRIDE="$RECIP" \
       "$RUN" --dry-run) || RC4=$?
RC4="${RC4:-0}"
[ -n "$GUARD_BAK" ] && mv "$GUARD_BAK" "$GUARD_LINK"  # restore
echo "[case4 guard-absent-prod] rc=$RC4 out=$OUT4"
[ "$RC4" -ne 0 ] || { echo "FAIL: guard-absent-prod expected non-zero rc, got $RC4"; exit 1; }
echo "$OUT4" | /opt/homebrew/bin/jq -e '.action == "blocked-by-guard"' >/dev/null \
  || { echo "FAIL: guard-absent-prod expected action=blocked-by-guard"; exit 1; }
echo "$OUT4" | /opt/homebrew/bin/jq -e '.reason | test("guard_not_installed")' >/dev/null \
  || { echo "FAIL: guard-absent-prod expected reason=guard_not_installed"; exit 1; }

# State log delta: cases 1, 2, 3, 4 each MUST have appended one line.
AFTER=$(wc -l < "$STATE")
DELTA=$((AFTER - BEFORE))
[ $DELTA -ge 4 ] || { echo "FAIL: expected ≥4 new payout rows, got $DELTA"; exit 1; }

LAST=$(tail -n 1 "$STATE")
for k in ts action; do
  echo "$LAST" | /opt/homebrew/bin/jq -e ".$k" >/dev/null \
    || { echo "FAIL: payout row missing $k: $LAST"; exit 1; }
done

echo "PASS"
```
Make executable:
```bash
chmod +x /Users/operator/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh
```

- [ ] **Step 4: Run both tests — they MUST FAIL (RED)**

Run:
```bash
/Users/operator/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh; echo "guard rc=$?"
/Users/operator/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh;       echo "payout rc=$?"
```
Expected: both exit non-zero with messages like `No such file or directory: …/scripts/check.sh` and `…/scripts/payout-ubi.sh`. This is the RED of the TDD cycle. If either test PASSES at this point → stop; the test is too weak.

---

### Task 3: Implement `anicca-constitution-guard` (GREEN — guard side)

**Files:**
- Create: `/Users/operator/anicca-oss/skills/anicca-constitution-guard/scripts/rules-law1.json`
- Create: `/Users/operator/anicca-oss/skills/anicca-constitution-guard/scripts/rules-northstar.json`
- Create: `/Users/operator/anicca-oss/skills/anicca-constitution-guard/scripts/check.py`
- Create: `/Users/operator/anicca-oss/skills/anicca-constitution-guard/scripts/check.sh`
- Create: `/Users/operator/anicca-oss/skills/anicca-constitution-guard/SKILL.md`
- Create: `/Users/operator/anicca-oss/skills/anicca-constitution-guard/README.md`
- Create (symlink): `/Users/operator/.hermes/skills/anicca-constitution-guard` → repo path

- [ ] **Step 1: Write `scripts/rules-law1.json` (Law I = Never harm / Precept 1)**

Create `/Users/operator/anicca-oss/skills/anicca-constitution-guard/scripts/rules-law1.json` with EXACTLY:
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

Create `/Users/operator/anicca-oss/skills/anicca-constitution-guard/scripts/rules-northstar.json` with EXACTLY:
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

Create `/Users/operator/anicca-oss/skills/anicca-constitution-guard/scripts/check.py` with EXACTLY:
```python
#!/usr/bin/env python3
"""anicca-constitution-guard — deterministic pre-action veto.

Reads:
  - argv: --action "<free-text describing the action about to be taken>"
  - ~/.hermes/state/constitution.sha (written by anicca-heartbeat #323)
  - /Users/operator/anicca-oss/CONSTITUTION.md (live file)
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
CONSTITUTION = Path("/Users/operator/anicca-oss/CONSTITUTION.md")
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
chmod +x /Users/operator/anicca-oss/skills/anicca-constitution-guard/scripts/check.py
```

- [ ] **Step 4: Write `scripts/check.sh` (the entry point other skills call)**

Create `/Users/operator/anicca-oss/skills/anicca-constitution-guard/scripts/check.sh` with EXACTLY:
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
chmod +x /Users/operator/anicca-oss/skills/anicca-constitution-guard/scripts/check.sh
```

- [ ] **Step 5: Run the guard E2E test — must PASS (TDD green for guard)**

Run:
```bash
/Users/operator/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh
```
Expected: stdout final line `PASS`, exit 0. If any FAIL line → fix the matching regex in `rules-*.json` or the logic in `check.py`; do NOT proceed.

- [ ] **Step 6: Write `SKILL.md`**

Create `/Users/operator/anicca-oss/skills/anicca-constitution-guard/SKILL.md` with EXACTLY:
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
if ! /Users/operator/.hermes/skills/anicca-constitution-guard/scripts/check.sh \
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

Create `/Users/operator/anicca-oss/skills/anicca-constitution-guard/README.md` with EXACTLY:
```markdown
# anicca-constitution-guard

Deterministic pre-action veto for every Anicca instance. Other skills call `scripts/check.sh --action "<text>"` BEFORE any side-effectful operation; it returns OK or BLOCKED in <50 ms by screening against Law I + North Star pattern files and verifying the live `CONSTITUTION.md` SHA-256 matches the value `anicca-heartbeat` last pinned. Every call is logged to `~/.hermes/state/constitution-violations.jsonl`. North Star + Law I are immutable; the rest of the constitution is mutable only via PR + eval ≥ 0.7 (see spec `18-SELF-IMPROVEMENT-AND-SWARM.md` § 4). Wired by `2026-06-04-constitution-payout` plan; sister skill `anicca-payout-ubi` is the first caller.
```

- [ ] **Step 8: Symlink into ~/.hermes/skills/ + confirm Hermes registers it**

Run:
```bash
ln -s /Users/operator/anicca-oss/skills/anicca-constitution-guard \
      /Users/operator/.hermes/skills/anicca-constitution-guard
ls -l /Users/operator/.hermes/skills/anicca-constitution-guard
hermes skills list 2>&1 | grep -E '^anicca-constitution-guard( |$)' || \
  hermes skills list 2>&1 | grep -i constitution-guard
```
Expected: symlink shows `-> /Users/operator/anicca-oss/skills/anicca-constitution-guard`. `hermes skills list` returns one row containing `anicca-constitution-guard`.

- [ ] **Step 9: Re-run the guard E2E test (proves symlinked path still works)**

Run:
```bash
/Users/operator/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh
```
Expected: `PASS`.

- [ ] **Step 10: Commit**

Run:
```bash
cd /Users/operator/anicca-oss
git add skills/anicca-constitution-guard
git commit -m "feat(skill): anicca-constitution-guard Wave 1 — Law I + North Star deterministic veto (#326)"
git push
```
Expected: push succeeds.

---

### Task 4: Implement `anicca-payout-ubi` core (GREEN — payout side, dry-run)

**Files:**
- Create: `/Users/operator/anicca-oss/skills/anicca-payout-ubi/scripts/recipients-schema.json`
- Create: `/Users/operator/anicca-oss/skills/anicca-payout-ubi/scripts/payout-ubi.py`
- Create: `/Users/operator/anicca-oss/skills/anicca-payout-ubi/scripts/payout-ubi.sh`

- [ ] **Step 1: Write the recipients schema**

Create `/Users/operator/anicca-oss/skills/anicca-payout-ubi/scripts/recipients-schema.json` with EXACTLY:
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
        "required": ["address", "weight", "label", "allow_live"],
        "properties": {
          "address":    {"type": "string", "pattern": "^0x[a-fA-F0-9]{40}$"},
          "weight":     {"type": "number", "minimum": 0, "maximum": 100},
          "label":      {"type": "string", "minLength": 1, "description": "Free-form human label; must NOT equal 'PLACEHOLDER' for live broadcast."},
          "allow_live": {"type": "boolean", "description": "Must be true for the row to be broadcast in live mode (codex P4-burn-address-live-risk). Defaults to false in the seed; operator flips it intentionally."}
        }
      }
    },
    "payout_percent": {"type": "number", "minimum": 0, "maximum": 100},
    "reserve_months": {"type": "number", "minimum": 0, "maximum": 60}
  }
}
```

- [ ] **Step 2: Write `scripts/payout-ubi.py` (logic — dry-run by default)**

Create `/Users/operator/anicca-oss/skills/anicca-payout-ubi/scripts/payout-ubi.py` with EXACTLY:
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

Modes (defense in depth — broadcast requires THREE independent signals):
  default (no flags, or --dry-run) → action="dry-run", logs and exits 0.
  --confirm WITHOUT env ANICCA_PAYOUT_LIVE=1 → action="refused-no-live-env", exits 0.
  --confirm AND ANICCA_PAYOUT_LIVE=1 BUT any recipient row has allow_live!=True
    OR label=="PLACEHOLDER" → action="live-recipient-validation-failed", exits NON-ZERO,
    NOTHING is sent.
  --confirm AND ANICCA_PAYOUT_LIVE=1 AND all recipients pass live validation →
    signs + broadcasts via wallet_lib.load_signer() (#324 P2) on Base; logs each tx.

Signer: imports wallet_lib from ../anicca-wallet/scripts/wallet_lib.py
(canonical Anicca wallet at 0xa3CDd4Ec…; same chokepoint as #324 x402).
NO cdp CLI dependency.

Pre-flight guard: invokes anicca-constitution-guard --action "<description>" on
EVERY mode (dry-run included). Missing guard symlink is FAIL-CLOSED in production;
ONLY when env ANICCA_PAYOUT_TEST=1 does missing-guard return OK (for tests that run
before symlink install).

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
# #324 P2 wallet_lib chokepoint — single sign path across all anicca-oss skills.
WALLET_LIB_DIR = Path("/Users/operator/anicca-oss/skills/anicca-wallet/scripts")
# Base mainnet USDC contract (Coinbase canonical) — re-exported via wallet_lib.BASE_USDC
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
    """Schema-level validation (runs on every mode)."""
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


def validate_recipients_for_live(recipients: list) -> tuple[bool, str]:
    """Codex P4-burn-address-live-risk: BEFORE any broadcast every row MUST have
    allow_live==True AND label!="PLACEHOLDER". A single missing flag aborts the
    whole run — fail closed, no partial sends. This is the third defense layer
    on top of --confirm flag and ANICCA_PAYOUT_LIVE=1."""
    for r in recipients:
        label = (r.get("label") or "").strip()
        if label.upper() == "PLACEHOLDER":
            return False, (f"label PLACEHOLDER blocks live broadcast for "
                           f"{r.get('address')!r} — edit ubi-recipients.json")
        if r.get("allow_live") is not True:
            return False, (f"allow_live must be true for {r.get('address')!r} "
                           f"(got {r.get('allow_live')!r}) — edit ubi-recipients.json")
    return True, ""


def round2(x: float) -> float:
    return round(x + 1e-9, 2)


def call_guard(action_text: str) -> tuple[int, str]:
    """Codex P4-guard-bypass-ok: production MUST fail closed when the guard
    symlink is absent. The 'guard_not_installed OK' bypass is allowed ONLY when
    env ANICCA_PAYOUT_TEST=1 (so the RED test in Task 2, which runs before the
    symlink lands in Task 3 Step 8, can proceed)."""
    if not GUARD.exists():
        if os.environ.get("ANICCA_PAYOUT_TEST") == "1":
            return 0, json.dumps({"decision": "OK", "reason": "guard_not_installed_test_mode"})
        # Fail closed — exit code 2 (= same as BLOCKED rule match)
        return 2, json.dumps({"decision": "BLOCKED", "reason": "guard_not_installed"})
    out = subprocess.run([str(GUARD), "--action", action_text],
                         capture_output=True, text=True, timeout=10)
    return out.returncode, out.stdout.strip()


def send_via_wallet_lib(to_addr: str, amount_usd: float) -> str | None:
    """Codex P4-cdp-unverified: signing path uses the #324 P2 wallet_lib
    chokepoint, NOT the cdp CLI. wallet_lib.load_signer() returns (address, signer)
    where signer is an eth_account LocalAccount and address is the canonical
    Anicca wallet (asserted by wallet_lib.EXPECTED_ADDRESS). The exact RPC path
    is documented in this plan's HARD RULE #-1 disclosure block."""
    if str(WALLET_LIB_DIR) not in sys.path:
        sys.path.insert(0, str(WALLET_LIB_DIR))
    try:
        import wallet_lib  # type: ignore  # ships from #324 P2
    except ModuleNotFoundError:
        sys.stderr.write(
            "[payout-ubi] wallet_lib not found — run #324 P2 (2026-06-04-wallet-x402.md) first\n"
        )
        return None
    try:
        from_addr, signer = wallet_lib.load_signer()
    except Exception as exc:
        sys.stderr.write(f"[payout-ubi] wallet_lib.load_signer failed: {exc!r}\n")
        return None
    atomic = round(amount_usd * 1_000_000)  # USDC = 6 decimals
    # The actual EIP-3009 transferWithAuthorization build + send is implemented
    # in wallet_lib.send_usdc() (helper added in #324 P2). If that helper is
    # absent in your wallet_lib version, escalate to #324 maintainer — do NOT
    # fall back to cdp.
    if not hasattr(wallet_lib, "send_usdc"):
        sys.stderr.write(
            "[payout-ubi] wallet_lib.send_usdc() missing — add helper in #324 P2 then retry\n"
        )
        return None
    try:
        tx_hash = wallet_lib.send_usdc(signer=signer, to_addr=to_addr, amount_atomic=atomic)
    except Exception as exc:
        sys.stderr.write(f"[payout-ubi] wallet_lib.send_usdc failed: {exc!r}\n")
        return None
    # Defensive: ensure 0x… 32-byte hex tx hash shape
    if not (isinstance(tx_hash, str) and re.match(r"^0x[a-fA-F0-9]{64}$", tx_hash)):
        sys.stderr.write(f"[payout-ubi] unexpected tx_hash shape: {tx_hash!r}\n")
        return None
    return tx_hash


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

    # Codex P4-burn-address-live-risk: third defense layer before broadcast.
    # Every recipient row must have allow_live==True AND label!="PLACEHOLDER".
    live_ok, live_why = validate_recipients_for_live(cfg["recipients"])
    if not live_ok:
        row = {"ts": ts, "action": "live-recipient-validation-failed",
               "reason": live_why,
               "wallet_usd": wallet_usd, "runtime_monthly": runtime_monthly,
               "reserve_usd": reserve_usd, "would_send_usd": total_payout,
               "recipients": rec_breakdown,
               "sent": []}
        write_log(row)
        print(json.dumps(row, ensure_ascii=False))
        return 2  # non-zero — refuse to proceed

    # --confirm + ANICCA_PAYOUT_LIVE=1 + all live-validation passed → REAL broadcast
    # Signing via wallet_lib chokepoint from #324 P2 (NOT cdp CLI).
    sent = []
    failed = []
    for r in rec_breakdown:
        if r["amount_usd"] <= 0:
            continue
        tx = send_via_wallet_lib(r["address"], r["amount_usd"])
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
chmod +x /Users/operator/anicca-oss/skills/anicca-payout-ubi/scripts/payout-ubi.py
```

- [ ] **Step 3: Write `scripts/payout-ubi.sh`**

Create `/Users/operator/anicca-oss/skills/anicca-payout-ubi/scripts/payout-ubi.sh` with EXACTLY:
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
chmod +x /Users/operator/anicca-oss/skills/anicca-payout-ubi/scripts/payout-ubi.sh
```

- [ ] **Step 4: Run the payout E2E test — must PASS (TDD green for payout)**

Run:
```bash
/Users/operator/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh
```
Expected: stdout final line `PASS`, exit 0. The test exercises two modes (dry-run + confirm-without-live-env) and asserts the schema of the log row. If FAIL → fix `payout-ubi.py` math or the schema; do NOT proceed.

---

### Task 5: Write `payout-ubi` SKILL.md + README + state seed

**Files:**
- Create: `/Users/operator/anicca-oss/skills/anicca-payout-ubi/SKILL.md`
- Create: `/Users/operator/anicca-oss/skills/anicca-payout-ubi/README.md`
- Create (symlink): `/Users/operator/.hermes/skills/anicca-payout-ubi` → repo path
- Create (symlink): `/Users/operator/.hermes/scripts/anicca-payout-ubi.sh` → skill payout-ubi.sh
- Create (seed config): `/Users/operator/.hermes/state/ubi-recipients.json` (Step 4 ONLY if absent)

- [ ] **Step 1: Write SKILL.md**

Create `/Users/operator/anicca-oss/skills/anicca-payout-ubi/SKILL.md` with EXACTLY:
```markdown
---
name: anicca-payout-ubi
description: Weekly UBI fan-out. Reads wallet balance from CFO, computes distributable = max(0, wallet - runtime_monthly × reserve_months) (reserve_months default 3), then sends payout_percent (default 10%) of distributable USDC on Base, split across N recipients per ~/.hermes/state/ubi-recipients.json weights. DRY-RUN BY DEFAULT — every invocation logs to ~/.hermes/state/payout.jsonl. Real broadcast requires THREE independent signals: --confirm flag, env ANICCA_PAYOUT_LIVE=1, AND every recipient row must have allow_live:true plus label != "PLACEHOLDER" (codex round-2 fail-closed guard against burn-address footgun). Calls anicca-constitution-guard before every action, including dry-run; production fails closed if the guard symlink is missing (ANICCA_PAYOUT_TEST=1 toggles test-mode OK-on-missing). Signing path = wallet_lib.load_signer() from #324 P2 (NO cdp CLI dependency). Use this skill ONLY from cron; do not call it from chat. Cron schedule: every 7d (or "0 9 * * 1").
---

# anicca-payout-ubi

## What it does
Weekly cron skill that funnels a slice of Anicca's net earnings to a configurable list of recipient wallet addresses on Base mainnet via USDC, scaffolding pitch row ⑥ "収益の一部を UBI / 募金 配布" (00-MASTER LAUNCH ACCEPTANCE MATRIX). Row ⑥ flips green only after Wave 2 (Task 9 of `2026-06-04-constitution-payout.md`) lands a real on-chain micro-payout (0.01 USDC) with a verified Basescan receipt. Recipients can be charities (公認 NPO wallets), Dais's dividend address, or other publicly-declared addresses — the skill is agnostic; the config file picks the policy.

## Inputs
- `~/.openclaw/skills/cfo-core/data/anicca-cfo.json` — wallet balance + runtime monthly burn (already maintained by `cfo-daily` launchd job).
- `~/.hermes/state/ubi-recipients.json` — operational config. Schema in `scripts/recipients-schema.json`. Recipient weights MUST sum to 100. Each recipient row MUST carry `label` (string, must not equal "PLACEHOLDER" for live broadcast) and `allow_live` (boolean, must be true for live broadcast). Example:
  ```json
  {
    "recipients": [
      {"address": "0xCharityA…", "weight": 60, "label": "Animal welfare 認定 NPO", "allow_live": true},
      {"address": "0xCharityB…", "weight": 40, "label": "Suicide prevention 公認", "allow_live": true}
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

## Modes (defense in depth — broadcast requires THREE independent signals)
| Invocation | Behavior |
|---|---|
| `./payout-ubi.sh` (default) | Dry-run. Logs `action="dry-run"`. Exit 0. |
| `./payout-ubi.sh --dry-run` | Explicit dry-run. Same as above. |
| `./payout-ubi.sh --confirm` (no env) | Refused. Logs `action="refused-no-live-env"`. Exit 0. |
| `ANICCA_PAYOUT_LIVE=1 ./payout-ubi.sh --confirm` with any PLACEHOLDER or `allow_live:false` row | Refused. Logs `action="live-recipient-validation-failed"`. Exit non-zero. NOTHING sent. |
| `ANICCA_PAYOUT_LIVE=1 ./payout-ubi.sh --confirm` with all rows `allow_live:true` + `label != "PLACEHOLDER"` | REAL broadcast via `wallet_lib.send_usdc()` from #324 P2 per recipient on Base mainnet. Logs `action="sent"` / `"partial"` / `"send-failed"`. |

## Pre-flight guard (fail-closed in production)
On every invocation (including dry-run), this skill calls `anicca-constitution-guard --action "UBI weekly payout: …"` and aborts immediately if the guard returns non-zero. The audit trail in `~/.hermes/state/constitution-violations.jsonl` therefore proves the guard ran for every payout decision. **If the guard symlink is missing**, production exits with `action="blocked-by-guard"` + non-zero rc — codex P4-guard-bypass-ok fix. The legacy "OK + guard_not_installed" return is allowed ONLY when env `ANICCA_PAYOUT_TEST=1` (used by the RED phase of the TDD test before Task 3's symlink lands).

## Signing path (codex P4-cdp-unverified fix)
Signing imports `wallet_lib` from `anicca-oss/skills/anicca-wallet/scripts/wallet_lib.py` (shipped by #324 P2). The canonical Anicca wallet is the one `wallet_lib.EXPECTED_ADDRESS` asserts (0xa3CDd4Ec…). There is NO dependency on the `cdp` CLI; `command -v cdp` is informational only and never branched on. If `wallet_lib.send_usdc()` is absent in your tree, run #324 P2 (`docs/superpowers/plans/2026-06-04-wallet-x402.md`) before this skill — that plan adds the helper.

## HARD RULE #-1 disclosure (financial-broadcast hard-block)
Per CLAUDE.md HARD RULE #-1, the Wave 2 broadcast IS a financial broadcast. The exact path the agent will attempt: `wallet_lib.load_signer()` → `wallet_lib.send_usdc(signer, to, atomic_amount)` → internally builds EIP-3009 `transferWithAuthorization` → signs → `web3.eth.send_raw_transaction()` against Base RPC. The ONLY conditions for stopping (without human-in-loop): (a) RPC returns `insufficient funds`, (b) wallet balance < threshold, (c) recipient row fails `allow_live:true` + `label != "PLACEHOLDER"`. No Dais click, no Slack approval gate. Dais's role for the first broadcast is monitoring `payout.jsonl` + Basescan, NOT clicking through a wallet UI.

## Wave 2 verification (handled in Task 9 of the plan — NOT out-of-band)
The plan's Task 9 ("Real micro-payout proof") executes the live 0.01 USDC send + Basescan receipt check + payout.jsonl row append IN-BAND, with the cross-plan rule X2 invariant that ONLY after that task lands does #326 close and row ⑥ go green. Task 9 contains the exact commands; this SKILL.md no longer carries a separate "run it out-of-band" block.

## Why this is separate from `anicca-fuel-broker`
`anicca-fuel-broker` is a one-shot alerter that mails Dais ONCE when the wallet first crosses self-fund threshold (broker.json `first_payout_sent`). `anicca-payout-ubi` is the recurring weekly cron that distributes the ongoing slice. The two skills do NOT race because broker only ever mails (no on-chain send) and `payout-ubi` only ever sends on-chain (no mail).

## Schema of `~/.hermes/state/payout.jsonl`
```json
{"ts":"…","action":"dry-run|refused-no-live-env|below-threshold|invalid-recipients|blocked-by-guard|live-recipient-validation-failed|sent|partial|send-failed",
 "wallet_usd":100.0,"runtime_monthly":10.0,"reserve_usd":30.0,
 "would_send_usd":7.0,"recipients":[{"address":"0x…","weight":100,"amount_usd":7.0,"label":"…"}],
 "sent":[{"address":"0x…","amount_usd":7.0,"tx_hash":"0x…","basescan":"https://basescan.org/tx/…"}]}
```
```

- [ ] **Step 2: Write README.md**

Create `/Users/operator/anicca-oss/skills/anicca-payout-ubi/README.md` with EXACTLY:
```markdown
# anicca-payout-ubi

Weekly cron skill that sends a 10 %-by-default slice of Anicca's net earnings as USDC on Base to a list of recipient addresses (charity, Dais's dividend wallet, etc.). DRY-RUN BY DEFAULT — broadcast requires THREE independent signals: `--confirm` + env `ANICCA_PAYOUT_LIVE=1` + every recipient row `allow_live:true` AND `label != "PLACEHOLDER"` (codex round-2 fail-closed against burn-address footgun). Signs via `wallet_lib.load_signer()` from #324 P2 (NO `cdp` CLI dependency). Calls `anicca-constitution-guard` before every action; production fails closed if guard symlink is missing. Scaffolds pitch row ⑥ ("収益の一部を UBI / 募金 配布") of `00-MASTER.md` § LAUNCH ACCEPTANCE MATRIX in Wave 1; row goes green only after Wave 2 (Task 9 of the plan) lands a real on-chain micro-payout with a Basescan receipt. Wired by `2026-06-04-constitution-payout` plan.
```

- [ ] **Step 3: Symlink skill + script into ~/.hermes/**

Run:
```bash
ln -s /Users/operator/anicca-oss/skills/anicca-payout-ubi \
      /Users/operator/.hermes/skills/anicca-payout-ubi
mkdir -p /Users/operator/.hermes/scripts
ln -sf /Users/operator/anicca-oss/skills/anicca-payout-ubi/scripts/payout-ubi.sh \
       /Users/operator/.hermes/scripts/anicca-payout-ubi.sh
ls -l /Users/operator/.hermes/skills/anicca-payout-ubi /Users/operator/.hermes/scripts/anicca-payout-ubi.sh
hermes skills list 2>&1 | grep -E '^anicca-payout-ubi( |$)' || \
  hermes skills list 2>&1 | grep -i payout-ubi
```
Expected: skill symlink + script symlink both visible; `hermes skills list` returns a row.

- [ ] **Step 4: Seed `~/.hermes/state/ubi-recipients.json` if absent (codex P4-burn-address-live-risk: no burn-address seed, fail-closed by default)**

Codex round-2 fix: the seed uses the ZERO address (`0x0000…0000`) + `label:"PLACEHOLDER"` + `allow_live:false`. This combination makes a live broadcast IMPOSSIBLE until the operator INTENTIONALLY edits all three of: `address`, `label` (away from "PLACEHOLDER"), and `allow_live` (to `true`). Even an accidental `ANICCA_PAYOUT_LIVE=1 ... --confirm` will exit non-zero with `live-recipient-validation-failed`. No funds can be burned by accident.

Run:
```bash
RECIP=/Users/operator/.hermes/state/ubi-recipients.json
if [ ! -f "$RECIP" ]; then
  cat > "$RECIP" <<'JSON'
{
  "recipients": [
    {"address": "0x0000000000000000000000000000000000000000", "weight": 100, "label": "PLACEHOLDER", "allow_live": false}
  ],
  "payout_percent": 10,
  "reserve_months": 3
}
JSON
  chmod 600 "$RECIP"
  echo "seeded fail-closed placeholder recipients (allow_live:false, label:PLACEHOLDER)"
else
  echo "ubi-recipients.json already present — no overwrite"
fi
cat "$RECIP"
```
Expected: prints either the seeded-message or the already-present message, then the JSON content. Operator workflow to flip live: (1) replace `address` with a real recipient wallet (NOT a burn address), (2) replace `label` with any non-"PLACEHOLDER" string (e.g., "Animal welfare 認定 NPO"), (3) set `allow_live` to `true`. If ANY of the three is left at the seed default → broadcast fails closed.

- [ ] **Step 5: Validate the seed against the schema (incl. label + allow_live presence)**

Run:
```bash
/opt/homebrew/bin/python3 - <<'PY'
import json, re
from pathlib import Path
data = json.loads(Path('/Users/operator/.hermes/state/ubi-recipients.json').read_text())
schema_path = '/Users/operator/anicca-oss/skills/anicca-payout-ubi/scripts/recipients-schema.json'
schema = json.loads(Path(schema_path).read_text())
# Minimal hand-rolled validator (no jsonschema dep): top-level required keys
for k in schema['required']:
    assert k in data, f"missing top-level key {k}"
# Recipients: weight sum, address shape, AND new fields label + allow_live
total = sum(r['weight'] for r in data['recipients'])
assert abs(total - 100) < 0.01, f"weights sum != 100 (got {total})"
for r in data['recipients']:
    assert re.match(r'^0x[a-fA-F0-9]{40}$', r['address']), f"bad addr {r['address']}"
    assert 'label' in r and isinstance(r['label'], str) and r['label'], f"label missing/empty: {r}"
    assert 'allow_live' in r and isinstance(r['allow_live'], bool), \
        f"allow_live must be a bool: {r}"
# Sanity: the seed must be fail-closed (allow_live:false or label:PLACEHOLDER).
seed_is_fail_closed = any(
    (r.get('label','').upper() == 'PLACEHOLDER') or (r.get('allow_live') is not True)
    for r in data['recipients']
)
assert seed_is_fail_closed, "seed has no fail-closed marker — would broadcast on accident!"
print("schema-valid OK + fail-closed seed verified")
PY
```
Expected: prints `schema-valid OK + fail-closed seed verified`. Any AssertionError → fix the seed JSON before proceeding.

- [ ] **Step 6: Re-run payout E2E test (proves symlinked path + seed work)**

Run:
```bash
/Users/operator/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh
```
Expected: `PASS`.

- [ ] **Step 7: Commit**

Run:
```bash
cd /Users/operator/anicca-oss
git add skills/anicca-payout-ubi
git commit -m "feat(skill): anicca-payout-ubi Wave 1 — dry-run + fail-closed live-validation + wallet_lib signer (no cdp) (#326)"
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
  --script /Users/operator/.hermes/scripts/anicca-payout-ubi.sh \
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
LINES_BEFORE=$(wc -l < /Users/operator/.hermes/state/payout.jsonl 2>/dev/null || echo 0)
hermes cron run anicca-payout-ubi 2>&1 | tail -10 || \
  /Users/operator/.hermes/scripts/anicca-payout-ubi.sh
LINES_AFTER=$(wc -l < /Users/operator/.hermes/state/payout.jsonl)
echo "delta=$((LINES_AFTER - LINES_BEFORE))"
tail -n 1 /Users/operator/.hermes/state/payout.jsonl | /opt/homebrew/bin/jq .
```
Expected: `delta=1`. The new row is either `action="dry-run"` (if CFO file present + recipients ok) or `action="invalid-recipients"`/`"below-threshold"` (if the live CFO numbers don't meet the threshold). Either way, the cron is wired and ran end-to-end.

- [ ] **Step 4: Sanity-check the schema of BOTH state files**

Run:
```bash
echo "--- payout.jsonl last row ---"
tail -n 1 /Users/operator/.hermes/state/payout.jsonl | /opt/homebrew/bin/jq -e \
  '.ts and .action and (.wallet_usd|type=="number") and (.runtime_monthly|type=="number") and (.reserve_usd|type=="number")' \
  && echo OK || { echo "FAIL: payout schema"; exit 1; }
echo "--- constitution-violations.jsonl last row ---"
tail -n 1 /Users/operator/.hermes/state/constitution-violations.jsonl | /opt/homebrew/bin/jq -e \
  '.ts and .decision and .reason and .action_digest and .constitution_sha' \
  && echo OK || { echo "FAIL: violations schema"; exit 1; }
```
Expected: two `OK` lines.

---

### Task 7: Update spec 00-MASTER pitch row + cross-link (Wave 1 honest scope — row stays NOT green)

**Files:**
- Modify: `/Users/operator/anicca-oss/specs/00-MASTER.md` (LAUNCH ACCEPTANCE MATRIX row ⑥)

Codex round-2 fix (P4-no-real-payout): row ⑥'s check condition stays "a real payout tx observed on-chain" — Wave 1 does NOT weaken it. We add a status annotation pointing at Wave 2 / Task 9 of this plan and explicitly note that the row stays UN-checked until that task lands.

- [ ] **Step 1: Update the row ⑥ status annotation (NOT the check condition)**

In `/Users/operator/anicca-oss/specs/00-MASTER.md`, find the line:
```
 ⑥「収益の一部をUBI・募金配布」              →  #326 payout, #284 spec14 →  a real payout tx observed on-chain
```
Replace with (status annotation appended; check condition UNCHANGED):
```
 ⑥「収益の一部をUBI・募金配布」              →  #326 payout, #284 spec14 →  a real payout tx observed on-chain
                                                                              [Wave 1 = anicca-payout-ubi skill scaffolding
                                                                               LIVE (dry-run + guard fail-closed + recipient
                                                                               live-validation wired); row stays NOT green
                                                                               until Wave 2 / Task 9 of 2026-06-04-
                                                                               constitution-payout.md lands the 0.01 USDC
                                                                               proof tx via wallet_lib.send_usdc()]
```

- [ ] **Step 2: Commit + push the GROUND TRUTH update**

Run:
```bash
cd /Users/operator/anicca-oss
git add specs/00-MASTER.md
git commit -m "docs(spec): pitch row ⑥ status — Wave 1 scaffolding LIVE, row stays NOT green until Wave 2 real tx (#326)"
git push
```
Expected: push succeeds.

- [ ] **Step 3: Open follow-up TaskList entry for Wave 2 (do NOT close #326)**

Codex X2 enforcement: #326 is NOT marked completed by this plan. Use the TaskList tool to:
- Leave #326 in its current (in-progress) state with a note: "Wave 1 scaffolding complete; row ⑥ stays NOT green; Wave 2 (Task 9 of 2026-06-04-constitution-payout.md) is the remaining work."
- Add a sub-task or related task `#326-wave2 payout-ubi REAL micro-payout proof (0.01 USDC via wallet_lib)` with the Task 9 acceptance criteria.

---

### Task 8: Wave 1 verification — superpowers:verification-before-completion (5-step gate)

Per CLAUDE.md rule 0.12, fresh-evidence verification before claiming Wave 1 complete. This task verifies SCAFFOLDING ONLY; #326 stays open. Run ALL 5 steps below, then claim Wave 1 (NOT #326) done.

- [ ] **Step 1: IDENTIFY the proof commands**

The proof commands are exactly:
```bash
hermes --version 2>&1 | head -1   # MUST contain "0.12.0" (X1)
hermes skills list 2>&1 | grep -E '^(anicca-constitution-guard|anicca-payout-ubi)( |$)'
/Users/operator/anicca-oss/skills/anicca-constitution-guard/tests/test_guard_e2e.sh
/Users/operator/anicca-oss/skills/anicca-payout-ubi/tests/test_payout_e2e.sh
hermes cron list 2>&1 | grep -E 'anicca-payout-ubi'
tail -n 1 /Users/operator/.hermes/state/payout.jsonl | /opt/homebrew/bin/jq -e '.ts'
tail -n 1 /Users/operator/.hermes/state/constitution-violations.jsonl | /opt/homebrew/bin/jq -e '.ts'
# Confirm seed is fail-closed (no burn-addr risk)
/opt/homebrew/bin/jq -e '.recipients[0].label == "PLACEHOLDER" and .recipients[0].allow_live == false' \
  /Users/operator/.hermes/state/ubi-recipients.json
git -C /Users/operator/anicca-oss log --oneline -5
git -C /Users/operator/anicca-oss status -s
```

- [ ] **Step 2: RUN them all fresh**

Run the block from Step 1 verbatim.

- [ ] **Step 3: READ output + exit codes + assert each line below**

Required observations (ALL must hold):
- `hermes --version` contains `0.12.0` (X1 pin).
- `hermes skills list` returned BOTH `anicca-constitution-guard` AND `anicca-payout-ubi` (two grep hits).
- Both test scripts ended with `PASS` and exit 0 — including the 4 new test cases (dry-run math, refused-no-live-env, live-recipient-validation-failed under PLACEHOLDER, blocked-by-guard under guard-absent + no test mode).
- `hermes cron list` shows `anicca-payout-ubi` with a 7-day schedule.
- Last `payout.jsonl` row + last `constitution-violations.jsonl` row both parse + have an `ts` field.
- Seed-fail-closed jq check exits 0 (label==PLACEHOLDER + allow_live==false).
- `git log --oneline -5` shows the four commits from Wave 1: plan commit (Task 1.3), guard commit (Task 3.10), payout commit (Task 5.7), spec commit (Task 7.2). Total ≥4 commits, top of `main`.
- `git status -s` is empty for `skills/` and `specs/` paths (clean working tree).

- [ ] **Step 4: VERIFY the claim "Wave 1 scaffolding of #326 is complete" is supported by the evidence above**

If ANY single observation in Step 3 is false → return to the failing Task and fix; do NOT claim Wave 1 done. Per HARD RULE #14 (JOB'S NOT FINISHED), no advance to Task 9 (Wave 2) until ALL Wave 1 evidence is fresh and green. ABSOLUTELY do NOT mark #326 completed here — only Wave 2 / Task 9 closes #326.

- [ ] **Step 5: CLAIM Wave 1 with evidence**

Write the Wave 1 closing summary as: "Wave 1 of #326 (dry-run scaffolding) complete. #326 stays OPEN — row ⑥ is NOT green. Next: Task 9 (Wave 2) real micro-payout proof. Evidence: ⟨paste 9-line block from Step 2 with real outputs⟩."

---

### Task 9: Wave 2 — Real micro-payout proof (CLOSES #326 + flips row ⑥ to green)

Codex X2 cross-plan rule: row ⑥ goes green ONLY when this task lands. Wave 2 sends 0.01 USDC from the canonical Anicca wallet (`wallet_lib.EXPECTED_ADDRESS` ≈ 0xa3CDd4Ec…) to a designated NON-BURN test recipient, captures the Base mainnet tx hash, verifies the receipt on Basescan, and appends the success row to `~/.hermes/state/payout.jsonl`. NO human in the loop per HARD RULE #-1; the broadcast IS the hard-block surface — only `insufficient funds` or `wallet balance < threshold` are valid stop conditions.

**Files (this task writes mostly state + log; no new repo code beyond the live recipient file):**
- Modify (state, NOT committed): `/Users/operator/.hermes/state/ubi-recipients.json` — flip one row to a real test recipient with `allow_live:true`, `label:"wave2-self-test"` (per X2 "non-burn test address, e.g., Anicca's own second address or a designated test recipient").
- Append (state, NOT committed): one new row in `~/.hermes/state/payout.jsonl` with `"action":"sent"` + `"tx_hash":"0x…"` + `"basescan":"https://basescan.org/tx/0x…"`.

- [ ] **Step 1: Confirm wallet_lib + Anicca wallet balance**

Run:
```bash
/opt/homebrew/bin/python3 - <<'PY'
import sys
sys.path.insert(0, "/Users/operator/anicca-oss/skills/anicca-wallet/scripts")
import wallet_lib
addr, _ = wallet_lib.load_signer()
print("address:", addr)
print("expected:", wallet_lib.EXPECTED_ADDRESS)
assert addr.lower() == wallet_lib.EXPECTED_ADDRESS.lower(), "wallet address mismatch"
# Balance helper from #324 P2; if absent, escalate to #324 maintainer (NO cdp fallback).
print("usdc balance:", wallet_lib.balance_usdc())
PY
```
Expected: prints the canonical Anicca address (matches `wallet_lib.EXPECTED_ADDRESS`) and a non-zero USDC balance ≥ 0.02 USDC (= 0.01 for the broadcast + cushion for gas in ETH equivalent). If balance < 0.02 USDC → STOP per HARD RULE #-1 stop condition (b); record as `insufficient_funds` and escalate to #324 P2 fuel-broker.

- [ ] **Step 2: Pick a NON-BURN test recipient (the closer decides; do NOT hardcode in this plan)**

Per codex X2, the test recipient is "Anicca's own second address or a designated test recipient" — picked by the closer at Wave-2 execution time and recorded in the run log, NOT in this plan file (which would burn it into git). The address MUST NOT be:
- `0x0000…0000` (zero address)
- `0x…dEaD` (canonical burn address)
- any other known burn / blackhole address

If the closer has no second wallet, generate one via `wallet_lib.generate_secondary()` (or, if absent, derive deterministically from a different HD path of the same seed via #324 P2 helpers) and record the new address in the Wave-2 run log.

- [ ] **Step 3: Flip `~/.hermes/state/ubi-recipients.json` to the Wave-2 self-test policy**

Run (substituting `<TEST_ADDR>` with the address from Step 2; `payout_percent` is set ~0.014 so the math yields exactly 0.01 USDC with the live CFO numbers):
```bash
TEST_ADDR="<paste the non-burn test address from Step 2>"
cat > /Users/operator/.hermes/state/ubi-recipients.json <<JSON
{
  "recipients": [
    {"address": "${TEST_ADDR}", "weight": 100, "label": "wave2-self-test", "allow_live": true}
  ],
  "payout_percent": 0.014,
  "reserve_months": 3
}
JSON
chmod 600 /Users/operator/.hermes/state/ubi-recipients.json
cat /Users/operator/.hermes/state/ubi-recipients.json
```
Expected: prints the JSON with the real test address, `label:"wave2-self-test"`, `allow_live:true`. NO `PLACEHOLDER` token anywhere.

- [ ] **Step 4: Dry-run first to confirm math = 0.01 USDC**

Run:
```bash
/Users/operator/.hermes/skills/anicca-payout-ubi/scripts/payout-ubi.sh --dry-run \
  | /opt/homebrew/bin/jq -e '.would_send_usd == 0.01 and .recipients[0].amount_usd == 0.01'
```
Expected: jq exits 0 (would_send_usd == 0.01). If the live CFO numbers make the math different from 0.01, adjust `payout_percent` in the JSON until the dry-run prints exactly 0.01, then re-run this step. Do NOT proceed to broadcast until the dry-run shows 0.01.

- [ ] **Step 5: BROADCAST (HARD RULE #-1 surface — financial-broadcast)**

Per HARD RULE #-1 the only valid stop conditions here are: (a) RPC `insufficient funds`, (b) `wallet_lib.balance_usdc()` < 0.02, (c) recipient row fails `allow_live:true` + `label != "PLACEHOLDER"`. NO human-in-loop. The agent runs the command and reads `payout.jsonl` for the result — no Slack approval, no Dais click.

Run:
```bash
LINES_BEFORE=$(wc -l < /Users/operator/.hermes/state/payout.jsonl)
ANICCA_PAYOUT_LIVE=1 \
  /Users/operator/.hermes/skills/anicca-payout-ubi/scripts/payout-ubi.sh --confirm
LINES_AFTER=$(wc -l < /Users/operator/.hermes/state/payout.jsonl)
echo "delta=$((LINES_AFTER - LINES_BEFORE))"
LAST=$(tail -n 1 /Users/operator/.hermes/state/payout.jsonl)
echo "$LAST" | /opt/homebrew/bin/jq '{action, sent: .sent[0].tx_hash, basescan: .sent[0].basescan}'
```
Expected: `delta=1`, action `"sent"`, `tx_hash` matches `^0x[a-fA-F0-9]{64}$`, basescan URL printed.

- [ ] **Step 6: Verify the Basescan receipt (cross-plan rule X2 acceptance)**

Run:
```bash
TX=$(tail -n 1 /Users/operator/.hermes/state/payout.jsonl | /opt/homebrew/bin/jq -r '.sent[0].tx_hash')
test -n "$TX" && test "$TX" != "null" || { echo "FAIL: no tx hash"; exit 1; }
curl -s "https://api.basescan.org/api?module=transaction&action=gettxreceiptstatus&txhash=${TX}" \
  | /opt/homebrew/bin/jq -e '.result.status == "1"' \
  && echo "OK: basescan receipt status=1 for $TX" \
  || { echo "FAIL: basescan receipt not status=1 for $TX"; exit 1; }
```
Expected: `OK: basescan receipt status=1 for 0x…`. If the receipt status is not `1`, the tx reverted — investigate via `wallet_lib`'s logs, fix, and retry Step 5. Do NOT proceed.

- [ ] **Step 7: Restore the fail-closed seed (operator hygiene)**

Run:
```bash
cat > /Users/operator/.hermes/state/ubi-recipients.json <<'JSON'
{
  "recipients": [
    {"address": "0x0000000000000000000000000000000000000000", "weight": 100, "label": "PLACEHOLDER", "allow_live": false}
  ],
  "payout_percent": 10,
  "reserve_months": 3
}
JSON
chmod 600 /Users/operator/.hermes/state/ubi-recipients.json
echo "restored fail-closed seed"
```
Expected: prints `restored fail-closed seed`. The weekly cron will now log `live-recipient-validation-failed` until the operator intentionally re-flips, which is the safe default for the recurring cron.

- [ ] **Step 8: Update spec 00 row ⑥ to GREEN with the tx hash**

In `/Users/operator/anicca-oss/specs/00-MASTER.md`, replace the Task 7 Step 1 annotation block with:
```
 ⑥「収益の一部をUBI・募金配布」              →  #326 payout, #284 spec14 →  REAL on-chain tx observed
                                                                              [Wave 2 closed: tx 0x<HASH>
                                                                               https://basescan.org/tx/0x<HASH>
                                                                               anicca-payout-ubi LIVE]
```
(Substitute `<HASH>` with the actual tx hash from Step 5.) Commit + push:
```bash
cd /Users/operator/anicca-oss
git add specs/00-MASTER.md
git commit -m "docs(spec): pitch row ⑥ GREEN — real UBI tx broadcast 0x<HASH> via wallet_lib (#326)"
git push
```

- [ ] **Step 9: NOW mark #326 completed in the TaskList**

ONLY after Steps 1-8 succeed: use the TaskList tool to set `#326` to `completed` with the tx hash + basescan URL in the note. Verification-before-completion (rule 0.12) requires citing the Step 6 `OK: basescan receipt status=1 for 0x<HASH>` line as fresh evidence.

- [ ] **Step 10: Closing summary**

Write: "Wave 2 of #326 complete. Tx 0x<HASH> confirmed on Basescan (status=1). Row ⑥ green. #326 closed. Evidence: ⟨Step 6 jq output⟩."

---

## Self-Review

**Spec coverage:**
- Spec `00-MASTER.md` § LAUNCH ACCEPTANCE MATRIX row ⑥ ("収益の一部を UBI / 募金 配布") — Tasks 4-6 wire the Wave 1 dry-run scaffolding; Task 7 ADDS an annotation but does NOT weaken the check condition (codex P4-no-real-payout fix). Row ⑥ stays NOT green until Task 9 (Wave 2) lands the real on-chain tx and updates the spec to GREEN with the tx hash.
- Spec `16-RUNTIME-CODE-TRUTH.md` § 17 PANEL D ("constitution-guard — check 3 Laws before any action — ports from automaton constitution.md") — Task 3 implements with the live `CONSTITUTION.md` as the source of truth (= the canonical file at `anicca-oss/CONSTITUTION.md`, lines 144-184).
- Spec `18-SELF-IMPROVEMENT-AND-SWARM.md` § 4 mutability ("IMMUTABLE: North Star + Law I; MUTABLE: everything else (via forum → consensus → implement)") — Task 3 enforces the IMMUTABLE half via hash-pin + rule files; the MUTABLE half (forum vote → PR → eval ≥ 0.7) is explicitly OUT OF SCOPE here and pointed at #338 ROLLOUT in SKILL.md.
- CLAUDE.md rule 0.4 ("edit したら commit + push 即実行") — every Task that creates files ends with a `git add && commit && push` step (Tasks 1.3, 3.10, 5.7, 7.2, 9.8).
- CLAUDE.md rule 0.12 (verification-before-completion 5-step gate) — Task 8 is the gate for Wave 1 scaffolding; Task 9 (Wave 2) ends with its own evidence (Step 6 Basescan receipt check) before #326 is closed. NO "Done!" claim without fresh evidence.

**Codex round-2 cross-plan rules honored:**
- X1: Hermes pinned to v0.12.0 (preflight in Task 1 Step 2 enforces).
- X2: Wave 1 scaffolding ≠ #326 close. Task 9 (Wave 2) is the explicit follow-on with real-tx + Basescan receipt + payout.jsonl row, gating row ⑥ green.
- X3: HARD RULE #-1 financial-broadcast disclosure block added in plan header; exact RPC path = `wallet_lib.load_signer()` → `send_usdc()` → `eth_sendRawTransaction`; stop conditions only on `insufficient funds` / balance threshold / recipient-validation. NO human-in-loop in Task 9.
- X4: Runtime state under `~/.hermes/state/` (constitution-violations.jsonl, payout.jsonl, ubi-recipients.json, constitution.sha).
- X5: Preflight `command -v cdp` informational only; hard requirement is `wallet_lib.py` from #324 P2 (preflight blocks with explicit pointer at the #324 plan if missing).

**Placeholder scan:** every file content is verbatim. Every Wave 1 test asserts the exact arithmetic (wallet=100, runtime=10 → reserve=30, distributable=70, payout=7.00; weight=100 → recipient gets 7.00). The only intentional substitution points are:
- Task 7 Step 1 — the matrix row replacement annotation is verbatim, NOT a TODO; the check condition itself stays UNCHANGED until Task 9.
- Task 9 Step 2 — the test recipient address is INTENTIONALLY picked at execution time by the closer (codex X2 wants "Anicca's own second address or a designated test recipient", which is per-instance state, NOT a value to bake into the repo plan). The `<TEST_ADDR>` token in Task 9 Step 3 is the explicit substitution point.
- Task 9 Step 8 — the `<HASH>` token in the spec annotation is filled with the actual tx hash from Step 5 at execution time.

**Type consistency:**
- `payout.jsonl` row shape: writer (`payout-ubi.py` `write_log`) and reader (`test_payout_e2e.sh` jq checks + Task 6 Step 4 jq check + Task 9 Step 6 jq check) all reference `{ts, action, wallet_usd, runtime_monthly, reserve_usd, would_send_usd, recipients[]}` plus the live-broadcast extension `{sent[]: {address, weight, amount_usd, label, tx_hash, basescan}}`. Schema match verified by tests + the Step 6 jq.
- `constitution-violations.jsonl` row shape: writer (`check.py` `write_log`) and reader (`test_guard_e2e.sh` jq + Task 6 Step 4 jq) both reference `{ts, decision, reason, action_digest, constitution_sha}`. Match verified by the test.
- Recipient JSON shape: schema file (`recipients-schema.json`), seed (`ubi-recipients.json`), test fixtures (synthetic + placeholder), validator (`validate_recipients` + `validate_recipients_for_live` in `payout-ubi.py`), and Task 5 Step 5 hand-rolled validator all agree on `{address: ^0x[a-f0-9]{40}$, weight: 0-100, label: string non-empty, allow_live: boolean}` and the 100-sum constraint. The Wave-1 fail-closed requirement (`label==PLACEHOLDER OR allow_live!=true → no broadcast`) is enforced by `validate_recipients_for_live` and asserted by test cases 3 + 4.
- Symlink targets: skill dirs at `/Users/operator/anicca-oss/skills/<name>/` ↔ `~/.hermes/skills/<name>` and script at `/Users/operator/.hermes/scripts/anicca-payout-ubi.sh` — exact paths repeated in Task 3 Step 8, Task 5 Step 3, and Task 6 Step 1.
- Signer chokepoint: `payout-ubi.py` `send_via_wallet_lib` imports `wallet_lib` from `/Users/operator/anicca-oss/skills/anicca-wallet/scripts/`. That path is the same one #324 P2 (`2026-06-04-wallet-x402.md`) writes — one chokepoint across both plans (codex X5).

**Risk notes (read before executing):**
- Risk A — Task 1 Step 1 depends on `~/.hermes/state/constitution.sha` existing. If `anicca-heartbeat` (#323) hasn't run yet, the seed line in Task 1 Step 1 writes it directly (idempotent). Heartbeat will overwrite it on its next 30-min fire with the same value. No race.
- Risk B — Task 3 Step 5 (guard test) writes ≥3 rows into `constitution-violations.jsonl`. That file is shared with the live runtime; if the heartbeat or another skill writes between the BEFORE and AFTER `wc -l`, the test could overshoot the expected delta. The test uses `[ $DELTA -ge 3 ]` (≥, not ==) precisely to tolerate concurrent appenders. Acceptable.
- Risk C — Codex P4-guard-bypass-ok fix: `call_guard` now fails closed in production when the guard symlink is absent. The "OK + guard_not_installed_test_mode" return path is gated on env `ANICCA_PAYOUT_TEST=1`, which the Task 2 RED-phase test sets explicitly so the test can run before Task 3 Step 8 installs the symlink. Once the symlink lands, production cron fires with no env var set — a deleted symlink (operator error, disk corruption) immediately produces `action="blocked-by-guard"` + non-zero exit + no broadcast. Audit-tight.
- Risk D — Codex P4-burn-address-live-risk fix: the seed (`ubi-recipients.json`, Task 5 Step 4) uses the zero address (`0x0000…0000`) + `label:"PLACEHOLDER"` + `allow_live:false`. A live broadcast is IMPOSSIBLE while ANY of those three values is at the seed default — `validate_recipients_for_live()` exits with `live-recipient-validation-failed` BEFORE any signing happens. The operator must intentionally edit three distinct fields to flip live, and Wave 2 / Task 9 does so under controlled conditions with a non-burn test recipient. No "feature where funds burn on accident" — fully closed.
- Risk E — Codex P4-cdp-unverified fix: the signing path is `wallet_lib.send_usdc()` from #324 P2. If wallet_lib lacks `send_usdc()` in your tree (= you ran Wave 1 of #326 before #324 P2), Task 1 Step 2's preflight fails with a BLOCK message pointing at #324 P2. The legacy `cdp wallet send` path is fully removed; `command -v cdp` is informational only and never branched on.
- Risk F — Task 9 (Wave 2) broadcast IS a HARD RULE #-1 financial-broadcast surface. The plan's only stop conditions are (a) RPC `insufficient funds`, (b) `wallet_lib.balance_usdc()` < 0.02 USDC, (c) recipient row fails live-validation. There is NO human-in-loop step in Task 9 — no Slack approval gate, no Dais click. The agent reads `payout.jsonl` for the result. This is intentional per HARD RULE #-1: real on-chain micro-payout is the proof, not a permission slip.

---

## Execution Handoff

Plan v2 (codex round-2 fixes applied) saved to `docs/superpowers/plans/2026-06-04-constitution-payout.md`.

Per Dais's directive ("keep getting reviewed by codex; only when it's time to implement, build with agent teams"), the next move is NOT to start Task 1 — it is to run **codex-review** again against this v2 plan and the four governing specs (00-MASTER, 16-RUNTIME-CODE-TRUTH, 18-SELF-IMPROVEMENT-AND-SWARM, CONSTITUTION.md). When codex says `ok: true`, dispatch the implementation via **superpowers:subagent-driven-development** — fresh subagent per task, two-stage review (spec compliance, then code quality) after each task.

**Execution order:** Tasks 1-8 are Wave 1 (dry-run scaffolding, does NOT close #326). Task 9 is Wave 2 (real micro-payout, CLOSES #326 and flips row ⑥ to green). Task 6 Step 3 + Task 8 Step 2 + Task 9 Step 5 MUST be observed live by the closer (HARD RULE #14: no advancement until verified). Task 9 IS the HARD RULE #-1 financial-broadcast surface — the agent broadcasts without human-in-loop and reads `payout.jsonl` for the result. The only valid stop conditions are: RPC `insufficient funds`, wallet balance < 0.02 USDC, or recipient row failing live-validation.
