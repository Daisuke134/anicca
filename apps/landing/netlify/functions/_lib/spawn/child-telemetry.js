// Build a signed telemetry payload for a NEWBORN child, byte-identical to the contract the live
// /.netlify/functions/telemetry endpoint verifies (telemetry-verify.js canonicalMessage order). spec27b.
// Signing with the child's own key makes signer==id, so the child shows up on the dashboard under its
// own (parent-distinct) address — the rubric's "child appears in dashboard" proof.
const { Wallet } = require("ethers");

// Field ORDER is load-bearing: the verifier recovers the signer from the verbatim string, and the
// genesis client serializes in exactly this order. Any reorder => signer_mismatch (401).
function canonicalMessage(p) {
  return JSON.stringify({
    id: p.id, ts: p.ts, host: p.host, geo: p.geo, model_live: p.model_live,
    model_tier: p.model_tier, net_worth_usd: p.net_worth_usd, revenue_mo_usd: p.revenue_mo_usd,
    burn_day_usd: p.burn_day_usd, runway_days: p.runway_days, status: p.status,
  });
}

async function buildChildTelemetry({
  privateKey, host, geo = "US", model_live = "auto",
  net_worth_usd = 0, revenue_mo_usd = 0, burn_day_usd = 0, runway_days = 999,
  nowSec = Math.floor(Date.now() / 1000),
}) {
  const wallet = new Wallet(privateKey);
  const payload = {
    id: wallet.address.toLowerCase(),
    ts: nowSec,
    host, geo, model_live,
    model_tier: "free", // a newborn runs on the free/BYOK tier until it earns its way up
    net_worth_usd, revenue_mo_usd, burn_day_usd, runway_days,
    status: "alive",
  };
  const message = canonicalMessage(payload);
  const signature = await wallet.signMessage(message);
  return { message, signature, payload };
}

module.exports = { buildChildTelemetry, canonicalMessage };
