const { test } = require("node:test");
const assert = require("node:assert");
const { execFileSync } = require("node:child_process");
const { verifyTelemetry } = require("../telemetry-verify");

test("ethers verifies a python eth_account signature over a 5.0/0.0 message", () => {
  // python emits the verbatim message AND signs it; we verify with our function.
  const py = `
import json, time
from eth_account import Account
from eth_account.messages import encode_defunct
acct = Account.from_key("0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d")
ts = int(time.time())
p = {"id": acct.address.lower(), "ts": ts, "host":"akash","geo":"US","model_live":"auto",
     "model_tier":"free","net_worth_usd": round(5.0,4), "revenue_mo_usd": round(0.0,4),
     "burn_day_usd":0, "runway_days":999, "status":"alive"}
msg = json.dumps(p, separators=(",",":"))            # emits "5.0"/"0.0"
s = Account.sign_message(encode_defunct(text=msg), private_key=acct.key).signature.hex()
sig = s if s.startswith("0x") else "0x"+s
print(json.dumps({"message": msg, "signature": sig, "ts": ts}))
`;
  let out;
  try { out = execFileSync("python3", ["-c", py], { encoding: "utf8" }); }
  catch (e) { console.log("SKIP: python3/eth_account unavailable —", e.message); return; }
  const { message, signature, ts } = JSON.parse(out);
  assert.ok(message.includes('"net_worth_usd":5.0'), "python must emit 5.0 (the bug input)");
  const r = verifyTelemetry(message, signature, { now: ts, lastTs: 0 });
  assert.strictEqual(r.ok, true);             // ethers recovers the signer from python's verbatim 5.0 message
  assert.strictEqual(r.payload.net_worth_usd, 5);
});

test("PROOF the old design was broken: re-stringifying drops the .0 (would 401)", () => {
  assert.strictEqual(
    JSON.stringify(JSON.parse('{"net_worth_usd":5.0,"revenue_mo_usd":0.0}')),
    '{"net_worth_usd":5,"revenue_mo_usd":0}'   // 5.0->5, 0.0->0 => different signed bytes
  );
});
