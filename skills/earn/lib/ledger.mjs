// Append-only, immutable ledger for state/earn-ledger.jsonl.
// One JSON object per line. Prior lines are NEVER rewritten — appendLedger only ever
// appends. The GATE-0 classifier (isProfitable) is the single source of truth for
// "1 profitable wake": net_usdc > 0 AND a real on-chain receipt status of 0x1.
import { promises as fs } from "node:fs";
import path from "node:path";

const round = (n) => Math.round(n * 1e6) / 1e6; // keep USDC at 6dp, kill fp noise

// Build a normalized ledger line. earn/cost in, net derived, ts stamped.
export function deriveLine(o) {
  const earn = Number(o.earn_usdc ?? 0);
  const cost = Number(o.cost_usdc ?? 0);
  const line = {
    ts: o.ts ?? Math.floor(Date.now() / 1000),
    wallet: o.wallet,
    source: o.source,
    task: o.task,
    earn_usdc: round(earn),
    cost_usdc: round(cost),
    net_usdc: round(earn - cost),
    wake: o.wake,
  };
  // tx/status only present for executed (on-chain) earns; absent for narrate/discovery.
  if (o.tx) line.tx = o.tx;
  if (o.status) line.status = o.status;
  return line;
}

// GATE-0 truth: a profitable wake needs a positive net AND a confirmed (0x1) tx receipt.
// narrate-only lines (no tx hash / no status) NEVER count, no matter the claimed net.
export function isProfitable(line) {
  return Boolean(line && line.tx && line.status === "0x1" && Number(line.net_usdc) > 0);
}

// Append a single line (creating the file + parent dir on first write). Append-only.
export async function appendLedger(file, line) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.appendFile(file, JSON.stringify(line) + "\n", "utf8");
  return line;
}

// Read every JSONL line into objects. Missing file -> []. Blank/garbage lines skipped.
export async function readLedger(file) {
  let raw;
  try {
    raw = await fs.readFile(file, "utf8");
  } catch (e) {
    if (e.code === "ENOENT") return [];
    throw e;
  }
  return raw
    .split("\n")
    .filter((l) => l.trim().length > 0)
    .map((l) => {
      try {
        return JSON.parse(l);
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}
