"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { recoverTypedDataAddress } = require("viem");

const {
  BASE_USDC,
  TRANSFER_TOPIC,
  settleBaseUsdc,
} = require("./base-usdc-payout.js");

const PRIVATE_KEY = `0x${"0".repeat(63)}1`;
const WALLET = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf";
const DESTINATION = "0x6592AA47ccAC10031253551D3CC30fC64Ba7edc7";
const TX = `0x${"a".repeat(64)}`;
const NONCE = Buffer.alloc(32, 7);

function response(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

function addressTopic(address) {
  return `0x${address.slice(2).toLowerCase().padStart(64, "0")}`;
}

function exactReceipt(overrides = {}) {
  return {
    transactionHash: TX,
    status: "0x1",
    blockNumber: "0x7b",
    logs: [{
      address: BASE_USDC,
      transactionHash: TX,
      topics: [
        TRANSFER_TOPIC,
        addressTopic(WALLET),
        addressTopic(DESTINATION),
      ],
      data: "0x6acfc0",
    }],
    ...overrides,
  };
}

function boundaries(overrides = {}) {
  const calls = [];
  const fetchImpl = async (url, init) => {
    const body = JSON.parse(init.body);
    calls.push({ kind: String(url).endsWith("/verify") ? "verify" : "settle", url: String(url), body });
    if (String(url).endsWith("/verify")) return response(200, { isValid: true });
    return response(200, { success: true, transaction: TX, payer: WALLET });
  };
  const rpcCall = async (method) => {
    calls.push({ kind: method });
    if (method === "eth_chainId") return "0x2105";
    if (method === "eth_getTransactionReceipt") return exactReceipt();
    throw new Error(`unexpected RPC ${method}`);
  };
  return {
    calls,
    fetchImpl,
    rpcCall,
    randomBytes: () => NONCE,
    ...overrides,
  };
}

function request(overrides = {}) {
  return {
    privateKey: PRIVATE_KEY,
    walletAddress: WALLET,
    destination: DESTINATION,
    amountAtomic: "7000000",
    payoutId: "tenant:u1:ledger-through-entry-42",
    facilitatorUrl: "http://127.0.0.1:8405",
    nowMs: Date.parse("2026-07-27T12:00:00.000Z"),
    ...overrides,
  };
}

test("success signs the Base USDC authorization, verifies, settles, and accepts one exact receipt", async () => {
  const deps = boundaries();
  const result = await settleBaseUsdc(request(), deps);

  assert.deepEqual(result, {
    txHash: TX,
    amountAtomic: "7000000",
    from: WALLET,
    to: DESTINATION,
    blockNumber: "123",
  });
  assert.deepEqual(deps.calls.map((call) => call.kind), [
    "verify", "settle", "eth_chainId", "eth_getTransactionReceipt",
  ]);

  const signed = deps.calls[0].body;
  assert.equal(signed.x402Version, 2);
  assert.equal(signed.paymentRequirements.network, "eip155:8453");
  assert.equal(signed.paymentRequirements.asset, BASE_USDC);
  assert.equal(signed.paymentRequirements.amount, "7000000");
  assert.equal(signed.paymentRequirements.payTo, DESTINATION);
  assert.equal(signed.paymentPayload.payload.authorization.from, WALLET);
  assert.equal(signed.paymentPayload.payload.authorization.to, DESTINATION);
  assert.equal(
    signed.paymentPayload.payload.authorization.nonce,
    "0x6776c2a0741f3207703c0658eb58bcce4e3d2aec9c8f90564591173d5cabae78",
  );
  assert.deepEqual(deps.calls[1].body, signed, "settle must receive the same authorization verify accepted");

  const recovered = await recoverTypedDataAddress({
    domain: {
      name: "USD Coin",
      version: "2",
      chainId: 8453,
      verifyingContract: BASE_USDC,
    },
    types: {
      TransferWithAuthorization: [
        { name: "from", type: "address" },
        { name: "to", type: "address" },
        { name: "value", type: "uint256" },
        { name: "validAfter", type: "uint256" },
        { name: "validBefore", type: "uint256" },
        { name: "nonce", type: "bytes32" },
      ],
    },
    primaryType: "TransferWithAuthorization",
    message: signed.paymentPayload.payload.authorization,
    signature: signed.paymentPayload.payload.signature,
  });
  assert.equal(recovered, WALLET);
});

test("the protected key must derive the stored agent wallet before any network call", async () => {
  const deps = boundaries();
  await assert.rejects(() => settleBaseUsdc(request({
    walletAddress: DESTINATION,
  }), deps), /signer|wallet/i);
  assert.equal(deps.calls.length, 0);
});

test("invalid destination and non-positive or fractional amounts fail before signing", async () => {
  for (const bad of [
    request({ destination: "0xdead" }),
    request({ amountAtomic: "0" }),
    request({ amountAtomic: "-1" }),
    request({ amountAtomic: "1.2" }),
  ]) {
    const deps = boundaries();
    await assert.rejects(() => settleBaseUsdc(bad, deps), /destination|amount/i);
    assert.equal(deps.calls.length, 0);
  }
});

test("only the loopback self-hosted facilitator may receive the signed payload", async () => {
  const deps = boundaries();
  await assert.rejects(() => settleBaseUsdc(request({
    facilitatorUrl: "https://facilitator.attacker.example",
  }), deps), /loopback|facilitator/i);
  assert.equal(deps.calls.length, 0);
});

test("one logical payout always reuses one authorization nonce, so concurrent retries cannot both settle", async () => {
  const first = boundaries({ randomBytes: () => Buffer.alloc(32, 1) });
  const second = boundaries({ randomBytes: () => Buffer.alloc(32, 2) });
  await settleBaseUsdc(request(), first);
  await settleBaseUsdc(request(), second);

  const firstNonce = first.calls[0].body.paymentPayload.payload.authorization.nonce;
  const secondNonce = second.calls[0].body.paymentPayload.payload.authorization.nonce;
  assert.equal(firstNonce, secondNonce);
  assert.notEqual(firstNonce, `0x${Buffer.alloc(32, 1).toString("hex")}`);
  assert.notEqual(firstNonce, `0x${Buffer.alloc(32, 2).toString("hex")}`);

  const missing = boundaries();
  await assert.rejects(() => settleBaseUsdc(request({ payoutId: "" }), missing), /payoutId/i);
  assert.equal(missing.calls.length, 0);
});

test("a verify refusal aborts before settle and chain confirmation", async () => {
  const deps = boundaries({
    fetchImpl: async (url) => {
      deps.calls.push({ kind: String(url).endsWith("/verify") ? "verify" : "settle" });
      return response(200, { isValid: false, invalidReason: "insufficient_funds" });
    },
  });
  await assert.rejects(() => settleBaseUsdc(request(), deps), /verify.*insufficient_funds/i);
  assert.deepEqual(deps.calls.map((call) => call.kind), ["verify"]);
});

test("a settle refusal is never dressed up as a transfer", async () => {
  const deps = boundaries({
    fetchImpl: async (url) => {
      const kind = String(url).endsWith("/verify") ? "verify" : "settle";
      deps.calls.push({ kind });
      return kind === "verify"
        ? response(200, { isValid: true })
        : response(500, { success: false, errorReason: "broadcast failed" });
    },
  });
  await assert.rejects(() => settleBaseUsdc(request(), deps), /settle.*broadcast failed/i);
  assert.deepEqual(deps.calls.map((call) => call.kind), ["verify", "settle"]);
});

test("a successful facilitator response on any chain except Base mainnet is rejected", async () => {
  const deps = boundaries({
    rpcCall: async (method) => {
      deps.calls.push({ kind: method });
      return method === "eth_chainId" ? "0x14a34" : exactReceipt();
    },
  });
  await assert.rejects(() => settleBaseUsdc(request(), deps), /chain/i);
  assert.deepEqual(deps.calls.map((call) => call.kind), ["verify", "settle", "eth_chainId"]);
});

test("a failed receipt or any non-exact USDC Transfer evidence is rejected", async () => {
  const badReceipts = [
    exactReceipt({ status: "0x0" }),
    exactReceipt({ transactionHash: `0x${"b".repeat(64)}` }),
    exactReceipt({ logs: [] }),
    exactReceipt({ logs: [exactReceipt().logs[0], exactReceipt().logs[0]] }),
    exactReceipt({ logs: [{ ...exactReceipt().logs[0], data: "0x6acfbf" }] }),
    exactReceipt({ logs: [{
      ...exactReceipt().logs[0],
      topics: [TRANSFER_TOPIC, addressTopic(WALLET), addressTopic(WALLET)],
    }] }),
  ];

  for (const receipt of badReceipts) {
    const deps = boundaries({
      rpcCall: async (method) => {
        deps.calls.push({ kind: method });
        return method === "eth_chainId" ? "0x2105" : receipt;
      },
    });
    await assert.rejects(() => settleBaseUsdc(request(), deps), /receipt|transfer/i);
  }
});
