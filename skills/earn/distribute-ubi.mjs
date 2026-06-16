// distribute-ubi.mjs — the bridge run.sh calls after a PROFITABLE external wake.
// Reads sibling-AI wallets (self/spawn children.jsonl) + human allow-list, plans the split
// (lib/ubi.mjs, pure+tested), and on outcome=send shells execute-ubi.py to do the real ERC20
// transfers. Appends ONE audit line to state/ubi-ledger.jsonl (own-side; NOT the earn ledger).
// Fail-soft: any error logs + records a 'skipped' line and exits 0 — the earn already succeeded,
// UBI must never brick the wake. NO FAKE: outcome 'done' is written ONLY after a real tx (0x1).
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { deriveLine, readLedger, appendLedger } from "./lib/ledger.mjs";
import { buildRecipients, planUbi } from "./lib/ubi.mjs";
import { usdcBalance } from "./lib/usdc.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const UBI_LEDGER = process.env.UBI_LEDGER || path.join(__dirname, "state", "ubi-ledger.jsonl");
const CHILDREN = process.env.UBI_CHILDREN ||
  path.join(__dirname, "..", "self", "spawn", "state", "children.jsonl");

async function readChildWallets(file) {
  try {
    const raw = await fs.readFile(file, "utf8");
    return raw.split("\n").map((l) => l.trim()).filter(Boolean)
      .map((l) => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean)
      .filter((r) => (r.status ? r.status === "active" : true))
      // child-spec.js:37 persists the sibling wallet under `wallet` (buildChildSpec `wallet: childWallet`).
      .map((r) => r.wallet).filter(Boolean);
  } catch (e) { if (e.code === "ENOENT") return []; throw e; }
}

async function readHumanWallets() {
  const fromEnv = (process.env.UBI_HUMAN_WALLETS || "").split(",").map((s) => s.trim()).filter(Boolean);
  if (fromEnv.length) return fromEnv;
  const f = process.env.UBI_RECIPIENTS_FILE || path.join(__dirname, "state", "ubi-recipients.json");
  try { const j = JSON.parse(await fs.readFile(f, "utf8")); return Array.isArray(j.human) ? j.human : []; }
  catch { return []; }
}

export async function distribute(rawLine, opts = {}) {
  // run.sh passes the SAME JSON it handed record.mjs: it has earn_usdc/cost_usdc but NO net_usdc.
  // Re-derive through ledger.mjs deriveLine (the single SSOT) so net_usdc is computed identically to
  // the earn ledger; deriveLine carries tx/status/external through, so isProfitable() can pass.
  const fundingLine = deriveLine(rawLine);
  const sender = (fundingLine.wallet || "").toLowerCase();
  const childWallets = await readChildWallets(opts.childrenFile || CHILDREN);
  const humanWallets = await readHumanWallets();
  const recipients = buildRecipients({ childWallets, humanWallets, sender });
  const ubiLines = await readLedger(opts.ubiLedger || UBI_LEDGER);
  const dryRun = process.env.UBI_DRY_RUN === "1";
  // live balance for the overspend guard (best-effort; null => guard skipped, executor re-checks
  // before any real send). In dry-run we SKIP the live RPC read entirely so dry-run is fully
  // offline + deterministic — a real send re-verifies balance anyway, so safety is unchanged.
  // opts.balanceFn (injectable, default usdc.mjs usdcBalance) lets a test stub the balance.
  const balanceFn = opts.balanceFn || usdcBalance;
  let walletBalanceUsdc = null;
  if (!dryRun && sender) {
    try { walletBalanceUsdc = await balanceFn(sender); } catch { /* offline-safe */ }
  }
  const cfg = {
    shareBps: parseInt(process.env.UBI_SHARE_BPS || "1000", 10),
    minPoolUsdc: Number(process.env.UBI_MIN_POOL_USDC || "0.10"),
    dryRun,
    walletBalanceUsdc,
  };
  const plan = planUbi({ fundingLine, recipients, cfg, ubiLines });
  const base = { kind: "ubi", ts: Math.floor(Date.now() / 1000), wallet: sender, wake: plan.wake,
    share_bps: cfg.shareBps, pool_usdc: plan.pool_usdc ?? 0, recipients: recipients.length };

  if (plan.outcome !== "send") {
    const line = { ...base, outcome: plan.outcome === "dry" ? "dry" : "skipped", reason: plan.reason || plan.outcome };
    await appendLedger(opts.ubiLedger || UBI_LEDGER, line);
    return { line, sent: false };
  }
  // outcome=send: do the REAL transfers via the python executor (signs with the same wallet key).
  const res = spawnSync("python3", [path.join(__dirname, "execute-ubi.py")], {
    encoding: "utf8",
    env: { ...process.env, UBI_PLAN: JSON.stringify(plan) },
  });
  let out = {}; try { out = JSON.parse((res.stdout || "").trim().split("\n").pop() || "{}"); } catch { /* */ }
  const ok = Array.isArray(out.txs) && out.txs.length > 0 && out.txs.every((t) => t.status === "0x1");
  const line = ok
    ? { ...base, outcome: "done", per_base: plan.per_base, txs: out.txs }       // NO FAKE: only after 0x1
    : { ...base, outcome: "skipped", reason: out.error || "transfer_failed", txs: out.txs || [] };
  await appendLedger(opts.ubiLedger || UBI_LEDGER, line);
  return { line, sent: ok };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const fundingLine = JSON.parse(process.argv[2] || "{}");
  distribute(fundingLine)
    .then(({ line, sent }) => { console.log(sent ? "UBI_SENT" : "UBI_NOOP"); console.error(JSON.stringify(line)); })
    .catch((e) => { console.error("distribute-ubi error:", e.message); process.exit(0); }); // fail-soft
}
