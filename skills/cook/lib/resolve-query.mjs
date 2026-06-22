// resolve-query.mjs — PURE: turn the model's ANICCA_ARGS into the cook search query.
//
// Replaces the fragile bash `ARGS="${ANICCA_ARGS:-{}}"` (whose `{}` default appended a stray `}`,
// corrupting a real `{"query":"X"}` into invalid JSON so the model's query was ALWAYS dropped to a
// seed). The model's query wins; a small rotating seed is ONLY a last-resort fallback when the model
// gives nothing — so cook never re-searches the same thing wake after wake. No hardcoded STRATEGY:
// the seeds are neutral curiosity-starters, not pinned repos/links; the model's own query overrides them.

export const SEEDS = [
  "new x402 paid API agents pay for",
  "open-source DeFi yield strategy 2026 base",
  "agent micro-task marketplace USDC",
  "new onchain fee-earning protocol base",
  "sell data or research for crypto agent",
];

// @param rawArgs   the raw ANICCA_ARGS string (JSON), possibly empty/undefined/malformed
// @param hourBucket integer hour (e.g. Math.floor(Date.now()/3600e3)) — chooses the rotating seed
// @returns the search query (model's own if present & non-blank, else a rotating seed). Never throws.
export function resolveQuery(rawArgs, hourBucket) {
  let q = "";
  try {
    const parsed = JSON.parse(rawArgs || "{}");
    q = (parsed && typeof parsed.query === "string") ? parsed.query.trim() : "";
  } catch {
    q = "";
  }
  if (q) return q;
  const bucket = Number.isFinite(hourBucket) ? Math.abs(Math.trunc(hourBucket)) : 0;
  return SEEDS[bucket % SEEDS.length];
}

// CLI: `node resolve-query.mjs "$ANICCA_ARGS"` → prints the resolved query (used by run.sh).
if (import.meta.url === `file://${process.argv[1]}`) {
  const raw = process.argv[2] || "";
  const hour = Math.floor(Date.now() / 3600e3);
  process.stdout.write(resolveQuery(raw, hour));
}
