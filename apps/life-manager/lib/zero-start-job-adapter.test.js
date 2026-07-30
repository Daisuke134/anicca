"use strict";
// AE-ZERO-START-1 §4.4 — the job that starts a tenant's agent at a balance of zero.
//
// The done condition this file has to defend: "a real worker wake at balance 0 emitting a started
// receipt; started even with no inflow", with "private key in DB/repo/log/TG 0". So the tests are about
// four refusals and one happy path.
//
//  - A balance that was not measured is never reported. If either chain reader fails, no message is sent.
//  - A message that was not sent is never claimed. No chat linked = an honest blocked error and a retry,
//    never a fabricated send; a provider answer with no message_id = a failure, not a success.
//  - Provisioning is idempotent. A second wake must not mint a second wallet for the same tenant.
//  - No key material reaches the Telegram payload, the receipt, or the database columns.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const {
  CAPABILITY,
  LOOP_ID,
  STARTED_RAILS,
  buildZeroStartJob,
  createZeroStartLoopAdapter,
  executeZeroStartJob,
  readZeroStartTenant,
  safeZeroStartSummary,
  verifyZeroStartReceipt,
  writeZeroStartWalletColumns,
} = require("./zero-start-job-adapter.js");
const { CONTRACT_METHODS } = require("./loop-adapter-registry.js");
const { hashChatId } = require("./telegram.js");
const { tenantWalletKeyRef, tenantWalletPaths } = require("./tenant-wallet-store.js");

const TOKEN_REF = "secret://telegram/bot-token";
const BOT_TOKEN = "123456:test-only-not-a-real-bot-token";

function sandbox() {
  return { LM_DATA_ROOT: fs.mkdtempSync(path.join(os.tmpdir(), "lm-zero-start-")) };
}

// A harness that records every side effect so a test can assert what did NOT happen.
function harness(overrides = {}) {
  const env = overrides.env || sandbox();
  const sent = [];
  const patched = [];
  const measured = [];
  const rows = new Map(Object.entries(overrides.rows || {
    "tenant-a": { uid: "tenant-a", telegram_chat_id: "555000111" },
  }));

  const deps = {
    env,
    now: () => "2026-07-30T09:00:00.000Z",
    secretProvider: {
      async get(tenantId, ref) {
        if (ref !== TOKEN_REF) throw new Error("unexpected secret reference");
        return BOT_TOKEN;
      },
    },
    async readTenant(uid) {
      const row = rows.get(uid);
      if (!row) throw new Error("zero-start tenant lookup did not resolve exactly one row");
      return { ...row };
    },
    async patchTenant(uid, columns) {
      patched.push({ uid, columns });
      rows.set(uid, { ...rows.get(uid), ...columns });
      return columns;
    },
    async readBaseBalance(address) {
      measured.push({ chain: "base", address });
      return overrides.baseBalance == null ? "0" : overrides.baseBalance;
    },
    async readSolanaBalance(address) {
      measured.push({ chain: "solana", address });
      return overrides.solanaBalance == null ? "0" : overrides.solanaBalance;
    },
    async sendTelegram(token, chatId, text, extra) {
      sent.push({ token, chatId, text, extra });
      if (typeof overrides.telegramResponse === "function") return overrides.telegramResponse();
      return overrides.telegramResponse === undefined
        ? { ok: true, result: { message_id: 4242, date: 1785481200 } }
        : overrides.telegramResponse;
    },
    ...overrides.deps,
  };
  return { env, deps, sent, patched, measured, rows };
}

function job(tenantId = "tenant-a") {
  return buildZeroStartJob({ tenantId, telegramTokenRef: TOKEN_REF });
}

test("the job is exactly-once per tenant by construction", () => {
  const built = job();
  assert.equal(built.capability, CAPABILITY);
  assert.equal(built.capability, "wallet.zero-start");
  assert.equal(built.loop_id, LOOP_ID);
  assert.equal(built.loop_id, "agent.zero-start");
  assert.equal(built.effect_class, "message");
  // lm_runtime_jobs has UNIQUE (tenant_id, effect_key) AND ON CONFLICT (job_id): a stable pair means a
  // re-enqueue on every scheduler sweep can never create a second zero-start message for a tenant.
  assert.equal(built.effect_key, "zero-start:tenant-a");
  assert.equal(built.job_id, "zero-start:tenant-a");
  assert.deepEqual(built.input_refs, { telegram_token_ref: TOKEN_REF });
  assert.equal(built.tenant_id, "tenant-a");
  assert.ok(built.max_attempts > 1, "a blocked tenant must get more than one wake");
});

test("the job refuses to carry a bot token instead of a reference to one", () => {
  assert.throws(() => buildZeroStartJob({ tenantId: "tenant-a", telegramTokenRef: BOT_TOKEN }), /reference/i);
  assert.throws(() => buildZeroStartJob({ tenantId: "", telegramTokenRef: TOKEN_REF }), /tenant/i);
  assert.throws(() => buildZeroStartJob({ tenantId: "tenant-a" }), /Telegram/i);
});

test("a fresh tenant is provisioned, measured, told, and receipted in one wake", async () => {
  const h = harness();
  const { receipt, result } = await executeZeroStartJob(job(), h.deps);

  // Wallets exist on disk, 0600, one per rail.
  const paths = tenantWalletPaths("tenant-a", h.env);
  for (const filePath of [paths.base, paths.solana]) {
    assert.equal(fs.statSync(filePath).mode & 0o777, 0o600);
  }

  // The database got exactly the columns the migration added.
  assert.equal(h.patched.length, 1);
  assert.deepEqual(Object.keys(h.patched[0].columns).sort(), [
    "agent_wallet_address",
    "agent_wallet_created_at",
    "agent_wallet_key_ref",
    "agent_wallet_solana_address",
    "agent_wallet_solana_key_ref",
  ]);
  assert.equal(h.patched[0].columns.agent_wallet_key_ref, tenantWalletKeyRef("tenant-a", "base"));
  assert.equal(h.patched[0].columns.agent_wallet_solana_key_ref, tenantWalletKeyRef("tenant-a", "solana"));

  // Both balances were read from the chains, for these exact addresses.
  assert.deepEqual(h.measured, [
    { chain: "base", address: receipt.base.address },
    { chain: "solana", address: receipt.solana.address },
  ]);

  // Exactly one message, to the tenant's chat, with the tenant's token.
  assert.equal(h.sent.length, 1);
  assert.equal(h.sent[0].chatId, "555000111");
  assert.equal(h.sent[0].token, BOT_TOKEN);

  assert.equal(receipt.status, "started");
  assert.equal(receipt.kind, "tenant_zero_start");
  assert.equal(receipt.message_id, 4242);
  assert.equal(receipt.chat_id_hash, hashChatId("555000111"));
  assert.equal(receipt.wallet_status, "created");
  assert.equal(verifyZeroStartReceipt(receipt), true);
  assert.equal(result.status, "started");
});

test("the message carries both addresses, both explorer links, and the measured balances", async () => {
  const h = harness();
  const { receipt } = await executeZeroStartJob(job(), h.deps);
  const text = h.sent[0].text;

  assert.ok(text.includes(receipt.base.address), "the Base address must be in the message");
  assert.ok(text.includes(receipt.solana.address), "the Solana address must be in the message");
  assert.ok(text.includes(`https://basescan.org/address/${receipt.base.address}`));
  assert.ok(text.includes(`https://solscan.io/account/${receipt.solana.address}`));
  assert.ok(text.includes("$0.00"), "the measured USDC balance must be shown");
  assert.ok(text.includes("0 SOL"), "the measured SOL balance must be shown");
  for (const rail of STARTED_RAILS) {
    assert.ok(text.includes(rail), `${rail} must be named as started`);
  }
  assert.deepEqual(STARTED_RAILS, [
    "x402 SELL (shared seller until AE-X402-TENANT-ROUTING-1)",
    "fee-free WORK",
    "incoming-payment watch",
  ]);
});

test("the message promises no income — spec 9.11 盛らない原則", async () => {
  const h = harness();
  await executeZeroStartJob(job(), h.deps);
  const text = h.sent[0].text.toLowerCase();
  for (const forbidden of [
    "guarantee",
    "guaranteed",
    "profit from day one",
    "$1k",
    "will earn",
    "expected return",
    "risk-free",
  ]) {
    assert.ok(!text.includes(forbidden), `the message must not say "${forbidden}"`);
  }
  // And it must say plainly that a later inflow is capital, not revenue.
  assert.ok(/capital/i.test(h.sent[0].text));
  assert.ok(/measured|read from/i.test(h.sent[0].text));
});

test("a non-zero measured balance is reported at the precision the chain gave", async () => {
  // USDC has six decimals and a cent is four of them wide, so most balances are not a whole number of
  // cents. Rounding down would shave the tenant's money and rounding up would invent it, so a sub-cent
  // balance is printed at full precision instead of being forced into $x.yz.
  const exact = harness({ baseBalance: "1230000", solanaBalance: "1500000000" });
  const exactRun = await executeZeroStartJob(job(), exact.deps);
  assert.equal(exactRun.receipt.base.balance_display, "$1.23");
  assert.equal(exactRun.receipt.solana.balance_lamports, "1500000000");
  assert.equal(exactRun.receipt.solana.balance_display, "1.5 SOL");
  assert.ok(exact.sent[0].text.includes("$1.23"));
  assert.ok(exact.sent[0].text.includes("1.5 SOL"));

  const subCent = harness({ baseBalance: "1234567", solanaBalance: "1" });
  const subCentRun = await executeZeroStartJob(job(), subCent.deps);
  assert.equal(subCentRun.receipt.base.balance_atomic, "1234567");
  assert.equal(subCentRun.receipt.base.balance_display, "$1.234567");
  assert.equal(subCentRun.receipt.solana.balance_display, "0.000000001 SOL");
});

test("a balance that could not be measured stops the message — no unmeasured $0.00", async () => {
  for (const failing of ["readBaseBalance", "readSolanaBalance"]) {
    const h = harness({
      deps: { [failing]: async () => { throw new Error("rpc down"); } },
    });
    await assert.rejects(() => executeZeroStartJob(job(), h.deps), /balance/i);
    assert.equal(h.sent.length, 0, "nothing may be sent when a balance is unknown");
  }
});

test("§11.2 MAJOR-5: no linked chat is a DEFERRED OUTCOME, not a failure", async () => {
  // It used to throw. Throwing burned one of the job row's 20 lifetime attempts per wake, and the schema
  // permits neither replacing the row nor resetting its attempt — so a tenant who linked Telegram after 20
  // sweeps could never be told. Completing with a real blocked receipt costs one attempt total.
  const h = harness({ rows: { "tenant-a": { uid: "tenant-a", telegram_chat_id: null } } });
  const { receipt, result } = await executeZeroStartJob(job(), h.deps);

  assert.equal(receipt.status, "blocked_no_chat");
  assert.equal(receipt.reason, "no_linked_chat");
  assert.equal(result.status, "blocked_no_chat");
  assert.equal(verifyZeroStartReceipt(receipt), true, "a blocked receipt is real evidence and must verify");
  assert.equal(safeZeroStartSummary(receipt).status, "blocked_no_chat");

  // Nothing was sent and nothing was claimed to have been sent.
  assert.equal(h.sent.length, 0);
  assert.equal(receipt.message_id, undefined);
  assert.equal(receipt.chat_id_hash, undefined);
  assert.equal(receipt.sent_at, undefined);

  // §11.1: the wallets ARE provisioned and published, so AC5 holds and the inflow watch can start.
  assert.equal(h.patched.length, 1);
  assert.equal(receipt.base.address.startsWith("0x"), true);
  assert.ok(receipt.solana.address.length >= 32);
  const paths = tenantWalletPaths("tenant-a", h.env);
  assert.equal(fs.existsSync(paths.base), true);
  assert.equal(fs.existsSync(paths.solana), true);
});

test("§11.2: a blocked receipt can never masquerade as an announcement", async () => {
  // The sweep decides whether to re-activate by looking for `status=started`. A blocked receipt that
  // carried a message id, or claimed `started`, would make the tenant look announced forever.
  const h = harness({ rows: { "tenant-a": { uid: "tenant-a", telegram_chat_id: "" } } });
  const { receipt } = await executeZeroStartJob(job(), h.deps);
  assert.notEqual(receipt.status, "started");

  for (const [label, mutate] of [
    ["a claimed message id", (r) => { r.message_id = 7; }],
    ["a claimed chat hash", (r) => { r.chat_id_hash = "a".repeat(64); }],
    ["a claimed send time", (r) => { r.sent_at = "2026-07-30T09:00:00.000Z"; }],
    ["started with no evidence", (r) => { r.status = "started"; }],
  ]) {
    const forged = JSON.parse(JSON.stringify(receipt));
    mutate(forged);
    assert.equal(verifyZeroStartReceipt(forged), false, `${label} must not verify`);
  }
});

test("§11.2: a chatless wake measures nothing and calls no chain — waiting must be cheap", async () => {
  const h = harness({ rows: { "tenant-a": { uid: "tenant-a", telegram_chat_id: null } } });
  await executeZeroStartJob(job(), h.deps);
  assert.deepEqual(h.measured, [], "a tenant we cannot message needs no RPC round trip");
});

test("a second wake reuses the same wallets instead of minting new ones", async () => {
  const h = harness();
  const first = await executeZeroStartJob(job(), h.deps);
  const paths = tenantWalletPaths("tenant-a", h.env);
  const before = [fs.readFileSync(paths.base, "utf8"), fs.readFileSync(paths.solana, "utf8")];

  const second = await executeZeroStartJob(job(), h.deps);
  assert.equal(second.receipt.base.address, first.receipt.base.address);
  assert.equal(second.receipt.solana.address, first.receipt.solana.address);
  assert.equal(second.receipt.wallet_status, "existing");
  assert.deepEqual(
    [fs.readFileSync(paths.base, "utf8"), fs.readFileSync(paths.solana, "utf8")],
    before,
    "an already-provisioned tenant's key files must be untouched",
  );
  // The row already agrees, so there is nothing to write the second time.
  assert.equal(h.patched.length, 1);
});

test("a provider answer with no message_id is a failure, not a success", async () => {
  const h = harness({ telegramResponse: { ok: true, result: {} } });
  await assert.rejects(
    () => executeZeroStartJob(job(), h.deps),
    (error) => {
      assert.match(error.message, /message id|receipt/i);
      // Dispatch started, so whether Telegram delivered it is genuinely unknown: reconcile, do not resend.
      assert.equal(error.unknownEffect, true);
      return true;
    },
  );
});

test("Telegram refusing the message is retryable; a transport failure is reconciled", async () => {
  // Telegram answered and said no: nothing was delivered, so a retry cannot double-send.
  const refused = harness({ telegramResponse: { ok: false, error_code: 403, description: "bot was blocked" } });
  await assert.rejects(
    () => executeZeroStartJob(job(), refused.deps),
    (error) => {
      assert.notEqual(error.unknownEffect, true);
      return true;
    },
  );

  // No answer at all (lib/telegram.js turns a thrown fetch into { ok: false, error }): delivery unknown.
  const dropped = harness({ telegramResponse: { ok: false, error: "TypeError: fetch failed" } });
  await assert.rejects(
    () => executeZeroStartJob(job(), dropped.deps),
    (error) => {
      assert.equal(error.unknownEffect, true);
      return true;
    },
  );
});

test("nothing secret reaches the message, the receipt, or the database columns", async () => {
  const h = harness();
  const { receipt } = await executeZeroStartJob(job(), h.deps);
  const paths = tenantWalletPaths("tenant-a", h.env);
  const secrets = [
    JSON.parse(fs.readFileSync(paths.base, "utf8")).privateKey,
    JSON.parse(fs.readFileSync(paths.solana, "utf8")).secretKey,
  ];

  const surfaces = [
    h.sent[0].text,
    JSON.stringify(receipt),
    JSON.stringify(h.patched),
  ];
  for (const secret of secrets) {
    assert.ok(secret.length > 32);
    for (const surface of surfaces) {
      assert.ok(!surface.includes(secret), "key material must never leave the key file");
      assert.ok(!surface.includes(secret.slice(0, 16)));
    }
  }
  // The bot token is a secret too and has no business in a durable receipt.
  assert.ok(!JSON.stringify(receipt).includes(BOT_TOKEN));
  const { assertNoSecret } = require("./earnings-ledger.js");
  assertNoSecret(receipt);
});

test("a job that is not this capability, or not this tenant's, is refused", async () => {
  const h = harness();
  const good = job();
  for (const broken of [
    { ...good, capability: "report.financial.telegram" },
    { ...good, effect_class: "none" },
    { ...good, effect_key: "zero-start:tenant-b" },
    { ...good, input_refs: {} },
    null,
  ]) {
    await assert.rejects(() => executeZeroStartJob(broken, h.deps), /zero-start/i);
  }
  assert.equal(h.sent.length, 0);
});

test("two tenants get two wallets, two messages, and two disjoint receipts", async () => {
  const env = sandbox();
  const rows = {
    "tenant-a": { uid: "tenant-a", telegram_chat_id: "111" },
    "tenant-b": { uid: "tenant-b", telegram_chat_id: "222" },
  };
  const h = harness({ env, rows });
  const a = await executeZeroStartJob(job("tenant-a"), h.deps);
  const b = await executeZeroStartJob(job("tenant-b"), h.deps);

  assert.notEqual(a.receipt.base.address, b.receipt.base.address);
  assert.notEqual(a.receipt.solana.address, b.receipt.solana.address);
  assert.notEqual(a.receipt.chat_id_hash, b.receipt.chat_id_hash);

  const [messageA, messageB] = h.sent.map((entry) => entry.text);
  assert.ok(!messageA.includes(b.receipt.base.address), "tenant A must not be told tenant B's address");
  assert.ok(!messageB.includes(a.receipt.base.address));
  assert.ok(!JSON.stringify(a.receipt).includes(b.receipt.solana.address));
});

test("a receipt without real evidence does not verify", () => {
  const good = {
    schema_version: 1,
    kind: "tenant_zero_start",
    status: "started",
    chat_id_hash: hashChatId("555000111"),
    message_id: 7,
    sent_at: "2026-07-30T09:00:00.000Z",
    measured_at: "2026-07-30T09:00:00.000Z",
    wallet_status: "created",
    base: {
      chain: "base",
      address: "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
      balance_atomic: "0",
      balance_decimals: 6,
      balance_display: "$0.00",
    },
    solana: {
      chain: "solana",
      address: "FVen3X669xLzsi6N2V91DoiyzHzg1uAgqiT8jZ9nS96Z",
      balance_lamports: "0",
      balance_display: "0 SOL",
    },
    started_rails: [...STARTED_RAILS],
  };
  assert.equal(verifyZeroStartReceipt(good), true);
  assert.deepEqual(safeZeroStartSummary(good).message_id, 7);

  for (const [label, mutate] of [
    ["no message id", (r) => { r.message_id = 0; }],
    ["a non-integer message id", (r) => { r.message_id = "7"; }],
    ["a chat id instead of its hash", (r) => { r.chat_id_hash = "555000111"; }],
    ["a Solana address in the EVM slot", (r) => { r.base.address = r.solana.address; }],
    ["an EVM address in the Solana slot", (r) => { r.solana.address = "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF"; }],
    ["an unmeasured balance", (r) => { r.base.balance_atomic = null; }],
    ["a float balance", (r) => { r.solana.balance_lamports = "1.5"; }],
    ["fewer started rails than were started", (r) => { r.started_rails = r.started_rails.slice(1); }],
    ["a renamed rail", (r) => { r.started_rails = ["something else", ...r.started_rails.slice(1)]; }],
    ["a bad timestamp", (r) => { r.sent_at = "yesterday"; }],
    ["the wrong kind", (r) => { r.kind = "telegram_financial_report"; }],
    ["a claimed status with no evidence", (r) => { r.status = "started"; delete r.base; }],
  ]) {
    const broken = JSON.parse(JSON.stringify(good));
    mutate(broken);
    assert.equal(verifyZeroStartReceipt(broken), false, `${label} must not verify`);
    assert.throws(() => safeZeroStartSummary(broken), /verification/i);
  }
});

test("the adapter satisfies the loop adapter contract the registry enforces", async () => {
  const h = harness();
  const adapter = createZeroStartLoopAdapter(h.deps);
  for (const method of CONTRACT_METHODS) {
    assert.equal(typeof adapter[method], "function", `${method} is required by the registry`);
  }
  const planned = await adapter.plan({ tenantId: "tenant-a", telegramTokenRef: TOKEN_REF });
  assert.equal(planned.length, 1);
  assert.equal(planned[0].effect_key, "zero-start:tenant-a");

  const executed = await adapter.execute(job());
  assert.equal(adapter.verify(executed.receipt), true);

  // Reconciliation is only as good as the proof it is handed; an unverifiable "present" is refused.
  const withProof = createZeroStartLoopAdapter({
    ...h.deps,
    inspectEffect: async () => ({ state: "present", receipt: executed.receipt }),
  });
  assert.deepEqual(await withProof.reconcile({}), { state: "present", receipt: executed.receipt });
  const withBadProof = createZeroStartLoopAdapter({
    ...h.deps,
    inspectEffect: async () => ({ state: "present", receipt: { kind: "nope" } }),
  });
  await assert.rejects(() => withBadProof.reconcile({}), /verification/i);
  assert.deepEqual(await createZeroStartLoopAdapter(h.deps).reconcile({}), { state: "unknown" });
});

test("the default tenant read asks Postgrest for exactly the wallet columns it needs", async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, status: 200, json: async () => [{ uid: "tenant-a", telegram_chat_id: "9" }] };
  };
  const row = await readZeroStartTenant("tenant-a", {
    supaUrl: "https://db.example",
    supaKey: "service-role-test-only",
    fetchImpl,
  });
  assert.equal(row.telegram_chat_id, "9");
  assert.match(calls[0].url, /lm_users\?uid=eq\.tenant-a/);
  for (const column of [
    "telegram_chat_id",
    "agent_wallet_address",
    "agent_wallet_solana_address",
    "agent_wallet_key_ref",
    "agent_wallet_solana_key_ref",
    "agent_wallet_created_at",
  ]) {
    assert.ok(calls[0].url.includes(column), `${column} must be selected`);
  }

  const missing = async () => ({ ok: true, status: 200, json: async () => [] });
  await assert.rejects(
    () => readZeroStartTenant("tenant-a", { supaUrl: "https://db.example", supaKey: "k", fetchImpl: missing }),
    /exactly one row/i,
  );
  const broken = async () => ({ ok: false, status: 500, json: async () => ({}) });
  await assert.rejects(
    () => readZeroStartTenant("tenant-a", { supaUrl: "https://db.example", supaKey: "k", fetchImpl: broken }),
    /read failed/i,
  );
});

test("the default column write is tenant-scoped and carries no key material", async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, status: 204, json: async () => [] };
  };
  const columns = {
    agent_wallet_address: "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
    agent_wallet_solana_address: "FVen3X669xLzsi6N2V91DoiyzHzg1uAgqiT8jZ9nS96Z",
    agent_wallet_key_ref: tenantWalletKeyRef("tenant-a", "base"),
    agent_wallet_solana_key_ref: tenantWalletKeyRef("tenant-a", "solana"),
    agent_wallet_created_at: "2026-07-30T09:00:00.000Z",
  };
  await writeZeroStartWalletColumns("tenant-a", columns, {
    supaUrl: "https://db.example",
    supaKey: "service-role-test-only",
    fetchImpl,
  });
  assert.equal(calls[0].options.method, "PATCH");
  assert.match(calls[0].url, /lm_users\?uid=eq\.tenant-a$/);
  assert.deepEqual(JSON.parse(calls[0].options.body), columns);

  // A column set that smuggled a key in would be refused before the request was made.
  await assert.rejects(
    () => writeZeroStartWalletColumns("tenant-a", { ...columns, privateKey: "ab".repeat(32) }, {
      supaUrl: "https://db.example",
      supaKey: "k",
      fetchImpl,
    }),
    /secret|column/i,
  );
  await assert.rejects(
    () => writeZeroStartWalletColumns("tenant-a", columns, {
      supaUrl: "https://db.example",
      supaKey: "k",
      fetchImpl: async () => ({ ok: false, status: 400, json: async () => ({}) }),
    }),
    /write failed/i,
  );
});
