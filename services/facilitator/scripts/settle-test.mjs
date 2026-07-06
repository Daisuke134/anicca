// Real EIP-3009 gasless settle through the self-host x402-rs facilitator.
// TEST_PAYER signs a transferWithAuthorization (off-chain, no gas needed by payer),
// this script POSTs it to the facilitator's /verify then /settle, and the facilitator's
// own signer (FACILITATOR_PRIVATE_KEY) pays L2 gas to submit the on-chain tx.
//
// Usage: node settle-test.mjs (reads TEST_PAYER_PRIVATE_KEY, FACILITATOR_ADDRESS from env)
import { privateKeyToAccount } from "viem/accounts";
import { randomBytes } from "node:crypto";

const FACILITATOR_URL = process.env.FACILITATOR_URL || "http://127.0.0.1:8405";
const USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"; // Base Sepolia USDC (Circle)
const CHAIN_ID = 84532; // eip155:84532 = Base Sepolia

const payer = privateKeyToAccount(process.env.TEST_PAYER_PRIVATE_KEY);
const payTo = process.env.FACILITATOR_ADDRESS; // receiver: facilitator's own signer address
const amount = "1000"; // 0.001 USDC (6 decimals) — small real transfer, plenty left in payer's 20 USDC

const now = Math.floor(Date.now() / 1000);
const nonce = "0x" + randomBytes(32).toString("hex");

const authorization = {
  from: payer.address,
  to: payTo,
  value: amount,
  validAfter: String(now - 60),
  validBefore: String(now + 300),
  nonce,
};

const domain = { name: "USDC", version: "2", chainId: CHAIN_ID, verifyingContract: USDC };
const types = {
  TransferWithAuthorization: [
    { name: "from", type: "address" },
    { name: "to", type: "address" },
    { name: "value", type: "uint256" },
    { name: "validAfter", type: "uint256" },
    { name: "validBefore", type: "uint256" },
    { name: "nonce", type: "bytes32" },
  ],
};

const signature = await payer.signTypedData({
  domain,
  types,
  primaryType: "TransferWithAuthorization",
  message: authorization,
});

const paymentRequirements = {
  scheme: "exact",
  network: `eip155:${CHAIN_ID}`,
  amount,
  payTo,
  maxTimeoutSeconds: 300,
  asset: USDC,
  extra: { name: "USDC", version: "2" },
};

const paymentPayload = {
  x402Version: 2,
  accepted: paymentRequirements,
  payload: { signature, authorization },
};

const body = {
  x402Version: 2,
  paymentPayload,
  paymentRequirements,
};

console.log("--- payer:", payer.address, " payTo:", payTo, " amount:", amount, "---");
console.log(JSON.stringify(body, null, 2));

for (const step of ["verify", "settle"]) {
  const res = await fetch(`${FACILITATOR_URL}/${step}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = await res.json();
  console.log(`\n=== POST /${step} -> ${res.status} ===`);
  console.log(JSON.stringify(json, null, 2));
  if (step === "verify" && json.isValid === false) {
    console.error("verify failed, aborting before settle");
    process.exit(1);
  }
}
