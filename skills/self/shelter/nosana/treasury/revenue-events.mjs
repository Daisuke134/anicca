// revenue-events.mjs — read/shape side of a NEW ledger, shelter-revenue.jsonl, living in the SAME
// state dir as shelter-cost.jsonl (via spawn/lib/state-path.js's resolveStateDir) and read with the
// SAME generic reader shelter-cost-ledger.js already uses (spawn/lib/ledger.js's readChildren) —
// not a new file-format convention, the same append-only-JSONL-with-fail-open-on-missing-file
// pattern every ledger in this repo already uses.
//
// No writer for this ledger exists yet anywhere in the colony for Franklin's Solana wallet
// specifically (see this feature's report for what was checked: the x402/Base rail's earn-ledger.jsonl
// tracks franklin1's EVM wallet, a DIFFERENT citizen; the gig/Coconala payout rail has never banked a
// transaction). Wiring a real writer (from whichever rail eventually pays this wallet) is
// deliberately OUT OF SCOPE here — this file defines the read contract + row shape so that when a
// writer exists, the solvency report picks its rows up with zero changes to the reading side. Until
// then, a missing file honestly means "no revenue channel observed yet", surfaced explicitly by
// `readShelterRevenueEvents` returning `{rows: [], sourceExists: false}` rather than a bare `[]` —
// so callers can tell "checked, found zero" apart from "file doesn't exist yet" instead of silently
// treating both the same as "$0 revenue".

import fs from "node:fs";
import { readChildren } from "../../../spawn/lib/ledger.js";

export const DEFAULT_REVENUE_LEDGER_FILENAME = "shelter-revenue.jsonl";

/**
 * I/O: read every row from `file`. Returns `{rows, sourceExists}` — `sourceExists: false` when the
 * file has never been created (distinct from `sourceExists: true, rows: []`, an empty-but-real
 * ledger, e.g. right after creation before any event lands). readChildren already fails open (empty
 * array) on ENOENT; this wrapper adds the existence flag on top without re-implementing that logic.
 */
export function readShelterRevenueEvents(file) {
  const sourceExists = fs.existsSync(file);
  const rows = readChildren(file);
  return { rows, sourceExists };
}

/**
 * Pure: shape one revenue-event row (kept out of inline object literals, mirroring
 * funding/acquire-nos.mjs's buildFundingIntentRecord convention, so the exact field set a future
 * writer must produce is documented in exactly one place).
 *
 * @param {{ts:number, amountUsd:number, from:string, chain:string, txSignature?:string, source?:string}} opts
 */
export function buildRevenueEventRecord({ ts, amountUsd, from, chain, txSignature, source }) {
  for (const [key, value] of Object.entries({ ts, amountUsd, from, chain })) {
    if (value === undefined || value === null || value === "") {
      throw new Error(`buildRevenueEventRecord: ${key} is required`);
    }
  }
  if (typeof amountUsd !== "number" || !Number.isFinite(amountUsd) || amountUsd < 0) {
    throw new Error(`buildRevenueEventRecord: amountUsd must be a non-negative finite number, got ${amountUsd}`);
  }
  return {
    ts,
    amountUsd,
    from,
    chain,
    txSignature: txSignature || null,
    source: source || null,
  };
}
