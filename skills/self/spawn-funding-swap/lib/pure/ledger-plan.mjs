// spawn-funding-swap pure core — REQ-004, REQ-005. planNextLeg (leg-scheduling state machine) and
// reconcileLedgerOnResume (parse/validation of the on-disk ledger). Pure, deterministic, no I/O
// (PROP-017's structural import-boundary guard) — the actual file read is effectful (ledger-store.mjs);
// interpreting its contents is pure.

/**
 * planNextLeg — REQ-004/REQ-005: given the route's leg count and the current ledger state, returns the
 * next leg to submit, or DONE (all legs confirmed, no prior completion marker), or ALREADY_COMPLETE (a
 * prior completion marker is already recorded). Never returns a leg index already `confirmed`.
 * @param {{txsRequired: number}} route
 * @param {{legs: Array<{legIndex: number, status: string}>, completedAtMs?: number|null}} ledgerState
 * @returns {{action: 'SUBMIT', legIndex: number} | {action: 'DONE'} | {action: 'ALREADY_COMPLETE'}}
 */
export function planNextLeg(route, ledgerState) {
  const legs = (ledgerState && ledgerState.legs) || [];
  const confirmedIdx = new Set(legs.filter((l) => l.status === "confirmed").map((l) => l.legIndex));
  const txsRequired = route.txsRequired;

  for (let i = 0; i < txsRequired; i++) {
    if (!confirmedIdx.has(i)) return { action: "SUBMIT", legIndex: i };
  }

  if (ledgerState && ledgerState.completedAtMs) return { action: "ALREADY_COMPLETE" };
  return { action: "DONE" };
}

/**
 * reconcileLedgerOnResume — REQ-005: pure parse/validation of the on-disk ledger's contents (raw string,
 * a plain object, or null for "never run before"). Fails closed ('CORRUPT') for unparseable/malformed
 * content — NEVER treated as "empty/start fresh" (which risks re-submitting an already-confirmed leg).
 * @param {unknown} ledgerFile
 * @returns {{legs: Array, completedAtMs: number|null, quoteSnapshot?: unknown} | 'CORRUPT'}
 */
export function reconcileLedgerOnResume(ledgerFile) {
  if (ledgerFile === null) return { legs: [], completedAtMs: null };

  let parsed;
  if (typeof ledgerFile === "string") {
    try {
      parsed = JSON.parse(ledgerFile);
    } catch {
      return "CORRUPT";
    }
  } else if (typeof ledgerFile === "object") {
    parsed = ledgerFile;
  } else {
    return "CORRUPT";
  }

  if (!parsed || typeof parsed !== "object" || !Array.isArray(parsed.legs)) return "CORRUPT";
  return { legs: parsed.legs, completedAtMs: parsed.completedAtMs ?? null, quoteSnapshot: parsed.quoteSnapshot };
}
