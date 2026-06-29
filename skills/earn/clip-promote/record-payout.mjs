// record-payout.mjs — the RECORD executor (the ONLY path that produces earned_usdc>0 = DONE).
// Verifies a promote.fun Solana withdrawal signature ON-CHAIN and appends one profitable ledger line
// IFF it is confirmed, inbound USDC delta > 0, and not already recorded (sig-keyed idempotency).
// run.sh invokes this under `env -i` (no PII) so the malice-guard in record.mjs passes. Pure logic;
// `opts.fetchImpl` injectable for tests (never touches the network in a unit test).
import { sigStatus, usdcDeltaForSig } from "../../_shared/lib/solana-verify.mjs";
import { alreadyRecordedSig } from "../../_shared/lib/ledger.mjs";
import { record } from "../lib/record.mjs";

export async function recordPayout(
  { sig, wallet, ledger, cost_usdc = 0, task = "promote.fun clip payout", wake },
  opts = {},
) {
  if (!sig || !wallet || !ledger) return { status: "bad-args", sig: sig || null };
  if (await alreadyRecordedSig(ledger, sig)) return { status: "duplicate", sig };
  const { confirmed } = await sigStatus(sig, opts);
  if (!confirmed) return { status: "unconfirmed", sig };
  const delta = await usdcDeltaForSig(sig, wallet, opts);
  if (!(delta > 0)) return { status: "zero-delta", sig, delta };
  const json = JSON.stringify({
    wallet, source: "promote.fun", task, earn_usdc: delta, cost_usdc,
    sig, confirmed: true, chain: "solana", external: true, wake,
  });
  const { profitable } = await record(json, ledger);
  return { status: profitable ? "recorded" : "rejected", sig, earn_usdc: delta };
}

// CLI: run.sh calls `env -i PATH HOME SOLANA_RPC_URL node record-payout.mjs` with SIG/WALLET/EARN_LEDGER
// in the (clean) env. Prints a JSON result line; exit 0 always (the slot never bricks on a record attempt).
if (process.argv[1] && import.meta.url.endsWith(process.argv[1].split("/").pop())) {
  const r = await recordPayout({
    sig: process.env.SIG,
    wallet: process.env.WALLET,
    ledger: process.env.EARN_LEDGER,
    cost_usdc: Number(process.env.COST_USDC || 0),
    wake: process.env.WAKE_ID,
  }).catch((e) => ({ status: "error", error: e.message }));
  console.log(JSON.stringify(r));
}
