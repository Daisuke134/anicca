// Append-only, immutable ledger for state/earn-ledger.jsonl.
// One JSON object per line. Prior lines are NEVER rewritten — appendLedger only ever
// appends. The GATE-0 classifier (isProfitable) is the single source of truth for
// "1 profitable wake": net_usdc > 0 AND a real on-chain receipt status of 0x1.
//
// ledger-uniqueness (REQ-005): TWO deliberately separate canonical ledgers exist per
// instance — do not "fix" the split by merging them.
//   1. `<ANICCA_HOME>/state/earn-ledger.jsonl` — founder-loop's own GATE-0 ledger
//      (skills/self/founder-loop/record-earn.mjs is the ONLY writer; EVM/Base-RPC-verified
//      external inflow only, wallet-pinned). Purpose: "did the founder wallet receive real
//      external USDC" — founder-loop.sh's literal done-check.
//   2. `<ANICCA_HOME>/skills/earn/state/earn-ledger.jsonl` — THIS file's own module, and the
//      canonical general multi-strategy ledger (x402/sol-trade/hl-trade/gig/cook/…, many
//      writers, many wallets/chains). `resolveEarnLedgerPath` below resolves THIS path.
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

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
  // fill_tid is the Hyperliquid equivalent of tx/sig: the settled fill's own stable integer id
  // (hl-realized-pnl REQ-C2). Passed through unchanged when present; absent as a key otherwise.
  if (o.fill_tid != null) line.fill_tid = o.fill_tid;
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
  // chain-correct confirmation: EVM (Base) receipt 0x1 OR Solana confirmed signature OR a
  // Hyperliquid fill (hl-realized-pnl REQ-C3) — the live userFills response for this instance's
  // own address IS the receipt (no separate broadcast/confirmation step the way an EVM tx can
  // still revert or a Solana signature can still land unconfirmed).
  const evmOk = Boolean(line.tx) && line.status === "0x1";
  const solOk = Boolean(line.sig) && line.confirmed === true;
  const hlOk = line.chain === "hyperliquid" && line.fill_tid != null && line.confirmed === true;
  return evmOk || solOk || hlOk;
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

// ledger-uniqueness REQ-001: canonical general-earn-ledger path resolver. Pure — computes a
// string only, never touches the filesystem. Mirrors
// skills/earn/self-improve/lib/ledger_reader.py::resolve_ledger_path()'s exact two-branch
// priority so both languages agree on ONE logical location by construction:
//   1. ANICCA_HOME (explicit `home`, else `env.ANICCA_HOME`, else `process.env.ANICCA_HOME`)
//      when non-empty -> <that>/skills/earn/state/earn-ledger.jsonl.
//   2. else -> this module's own file-relative earn/state/ (climbs _shared/lib -> _shared ->
//      skills, mirrors the Python module's lib -> self-improve -> earn climb).
// Resolves FRESH on every call (REQ-RL3 convention) — never a frozen module-level constant.
const EARN_LEDGER_FILENAME = "earn-ledger.jsonl"; // single source of truth for the filename both branches below join onto

export function resolveEarnLedgerPath({ home, env } = {}) {
  const effectiveEnv = env !== undefined ? env : process.env;
  const aniccaHome = home && home !== "" ? home : effectiveEnv && effectiveEnv.ANICCA_HOME;
  if (aniccaHome) {
    return {
      path: path.join(aniccaHome, "skills", "earn", "state", EARN_LEDGER_FILENAME),
      resolved: true,
      resolutionSource: "anicca_home_env",
    };
  }

  // this file: <root>/skills/_shared/lib/ledger.mjs
  const libDir = path.dirname(fileURLToPath(import.meta.url)); // skills/_shared/lib
  const sharedDir = path.dirname(libDir); // skills/_shared
  const skillsDir = path.dirname(sharedDir); // skills
  return {
    path: path.join(skillsDir, "earn", "state", EARN_LEDGER_FILENAME),
    resolved: true,
    resolutionSource: "file_relative_default",
  };
}

// ledger-uniqueness REQ-002: wallet-based allow-list filter over already-parsed ledger rows
// (the output of readLedger). Pure, read-only, never mutates `rows` or any row object —
// Array.prototype.filter always returns a NEW array and this function never assigns into a
// row. `ownWallets` is a string or array of strings (this instance's own wallet address(es));
// omitted/empty means "no known own wallet", so every walleted row is excluded (fail-closed —
// see REQ-002 edge cases). A row with NO `wallet` key (Solana/Hyperliquid/narrate rows never
// stamp an EVM wallet) always passes through: it is never cross-instance-attributable by this
// check. Comparison is case-insensitive. This is an ALLOW-list (not the SHARED blacklist
// pinned in record-earn.mjs:39), so it fails closed against wallets not yet known to be
// compromised, not only the three currently-pinned ones.
export function filterOwnWalletRows(rows, ownWallets) {
  const inputRows = Array.isArray(rows) ? rows : [];
  const ownList = ownWallets == null ? [] : Array.isArray(ownWallets) ? ownWallets : [ownWallets];
  const ownSet = new Set(
    ownList.filter((w) => typeof w === "string" && w.length > 0).map((w) => w.toLowerCase())
  );
  return inputRows.filter((row) => {
    if (!row || typeof row !== "object") return false;
    const wallet = row.wallet;
    if (wallet === undefined || wallet === null) return true; // walletless row: always passes
    if (typeof wallet !== "string" || wallet.length === 0) return false; // no proof of ownership
    return ownSet.has(wallet.toLowerCase());
  });
}
