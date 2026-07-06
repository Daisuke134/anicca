// ensure-agent-id.test.mjs — orchestration-layer tests for lib/ensure-agent-id.mjs. Injects fake
// register/verify implementations (no real network, no real testnet funds) to exercise the caching
// logic itself: register-once, reuse-when-valid, never-trust-a-stale-or-foreign cache. Mirrors
// __tests__/gig.test.mjs's dependency-injection style (fakes replace EXTERNAL I/O only).
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";
import { ensureAgentId } from "../lib/ensure-agent-id.mjs";

async function tmpCacheFile() {
  const d = await fs.mkdtemp(path.join(os.tmpdir(), "gig-agentid-"));
  return path.join(d, "gig-agent-id.json");
}

function counting(fn) {
  const calls = [];
  const wrapped = async (...args) => {
    calls.push(args);
    return fn(...args);
  };
  wrapped.calls = calls;
  return wrapped;
}

test("ensureAgentId: no cache -> registers on-chain once and writes the cache", async () => {
  const cacheFile = await tmpCacheFile();
  const pk = generatePrivateKey();
  const address = privateKeyToAccount(pk).address;
  const registerFn = counting(async () => ({ ok: true, agentId: "42", address, tx: "0xdeadbeef" }));
  const verifyFn = counting(async () => ({ ok: true, valid: true }));

  const r = await ensureAgentId({ privateKey: pk, cacheFile, registerFn, verifyFn });

  assert.equal(r.ok, true);
  assert.equal(r.agentId, "42");
  assert.equal(r.cached, false);
  assert.equal(registerFn.calls.length, 1, "must register on-chain when no cache exists");
  assert.equal(verifyFn.calls.length, 0, "no cache to verify yet");

  const written = JSON.parse(await fs.readFile(cacheFile, "utf8"));
  assert.equal(written.agentId, "42");
  assert.equal(written.address.toLowerCase(), address.toLowerCase());
});

test("ensureAgentId: valid cache for the SAME address -> reuses it, never re-registers", async () => {
  const cacheFile = await tmpCacheFile();
  const pk = generatePrivateKey();
  const address = privateKeyToAccount(pk).address;
  await fs.writeFile(cacheFile, JSON.stringify({ address, agentId: "7" }));

  const registerFn = counting(async () => ({ ok: true, agentId: "999", address }));
  const verifyFn = counting(async ({ agentId, expectedAddress }) => ({
    ok: true,
    valid: agentId === "7" && expectedAddress.toLowerCase() === address.toLowerCase(),
  }));

  const r = await ensureAgentId({ privateKey: pk, cacheFile, registerFn, verifyFn });

  assert.equal(r.ok, true);
  assert.equal(r.agentId, "7");
  assert.equal(r.cached, true);
  assert.equal(registerFn.calls.length, 0, "must NOT mint a duplicate identity when the cache is valid");
  assert.equal(verifyFn.calls.length, 1, "must re-verify the cached agentId on-chain before trusting it");
});

test("ensureAgentId: cache belongs to a DIFFERENT address (foreign/stale) -> ignored, registers fresh", async () => {
  const cacheFile = await tmpCacheFile();
  const pk = generatePrivateKey();
  const address = privateKeyToAccount(pk).address;
  const foreignAddress = privateKeyToAccount(generatePrivateKey()).address;
  await fs.writeFile(cacheFile, JSON.stringify({ address: foreignAddress, agentId: "1" }));

  const registerFn = counting(async () => ({ ok: true, agentId: "55", address }));
  const verifyFn = counting(async () => ({ ok: true, valid: true }));

  const r = await ensureAgentId({ privateKey: pk, cacheFile, registerFn, verifyFn });

  assert.equal(r.ok, true);
  assert.equal(r.agentId, "55");
  assert.equal(r.cached, false);
  assert.equal(registerFn.calls.length, 1, "a cache for a different address must never be reused");
  assert.equal(verifyFn.calls.length, 0);
});

test("ensureAgentId: cache no longer verifies on-chain (revoked/wrong) -> falls through to register fresh", async () => {
  const cacheFile = await tmpCacheFile();
  const pk = generatePrivateKey();
  const address = privateKeyToAccount(pk).address;
  await fs.writeFile(cacheFile, JSON.stringify({ address, agentId: "7" }));

  const registerFn = counting(async () => ({ ok: true, agentId: "999", address }));
  const verifyFn = counting(async () => ({ ok: true, valid: false })); // on-chain says this isn't valid anymore

  const r = await ensureAgentId({ privateKey: pk, cacheFile, registerFn, verifyFn });

  assert.equal(r.ok, true);
  assert.equal(r.agentId, "999");
  assert.equal(r.cached, false);
  assert.equal(registerFn.calls.length, 1, "an invalid cached agentId must never be trusted blindly");
});

test("ensureAgentId: registration itself fails -> fail closed, never fabricates an agentId", async () => {
  const cacheFile = await tmpCacheFile();
  const pk = generatePrivateKey();
  const registerFn = counting(async () => ({ ok: false, reason: "insufficient gas" }));
  const verifyFn = counting(async () => ({ ok: true, valid: true }));

  const r = await ensureAgentId({ privateKey: pk, cacheFile, registerFn, verifyFn });

  assert.equal(r.ok, false);
  assert.match(r.reason, /insufficient gas/);
});

test("ensureAgentId: no signing key -> fail closed, never calls register or verify", async () => {
  const registerFn = counting(async () => ({ ok: true, agentId: "1", address: "0x0" }));
  const verifyFn = counting(async () => ({ ok: true, valid: true }));

  const r = await ensureAgentId({ privateKey: null, registerFn, verifyFn });

  assert.equal(r.ok, false);
  assert.match(r.reason, /no signing key/);
  assert.equal(registerFn.calls.length, 0);
  assert.equal(verifyFn.calls.length, 0);
});
