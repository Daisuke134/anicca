// yield-keeper.mjs — the net-positive baseline earner, DETERMINISTIC, ZERO LLM.
//
// The core finding of our earn verification: DeFi yield is the only thing that earns USDC with no
// human in the loop — but paying an LLM to "decide" to make a fixed deposit is pure waste (the
// inference burn dwarfs the yield on small capital, so the LLM loop runs net-NEGATIVE). The fix:
// the routine earner needs no brain. This keeper deploys idle USDC into the best safe stable yield
// (via the proven execute-yield.mjs) on a slow schedule, with ZERO LLM calls → ~$0 compute → the
// position simply accrues → net-positive. The LLM brain is reserved for real decisions (exploring
// new earners, solving paid tasks) — not for routine deposits.
//
// Honest: this does NOT fake earning. It only deploys real idle USDC into a real on-chain vault and
// logs the real tx. With no idle USDC it holds (the deployed position keeps accruing). Extractable
// any time via withdraw (verified: Beefy withdrawAll → USDC back).
import { spawn } from "child_process";
import fs from "fs";
import path from "path";

const HOME = process.env.HOME;
const EARN = process.env.ANICCA_EARN_YIELD || path.join(HOME, "anicca/skills/earn/execute-yield.mjs");
const LEDGER = (process.env.ANICCA_HOME || path.join(HOME, ".anicca")) + "/state/ledger.jsonl";
const INTERVAL_S = parseInt(process.env.YIELD_KEEP_INTERVAL_S || "21600", 10); // 6h — yield is passive
const RESERVE = process.env.YIELD_RESERVE_USDC || "1"; // keep $1 liquid for gas-adjacent ops

function log(obj) {
  try { fs.mkdirSync(path.dirname(LEDGER), { recursive: true }); } catch {}
  fs.appendFileSync(LEDGER, JSON.stringify({ ts: Math.floor(Date.now() / 1000), ...obj }) + "\n");
}

function runEarn() {
  return new Promise((resolve) => {
    let out = "";
    const p = spawn("node", [EARN], { env: { ...process.env, YIELD_RESERVE_USDC: RESERVE } });
    p.stdout.on("data", (d) => (out += d));
    p.stderr.on("data", () => {});
    p.on("close", () => {
      let r = null;
      try { r = JSON.parse(out.trim().split("\n").pop()); } catch {}
      resolve(r || { error: "no output", raw: out.slice(0, 200) });
    });
  });
}

async function tick() {
  const r = await runEarn();
  // record kind:yield only when an actual deposit happened; otherwise kind:yield_hold (no idle, just accruing)
  if (r && r.tx && r.status === "0x1") log({ kind: "yield", keeper: true, protocol: r.protocol, apy_pct: r.apy_pct, deposited_usdc: r.deposited_usdc, tx: r.tx });
  else log({ kind: "yield_hold", keeper: true, note: r?.abort || r?.error || "held", llm: false });
  console.log(new Date().toISOString(), "yield-keeper tick:", JSON.stringify(r));
}

await tick();
setInterval(tick, INTERVAL_S * 1000);
console.log(`[yield-keeper] running deterministically every ${INTERVAL_S}s, ZERO LLM, reserve $${RESERVE}`);
