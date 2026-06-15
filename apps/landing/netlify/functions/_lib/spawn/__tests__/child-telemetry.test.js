const { test } = require("node:test");
const assert = require("node:assert");
const { buildChildTelemetry } = require("../child-telemetry");
const { newChildWallet } = require("../child-wallet");
const { verifyMessage } = require("ethers");

test("buildChildTelemetry produces a payload the live verifier would accept", async () => {
  const w = newChildWallet();
  const now = 1781600000;
  const { message, signature } = await buildChildTelemetry({
    privateKey: w.privateKey, host: "do", geo: "US", model_live: "x", nowSec: now,
  });
  const p = JSON.parse(message);
  // id is the child's own address, lower-cased to match the telemetry contract
  assert.equal(p.id, w.address.toLowerCase());
  assert.equal(p.ts, now);
  assert.equal(p.host, "do");
  assert.equal(p.status, "alive");
  assert.equal(p.model_tier, "free");
  assert.equal(typeof p.net_worth_usd, "number");
  // signature recovers the child's address (signer == id) — exactly telemetry-verify's gate
  assert.equal(verifyMessage(message, signature).toLowerCase(), p.id);
});

test("field order matches the canonical message contract (no signer_mismatch)", async () => {
  const w = newChildWallet();
  const { message } = await buildChildTelemetry({ privateKey: w.privateKey, host: "akash", geo: "JP", model_live: "auto", nowSec: 1781600001 });
  assert.equal(
    Object.keys(JSON.parse(message)).join(","),
    "id,ts,host,geo,model_live,model_tier,net_worth_usd,revenue_mo_usd,burn_day_usd,runway_days,status"
  );
});

test("defaults newborn economics (zero revenue, conservative net worth)", async () => {
  const w = newChildWallet();
  const { message } = await buildChildTelemetry({ privateKey: w.privateKey, host: "do", geo: "US", model_live: "x", nowSec: 1781600002 });
  const p = JSON.parse(message);
  assert.equal(p.revenue_mo_usd, 0);
  assert.ok(p.runway_days >= 0);
  assert.ok(p.net_worth_usd >= 0);
});
