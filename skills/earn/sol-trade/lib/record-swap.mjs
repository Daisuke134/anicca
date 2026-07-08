// record-swap.mjs — record the on-chain USDC P&L of a sol-trade Jupiter swap (WIN *or* LOSS) so
// isProfitable / self-eval can finally see Franklin's own realized results. Mirrors the proven
// clip-promote/record-payout.mjs pipeline (sigStatus -> usdcDeltaForSig -> record) with ONE deliberate
// difference: record-payout gates on delta>0 (a payout confirmation); this records ANY confirmed delta,
// because REQ-002's purpose is P&L VISIBILITY (a loss must be recorded too, or the guard/self-eval is
// blind to it). sig-keyed idempotency. run.sh invokes this under `env -i` so record.mjs's malice-guard
// passes. Never throws to the caller (the slot must never brick on a record attempt).
import { sigStatus, usdcDeltaForSig } from "../../../_shared/lib/solana-verify.mjs";
import { alreadyRecordedSig } from "../../../_shared/lib/ledger.mjs";
import { record } from "../../lib/record.mjs";

export async function recordSwap(
  { sig, wallet, ledger, task = "jupiter swap round-trip", wake },
  opts = {},
) {
  if (!sig || !wallet || !ledger) return { status: "bad-args", sig: sig || null };
  if (await alreadyRecordedSig(ledger, sig)) return { status: "duplicate", sig };
  const { confirmed } = await sigStatus(sig, opts);
  if (!confirmed) return { status: "unconfirmed", sig };
  const delta = await usdcDeltaForSig(sig, wallet, opts);
  if (delta === null || delta === undefined || Number.isNaN(delta)) {
    return { status: "no-delta", sig };
  }
  // net_usdc = earn - cost = delta, keeping earn_usdc/cost_usdc non-negative for both win and loss.
  const earn_usdc = delta > 0 ? delta : 0;
  const cost_usdc = delta < 0 ? -delta : 0;
  const json = JSON.stringify({
    wallet, source: "sol-trade", task, earn_usdc, cost_usdc,
    sig, confirmed: true, chain: "solana", external: true, wake,
  });
  const { profitable } = await record(json, ledger);
  return { status: "recorded", sig, net_usdc: delta, profitable };
}

// CLI: run.sh calls `env -i PATH HOME SOLANA_RPC_URL SIG WALLET EARN_LEDGER WAKE_ID node record-swap.mjs`.
// Prints a JSON result line; never exits non-zero (the slot never bricks on a record attempt).
if (process.argv[1] && import.meta.url.endsWith(process.argv[1].split("/").pop())) {
  const r = await recordSwap({
    sig: process.env.SIG,
    wallet: process.env.WALLET,
    ledger: process.env.EARN_LEDGER,
    wake: process.env.WAKE_ID,
  }).catch((e) => ({ status: "error", error: e.message }));
  console.log(JSON.stringify(r));
}
