"use strict";
// AE-ZERO-START-1 §4.4 — the measured Solana balance.
//
// The point of this reader is the sentence in the spec: "a $0.00 that was not measured is a lie". So the
// tests are mostly about refusing to return a number. Anything the RPC will not answer cleanly — a non-200,
// a JSON-RPC error body, a missing or non-integer value — has to throw, because a thrown error stops the
// report while a defaulted 0 would be published as fact.
const test = require("node:test");
const assert = require("node:assert/strict");

const { DEFAULT_SOLANA_RPC_URL, LAMPORTS_PER_SOL, formatSol, readSolBalance } = require("./solana-balance.js");

// A published RFC 8032 vector's public key, used here purely as a well-formed base58 address.
const ADDRESS = "FVen3X669xLzsi6N2V91DoiyzHzg1uAgqiT8jZ9nS96Z";

function rpc(body, init = {}) {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options, payload: JSON.parse(options.body) });
    return {
      ok: init.ok !== false,
      status: init.status == null ? 200 : init.status,
      json: async () => body,
    };
  };
  return { calls, fetchImpl };
}

test("it asks getBalance for exactly the address it was given", async () => {
  const { calls, fetchImpl } = rpc({ jsonrpc: "2.0", id: 1, result: { context: { slot: 1 }, value: 0 } });
  const balance = await readSolBalance(ADDRESS, { fetchImpl });

  assert.equal(balance, "0");
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, DEFAULT_SOLANA_RPC_URL);
  assert.equal(calls[0].payload.method, "getBalance");
  assert.deepEqual(calls[0].payload.params[0], ADDRESS);
  assert.equal(calls[0].payload.params[1].commitment, "confirmed");
});

test("a non-zero balance comes back as an exact integer string, never a float", async () => {
  // Lamports are integers and JavaScript numbers are not, so the value crosses the boundary as a string.
  const { fetchImpl } = rpc({ result: { value: 1_234_567_890 } });
  assert.equal(await readSolBalance(ADDRESS, { fetchImpl }), "1234567890");

  // The largest value JSON.parse can still represent exactly (~9,007,199 SOL, far above any real balance).
  const safe = rpc({ result: { value: Number.MAX_SAFE_INTEGER } });
  assert.equal(await readSolBalance(ADDRESS, { fetchImpl: safe.fetchImpl }), "9007199254740991");
});

test("a lamport value JSON already rounded is refused, not published as measured", async () => {
  // JSON.parse(9007199254740993) silently yields ...992. Returning that would report a balance the chain
  // never stated, which is the one thing this reader exists to prevent.
  const { fetchImpl } = rpc({ result: { value: 9007199254740993 } });
  await assert.rejects(() => readSolBalance(ADDRESS, { fetchImpl }), /balance/i);
});

test("a custom RPC url is honoured", async () => {
  const { calls, fetchImpl } = rpc({ result: { value: 5 } });
  await readSolBalance(ADDRESS, { fetchImpl, rpcUrl: "https://rpc.example/solana" });
  assert.equal(calls[0].url, "https://rpc.example/solana");
});

test("an address that is not a Solana address is refused before any request is made", async () => {
  const { calls, fetchImpl } = rpc({ result: { value: 0 } });
  for (const bad of ["", "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf", "0OIl".repeat(8), "short", null]) {
    await assert.rejects(() => readSolBalance(bad, { fetchImpl }), /address/i);
  }
  assert.equal(calls.length, 0, "a malformed address must not reach the network");
});

test("anything the RPC will not answer cleanly throws instead of defaulting to zero", async () => {
  for (const [label, body, init] of [
    ["a transport failure", { result: { value: 0 } }, { ok: false, status: 503 }],
    ["a JSON-RPC error", { error: { code: -32602, message: "Invalid param" } }, {}],
    ["a missing result", {}, {}],
    ["a null value", { result: { value: null } }, {}],
    ["a non-integer value", { result: { value: 1.5 } }, {}],
    ["a negative value", { result: { value: -1 } }, {}],
    ["a stringly value", { result: { value: "0" } }, {}],
    ["an empty body", null, {}],
  ]) {
    const { fetchImpl } = rpc(body, init);
    await assert.rejects(
      () => readSolBalance(ADDRESS, { fetchImpl }),
      /balance/i,
      `${label} must throw`,
    );
  }
});

test("an unparseable body throws rather than being treated as zero", async () => {
  const fetchImpl = async () => ({ ok: true, status: 200, json: async () => { throw new Error("bad json"); } });
  await assert.rejects(() => readSolBalance(ADDRESS, { fetchImpl }), /balance/i);
});

test("with no fetch available at all it says so instead of failing obscurely", async () => {
  // fetchImpl defaults to globalThis.fetch (same as lib/base-usdc-balance.js), so the guard is only
  // reachable when the runtime has no fetch. Removed and restored so no test ever hits the real network.
  const original = globalThis.fetch;
  globalThis.fetch = undefined;
  try {
    await assert.rejects(() => readSolBalance(ADDRESS, {}), /fetch/i);
  } finally {
    globalThis.fetch = original;
  }
});

test("lamports render as SOL exactly, with no floating point drift", () => {
  assert.equal(LAMPORTS_PER_SOL, 1_000_000_000n);
  assert.equal(formatSol("0"), "0 SOL");
  assert.equal(formatSol("1"), "0.000000001 SOL");
  assert.equal(formatSol("1000000000"), "1 SOL");
  assert.equal(formatSol("1500000000"), "1.5 SOL");
  assert.equal(formatSol("2000000001"), "2.000000001 SOL");
  // 0.1 + 0.2 arithmetic is exactly what a ledger cannot survive, so the formatter is integer-only.
  assert.equal(formatSol("300000000"), "0.3 SOL");
  assert.throws(() => formatSol("1.5"), /lamports/i);
  assert.throws(() => formatSol("-1"), /lamports/i);
});
