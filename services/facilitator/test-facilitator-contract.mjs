// Real-request contract test (no mock) for the self-host x402-rs facilitator.
// RED: facilitator not running -> fetch throws (connection refused).
// GREEN: `./start.sh` running -> all checks pass against the live process.
// Run: node test-facilitator-contract.mjs
const FACILITATOR_URL = process.env.FACILITATOR_URL || "http://127.0.0.1:8405";
let fail = 0;
const ok = (c, m) => { if (!c) { console.error("FAIL", m); fail++; } else console.log("ok", m); };

// 1. /supported lists our chain + signer (proves config.json loaded + key derived correctly)
const supported = await (await fetch(`${FACILITATOR_URL}/supported`)).json();
ok(
  supported.kinds?.some((k) => k.network === "eip155:84532"),
  "/supported lists eip155:84532",
);
ok(
  Array.isArray(supported.signers?.["eip155:84532"]) && supported.signers["eip155:84532"].length === 1,
  "/supported exposes exactly one signer for eip155:84532",
);

// 2. /verify with a garbage payload must NOT crash — structured error, not a 500/exception (hard 0.24 no-mock/no-crash)
const garbageRes = await fetch(`${FACILITATOR_URL}/verify`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({}),
});
const garbage = await garbageRes.json();
ok(garbageRes.status < 500, `/verify with garbage payload responds ${garbageRes.status} (no 5xx crash)`);
ok(garbage.isValid === false && typeof garbage.invalidReason === "string", "/verify with garbage payload returns structured {isValid:false, invalidReason}");

// 3. Regression guard: a real signed EIP-3009 payload must still verify true.
// (Full on-chain settle proof lives in scripts/settle-test.mjs + evidence/p2.1-facilitator-settle.md;
//  this just re-checks /verify doesn't regress using the same real tx's payload shape.)
if (process.env.TEST_PAYER_PRIVATE_KEY && process.env.FACILITATOR_ADDRESS) {
  const { privateKeyToAccount } = await import("viem/accounts");
  const { randomBytes } = await import("node:crypto");
  const payer = privateKeyToAccount(process.env.TEST_PAYER_PRIVATE_KEY);
  const payTo = process.env.FACILITATOR_ADDRESS;
  const USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e";
  const now = Math.floor(Date.now() / 1000);
  const authorization = {
    from: payer.address, to: payTo, value: "1",
    validAfter: String(now - 60), validBefore: String(now + 300),
    nonce: "0x" + randomBytes(32).toString("hex"),
  };
  const signature = await payer.signTypedData({
    domain: { name: "USDC", version: "2", chainId: 84532, verifyingContract: USDC },
    types: { TransferWithAuthorization: [
      { name: "from", type: "address" }, { name: "to", type: "address" },
      { name: "value", type: "uint256" }, { name: "validAfter", type: "uint256" },
      { name: "validBefore", type: "uint256" }, { name: "nonce", type: "bytes32" },
    ] },
    primaryType: "TransferWithAuthorization",
    message: authorization,
  });
  const paymentRequirements = {
    scheme: "exact", network: "eip155:84532", amount: "1", payTo,
    maxTimeoutSeconds: 300, asset: USDC, extra: { name: "USDC", version: "2" },
  };
  const verifyRes = await fetch(`${FACILITATOR_URL}/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      x402Version: 2,
      paymentPayload: { x402Version: 2, accepted: paymentRequirements, payload: { signature, authorization } },
      paymentRequirements,
    }),
  });
  const verify = await verifyRes.json();
  ok(verify.isValid === true, "/verify accepts a genuinely signed EIP-3009 authorization (isValid:true)");
} else {
  console.log("skip: real-signature regression check (set TEST_PAYER_PRIVATE_KEY + FACILITATOR_ADDRESS to enable)");
}

process.exit(fail ? 1 : 0);
