# P-gate0-external — land ONE real EXTERNAL-revenue wake (the true GATE-0), or soften the headline truthfully

> Spec: `28-product-redesign-merge-2026-06-16.md` §4. Task #3. Target: `~/anicca/skills/earn` (OSS) + live runtime.
> **The honest problem:** the existing `A-earn-gate0-live.patch.md` lands a **swap (ETH→USDC)**, but `/me` correctly
> classifies a swap as **asset liquidation, NOT external earning** (`app/me/page.tsx:91-93` `GATE0_EXTERNAL =
> !/swap|liquidat/i.test(...)` → `GATE0_MET=false`). So GATE-0-as-external-revenue (the launch-post headline
> "自律的に稼ぐ") is **genuinely unmet**. This patch lands a real EXTERNAL inflow, or softens the claim — never fakes it.

---

## §1 Reality found (cited)

| fact | evidence |
|---|---|
| swap is explicitly NOT external revenue on the live site | `app/me/page.tsx:90-94` — `GATE0_EXTERNAL`/`GATE0_MET`, "A swap is asset liquidation, not external earning" |
| earn `run.sh` already supports a NON-swap external path | `~/anicca/skills/earn/run.sh:9-12` — `EARN_TX` preset ("externally-executed earn, e.g. x402: verify that tx, record it") + `execute-0xwork.py` (`run.sh:62`) |
| an x402 worker/serve endpoint exists (an external payer pays the agent) | `~/anicca/services/x402-worker/serve.sh` (verified present; from commit `ba58449`) |
| GATE-0 unlocks ONLY on an external line | `~/anicca/skills/earn/lib/oxwork.mjs` `isExternalPayout` sets `external:true`; `lib/ledger.mjs:43-49` `isProfitable` = external + `status=0x1` + net>0 (a swap is never external) |
| the earn ledger + tx-verify primitives exist | `~/anicca/skills/earn/lib/{ledger.mjs,usdc.mjs,record.mjs}` + `lib/verify-tx.mjs` exports `receiptStatus(txHash)` (a module, NOT a CLI) |
| malice-guard requires earn use OWN wallet only | `~/anicca/skills/earn/lib/identity-guard.mjs` (P-malice-guard) |

**External-revenue definition (must satisfy `GATE0_EXTERNAL`):** USDC arrives in Anicca's OWN wallet from an
**outside payer** (an x402 client paying for a served task, or a 0xwork/bounty payout) — `source` does NOT match
`/swap|liquidat/i`, `status=0x1` on Base, USDC balance delta > 0 attributable to the external payer.

## §2 The run (two real external paths; do at least one)

### Path B — 0xwork external payout (PRIMARY; default live strategy, run.sh:58)
```bash
cd ~/anicca/skills/earn
EARN_MODE=execute EARN_STRATEGY=0xwork bash run.sh   # execute-0xwork.py performs/verifies an external-paid task;
# the recorded line gets external:true ONLY via lib/oxwork.mjs isExternalPayout → that is what unlocks GATE-0.
```

### Path A — x402-served task (alt: a real external client pays the agent)
```bash
bash ~/anicca/services/x402-worker/serve.sh   # boots the x402 endpoint + free cloudflared tunnel → public URL
# drive ONE real external payment to the endpoint (an outside wallet/client pays the x402 invoice), then record it
# as an external line (the verify path must set external:true, same gate as 0xwork — NOT a bare EARN_TX swap).
```

Either path writes a `earn-ledger.jsonl` line with `external:true`, `source∈{x402,0xwork}`, real `tx`, `net_usdc>0`.

## §3 Verify (HARD 0.24/0.31 — fresh on-chain evidence)
```bash
# 1. ledger line is external (not swap):
tail -1 ~/anicca/skills/earn/state/earn-ledger.jsonl | jq '{source,tx,net_usdc,status}'   # source must NOT be swap/liquidat
# 2. on-chain proof (verify-tx.mjs is a MODULE exporting receiptStatus, not a CLI — import it):
cd ~/anicca/skills/earn && node --input-type=module -e \
  'import {receiptStatus} from "./lib/verify-tx.mjs"; receiptStatus(process.argv[1]).then(s=>console.log(JSON.stringify(s)))' "<tx>"
# expect status=0x1; cross-check USDC delta to our wallet > 0 via basescan or lib/usdc.mjs balanceOf before/after
# 3. /me reflects it: update GATE0_WAKE in app/me/page.tsx to the real external wake (source=x402/0xwork)
#    so GATE0_EXTERNAL && GATE0_MET become TRUE — only on a genuinely external line.
```

## §4 Headline-truth fallback (if no external payer lands by launch)
If neither path lands a real external USDC inflow before launch, **do NOT** set `GATE0_MET=true`. Instead soften
launch-post line ① to the truthful: *"Anicca pays its own compute and is working toward its first profitable
external wake — full P&L is public on /dashboard"*, and keep the `/me` amber "未達" badge. Honesty over a fake green
(HARD 0.24). The dashboard already publishes the real (swap-only) ledger, so the softened claim is fully backed.

## §5 Acceptance
1. A real external ledger line (`source` not swap/liquidat, `net_usdc>0`, `status=0x1`) committed to `~/anicca` main, OR
2. the softened headline shipped (no `GATE0_MET=true`), with the amber badge intact — verified live on `/me`.
3. Either way: NO swap is presented as "external earning"; NO fake green.

## §6 Boundaries
This is a RUN + verify task on existing earn infra (no new earn strategy invented unless a minimal x402/0xwork glue is
needed). Must pass identity-guard (own wallet only). The only products-repo edit is the `GATE0_WAKE` constant on `/me`
IF a real external wake lands. Reuses A-earn-gate0 infra; this patch is the external-revenue gate it did not meet.
