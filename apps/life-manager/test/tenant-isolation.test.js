"use strict";
// HARD-4 per-tenant isolation — a throw while processing ONE tenant must NOT prevent the others from being
// processed in the same in-process tick (matches the Inngest per-user isolation used in production).
// Run: node --test test/tenant-isolation.test.js
const { test } = require("node:test");
const assert = require("node:assert");
const { forEachUserSafe, tick, travelTick, askTickAll } = require("../scheduler.js");

test("forEachUserSafe: a throwing tenant does NOT stop the others", async () => {
  const processed = [];
  await forEachUserSafe(
    [{ uid: "aaaaaaaaaaaa" }, { uid: "bbbbbbbbbbbb" }, { uid: "cccccccccccc" }],
    "test",
    (u) => { if (u.uid.startsWith("b")) throw new Error("boom"); processed.push(u.uid); },
  );
  assert.deepStrictEqual(processed, ["aaaaaaaaaaaa", "cccccccccccc"], "a and c processed despite b throwing");
});

test("forEachUserSafe: an async rejection for one tenant is contained too", async () => {
  const processed = [];
  await forEachUserSafe(
    [{ uid: "u1" }, { uid: "u2" }, { uid: "u3" }],
    "test",
    async (u) => { if (u.uid === "u2") return Promise.reject(new Error("async boom")); processed.push(u.uid); },
  );
  assert.deepStrictEqual(processed, ["u1", "u3"]);
});

test("forEachUserSafe: all-ok processes every tenant in order", async () => {
  const processed = [];
  await forEachUserSafe([{ uid: "x" }, { uid: "y" }], "test", (u) => { processed.push(u.uid); });
  assert.deepStrictEqual(processed, ["x", "y"]);
});

test("forEachUserSafe: empty list is a no-op (no throw)", async () => {
  await forEachUserSafe([], "test", () => { throw new Error("should not be called"); });
  await forEachUserSafe(null, "test", () => { throw new Error("should not be called"); });
});

test("forEachUserSafe: a malformed user row (no uid) is contained, others continue", async () => {
  const processed = [];
  await forEachUserSafe([{ uid: "ok1" }, null, { uid: "ok2" }], "test",
    (u) => { processed.push(u.uid); }); // null → fn throws on u.uid → contained
  assert.deepStrictEqual(processed, ["ok1", "ok2"]);
});

// FIND-001: prove the PUBLIC loops actually route through isolation (not just the helper) — a future revert
// to a raw `for...await XUserOnce(u)` in any loop would fail THESE tests, not pass silently.
test("FIND-001: tick() isolates a throwing tenant (others still processed)", async () => {
  const processed = [];
  await tick({ listUsers: async () => [{ uid: "tA" }, { uid: "tB" }, { uid: "tC" }], now: 0,
    wake: (u) => { if (u.uid === "tB") throw new Error("boom"); processed.push(u.uid); } });
  assert.deepStrictEqual(processed, ["tA", "tC"]);
});
test("FIND-001: travelTick() isolates a throwing tenant", async () => {
  process.env.COMPOSIO_API_KEY = "x"; process.env.GOOGLE_API_KEY = "y";
  const processed = [];
  await travelTick({ listUsers: async () => [{ uid: "a" }, { uid: "b" }],
    travel: (u) => { if (u.uid === "a") throw new Error("boom"); processed.push(u.uid); } });
  assert.deepStrictEqual(processed, ["b"]);
});
test("FIND-001: askTickAll() isolates a throwing tenant", async () => {
  process.env.COMPOSIO_API_KEY = "x"; process.env.GEMINI_API_KEY = "y"; process.env.SUPABASE_URL = "http://x";
  const processed = [];
  await askTickAll({ listUsers: async () => [{ uid: "a" }, { uid: "b" }],
    ask: (u) => { if (u.uid === "a") throw new Error("boom"); processed.push(u.uid); } });
  assert.deepStrictEqual(processed, ["b"]);
});

// AE-ZERO-START-1 §5 / test matrix #4 — wallet isolation is part of tenant isolation.
//
// The headline risk in the zero-start slice is cross-contamination: tenant A ending up with tenant B's
// address, key file, key reference, or ledger row. A tenant told the wrong address is a tenant whose money
// goes somewhere else, so these assertions provision two tenants for real and compare everything.
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { ensureTenantWallets, readTenantWallet, tenantWalletPaths } = require("../lib/tenant-wallet-store.js");
const { executeZeroStartJob, buildZeroStartJob } = require("../lib/zero-start-job-adapter.js");
const { executeWalletInflowJob, buildWalletInflowJob } = require("../lib/wallet-inflow-job-adapter.js");

const WALLET_TOKEN_REF = "secret://telegram/bot-token";

function walletSandbox() {
  return { LM_DATA_ROOT: fs.mkdtempSync(path.join(os.tmpdir(), "lm-tenant-isolation-")) };
}

test("AE-ZERO-START-1: two tenants get disjoint addresses, key files, and key references", () => {
  const env = walletSandbox();
  const a = ensureTenantWallets("tenant-a", { env, now: () => "2026-07-30T00:00:00.000Z" });
  const b = ensureTenantWallets("tenant-b", { env, now: () => "2026-07-30T00:00:00.000Z" });

  for (const field of ["agent_wallet_address", "agent_wallet_solana_address", "agent_wallet_key_ref", "agent_wallet_solana_key_ref"]) {
    assert.notStrictEqual(a.columns[field], b.columns[field], `${field} must differ between tenants`);
  }
  const pathsA = tenantWalletPaths("tenant-a", env);
  const pathsB = tenantWalletPaths("tenant-b", env);
  assert.notStrictEqual(pathsA.dir, pathsB.dir);

  // No tenant's key material appears in any other tenant's file.
  const secretA = readTenantWallet("tenant-a", "base", { env }).secret;
  const secretB = readTenantWallet("tenant-b", "base", { env }).secret;
  assert.notStrictEqual(secretA, secretB);
  assert.strictEqual(fs.readFileSync(pathsB.base, "utf8").includes(secretA), false);
  assert.strictEqual(fs.readFileSync(pathsA.base, "utf8").includes(secretB), false);
  // Every key file is 0600 in a 0700 directory, for both tenants.
  for (const paths of [pathsA, pathsB]) {
    assert.strictEqual(fs.statSync(paths.dir).mode & 0o777, 0o700);
    assert.strictEqual(fs.statSync(paths.base).mode & 0o777, 0o600);
    assert.strictEqual(fs.statSync(paths.solana).mode & 0o777, 0o600);
  }
});

test("AE-ZERO-START-1: a tenant is told its own addresses and never another tenant's", async () => {
  const env = walletSandbox();
  const rows = {
    "tenant-a": { uid: "tenant-a", telegram_chat_id: "111" },
    "tenant-b": { uid: "tenant-b", telegram_chat_id: "222" },
  };
  const sent = [];
  const deps = {
    env,
    now: () => "2026-07-30T09:00:00.000Z",
    secretProvider: { async get() { return "123456:test-only-not-a-real-bot-token"; } },
    async readTenant(uid) { return { ...rows[uid] }; },
    async patchTenant(uid, columns) { rows[uid] = { ...rows[uid], ...columns }; return columns; },
    async readBaseBalance() { return "0"; },
    async readSolanaBalance() { return "0"; },
    async sendTelegram(token, chatId, text) {
      sent.push({ chatId, text });
      return { ok: true, result: { message_id: sent.length, date: 1785481200 } };
    },
  };

  const a = await executeZeroStartJob(buildZeroStartJob({ tenantId: "tenant-a", telegramTokenRef: WALLET_TOKEN_REF }), deps);
  const b = await executeZeroStartJob(buildZeroStartJob({ tenantId: "tenant-b", telegramTokenRef: WALLET_TOKEN_REF }), deps);

  const [messageA, messageB] = sent.map((entry) => entry.text);
  assert.strictEqual(messageA.includes(a.receipt.base.address), true);
  assert.strictEqual(messageA.includes(b.receipt.base.address), false, "tenant A must not see tenant B's address");
  assert.strictEqual(messageA.includes(b.receipt.solana.address), false);
  assert.strictEqual(messageB.includes(a.receipt.base.address), false);
  assert.notStrictEqual(a.receipt.chat_id_hash, b.receipt.chat_id_hash);
  // The two effect keys are distinct, so the runtime cannot collapse the two messages into one.
  assert.notStrictEqual(
    buildZeroStartJob({ tenantId: "tenant-a", telegramTokenRef: WALLET_TOKEN_REF }).effect_key,
    buildZeroStartJob({ tenantId: "tenant-b", telegramTokenRef: WALLET_TOKEN_REF }).effect_key,
  );
});

test("AE-ZERO-START-1: an inflow to one tenant produces no ledger row for the other", async () => {
  const env = walletSandbox();
  const a = ensureTenantWallets("tenant-a", { env, now: () => "2026-07-30T00:00:00.000Z" });
  const b = ensureTenantWallets("tenant-b", { env, now: () => "2026-07-30T00:00:00.000Z" });
  const rows = {
    "tenant-a": { uid: "tenant-a", ...a.columns },
    "tenant-b": { uid: "tenant-b", ...b.columns },
  };
  const recorded = [];
  const TX = `0x${"1".repeat(64)}`;
  const deps = {
    now: () => "2026-07-30T10:00:00.000Z",
    async readTenant(uid) { return { ...rows[uid] }; },
    async readCursor() { return null; },
    async baseRpc(method, params) {
      // §10 MAJOR-6: the scan is bounded by the finalized head, so a fixture must answer the finality tag.
      if (method === "eth_getBlockByNumber" && params[0] === "finalized") {
        return { number: "0x4b0", timestamp: "0x68a3f000" };
      }
      if (method === "eth_getBlockByNumber") return { number: params[0], timestamp: "0x68a3f000" };
      if (method !== "eth_getLogs") throw new Error(`unexpected ${method}`);
      // Only tenant A's address ever receives anything.
      const wanted = `0x${a.columns.agent_wallet_address.slice(2).toLowerCase().padStart(64, "0")}`;
      if (params[0].topics[2] !== wanted) return [];
      return [{
        // The adapter re-derives the token contract and recipient from the payload (§10 MAJOR-4), so a
        // fixture must look like a real USDC Transfer log or it is correctly ignored.
        address: require("../lib/base-usdc-payout.js").BASE_USDC,
        transactionHash: TX,
        logIndex: "0x0",
        blockNumber: "0x44c",
        topics: [
          "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
          `0x${"0".repeat(24)}1111111111111111111111111111111111111111`,
          wanted,
        ],
        data: `0x${(250000).toString(16).padStart(64, "0")}`,
      }];
    },
    async solanaRpc(method) {
      if (method === "getSignaturesForAddress") return [];
      throw new Error(`unexpected ${method}`);
    },
    async recordEarning(entry) { recorded.push(entry); return { ok: true, duplicate: false, entry_key: entry.entry_key }; },
  };

  const forA = await executeWalletInflowJob(buildWalletInflowJob({ tenantId: "tenant-a", nowMs: 1785484800000 }), deps);
  const forB = await executeWalletInflowJob(buildWalletInflowJob({ tenantId: "tenant-b", nowMs: 1785484800000 }), deps);

  assert.strictEqual(forA.receipt.recorded, 1);
  assert.strictEqual(forB.receipt.recorded, 0, "tenant B must get no rows from tenant A's inflow");
  assert.strictEqual(recorded.length, 1);
  assert.strictEqual(recorded[0].wallet_address, a.columns.agent_wallet_address);
  assert.notStrictEqual(recorded[0].wallet_address, b.columns.agent_wallet_address);
  // Capital, never revenue — for either tenant.
  assert.strictEqual(recorded[0].kind, "financial_deposit");
});

// FIND-002: a HANG (never-resolving) in one tenant is abandoned after the per-user timeout; others proceed.
test("FIND-002: a hanging tenant is abandoned after the timeout, others still processed", async () => {
  const processed = [];
  await forEachUserSafe([{ uid: "hang" }, { uid: "ok" }], "test",
    (u) => (u.uid === "hang" ? new Promise(() => {}) : Promise.resolve(processed.push(u.uid))),
    50);
  assert.deepStrictEqual(processed, ["ok"], "hung tenant abandoned after 50ms, ok processed");
});
