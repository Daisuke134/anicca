// VCSDD Phase 2a RED — R10: canonicalMessage includes additive signed fields when present.
// FAILS until GREEN extends telemetry-verify.canonicalMessage.
const { test } = require("node:test");
const assert = require("node:assert");
const { canonicalMessage } = require("../telemetry-verify");

const base = { id: "0x" + "a".repeat(40), ts: 1, host: "h", geo: "US", model_live: "m",
  model_tier: "free", net_worth_usd: 1, revenue_mo_usd: 1, burn_day_usd: 0.1, runway_days: 1, status: "alive" };

test("R10: canonicalMessage includes tags when present (so they are signed)", () => {
  const msg = canonicalMessage({ ...base, tags: ["agent-hackathon"] });
  assert.ok(msg.includes("agent-hackathon"), "signed message must cover tags");
});
test("R10: canonicalMessage includes revenue_today_usd when present", () => {
  const msg = canonicalMessage({ ...base, revenue_today_usd: 3 });
  assert.ok(/revenue_today_usd/.test(msg));
});
