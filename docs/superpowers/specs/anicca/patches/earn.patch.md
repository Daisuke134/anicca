# Patch — A-earn GATE-0 via REAL EXTERNAL REVENUE (0xwork), NOT swap

2026-06-16. GATE-0 = **ONE profitable wake** = wallet USDC delta > 0 from **EXTERNAL revenue**
(a third party pays Anicca for work) with a Base receipt `status=0x1` recorded in
`earn-ledger.jsonl`. This patch supersedes the "swap is earn" framing of
`A-earn-gate0-live.patch.md` for the *gate itself*: **an ETH→USDC swap is net-zero asset
liquidation — it moves Anicca's own value between tokens and does NOT count as earning.**
GATE-0 requires money to enter the wallet *from outside* (someone else's escrow paying out).

Files read (RAW evidence basis):
- `docs/superpowers/specs/anicca/patches/A-earn-gate0.patch.md` (the contract: ledger schema, acceptance)
- `docs/superpowers/specs/anicca/patches/A-earn-gate0-live.patch.md` (the swap framing this patch overrides for GATE-0)
- `docs/superpowers/specs/anicca/04-earn.md` (curated sources: nookplot, x402 sell, 0xwork)
- `docs/superpowers/specs/anicca/MONEYMAKER-EVAL.md` (0xwork = ★★★ primary external-revenue skill; live battle-test)
- `docs/superpowers/specs/anicca/10-self-funding-architecture.md` (wallet 0xa3CDd4, USDC = survival currency)
- `docs/superpowers/specs/anicca/commands/Q22.command.sh` (LITCOIN claim **then swap** — the swap leg ≠ earn)
- `docs/superpowers/specs/anicca/commands/Q30.command.sh` (Bankr token launch — fundraise/sell own token, not bounty revenue)
- `docs/superpowers/specs/anicca/commands/Q31.command.sh` (rentahuman — Anicca PAYS humans; outbound, never earn)
- `~/anicca/skills/earn/run.sh`, `SKILL.md`, `lib/{ledger,record,verify-tx,usdc}.mjs` (the live skill)
- `~/anicca/skills/registry.json` (earn slot already `status:"live"`)
- LIVE: `GET https://api.0xwork.org/manifest.json` → v4.0.0, chain Base 8453, taskPool `0xF404aFdbA46e05Af7B395FB45c43e66dB549C6D2`, usdc `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- LIVE: `https://0xwork.org/agent-quickstart` → "559 AGENTS / 368 TASKS COMPLETED / $8,013.23 PAID OUT", **zero gas, free register, faucet sends gas ETH + tokens, no funding needed**
- LIVE: wallet `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21` (derived from `BLOCKRUN_WALLET_KEY`) holds **0.014475 USDC** + **0.000801 ETH** on Base today

---

## Gaps

| # | Spec requires | RAW evidence (what exists vs spec) | Severity |
|---|---|---|---|
| G1 | GATE-0 line from **external revenue**, not swap (`04-earn.md` "ACTUALLY earns USDC"; MONEYMAKER-EVAL ③ "USDC着金"). | `run.sh` `EARN_STRATEGY=swap` (default) executes a Uniswap V3 **ETH→USDC swap** and records it as the GATE-0 line (`source:"swap-eth-usdc"`). A swap is net-zero: total wallet value is unchanged minus gas. **No external payer.** `A-earn-gate0-live.patch.md` §"Why a swap is a legitimate earn" explicitly defends this — that defense is REJECTED here for the gate. | **CRITICAL** — the gate is currently met (if at all) by an asset rotation, not by earning. |
| G2 | An external-revenue executor wired into the loop. | `run.sh` has a generic external path (`EARN_MODE=execute` + preset `EARN_TX`/`EARN_SOURCE`/`EARN_AMOUNT` → verify receipt → record) — **the plumbing exists** — but there is **no executor** that actually does external work and produces that `EARN_TX`. `04-earn.md` names `skills/earn/nookplot.mjs`, `x402-sell.mjs`, `content.mjs`; **none exist** (`find skills/earn` → only `swap`/`record`/`ledger`/`usdc`/`verify-tx`). | **CRITICAL** — nothing turns work into an inbound USDC tx. |
| G3 | A committed `state/earn-ledger.jsonl` with a real profitable line. | `~/anicca/skills/earn/state/` **does not exist** (no ledger committed). Registry earn slot is already flipped `status:"live"` with **zero verified external wake** behind it. | **HIGH** — `live` flag is unbacked by GATE-0 evidence. |
| G4 | No-seed-capital path. | 0xwork register is **free + faucet-funded** (gas ETH + $AXOBOTL auto-sent) — viable with no seed. BUT some 0xwork tasks carry a worker `stake_amount` (manifest task schema has `stake_amount`); wallet has only 0.0145 USDC, so **stake-required tasks are blocked** until a no-stake task is claimed (many are `stake_amount:null`). | **MEDIUM** — pick a `stake_amount:null` task for the first wake. |
| G5 | Earn must run "by the agent, verified by Claude — not run by Claude" (`04-earn.md`; `A-earn-gate0.patch.md` Acceptance). | Loop wiring in `A-earn-gate0-live.patch.md` points the heartbeat at `EARN_STRATEGY=swap`. To satisfy GATE-0 with external revenue the loop must default to an **external strategy** (0xwork), with swap demoted to a non-gate fallback only. | **HIGH** |

---

## Diff

### Chosen external-revenue path: **0xwork** (cite: `MONEYMAKER-EVAL.md` ★★★ primary; LIVE manifest + quickstart)

**Why this is EARN, not SWAP:** 0xwork is a Base task marketplace where a **third-party poster funds a USDC bounty into on-chain escrow** (`taskPool 0xF404aFdbA46e05Af7B395FB45c43e66dB549C6D2`). When Anicca completes the task and the poster approves, **the escrow releases USDC from the poster's funds into Anicca's wallet** — a `transfer` whose `from` is the taskPool, not Anicca. Anicca's spendable runway grows because *someone else paid it*. That is external revenue (`from != wallet`), unlike a swap where Anicca trades its own ETH for its own USDC (total value flat). The before/after USDC delta is positive **and** sourced from an external counterparty — exactly what GATE-0 demands.

Plumbing already present (reuse, do not rebuild): `run.sh` `EARN_MODE=execute` with preset
`EARN_TX` → `verify-tx.mjs receiptStatus` → `0x1` → `record.mjs` → `ledger.mjs isProfitable`.
The only NEW code is the **0xwork executor** that does the work and surfaces the payout tx.

```diff
*** NEW FILE: ~/anicca/skills/earn/lib/oxwork.mjs
+ // 0xwork external-revenue executor. A third party funds a USDC bounty into the
+ // taskPool escrow; Anicca claims an OPEN, stake-free task, submits the deliverable,
+ // and the poster's approval RELEASES USDC FROM ESCROW INTO ANICCA'S WALLET.
+ // The payout is an inbound USDC transfer (from = taskPool, to = wallet) => EXTERNAL
+ // revenue, not a swap. Pure transport: fetch + the on-chain payout tx are injectable
+ // so unit tests never touch the network or sign anything.
+ const API = process.env.OXWORK_API || "https://api.0xwork.org";
+ const USDC = (process.env.USDC_ADDRESS || "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913").toLowerCase();
+ const TASKPOOL = (process.env.OXWORK_TASKPOOL || "0xF404aFdbA46e05Af7B395FB45c43e66dB549C6D2").toLowerCase();
+
+ // Pick the first OPEN task with NO worker stake (wallet has ~0 working capital) whose
+ // category is in our capability set (Writing/Research/Code/Data — Anicca's strengths).
+ export async function pickTask(caps, opts = {}) {
+   const fetchImpl = opts.fetchImpl || globalThis.fetch;
+   const res = await fetchImpl(`${API}/tasks?status=open`);
+   if (!res.ok) throw new Error(`oxwork: tasks ${res.status}`);
+   const { tasks = [] } = await res.json();
+   const capSet = new Set(caps.map((c) => c.toLowerCase()));
+   return (
+     tasks.find(
+       (t) =>
+         (t.stake_amount === null || Number(t.stake_amount) === 0) &&
+         capSet.has(String(t.category).toLowerCase()) &&
+         Number(t.bounty_amount) > 0
+     ) || null
+   );
+ }
+
+ // GATE-0 proof: confirm the payout tx is an inbound USDC transfer to OUR wallet from the
+ // 0xwork escrow (NOT a swap). Parses the ERC-20 Transfer log (topic0 = keccak Transfer,
+ // topic2 = to == wallet) and asserts log.address == USDC && from == taskPool.
+ export async function isExternalPayout(receipt, wallet) {
+   if (!receipt || !Array.isArray(receipt.logs)) return false;
+   const TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
+   const padW = "0x" + wallet.toLowerCase().replace(/^0x/, "").padStart(64, "0");
+   const padPool = "0x" + TASKPOOL.replace(/^0x/, "").padStart(64, "0");
+   return receipt.logs.some(
+     (l) =>
+       l.address.toLowerCase() === USDC &&
+       l.topics[0] === TRANSFER &&
+       l.topics[2].toLowerCase() === padW &&        // to = our wallet
+       l.topics[1].toLowerCase() === padPool        // from = 0xwork escrow (external)
+   );
+ }
```

```diff
*** EDIT: ~/anicca/skills/earn/run.sh  (own slot; add 0xwork as the GATE-0 external strategy)
@@ MODE="${EARN_MODE:-discover}"
@@ STRATEGY="${EARN_STRATEGY:-swap}"
+ # GATE-0 default is EXTERNAL revenue. Swap is demoted to a non-gate fallback only.
+ STRATEGY="${EARN_STRATEGY:-0xwork}"
@@
+ # --- strategy=0xwork: REAL EXTERNAL REVENUE (a poster's escrow pays USDC to our wallet) ----
+ if [ "$STRATEGY" = "0xwork" ] && [ -z "${EARN_TX:-}" ]; then
+   #  The agent (no human, no Claude) drives the 0xwork CLI: register (idempotent, faucet-funded),
+   #  discover -> claim a stake-free task -> submit the deliverable. On poster approval the escrow
+   #  releases USDC; the payout tx hash is captured. (CLI: npm i -g @0xwork/cli; quickstart verified.)
+   BEFORE=$(node -e "import('$HERE/lib/usdc.mjs').then(m=>m.usdcBalance('$WLOW')).then(b=>console.log(b))")
+   RES=$(OXWORK_PKVAR="$PKVAR" python3 "$HERE/execute-0xwork.py" 2>/dev/null)   # NEW executor, mirrors execute-swap.py
+   PAYTX=$(printf '%s' "$RES" | python3 -c "import json,sys;print(json.load(sys.stdin).get('payout_tx',''))")
+   if [ -z "$PAYTX" ]; then
+     # No approved payout this wake (claimed/submitted, awaiting poster) -> NARRATE, never GATE-0.
+     JSON=$(python3 -c "import json;print(json.dumps({'wallet':'${WLOW:-unknown}','source':'0xwork','task':'claimed-awaiting-approval','earn_usdc':0,'cost_usdc':0,'wake':'$WAKE'}))")
+     OUT=$(record_line "$JSON"); echo "[earn] 0xwork narrate -> $OUT"; exit 0
+   fi
+   # Hand the externally-executed payout tx to the EXISTING verify+record path:
+   EARN_TX="$PAYTX"; EARN_SOURCE="0xwork"
+   AFTER=$(node -e "import('$HERE/lib/usdc.mjs').then(m=>m.usdcBalance('$WLOW')).then(b=>console.log(b))")
+   EARN_AMOUNT=$(node -e "console.log(Math.max(0, ($AFTER) - ($BEFORE)))")
+   EARN_COST="${EARN_COST:-0}"   # 0xwork advertises ZERO gas fees; gas (if any) measured by executor
+   EARN_TASK="$(printf '%s' "$RES" | python3 -c "import json,sys;print(json.load(sys.stdin).get('task_id','0xwork-task'))")"
+ fi
@@ (existing) "${EARN_TX:?execute mode needs EARN_TX ...}"  ## the 0xwork branch falls through to here:
+ # verify-tx.mjs -> status; record.mjs -> isProfitable (net>0 && 0x1). External-payout assertion:
+ EXT=$(node -e "import('$HERE/lib/verify-tx.mjs').then(async m=>{const r=await (await fetch(process.env.BASE_RPC_URL||'https://mainnet.base.org',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:1,method:'eth_getTransactionReceipt',params:['$EARN_TX']})})).json();const o=await import('$HERE/lib/oxwork.mjs');console.log(await o.isExternalPayout(r.result,'$WLOW'))})")
+ [ "$EXT" = "true" ] || { echo "[earn] REJECT: $EARN_TX is not an external 0xwork payout (swap/self-transfer) — NOT GATE-0"; exit 1; }
```

```diff
*** NEW FILE: ~/anicca/skills/earn/state/earn-ledger.jsonl  (committed AFTER the real wake; one line)
+ {"ts":<real>,"wallet":"0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21","source":"0xwork","task":"<taskId> <category>","earn_usdc":<bounty>,"cost_usdc":0,"net_usdc":<bounty>,"tx":"0x<66hex payout>","status":"0x1","wake":"<wake>"}
```

```diff
*** EDIT: ~/.hermes/cron/jobs.json  (runtime store, main-direct per HARD RULE #0 exception)
- EARN_MODE=execute EARN_STRATEGY=swap  bash $ANICCA_HOME/skills/earn/run.sh
+ EARN_MODE=execute EARN_STRATEGY=0xwork bash $ANICCA_HOME/skills/earn/run.sh   # external revenue = GATE-0
+ # swap stays available as EARN_STRATEGY=swap fallback ONLY (runway top-up), never the gate.
```

```diff
*** NEW FILE: ~/anicca/skills/earn/lib/__tests__/oxwork.test.js  (node:test, zero new dep — TDD)
+ // RED: pickTask skips tasks with stake_amount>0 and non-capability categories; returns null when none.
+ // RED: isExternalPayout TRUE only when a USDC Transfer log has from=taskPool AND to=wallet;
+ //      FALSE for a swap receipt (no taskPool->wallet USDC transfer) — this is the swap-vs-earn guard.
```

(`apps/landing/app/me/page.tsx` unchanged from `A-earn-gate0-live.patch.md` — it already renders the
latest ledger line; with `source:"0xwork"` it shows external-revenue provenance + basescan link.)

---

## Commands

Run by the **agent** (no human, no Claude in the loop); **verified** by Claude. Do NOT run here.

```bash
# 0) one-time: install + register the 0xwork agent (free, faucet sends gas ETH + tokens; quickstart verified)
npm install -g @0xwork/cli
0xwork init                                      # writes a Base wallet to .env (or reuse BLOCKRUN_WALLET_KEY)
0xwork register --name="Anicca" --description="autonomous research/writing/code agent" \
                --capabilities=Writing,Research,Code,Data

# 1) BEFORE: snapshot wallet USDC (external delta proof)
W=0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21
node -e "import('$HOME/anicca/skills/earn/lib/usdc.mjs').then(m=>m.usdcBalance('$W')).then(b=>console.log('BEFORE',b))"

# 2) ONE profitable wake (agent picks a stake-free Writing/Research/Code task, does it, submits)
0xwork discover
0xwork claim  <taskId>
0xwork submit <taskId> --files=output.md --summary="..."
# ... poster approves -> escrow releases USDC -> capture the payout tx hash as PAYTX

# 3) record via the live skill (verifies receipt + classifies GATE-0)
EARN_MODE=execute EARN_STRATEGY=0xwork EARN_TX=$PAYTX EARN_SOURCE=0xwork \
  EARN_AMOUNT=<bounty_usdc> EARN_COST=0 EARN_TASK=<taskId> \
  bash $HOME/anicca/skills/earn/run.sh        # prints "GATE-0 MET" iff net>0 && status 0x1

# 4) VERIFY (independent) — external delta + receipt 0x1 + external-payout assertion
node -e "import('$HOME/anicca/skills/earn/lib/usdc.mjs').then(m=>m.usdcBalance('$W')).then(b=>console.log('AFTER',b))"   # AFTER-BEFORE > 0
node -e "import('$HOME/anicca/skills/earn/lib/verify-tx.mjs').then(m=>m.receiptStatus('$PAYTX')).then(console.log)"      # -> 0x1
# external (not swap): the payout tx must carry a USDC Transfer with from=taskPool, to=wallet
curl -s https://mainnet.base.org -H 'content-type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getTransactionReceipt\",\"params\":[\"$PAYTX\"]}" \
  | node -e "process.stdin.on('data',async d=>{const r=JSON.parse(d).result;const o=await import('$HOME/anicca/skills/earn/lib/oxwork.mjs');console.log('EXTERNAL:',await o.isExternalPayout(r,'$W'))})"  # -> true
# basescan human check:  https://basescan.org/tx/$PAYTX  (Status: Success, ERC-20 USDC transfer to wallet)

# 5) unit tests green
node --test $HOME/anicca/skills/earn/lib/__tests__/*.test.js $HOME/anicca/skills/earn/__tests__/*.test.js
```

---

## Acceptance (GATE-0 rubric — ALL must hold; swap or narration = FAIL)

1. `~/anicca/skills/earn/state/earn-ledger.jsonl` committed to main with ≥1 line where
   `source` is an **external counterparty** (`"0xwork"`), `net_usdc > 0`, `status == "0x1"`,
   `tx` is a 66-char hash.
2. That `tx` resolves on Base to `status=0x1` (basescan / `eth_getTransactionReceipt`).
3. Wallet USDC `after − before > 0` **and** the payout tx contains a USDC `Transfer`
   with `from == taskPool (0xF404…C6D2)` and `to == wallet` (`isExternalPayout → true`).
   This is the literal swap-vs-earn discriminator: a swap has **no** taskPool→wallet transfer.
4. Live loop (`~/.hermes/cron/jobs.json`) invokes `earn/run.sh` with `EARN_STRATEGY=0xwork`
   (grep proves wiring); registry earn slot `status == "live"` is now backed by a real external wake.
5. `node --test` on all earn lib tests green (incl. the new `oxwork.test.js` swap-guard test).
6. aniccaai.com/me renders the line showing `source:0xwork` + basescan link.

**FAIL conditions (explicit):** `source:"swap-eth-usdc"` (asset rotation, net-zero), any line with
no `tx`/`status` (narration), `status=null`/`0x0`, an uncommitted ledger, or a payout tx whose
USDC `Transfer.from` is the wallet itself / a DEX router (= swap, not external revenue).

---

## Blockers

| Blocker | Reality (RAW) | Cheapest path |
|---|---|---|
| **External account/registration** | 0xwork requires an on-chain agent registration. RAW: `https://0xwork.org/agent-quickstart` — register is **free**, faucet **auto-sends gas ETH + 15,000 $AXOBOTL**, "No funding needed". `npm i -g @0xwork/cli` then `0xwork register`. No KYC, no human, no card. | **No seed capital required.** One-time `0xwork register` (≤60s, agent-run). |
| **Worker stake on some tasks** | Wallet `0xa3CDd4…` holds **0.0145 USDC** today. Some 0xwork tasks set `stake_amount > 0` (manifest task schema). Those are blocked. | Claim a `stake_amount:null` task (many exist) for the first wake. If only staked tasks remain, ~**$1–5 USDC seed** unlocks them — but **not needed for GATE-0** if a stake-free task is available. |
| **Task supply / approval latency** | RAW (2026-06-16): open tasks skew `category:"Social"` (e.g. id 391 "get @jessepollak to follow", bounty $50) which are influence-based, not Anicca's wheelhouse; Writing/Research/Code supply fluctuates (MONEYMAKER-EVAL notes "供給は変動する"). Payout is **after poster approval** — not guaranteed same-wake. | Loop default `EARN_STRATEGY=0xwork`; wakes with no approved payout record **NARRATE** (never GATE-0) and retry next wake. The first *approved* payout closes GATE-0. As secondary external sources, wire **x402 sell** (`04-earn.md`; instant, no approval wait) and **litcoin mining** (`Q22` — but its swap leg is NOT the earn; only the inbound mined-token→USDC *sale to a buyer* would be, and that needs a counterparty). |
| **Gas** | 0xwork advertises **ZERO gas fees** (sponsored); wallet also has 0.0008 ETH as backstop. | None — covered. |

**Genuinely required before a real wake:** (a) `0xwork register` (free, agent-run), and (b) one
available stake-free Writing/Research/Code/Data task. Neither needs Dais. If task supply in
Anicca's categories is dry at run time, GATE-0 slips to the next wake with an approved payout — it
does **not** justify falling back to a swap to "show green".
