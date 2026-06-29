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
  // tx/status only present for executed EVM (Base) earns; absent for narrate/discovery.
  if (o.tx) line.tx = o.tx;
  if (o.status) line.status = o.status;
  // sig/confirmed/chain are the Solana equivalents (e.g. promote.fun USDC-Solana payout). MUST be
  // carried through or isProfitable can never see the on-chain proof on a Solana line.
  if (o.sig) line.sig = o.sig;
  if (o.confirmed === true) line.confirmed = true;
  if (o.chain) line.chain = o.chain;
  if (o.external === true) line.external = true; // set only after external-payout assertion
  return line;
}

// A swap (Anicca trading its own ETH for its own USDC) is net-zero asset rotation and is NOT
// earning. GATE-0 requires EXTERNAL revenue: an inbound USDC transfer to our wallet from a
// counterparty (0xwork escrow, x402 payer). The classifier therefore demands:
//   tx present  &&  status 0x1  &&  net_usdc > 0  &&  external == true  &&  source not a swap.
// `external` is set ONLY by run.sh after asserting an inbound USDC Transfer whose `from` is an
// approved external payer (see oxwork.isExternalPayout / x402 settle proof). A swap line can
// never set external:true, so no env var (EARN_STRATEGY=swap) can re-open false-green.
const SWAP_SOURCES = new Set(["swap-eth-usdc", "swap", "swap-usdc-eth"]);

// GATE-0 truth: a profitable wake needs a positive net, a confirmed (0x1) tx receipt, AND
// proven external revenue. narrate-only lines (no tx hash / no status) NEVER count; swap lines
// (asset rotation) NEVER count; any line without external:true NEVER counts.
export function isProfitable(line) {
  if (!line) return false;
  if (!(Number(line.net_usdc) > 0)) return false;
  if (SWAP_SOURCES.has(String(line.source))) return false; // asset rotation is never GATE-0
  if (line.external !== true) return false; // require proven external inbound
  // chain-correct confirmation: EVM (Base) receipt 0x1 OR Solana confirmed signature.
  const evmOk = Boolean(line.tx) && line.status === "0x1";
  const solOk = Boolean(line.sig) && line.confirmed === true;
  return evmOk || solOk;
}

// sig-keyed idempotency for Solana payouts: true iff a ledger line already carries this signature.
// The append-only ledger has no built-in dedup; the RECORD wake calls this before appending so a
// re-run of the same withdrawal never double-counts. Pure over readLedger (missing file -> false).
export async function alreadyRecordedSig(file, sig) {
  if (!sig) return false;
  const rows = await readLedger(file);
  return rows.some((r) => r && r.sig === sig);
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
