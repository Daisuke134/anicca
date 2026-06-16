# Patch — A-earn GATE-0 via REAL EXTERNAL REVENUE (0xwork), NOT swap  (rev2, adversarial-review fixes)

2026-06-16. GATE-0 = **ONE profitable wake** = wallet USDC delta > 0 from **EXTERNAL revenue**
(a third party pays Anicca for work) with a Base receipt `status=0x1` recorded in
`earn-ledger.jsonl`. An ETH→USDC **swap is net-zero asset liquidation** — it moves Anicca's own
value between tokens and does NOT count. GATE-0 requires money entering the wallet *from outside*.

**rev2** closes the 5 blocking gaps the adversarial verifier raised (ok=FALSE on rev1):
false-green via the source-blind classifier, the wrong runtime (`~/clawd`, not `~/anicca`),
the now-false "free faucet/no seed" claim, the black-box executor, and pickTask matching zero
live tasks. Each fix below cites RAW evidence I re-verified this session.

### Files read / re-verified (RAW evidence)
- `~/anicca/skills/earn/lib/ledger.mjs:32-34` — `isProfitable()` is **source-blind**: `Boolean(line && line.tx && line.status === "0x1" && Number(line.net_usdc) > 0)`. No source check.
- `~/anicca/skills/earn/run.sh:57-89` — `EARN_STRATEGY=swap` branch does `record_line` then `exit 0` (the "GATE-0 MET" `exit 0` at ~line 85) **before** any external-payout assertion downstream → rev1's guard was unreachable on the swap path.
- **Runtime is a COPY, not `~/anicca`**: `ls /Users/anicca/clawd/skills/earn/` → `run.sh`, `lib/`, `state/`, `execute-swap.py` present; `readlink` empty (NOT a symlink); `diff -q ~/clawd/skills/earn/run.sh ~/anicca/skills/earn/run.sh` → **IDENTICAL COPY**.
- **Live loop target** = `/Users/anicca/.hermes/cron/jobs.json` → earn job runs `EARN_MODE=execute EARN_STRATEGY=swap bash ~/clawd/skills/earn/run.sh`, writes `~/clawd/skills/earn/state/earn-ledger.jsonl`, then `~/clawd/skills/report-slack/scripts/report.sh`. (grep `EARN_STRATEGY` in jobs.json → only `EARN_STRATEGY=swap`.)
- **0xwork seed reality** (authoritative JSON, `GET https://api.0xwork.org/quickstart`): step 3 `description` = **"External wallets must already hold the required AXOBOTL stake and Base ETH"**; `requirements.cost` = **"Requires AXOBOTL stake + Base ETH for external wallets"**; `postRegistration` includes `0xwork stake --amount 40000`. The faucet auto-funds **only a fresh `0xwork init` wallet** (`/connect`: "Gas + $AXOBOTL stake are free — sponsored automatically via faucet… wallet creation, registration…"). Our `0xa3CDd4` is an **external** wallet → NOT faucet-funded.
- **Live open tasks** (`GET https://api.0xwork.org/tasks?status=open`, 2026-06-16): exactly **2 tasks**, both `status:"Open"` (capitalized), `category:"Social"`, `stake_amount:null`, `bounty:"50"` (ids 390, 391). Zero in Writing/Research/Code/Data today.
- Wallet `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21` (from `BLOCKRUN_WALLET_KEY`): **0.014475 USDC** + **0.000801 ETH** on Base.
- `~/anicca/skills/earn/execute-swap.py:1-40` — executor pattern to mirror (signs with wallet key, broadcasts, prints JSON `{tx,status,before_usdc,after_usdc,gross_usdc,cost_usdc}`).
- Contract/eval basis: `A-earn-gate0.patch.md`, `A-earn-gate0-live.patch.md`, `04-earn.md`, `MONEYMAKER-EVAL.md` (0xwork ★★★, x402-sell), `10-self-funding-architecture.md`, commands `Q22/Q30/Q31`.

---

## Gaps

| # | Spec requires | RAW evidence (exists vs spec) | Severity |
|---|---|---|---|
| G1 | The GATE-0 classifier must reject swaps / require external-payout proof for **any** entrypoint. | `ledger.mjs:33` `isProfitable` is source-blind (net>0 && 0x1 only). The `run.sh` swap branch records + `exit 0` (~line 85) before reaching rev1's external assertion → **one env var (`EARN_STRATEGY=swap`) re-opens false-green**. | **CRITICAL** |
| G2 | The fix must change the **running** loop. | The loop runs `~/clawd/skills/earn/run.sh` (an IDENTICAL non-symlink COPY of `~/anicca`) and `~/.hermes/cron/jobs.json`. Editing `~/anicca` alone does **nothing** to the live loop. rev1 targeted `~/anicca` + a non-existent `~/.hermes/cron/jobs.json` swap line. | **CRITICAL** |
| G3 | A no-seed-capital external path, honestly stated. | rev1 claimed 0xwork register is "free + faucet, no seed." **FALSE for our external wallet**: JSON `requirements` = "Requires AXOBOTL stake + Base ETH for external wallets." Faucet funds only fresh `0xwork init` wallets. | **HIGH** |
| G4 | The executor that turns work into the post-approval payout tx must be specified. | rev1's `execute-0xwork.py` was a black box; GATE-0's `payout_tx` had no defined source. | **HIGH** |
| G5 | An earn path that actually exists in one wake. | rev1 `pickTask` capSet {Writing,Research,Code,Data} matches **zero** live tasks (both are `Social`); also queried `status=open` lowercase while live status is `"Open"`. No reachable wake. | **CRITICAL** |
| G6 (carried) | External-revenue executor exists at all. | `04-earn.md` names `nookplot.mjs`/`x402-sell.mjs`/`content.mjs`; none exist (`find skills/earn` → only swap/record/ledger/usdc/verify-tx). | HIGH |

---

## Diff

### Path: **0xwork** (external counterparty escrow pays USDC) with **x402-sell** as the same-wake fallback.

**Why EARN not SWAP:** 0xwork is a Base marketplace where a **third-party poster funds a USDC
bounty into escrow** (`taskPool 0xF404…C6D2`). On approval the escrow releases USDC **from the
poster's funds into Anicca's wallet** — the payout tx has `from = taskPool`, not Anicca. Anicca's
runway grows because *someone else paid it*. A swap has no taskPool→wallet transfer; total value is
flat. This `from != self` discriminator is now enforced **inside the classifier** (G1).

#### Fix G1 — move the external-payout proof INTO `isProfitable()` (source-blind → source-aware)

```diff
*** ~/anicca/skills/earn/lib/ledger.mjs  AND  ~/clawd/skills/earn/lib/ledger.mjs (both — runtime is the copy)
@@ // GATE-0 truth ...
- export function isProfitable(line) {
-   return Boolean(line && line.tx && line.status === "0x1" && Number(line.net_usdc) > 0);
- }
+ // A swap (Anicca trading its own ETH for its own USDC) is net-zero asset rotation and is NOT
+ // earning. GATE-0 requires EXTERNAL revenue: an inbound USDC transfer to our wallet from a
+ // counterparty (0xwork escrow, x402 payer). The classifier therefore demands:
+ //   tx present  &&  status 0x1  &&  net_usdc > 0  &&  external == true  &&  source not a swap.
+ // `external` is set ONLY by run.sh after asserting an inbound USDC Transfer whose `from` is an
+ // approved external payer (see oxwork.isExternalPayout / x402 settle proof). A swap line can
+ // never set external:true, so no env var (EARN_STRATEGY=swap) can re-open false-green.
+ const SWAP_SOURCES = new Set(["swap-eth-usdc", "swap", "swap-usdc-eth"]);
+ export function isProfitable(line) {
+   if (!line || !line.tx || line.status !== "0x1") return false;
+   if (!(Number(line.net_usdc) > 0)) return false;
+   if (SWAP_SOURCES.has(String(line.source))) return false;   // asset rotation is never GATE-0
+   if (line.external !== true) return false;                  // require proven external inbound
+   return true;
+ }
```

```diff
*** ~/anicca/skills/earn/lib/ledger.mjs (deriveLine — carry the proof flag onto the line)
@@ if (o.tx) line.tx = o.tx;
@@ if (o.status) line.status = o.status;
+ if (o.external === true) line.external = true;   // set only after external-payout assertion
  return line;
```
(`record.mjs` already passes the parsed JSON straight to `deriveLine`; it needs no change — run.sh
puts `external:true` into the JSON only on a verified external payout. The **swap branch never sets
it**, so swaps now record as NARRATE even with status 0x1: honest, never GATE-0.)

#### Fix G5/G6 — `oxwork.mjs` executor lib (capability match fixed; case-insensitive status)

```diff
*** NEW: ~/anicca/skills/earn/lib/oxwork.mjs  (+ identical sync to ~/clawd/skills/earn/lib/oxwork.mjs)
+ // 0xwork external-revenue helpers. Pure transport (fetch injectable); no signing here.
+ const API = process.env.OXWORK_API || "https://api.0xwork.org";
+ const USDC = (process.env.USDC_ADDRESS || "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913").toLowerCase();
+ const TASKPOOL = (process.env.OXWORK_TASKPOOL || "0xF404aFdbA46e05Af7B395FB45c43e66dB549C6D2").toLowerCase();
+ // Anicca's capability set. NOTE: live supply is volatile (today both open tasks are "Social").
+ // We match case-insensitively AND default-allow when OXWORK_ANY_CATEGORY=1 so a wake is reachable
+ // even when only Social tasks exist — the agent decides per-task if it can deliver verifiable proof.
+ const DEFAULT_CAPS = (process.env.OXWORK_CAPS || "Writing,Research,Code,Data,Social,Creative").split(",");
+
+ export async function pickTask(caps = DEFAULT_CAPS, opts = {}) {
+   const fetchImpl = opts.fetchImpl || globalThis.fetch;
+   const res = await fetchImpl(`${API}/tasks?status=open`);
+   if (!res.ok) throw new Error(`oxwork: tasks ${res.status}`);
+   const { tasks = [] } = await res.json();
+   const capSet = new Set(caps.map((c) => c.trim().toLowerCase()));
+   const anyCat = process.env.OXWORK_ANY_CATEGORY === "1" || capSet.size === 0;
+   return (
+     tasks
+       .filter((t) => String(t.status).toLowerCase() === "open")                // case-insensitive status ("Open")
+       .filter((t) => t.stake_amount === null || Number(t.stake_amount) === 0)  // no worker stake (wallet ~0)
+       .filter((t) => Number(t.bounty_amount) > 0)
+       .find((t) => anyCat || capSet.has(String(t.category).toLowerCase())) || null
+   );
+ }
+
+ // GATE-0 proof: the payout tx carries an ERC-20 USDC Transfer (topic0=Transfer) with
+ // from == taskPool (external) and to == our wallet. A swap has NO such log => false.
+ export async function isExternalPayout(receipt, wallet) {
+   if (!receipt || !Array.isArray(receipt.logs)) return false;
+   const TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
+   const padW = "0x" + wallet.toLowerCase().replace(/^0x/, "").padStart(64, "0");
+   const padPool = "0x" + TASKPOOL.replace(/^0x/, "").padStart(64, "0");
+   return receipt.logs.some(
+     (l) =>
+       l.address.toLowerCase() === USDC &&
+       l.topics[0] === TRANSFER &&
+       l.topics[1].toLowerCase() === padPool &&   // from = 0xwork escrow (external)
+       l.topics[2].toLowerCase() === padW         // to   = our wallet
+   );
+ }
```

#### Fix G4 — `execute-0xwork.py` executor contract (no longer a black box)

```diff
*** NEW: ~/anicca/skills/earn/execute-0xwork.py  (+ sync to ~/clawd/skills/earn/execute-0xwork.py)
+ #!/usr/bin/env python3
+ """execute-0xwork — the external-revenue executor run.sh calls for EARN_STRATEGY=0xwork.
+ Mirrors execute-swap.py's contract: reads env, drives 0xwork, prints ONE JSON line to stdout.
+
+ INPUTS (env):
+   OXWORK_PKVAR / BLOCKRUN_WALLET_KEY   signing+receiving wallet (the ledger/usdc proof reads it)
+   OXWORK_API        default https://api.0xwork.org
+   OXWORK_TASK_ID    (optional) pin a specific task; else pickTask via the CLI/SDK discover
+   OXWORK_DELIVER    path to the deliverable file the agent produced this wake (required to submit)
+   OXWORK_POLL_SECS  default 0  (0 = do NOT block on approval; return claimed/awaiting -> NARRATE)
+
+ EXACT CALLS (CLI is the supported surface; `npm i -g @0xwork/cli`, quickstart-verified):
+   register (idempotent):  `0xwork register --name=Anicca --capabilities=Writing,Research,Code,Data`
+   discover:               `0xwork discover --json`        -> open tasks (or SDK GET /tasks?status=open)
+   claim:                  `0xwork claim <taskId> --json`  -> on-chain claim tx
+   submit:                 `0xwork submit <taskId> --files=$OXWORK_DELIVER --summary="..." --json`
+   payout (post-approval): the poster approves -> escrow releases USDC. The payout tx hash is read
+                           from `0xwork task <taskId> --json` field `payout_tx_hash`
+                           (manifest task schema field, confirmed present) OR from
+                           `0xwork balance --json` last settlement. We do NOT fabricate it: if the
+                           task is not yet 'Completed'/'Paid', payout_tx is "" and the wake NARRATEs.
+
+ OUTPUT (stdout, one JSON object — same shape run.sh already parses):
+   {"task_id": "<id>", "payout_tx": "0x<66hex>" | "",
+    "status": "0x1" | "", "before_usdc": <n>, "after_usdc": <n>}
+ Errors print {"error": "<msg>"} and run.sh degrades to a NARRATE line (never bricks, never GATE-0).
+ NO HUMAN, NO CLAUDE: the agent picks/does/submits the task; this script only orchestrates the CLI
+ and surfaces the real, externally-approved payout tx. Claude verifies; Claude does not run it.
+ """
+ # Implementation: subprocess the 0xwork CLI per the calls above, capture --json, read
+ # payout_tx_hash; snapshot usdcBalance(wallet) before claim and after payout for the delta.
```

#### Fix G2 — wire the **running** loop (the COPY + the real jobs.json)

```diff
*** ~/clawd/skills/earn/run.sh   (the LIVE entrypoint — edit the COPY, not just ~/anicca)
@@ STRATEGY="${EARN_STRATEGY:-swap}"
+ # GATE-0 default = EXTERNAL revenue. Swap demoted to a non-gate runway fallback ONLY.
+ STRATEGY="${EARN_STRATEGY:-0xwork}"
@@ (swap branch, ~57-89) — swaps may still top up runway but must record as NARRATE:
- JSON=$(python3 -c "... 'source':'$EARN_SOURCE' ... 'tx':'$EARN_TX','status':'$STATUS' ...")
+ # swap line carries NO 'external' flag -> isProfitable() returns false -> NARRATE, never GATE-0.
+ JSON=$(python3 -c "... 'source':'swap-eth-usdc' ... 'tx':'$EARN_TX','status':'$STATUS' ...")   # (no 'external')
+ # --- strategy=0xwork: REAL EXTERNAL REVENUE (escrow pays USDC to our wallet) ----------------
+ if [ "$STRATEGY" = "0xwork" ] && [ -z "${EARN_TX:-}" ]; then
+   BEFORE=$(node -e "import('$HERE/lib/usdc.mjs').then(m=>m.usdcBalance('$WLOW')).then(b=>console.log(b))")
+   RES=$(OXWORK_PKVAR="$PKVAR" python3 "$HERE/execute-0xwork.py" 2>/dev/null)
+   PAYTX=$(printf '%s' "$RES" | python3 -c "import json,sys;print(json.load(sys.stdin).get('payout_tx',''))")
+   if [ -z "$PAYTX" ]; then
+     JSON=$(python3 -c "import json;print(json.dumps({'wallet':'${WLOW:-unknown}','source':'0xwork','task':'claimed-awaiting-approval','earn_usdc':0,'cost_usdc':0,'wake':'$WAKE'}))")
+     OUT=$(record_line "$JSON"); echo "[earn] 0xwork narrate -> $OUT"; exit 0
+   fi
+   # Assert the payout is an EXTERNAL inbound USDC transfer (from=taskPool) BEFORE recording GATE-0:
+   RECEIPT=$(curl -s "${BASE_RPC_URL:-https://mainnet.base.org}" -H 'content-type: application/json' -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getTransactionReceipt\",\"params\":[\"$PAYTX\"]}")
+   EXT=$(printf '%s' "$RECEIPT" | node -e "process.stdin.on('data',async d=>{const r=JSON.parse(d).result;const o=await import('$HERE/lib/oxwork.mjs');console.log(await o.isExternalPayout(r,'$WLOW'))})")
+   [ "$EXT" = "true" ] || { echo "[earn] REJECT: $PAYTX not an external 0xwork payout — NOT GATE-0"; exit 1; }
+   STATUS=$(node -e "import('$HERE/lib/verify-tx.mjs').then(m=>m.receiptStatus('$PAYTX')).then(s=>console.log(s||'null'))")
+   AFTER=$(node -e "import('$HERE/lib/usdc.mjs').then(m=>m.usdcBalance('$WLOW')).then(b=>console.log(b))")
+   AMT=$(node -e "console.log(Math.max(0,($AFTER)-($BEFORE)))")
+   # external:true is what unlocks isProfitable() — set ONLY here, after the assertion passed.
+   JSON=$(python3 -c "import json;print(json.dumps({'wallet':'${WLOW:-unknown}','source':'0xwork','task':'$(printf '%s' "$RES" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("task_id","0xwork"))')','earn_usdc':float('$AMT'),'cost_usdc':0,'tx':'$PAYTX','status':'$STATUS','external':True,'wake':'$WAKE'}))")
+   OUT=$(record_line "$JSON"); echo "[earn] 0xwork recorded -> $OUT"
+   [ "$OUT" = "PROFITABLE" ] && echo "[earn] GATE-0 MET (external revenue, status 0x1)."; exit 0
+ fi
```

```diff
*** /Users/anicca/.hermes/cron/jobs.json   (the LIVE loop target; runtime store, main-direct per HARD #0 exception)
- EARN_MODE=execute EARN_STRATEGY=swap bash ~/clawd/skills/earn/run.sh
+ EARN_MODE=execute EARN_STRATEGY=0xwork bash ~/clawd/skills/earn/run.sh
  # (also update the prose lines in this job that describe "liquidates ETH->USDC" — swap is now a
  #  non-gate runway fallback; the GATE-0 strategy is 0xwork external revenue.)
```

```diff
*** SYNC (required, because runtime ≠ ~/anicca): after editing ~/anicca/skills/earn/**, copy into the live body:
+   cp ~/anicca/skills/earn/lib/{ledger,oxwork}.mjs        ~/clawd/skills/earn/lib/
+   cp ~/anicca/skills/earn/execute-0xwork.py              ~/clawd/skills/earn/
+   cp ~/anicca/skills/earn/run.sh                         ~/clawd/skills/earn/
+   cp ~/anicca/skills/earn/lib/__tests__/oxwork.test.js   ~/clawd/skills/earn/lib/__tests__/
# (Keep ~/anicca canonical for install.sh/OSS; ~/clawd is the body the heartbeat actually executes.
#  Better: convert ~/clawd/skills/earn into a symlink of ~/anicca/skills/earn IF the OpenClaw loader
#  follows symlinks — verify before relying on it; until then the cp sync is mandatory.)
```

#### Fix G5 (same-wake reachability) — x402-sell fallback when no doable 0xwork task exists

```diff
*** ~/clawd/skills/earn/run.sh  (after the 0xwork narrate branch: try x402 sell so a wake can still close)
+ # If 0xwork has no doable task this wake, fall back to selling Anicca's own output via x402
+ # (04-earn.md "x402 sell own work"). x402 settles instantly (no poster approval wait): a payer
+ # streams USDC to our wallet for a delivered artifact. Same external-payout assertion + external:true.
+ #   EARN_STRATEGY=x402 -> execute-x402-sell.py prints {payout_tx,...}; isExternalPayout proves from!=self.
```

```diff
*** ~/anicca/skills/registry.json  (earn slot only) — keep "live" but it is now backed by an EXTERNAL wake (not a swap).
  "earn": { ... "status": "live" }   # value unchanged; meaning corrected by the classifier + loop wiring above.
```

```diff
*** NEW: ~/anicca/skills/earn/lib/__tests__/oxwork.test.js (node:test, zero new dep — TDD)
+ // RED: isProfitable rejects {source:"swap-eth-usdc",tx,status:"0x1",net_usdc:0.5} (swap guard).
+ // RED: isProfitable rejects {source:"0xwork",tx,status:"0x1",net_usdc:0.5,external:undefined} (needs proof).
+ // GREEN: isProfitable true ONLY for {source:"0xwork",tx,status:"0x1",net_usdc>0,external:true}.
+ // RED: isExternalPayout TRUE only when a USDC Transfer log has from=taskPool && to=wallet;
+ //      FALSE for a swap receipt (no taskPool->wallet USDC transfer).
+ // RED: pickTask skips stake>0 + non-"open" status; with OXWORK_ANY_CATEGORY=1 returns a "Social"/"Open" task.
```

(`apps/landing/app/me/page.tsx` unchanged — renders the latest ledger line; `source:"0xwork"`,
`external:true` shows external provenance + basescan link.)

---

## Commands

Run by the **agent** (no human, no Claude in the loop); **verified** by Claude. Do NOT run here.

```bash
# 0) decide the wallet (see Blockers G3): cheapest no-seed = a FRESH faucet-funded 0xwork wallet.
npm install -g @0xwork/cli
0xwork init                         # NEW Base wallet -> .env (faucet auto-funds gas ETH + AXOBOTL stake)
0xwork register --name="Anicca" --description="autonomous research/writing/code agent" \
                --capabilities=Writing,Research,Code,Data
# The earn skill must read THIS wallet for the delta proof: export PKVAR=OXWORK_WALLET_KEY (the init key).
# (Alternative: stake our external 0xa3CDd4 — needs AXOBOTL+ETH seed; see Blockers.)

# 1) BEFORE: snapshot the receiving wallet's USDC
W=<0xwork-init-wallet-address>
node -e "import('$HOME/clawd/skills/earn/lib/usdc.mjs').then(m=>m.usdcBalance('$W')).then(b=>console.log('BEFORE',b))"

# 2) ONE external wake (agent does it via the LIVE COPY; OXWORK_ANY_CATEGORY=1 since only Social is open today)
OXWORK_ANY_CATEGORY=1 EARN_MODE=execute EARN_STRATEGY=0xwork \
  PKVAR=OXWORK_WALLET_KEY OXWORK_DELIVER=$HOME/clawd/state/deliverable.md OXWORK_POLL_SECS=0 \
  bash $HOME/clawd/skills/earn/run.sh
#   -> claim+submit this wake (NARRATE: "claimed-awaiting-approval"); next wake after poster approval -> GATE-0.

# 3) VERIFY (independent) after an approved payout
node -e "import('$HOME/clawd/skills/earn/lib/usdc.mjs').then(m=>m.usdcBalance('$W')).then(b=>console.log('AFTER',b))"     # AFTER-BEFORE > 0
PAYTX=<payout tx from ledger>
node -e "import('$HOME/clawd/skills/earn/lib/verify-tx.mjs').then(m=>m.receiptStatus('$PAYTX')).then(console.log)"        # -> 0x1
curl -s https://mainnet.base.org -H 'content-type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getTransactionReceipt\",\"params\":[\"$PAYTX\"]}" \
  | node -e "process.stdin.on('data',async d=>{const r=JSON.parse(d).result;const o=await import('$HOME/clawd/skills/earn/lib/oxwork.mjs');console.log('EXTERNAL:',await o.isExternalPayout(r,'$W'))})"   # -> true
# basescan: https://basescan.org/tx/$PAYTX  (Status: Success; ERC-20 USDC transfer FROM taskPool 0xF404…C6D2 TO wallet)

# 4) classifier + tests (the false-green guard)
grep -n "external !== true\|SWAP_SOURCES" $HOME/clawd/skills/earn/lib/ledger.mjs       # proof the guard is in the COPY
node --test $HOME/clawd/skills/earn/lib/__tests__/*.test.js $HOME/clawd/skills/earn/__tests__/*.test.js

# 5) prove the running loop is wired to external revenue
grep -n "EARN_STRATEGY=0xwork" $HOME/.hermes/cron/jobs.json
```

---

## Acceptance (GATE-0 rubric — ALL must hold; swap or narration = FAIL)

1. `~/clawd/skills/earn/state/earn-ledger.jsonl` (the RUNNING body's ledger; mirror committed to
   `~/anicca` on main) has ≥1 line with `source:"0xwork"` (or `x402`), `external:true`,
   `net_usdc > 0`, `status == "0x1"`, `tx` a 66-char hash.
2. That `tx` resolves on Base to `status=0x1`.
3. Wallet USDC `after − before > 0` **and** `isExternalPayout(receipt,wallet) === true` (USDC
   `Transfer` `from = taskPool 0xF404…C6D2`, `to = wallet`). A swap fails this (no such log).
4. `isProfitable()` in the COPY (`~/clawd/.../ledger.mjs`) returns **false** for any
   `source:"swap-eth-usdc"` or any line without `external:true` (grep + `oxwork.test.js` green) —
   no `EARN_STRATEGY` value can produce a GATE-0 line from a swap.
5. `~/.hermes/cron/jobs.json` earn job invokes `run.sh` with `EARN_STRATEGY=0xwork` (grep proves it).
6. `node --test` on all earn lib tests green (incl. the swap-guard + pickTask tests).
7. aniccaai.com/me renders the line showing `source:0xwork`/`external:true` + basescan link.

**FAIL:** `source:"swap-eth-usdc"`, any line missing `external:true`, a payout tx whose USDC
`Transfer.from` is the wallet itself or a DEX router (= swap), narration only, `status=null`/`0x0`,
an uncommitted ledger, or wiring left at `EARN_STRATEGY=swap`.

---

## Blockers

| Blocker | Reality (RAW) | Cheapest path |
|---|---|---|
| **AXOBOTL stake + Base ETH for OUR external wallet** | `GET https://api.0xwork.org/quickstart` `requirements.cost` = "Requires AXOBOTL stake + Base ETH for external wallets"; `postRegistration` lists `0xwork stake --amount 40000`. Our `0xa3CDd4` holds 0.0145 USDC / 0.0008 ETH — **not** faucet-eligible (faucet funds only fresh `0xwork init` wallets, per `/connect`). | **No-seed path: use a fresh `0xwork init` wallet** — the faucet auto-funds its gas ETH + AXOBOTL stake. Set the earn skill's `PKVAR` to that wallet's key so the USDC delta proof reads the wallet that receives payouts. **Trade-off:** payouts land in the new wallet, not the canonical `0xa3CDd4`; sweep to canonical later (that sweep is itself a transfer, not a swap). If we must keep `0xa3CDd4`, a **one-time AXOBOTL stake + ~$1–3 Base ETH seed** is genuinely required (Dais-provided, or fund gas via a single accepted swap — but that swap funds gas, it is **not** the GATE-0 earn). |
| **Task supply in Anicca's wheelhouse** | Live (2026-06-16): only 2 open tasks, both `category:"Social"` ("get @jessepollak to follow…", $50). Zero Writing/Research/Code/Data. Supply is volatile (`MONEYMAKER-EVAL`: "供給は変動する"). | `OXWORK_ANY_CATEGORY=1` makes the Social task claimable when Anicca can deliver verifiable proof; otherwise wait for a doable task, **or** use the **x402-sell** fallback (instant settle, no approval wait) so a wake can still close GATE-0. |
| **Post-approval payout latency** | 0xwork payout fires only after the **poster approves** the submission — not guaranteed same wake. | Claim+submit wakes record NARRATE (never GATE-0); the first **approved** payout closes the gate. x402-sell is the same-wake alternative (no human approval). |
| **Runtime is a COPY** | `~/clawd/skills/earn` is a non-symlink copy; editing `~/anicca` won't change the loop. | The SYNC `cp` block above is mandatory; or convert `~/clawd/skills/earn` to a symlink of `~/anicca/skills/earn` (verify the OpenClaw loader follows symlinks first). |

**Genuinely required before a real GATE-0 wake:** (a) a faucet-funded `0xwork init` wallet **or** a
one-time AXOBOTL/ETH seed for `0xa3CDd4`; (b) one doable open task (or the x402-sell fallback wired);
(c) the SYNC into `~/clawd`. None of (a)–(c) justifies recording a swap as the gate.
