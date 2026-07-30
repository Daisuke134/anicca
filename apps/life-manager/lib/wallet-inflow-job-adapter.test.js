"use strict";
// AE-ZERO-START-1 §4.5 — the incoming-payment watch.
//
// The done condition is "a later inflow recorded exactly-once as capital_in / revenue 0". Three things
// therefore have to be true no matter what the chains say.
//
//  - Exactly once. `entry_key` is `inflow:<chain>:<tx>` and lm_agent_earnings carries
//    UNIQUE (wallet_address, entry_key), so a replayed window refuses the second write instead of
//    double-counting a deposit.
//  - Revenue 0. Every row is `financial_deposit`, which is in EXCLUDED_KINDS, so `rollUpMonth` skips it
//    before any arithmetic. The tests assert that against the real ledger, not against a comment.
//  - Nothing is invented. A silent RPC failure must not become "no inflows", and a SOL amount must not
//    become a USD amount, because that needs a price nobody measured.

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  BASE_MAX_BLOCKS_PER_WAKE,
  BASE_USDC,
  CAPABILITY,
  CAPITAL_CLASS,
  LEDGER_KIND,
  LOOP_ID,
  MAX_ENTRIES_PER_WAKE,
  SOLANA_MAX_SIGNATURES,
  SOLANA_USDC_MINT,
  TRANSFER_TOPIC,
  buildWalletInflowJob,
  createWalletInflowLoopAdapter,
  executeWalletInflowJob,
  safeWalletInflowSummary,
  verifyWalletInflowReceipt,
} = require("./wallet-inflow-job-adapter.js");
const { CONTRACT_METHODS } = require("./loop-adapter-registry.js");
const { EXCLUDED_KINDS, normaliseEntry, rollUpMonth } = require("./earnings-ledger.js");

const BASE_ADDRESS = "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF";
const SOLANA_ADDRESS = "FVen3X669xLzsi6N2V91DoiyzHzg1uAgqiT8jZ9nS96Z";
const OTHER_SOLANA_ADDRESS = "586Z7H2vpX9qNhN2T4e9Utugie3ogjbxzGaMtM3E6HR5";
const PAYER = "0x1111111111111111111111111111111111111111";
const SELF_WALLET = "0x810f6d61f7606deee2657d3083e150a222bc29c5";
const TX = "0xaa".padEnd(66, "b");
// An 88-character base58 string in the Solana signature shape.
const SIG = "5".repeat(88);
const OLDER_SIG = "6".repeat(88);
const NOW = "2026-07-30T10:00:00.000Z";

function hex(value) {
  return `0x${BigInt(value).toString(16)}`;
}

function transferLog({ from = PAYER, tx = TX, amount = 250000n, block = 1000, logIndex = 0 } = {}) {
  return {
    address: BASE_USDC,
    transactionHash: tx,
    logIndex: hex(logIndex),
    blockNumber: hex(block),
    topics: [
      TRANSFER_TOPIC,
      `0x${from.slice(2).toLowerCase().padStart(64, "0")}`,
      `0x${BASE_ADDRESS.slice(2).toLowerCase().padStart(64, "0")}`,
    ],
    data: `0x${amount.toString(16).padStart(64, "0")}`,
  };
}

function solanaTransfer({ lamports = 0, usdc = 0, signature = SIG } = {}) {
  return {
    signature,
    transaction: { message: { accountKeys: [{ pubkey: SOLANA_ADDRESS }, { pubkey: OTHER_SOLANA_ADDRESS }] } },
    meta: {
      err: null,
      preBalances: [1_000_000, 5_000_000],
      postBalances: [1_000_000 + lamports, 5_000_000],
      preTokenBalances: [
        { owner: SOLANA_ADDRESS, mint: SOLANA_USDC_MINT, uiTokenAmount: { amount: "0", decimals: 6 } },
      ],
      postTokenBalances: [
        { owner: SOLANA_ADDRESS, mint: SOLANA_USDC_MINT, uiTokenAmount: { amount: String(usdc), decimals: 6 } },
      ],
    },
  };
}

function harness(overrides = {}) {
  const recorded = [];
  const baseCalls = [];
  const solanaCalls = [];
  const seen = new Set(overrides.alreadyRecorded || []);
  const logs = overrides.logs === undefined ? [] : overrides.logs;
  const signatures = overrides.signatures === undefined ? [] : overrides.signatures;
  const transactions = overrides.transactions || {};

  const deps = {
    now: () => NOW,
    async readTenant() {
      return overrides.row === undefined
        ? { uid: "tenant-a", agent_wallet_address: BASE_ADDRESS, agent_wallet_solana_address: SOLANA_ADDRESS }
        : overrides.row;
    },
    async readCursor() {
      return overrides.cursor === undefined ? null : overrides.cursor;
    },
    async baseRpc(method, params) {
      baseCalls.push({ method, params });
      if (method === "eth_blockNumber") return hex(overrides.latestBlock == null ? 1200 : overrides.latestBlock);
      if (method === "eth_getBlockByNumber" && typeof params[0] === "string" && !params[0].startsWith("0x")) {
        // A finality tag. `finalized` trails `latest`; a node that does not support it answers null.
        const tags = overrides.finalityTags || { finalized: overrides.latestBlock == null ? 1200 : overrides.latestBlock };
        const value = tags[params[0]];
        if (value instanceof Error) throw value;
        return value == null ? null : { number: hex(value), timestamp: hex(1785484800) };
      }
      if (method === "eth_getBlockByNumber") return { number: params[0], timestamp: hex(1785484800) };
      if (method === "eth_getLogs") {
        const from = BigInt(params[0].fromBlock);
        const to = BigInt(params[0].toBlock);
        return logs.filter((log) => BigInt(log.blockNumber) >= from && BigInt(log.blockNumber) <= to);
      }
      throw new Error(`unexpected Base RPC ${method}`);
    },
    async solanaRpc(method, params) {
      solanaCalls.push({ method, params });
      if (method === "getSignaturesForAddress") {
        return signatures.map((entry) => (typeof entry === "string" ? { signature: entry, err: null } : entry));
      }
      if (method === "getTransaction") {
        const found = transactions[params[0]];
        if (!found) throw new Error("unexpected getTransaction");
        return found;
      }
      throw new Error(`unexpected Solana RPC ${method}`);
    },
    async recordEarning(entry) {
      // Stands in for lm_agent_earnings, including the unique constraint that makes retries safe.
      const row = normaliseEntry(entry);
      const key = `${row.wallet_address}|${row.entry_key}`;
      if (seen.has(key)) return { ok: true, duplicate: true, entry_key: row.entry_key };
      seen.add(key);
      recorded.push(row);
      return { ok: true, duplicate: false, entry_key: row.entry_key };
    },
    ...overrides.deps,
  };
  return { deps, recorded, baseCalls, solanaCalls, seen };
}

function job(tenantId = "tenant-a") {
  return buildWalletInflowJob({ tenantId, nowMs: Date.parse(NOW) });
}

test("the watch job is a recurring, effect-free observation", () => {
  const built = job();
  assert.equal(built.capability, CAPABILITY);
  assert.equal(built.capability, "wallet.inflow.watch");
  assert.equal(built.loop_id, LOOP_ID);
  // Observing is not an external effect. The money is made exactly-once by the ledger's unique
  // entry_key, so the job needs no effect_key — and the schema requires it to be null for 'none'.
  assert.equal(built.effect_class, "none");
  assert.equal(built.effect_key, null);
  assert.equal(built.tenant_id, "tenant-a");

  // A recurring job needs a fresh id per wake or the second wake would be deduped away by job_id.
  const later = buildWalletInflowJob({ tenantId: "tenant-a", nowMs: Date.parse(NOW) + 300_000 });
  assert.notEqual(later.job_id, built.job_id);
  assert.notEqual(buildWalletInflowJob({ tenantId: "tenant-b", nowMs: Date.parse(NOW) }).job_id, built.job_id);
  assert.throws(() => buildWalletInflowJob({ tenantId: "", nowMs: Date.parse(NOW) }), /tenant/i);
  assert.throws(() => buildWalletInflowJob({ tenantId: "tenant-a", nowMs: NaN }), /instant/i);
});

test("no inflow is a quiet receipt, not an error", async () => {
  const h = harness();
  const { receipt, result } = await executeWalletInflowJob(job(), h.deps);

  assert.equal(receipt.status, "checked");
  assert.equal(receipt.outcome, "none");
  assert.deepEqual(receipt.entries, []);
  assert.equal(receipt.found, 0);
  assert.equal(receipt.recorded, 0);
  assert.equal(h.recorded.length, 0);
  assert.equal(verifyWalletInflowReceipt(receipt), true);
  assert.equal(safeWalletInflowSummary(receipt).outcome, "none");
  assert.equal(result.recorded, 0);
});

test("§10 MAJOR-2: two transfers to the same wallet in ONE tx are two separate deposits", async () => {
  // The measured defect: `entry_key` was per transaction, so a tx carrying two transfers to the same
  // wallet recorded the first and refused the second AS A DUPLICATE — real money silently unbooked.
  // A batch payout, a router, or a contract paying an invoice in two tranches all produce this.
  const h = harness({
    logs: [
      transferLog({ block: 1100, tx: TX, logIndex: 3, amount: 250000n }),
      transferLog({ block: 1100, tx: TX, logIndex: 7, amount: 1_000_000n }),
    ],
  });
  const { receipt } = await executeWalletInflowJob(job(), h.deps);

  assert.equal(h.recorded.length, 2, "both transfers must be booked");
  assert.deepEqual(h.recorded.map((row) => row.entry_key).sort(), [
    `inflow:base:${TX}:3`,
    `inflow:base:${TX}:7`,
  ]);
  assert.deepEqual(h.recorded.map((row) => row.amount_atomic).sort(), ["1000000", "250000"]);
  assert.equal(receipt.recorded, 2);
  assert.equal(receipt.duplicates, 0);
  // Both carry the same tx hash — the hash is evidence, the log index is identity.
  assert.equal(new Set(h.recorded.map((row) => row.tx_hash)).size, 1);

  // And replaying the identical window still refuses both, so the finer key did not cost exactly-once.
  const replay = await executeWalletInflowJob(job(), { ...h.deps, readCursor: async () => null });
  assert.equal(replay.receipt.recorded, 0);
  assert.equal(replay.receipt.duplicates, 2);
  assert.equal(h.recorded.length, 2);
});

test("§10 MAJOR-2: a log with no usable index is refused, not given a guessed identity", async () => {
  // Without a log index there is no way to tell a second transfer from a replay of the first. Recording
  // it under a tx-only key is exactly the collision that lost money; guessing an index would invent one.
  for (const logIndex of [undefined, null, "", "0xzz", "not-hex"]) {
    const log = transferLog({ block: 1100, tx: TX });
    if (logIndex === undefined) delete log.logIndex;
    else log.logIndex = logIndex;
    const h = harness({ logs: [log] });
    await assert.rejects(
      () => executeWalletInflowJob(job(), h.deps),
      /log index/i,
      `logIndex=${String(logIndex)} must fail closed`,
    );
    assert.equal(h.recorded.length, 0);
  }
});

test("a Base USDC inflow becomes exactly one capital-in row with revenue 0", async () => {
  const h = harness({ logs: [transferLog({ amount: 250000n, block: 1100, logIndex: 0 })] });
  const { receipt } = await executeWalletInflowJob(job(), h.deps);

  assert.equal(h.recorded.length, 1);
  const row = h.recorded[0];
  assert.equal(row.entry_key, `inflow:base:${TX}:0`);
  assert.equal(row.kind, LEDGER_KIND);
  assert.equal(row.kind, "financial_deposit");
  assert.equal(row.wallet_address, BASE_ADDRESS);
  assert.equal(row.amount_atomic, "250000");
  assert.equal(row.amount_decimals, 6);
  assert.equal(row.currency, "USD");
  assert.equal(row.tx_hash, TX);

  // capital_in is the semantic label, carried on the receipt — it is NOT a ledger kind.
  assert.equal(receipt.capital_class, CAPITAL_CLASS);
  assert.equal(receipt.capital_class, "capital_in");
  assert.equal(receipt.ledger_kind, "financial_deposit");
  assert.equal(receipt.outcome, "recorded");
  assert.equal(receipt.recorded, 1);
  assert.equal(verifyWalletInflowReceipt(receipt), true);
});

test("the recorded kind is one the revenue roll-up excludes — proven against the real ledger", async () => {
  const h = harness({ logs: [transferLog({ amount: 5_000_000n, block: 1100 })] });
  await executeWalletInflowJob(job(), h.deps);

  assert.equal(EXCLUDED_KINDS.has(h.recorded[0].kind), true);
  const summary = rollUpMonth(h.recorded, {
    year: 2026,
    month: 7,
    timezone: "UTC",
    walletAddress: BASE_ADDRESS,
    balanceAtomic: "5000000",
    balanceDecimals: 6,
  });
  // A $5 deposit must move no revenue figure at all.
  assert.equal(summary.counted_rows, 0);
  assert.equal(summary.excluded_rows, 1);
  assert.equal(summary.gross_usd_micros, "0");
  assert.equal(summary.net_usd_micros, "0");
  assert.equal(summary.is_loss, false);
});

test("a replayed window refuses the second write instead of double-counting", async () => {
  const h = harness({ logs: [transferLog({ amount: 250000n, block: 1100 })] });
  const first = await executeWalletInflowJob(job(), h.deps);
  assert.equal(first.receipt.recorded, 1);
  assert.equal(first.receipt.duplicates, 0);

  // Same window, same log: the unique entry_key does its job.
  const second = await executeWalletInflowJob(job(), { ...h.deps, readCursor: async () => null });
  assert.equal(second.receipt.recorded, 0);
  assert.equal(second.receipt.duplicates, 1);
  assert.equal(second.receipt.outcome, "duplicate");
  assert.equal(h.recorded.length, 1, "the ledger must still hold exactly one deposit");
});

test("the cursor is persisted in the receipt and honoured on the next wake", async () => {
  const h = harness({ latestBlock: 1200, logs: [transferLog({ block: 1100 })] });
  const { receipt } = await executeWalletInflowJob(job(), h.deps);

  assert.equal(receipt.base.scanned_to_block, 1200);
  assert.ok(receipt.next_cursor.base_next_block > 1100);
  assert.equal(receipt.next_cursor.schema_version, 1);

  // Given that cursor, the next wake starts where the last one stopped rather than re-scanning history.
  const next = harness({
    latestBlock: 1400,
    logs: [transferLog({ block: 1300, tx: `0xcc${"d".repeat(62)}` })],
    cursor: receipt.next_cursor,
  });
  const second = await executeWalletInflowJob(job(), next.deps);
  assert.equal(second.receipt.base.scanned_from_block, receipt.next_cursor.base_next_block);
  const getLogs = next.baseCalls.filter((call) => call.method === "eth_getLogs");
  assert.ok(getLogs.length >= 1);
  assert.equal(BigInt(getLogs[0].params[0].fromBlock), BigInt(receipt.next_cursor.base_next_block));
});

test("the scanned window is bounded, so a long outage cannot ask for the whole chain", async () => {
  const h = harness({ latestBlock: 5_000_000, cursor: { schema_version: 1, base_next_block: 1 } });
  const { receipt } = await executeWalletInflowJob(job(), h.deps);

  const span = receipt.base.scanned_to_block - receipt.base.scanned_from_block + 1;
  assert.ok(span <= BASE_MAX_BLOCKS_PER_WAKE, `${span} blocks must be bounded`);
  assert.ok(receipt.base.scanned_to_block < 5_000_000, "a bounded wake must leave work for the next one");
  // And every getLogs range respects the public RPC chunk cap.
  for (const call of h.baseCalls.filter((c) => c.method === "eth_getLogs")) {
    const width = Number(BigInt(call.params[0].toBlock) - BigInt(call.params[0].fromBlock)) + 1;
    assert.ok(width <= 10_000, `a getLogs range of ${width} blocks would be refused by a public RPC`);
  }
});

test("it asks for USDC Transfer logs addressed to this tenant and nobody else", async () => {
  const h = harness({ logs: [transferLog()] });
  await executeWalletInflowJob(job(), h.deps);
  const call = h.baseCalls.find((entry) => entry.method === "eth_getLogs");
  assert.equal(call.params[0].address, BASE_USDC);
  assert.equal(call.params[0].topics[0], TRANSFER_TOPIC);
  assert.equal(call.params[0].topics[1], null, "any sender");
  assert.equal(
    call.params[0].topics[2],
    `0x${BASE_ADDRESS.slice(2).toLowerCase().padStart(64, "0")}`,
    "the recipient topic must be this tenant's address",
  );
});

// §10 MAJOR-4 — hostile payloads. The RPC's filter is a request, not a guarantee: a buggy, cached,
// load-balanced or malicious node can return logs that do not match it. Every fact that decides an amount
// or an owner is re-derived from the payload.
// §10 MAJOR-6 — hostile payloads. An append-only money ledger cannot retract a reorged row, so only
// finalized chain data may enter it.
test("§10 MAJOR-6: the scan stops at the finalized head, never at latest", async () => {
  // `latest` is 5000 but only 4000 is finalized. Booking blocks 4001-5000 would put money in an
  // append-only ledger that a reorg can erase, and the ledger has no way to take it back.
  const h = harness({ latestBlock: 5000, finalityTags: { finalized: 4000, safe: 4500 } });
  const { receipt } = await executeWalletInflowJob(job(), h.deps);

  assert.equal(receipt.base.scanned_to_block, 4000);
  assert.equal(receipt.base.finality, "finalized");
  assert.ok(receipt.next_cursor.base_next_block <= 4001, "the cursor may not run ahead of finality");
  // eth_blockNumber is `latest` and must not be what bounds the scan.
  assert.equal(h.baseCalls.some((call) => call.method === "eth_blockNumber"), false);
  for (const call of h.baseCalls.filter((c) => c.method === "eth_getLogs")) {
    assert.ok(BigInt(call.params[0].toBlock) <= 4000n, "no getLogs range may exceed the finalized head");
  }
});

test("§10 MAJOR-6: with no finalized head the wake fails closed instead of using latest", async () => {
  // A node that cannot answer `finalized` or `safe` cannot tell us what is irreversible. Falling back to
  // `latest` would be the exact silent downgrade this rule exists to prevent.
  for (const finalityTags of [
    { finalized: null, safe: null },
    { finalized: new Error("method not supported"), safe: null },
    { finalized: null, safe: new Error("method not supported") },
    {},
  ]) {
    const h = harness({ latestBlock: 5000, finalityTags, logs: [transferLog({ block: 1100 })] });
    await assert.rejects(() => executeWalletInflowJob(job(), h.deps), /finalized/i);
    assert.equal(h.recorded.length, 0);
  }
});

test("§10 MAJOR-6: safe is accepted when finalized is unavailable, and is labelled", async () => {
  const h = harness({ latestBlock: 5000, finalityTags: { finalized: null, safe: 4500 } });
  const { receipt } = await executeWalletInflowJob(job(), h.deps);
  assert.equal(receipt.base.scanned_to_block, 4500);
  assert.equal(receipt.base.finality, "safe");
});

test("§10 MAJOR-6: a log flagged removed by a reorg is never booked", async () => {
  const reorged = transferLog({ block: 1100, tx: `0x${"e".repeat(64)}`, amount: 9_000_000n });
  reorged.removed = true;
  const kept = transferLog({ block: 1101, tx: `0x${"f".repeat(64)}`, amount: 1n, logIndex: 1 });
  const h = harness({ logs: [reorged, kept], latestBlock: 1200, finalityTags: { finalized: 1200 } });
  await executeWalletInflowJob(job(), h.deps);

  assert.equal(h.recorded.length, 1, "the reorged log must not be booked");
  assert.equal(h.recorded[0].amount_atomic, "1");
});

test("§10 MAJOR-6: Solana is read at finalized commitment, never confirmed", async () => {
  const h = harness({
    signatures: [SIG],
    transactions: { [SIG]: solanaTransfer({ usdc: 10 }) },
    finalityTags: { finalized: 1200 },
  });
  await executeWalletInflowJob(job(), h.deps);
  const commitments = h.solanaCalls.map((call) => {
    const options = call.params[1] || {};
    return `${call.method}:${options.commitment}`;
  });
  assert.deepEqual(commitments, [
    "getSignaturesForAddress:finalized",
    "getTransaction:finalized",
  ]);
  assert.equal(commitments.some((entry) => entry.includes("confirmed")), false);
});

test("§10 MAJOR-4: a log the RPC returned but did not match the filter is dropped", async () => {
  const otherTenantTopic = `0x${"9".repeat(24)}${"ab".repeat(20).slice(0, 40)}`;
  const hostile = [
    // Addressed to somebody else entirely — the defect that would book another tenant's money.
    { ...transferLog({ block: 1101, tx: `0x${"1".repeat(64)}` }), topics: [TRANSFER_TOPIC, `0x${"0".repeat(24)}${PAYER.slice(2)}`, otherTenantTopic] },
    // Right recipient, wrong event: an Approval carries an allowance in `data`, not a transfer.
    { ...transferLog({ block: 1102, tx: `0x${"2".repeat(64)}` }), topics: [`0x${"8".repeat(64)}`, `0x${"0".repeat(24)}${PAYER.slice(2)}`, `0x${BASE_ADDRESS.slice(2).toLowerCase().padStart(64, "0")}`] },
    // Right topics, wrong token contract: anyone can deploy a token and emit a Transfer.
    { ...transferLog({ block: 1103, tx: `0x${"3".repeat(64)}` }), address: "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef" },
    // Truncated topics: there is no recipient to check.
    { ...transferLog({ block: 1104, tx: `0x${"4".repeat(64)}` }), topics: [TRANSFER_TOPIC, `0x${"0".repeat(24)}${PAYER.slice(2)}`] },
    // A real one, so the test proves discrimination rather than blanket rejection.
    transferLog({ block: 1105, tx: `0x${"5".repeat(64)}`, amount: 777n }),
  ];
  const h = harness({ logs: hostile });
  const { receipt } = await executeWalletInflowJob(job(), h.deps);

  assert.equal(h.recorded.length, 1, "exactly one of the five logs is this tenant's USDC transfer");
  assert.equal(h.recorded[0].amount_atomic, "777");
  assert.equal(receipt.entries.length, 1);
  assert.ok(receipt.entries[0].entry_key.includes("5".repeat(64)));
});

test("§10 MAJOR-4: case differences in a returned topic still match, and still only for this tenant", async () => {
  // Nodes are inconsistent about hex casing; a case-sensitive comparison would silently drop real money.
  const upper = transferLog({ block: 1100, amount: 500n });
  upper.topics = [
    TRANSFER_TOPIC.toUpperCase().replace("0X", "0x"),
    upper.topics[1],
    `0x${BASE_ADDRESS.slice(2).toUpperCase().padStart(64, "0")}`,
  ];
  upper.address = BASE_USDC.toUpperCase().replace("0X", "0x");
  const h = harness({ logs: [upper] });
  await executeWalletInflowJob(job(), h.deps);
  assert.equal(h.recorded.length, 1);
  assert.equal(h.recorded[0].amount_atomic, "500");
});

test("an inflow from a wallet the colony controls is still capital, and is labelled as such", async () => {
  // Every inflow is capital_in regardless of sender, so the self/external split cannot change revenue.
  // It is recorded as a label so a reader can tell a real buyer from our own money moving.
  const h = harness({ logs: [transferLog({ from: SELF_WALLET, block: 1100 })] });
  const { receipt } = await executeWalletInflowJob(job(), {
    ...h.deps,
    selfWallets: new Set([SELF_WALLET]),
  });
  assert.equal(h.recorded[0].kind, "financial_deposit");
  assert.equal(receipt.entries[0].from_is_self, true);

  const external = harness({ logs: [transferLog({ from: PAYER, block: 1100 })] });
  const run = await executeWalletInflowJob(job(), { ...external.deps, selfWallets: new Set([SELF_WALLET]) });
  assert.equal(run.receipt.entries[0].from_is_self, false);
});

test("without the shared self-wallet list the label is unknown, never a guessed false", async () => {
  const h = harness({ logs: [transferLog({ from: PAYER, block: 1100 })] });
  const { receipt } = await executeWalletInflowJob(job(), { ...h.deps, selfWallets: null });
  assert.equal(receipt.entries[0].from_is_self, null);
  assert.equal(receipt.self_wallets_known, false);
});

test("a Solana USDC inflow is recorded in USD; a native SOL inflow is recorded in lamports", async () => {
  const h = harness({
    signatures: [SIG],
    transactions: { [SIG]: solanaTransfer({ lamports: 2_000_000_000, usdc: 750000 }) },
  });
  const { receipt } = await executeWalletInflowJob(job(), h.deps);

  const usdc = h.recorded.find((row) => row.entry_key === `inflow:solana:${SIG}`);
  assert.ok(usdc, "the SPL USDC delta must be recorded");
  assert.equal(usdc.currency, "USD");
  assert.equal(usdc.amount_atomic, "750000");
  assert.equal(usdc.amount_decimals, 6);
  assert.equal(usdc.wallet_address, SOLANA_ADDRESS);
  assert.equal(usdc.tx_hash, SIG);
  assert.equal(usdc.kind, "financial_deposit");

  // A SOL amount has no exact USD value without a price feed, and a ledger may not carry an invented
  // number, so lamports are stored as themselves.
  const sol = h.recorded.find((row) => row.entry_key === `inflow:solana-sol:${SIG}`);
  assert.ok(sol, "the native SOL delta must be recorded");
  assert.equal(sol.currency, "SOL");
  assert.equal(sol.amount_minor, 2_000_000_000);
  assert.equal(sol.amount_atomic, null);
  assert.deepEqual(sol.meta, { unit: "lamports", decimals: 9, capital_class: "capital_in" });
  assert.equal(sol.kind, "financial_deposit");

  assert.equal(receipt.solana.scanned_signatures, 1);
  assert.equal(receipt.recorded, 2);
  assert.equal(verifyWalletInflowReceipt(receipt), true);
});

test("an outgoing or failed Solana transaction is not an inflow", async () => {
  const failed = solanaTransfer({ lamports: 5, signature: SIG });
  failed.meta.err = { InstructionError: [0, "Custom"] };
  const outgoing = solanaTransfer({ lamports: -3_000, usdc: 0, signature: OLDER_SIG });
  outgoing.meta.preTokenBalances[0].uiTokenAmount.amount = "500";
  outgoing.meta.postTokenBalances[0].uiTokenAmount.amount = "100";

  const h = harness({
    signatures: [{ signature: SIG, err: { InstructionError: [0, "Custom"] } }, { signature: OLDER_SIG, err: null }],
    transactions: { [SIG]: failed, [OLDER_SIG]: outgoing },
  });
  const { receipt } = await executeWalletInflowJob(job(), h.deps);
  assert.equal(h.recorded.length, 0, "a failed tx and a net outflow are not deposits");
  assert.equal(receipt.outcome, "none");
});

test("the Solana window is bounded and resumes from the persisted signature", async () => {
  const many = Array.from({ length: 200 }, (_, index) => `${String((index % 9) + 1)}`.repeat(88));
  const h = harness({ signatures: many.slice(0, 3), cursor: { schema_version: 1, solana_last_signature: OLDER_SIG } });
  const { receipt } = await executeWalletInflowJob(job(), {
    ...h.deps,
    solanaRpc: async (method, params) => {
      if (method === "getSignaturesForAddress") {
        assert.equal(params[0], SOLANA_ADDRESS);
        assert.ok(params[1].limit <= SOLANA_MAX_SIGNATURES, "the signature page must be bounded");
        assert.equal(params[1].until, OLDER_SIG, "it must resume from the persisted signature");
        assert.equal(params[1].commitment, "finalized", "§10 MAJOR-6: only finalized data may be booked");
        return [];
      }
      throw new Error("unexpected");
    },
  });
  assert.equal(receipt.solana.scanned_signatures, 0);
  assert.equal(receipt.next_cursor.solana_last_signature, OLDER_SIG, "an empty page keeps the cursor");
});

test("more inflows than one wake may process leaves the rest for the next wake", async () => {
  const logs = Array.from({ length: MAX_ENTRIES_PER_WAKE + 5 }, (_, index) => transferLog({
    tx: `0x${(index + 1).toString(16).padStart(64, "0")}`,
    block: 1000 + index,
  }));
  const h = harness({ logs, latestBlock: 1200 });
  const { receipt } = await executeWalletInflowJob(job(), h.deps);

  assert.equal(h.recorded.length, MAX_ENTRIES_PER_WAKE);
  assert.equal(receipt.truncated, true);
  assert.ok(
    receipt.next_cursor.base_next_block <= 1000 + MAX_ENTRIES_PER_WAKE,
    "the cursor must not skip past inflows this wake did not process",
  );
});

test("an RPC that fails throws — a silent failure would read as 'no inflows'", async () => {
  for (const failing of ["baseRpc", "solanaRpc"]) {
    const h = harness({
      logs: [transferLog()],
      signatures: [SIG],
      transactions: { [SIG]: solanaTransfer({ usdc: 10 }) },
      deps: { [failing]: async () => { throw new Error("rpc down"); } },
    });
    await assert.rejects(() => executeWalletInflowJob(job(), h.deps), /inflow/i, `${failing} must surface`);
  }
});

test("a tenant with no wallets yet is skipped honestly, not scanned", async () => {
  const h = harness({ row: { uid: "tenant-a", agent_wallet_address: null, agent_wallet_solana_address: null } });
  const { receipt } = await executeWalletInflowJob(job(), h.deps);
  assert.equal(receipt.status, "skipped");
  assert.equal(receipt.reason, "no_wallets");
  assert.equal(h.baseCalls.length, 0);
  assert.equal(h.solanaCalls.length, 0);
  assert.equal(verifyWalletInflowReceipt(receipt), true);
});

test("only one rail provisioned is still watched", async () => {
  const h = harness({
    row: { uid: "tenant-a", agent_wallet_address: BASE_ADDRESS, agent_wallet_solana_address: null },
    logs: [transferLog({ block: 1100 })],
  });
  const { receipt } = await executeWalletInflowJob(job(), h.deps);
  assert.equal(receipt.recorded, 1);
  assert.equal(receipt.solana, null);
  assert.equal(h.solanaCalls.length, 0);
  assert.equal(verifyWalletInflowReceipt(receipt), true);
});

test("one tenant's inflow is never written against another tenant's wallet", async () => {
  const h = harness({ logs: [transferLog({ block: 1100 })] });
  await assert.rejects(
    () => executeWalletInflowJob({ ...job(), tenant_id: "tenant-b" }, h.deps),
    /scope|tenant/i,
  );
  assert.equal(h.recorded.length, 0);

  // And the row it does write is bound to the address it scanned.
  await executeWalletInflowJob(job(), h.deps);
  assert.equal(h.recorded[0].wallet_address, BASE_ADDRESS);
  assert.notEqual(h.recorded[0].wallet_address, SOLANA_ADDRESS);
});

test("a job that is not this capability is refused", async () => {
  const h = harness();
  for (const broken of [
    { ...job(), capability: "wallet.zero-start" },
    { ...job(), effect_class: "message" },
    null,
  ]) {
    await assert.rejects(() => executeWalletInflowJob(broken, h.deps), /inflow/i);
  }
});

test("a receipt that claims a recording without evidence does not verify", () => {
  const good = {
    schema_version: 1,
    kind: "tenant_wallet_inflow",
    status: "checked",
    outcome: "recorded",
    capital_class: "capital_in",
    ledger_kind: "financial_deposit",
    checked_at: NOW,
    found: 1,
    recorded: 1,
    duplicates: 0,
    truncated: false,
    self_wallets_known: true,
    base: { address: BASE_ADDRESS, scanned_from_block: 1000, scanned_to_block: 1200, finality: "finalized", found: 1 },
    solana: { address: SOLANA_ADDRESS, scanned_signatures: 0, commitment: "finalized", found: 0 },
    entries: [{
      entry_key: `inflow:base:${TX}`,
      chain: "base",
      tx: TX,
      kind: "financial_deposit",
      currency: "USD",
      amount: "250000",
      amount_unit: "atomic:6",
      recorded: true,
      from_is_self: false,
    }],
    next_cursor: { schema_version: 1, base_next_block: 1201, solana_last_signature: null },
  };
  assert.equal(verifyWalletInflowReceipt(good), true);

  for (const [label, mutate] of [
    ["a revenue kind", (r) => { r.entries[0].kind = "financial_external_income"; }],
    ["a revenue ledger kind at the top level", (r) => { r.ledger_kind = "financial_external_income"; }],
    ["the wrong capital class", (r) => { r.capital_class = "revenue"; }],
    ["counts that disagree with the entries", (r) => { r.recorded = 5; }],
    ["a recorded outcome with no entries", (r) => { r.entries = []; }],
    ["a missing cursor", (r) => { delete r.next_cursor; }],
    ["a non-integer block", (r) => { r.base.scanned_to_block = "1200"; }],
    ["a bad timestamp", (r) => { r.checked_at = "later"; }],
    ["the wrong kind", (r) => { r.kind = "tenant_zero_start"; }],
    ["a fractional amount", (r) => { r.entries[0].amount = "1.5"; }],
    // §10 MAJOR-6: a receipt that read unfinalized data, or will not say what it read, is not auditable.
    ["a latest-head scan", (r) => { r.base.finality = "latest"; }],
    ["no stated finality", (r) => { delete r.base.finality; }],
    ["a confirmed Solana read", (r) => { r.solana.commitment = "confirmed"; }],
  ]) {
    const broken = JSON.parse(JSON.stringify(good));
    mutate(broken);
    assert.equal(verifyWalletInflowReceipt(broken), false, `${label} must not verify`);
    assert.throws(() => safeWalletInflowSummary(broken), /verification/i);
  }
});

test("the adapter satisfies the loop adapter contract the registry enforces", async () => {
  const h = harness({ logs: [transferLog({ block: 1100 })] });
  const adapter = createWalletInflowLoopAdapter(h.deps);
  for (const method of CONTRACT_METHODS) {
    assert.equal(typeof adapter[method], "function", `${method} is required by the registry`);
  }
  const planned = await adapter.plan({ tenantId: "tenant-a", nowMs: Date.parse(NOW) });
  assert.equal(planned.length, 1);
  assert.equal(planned[0].capability, CAPABILITY);

  const executed = await adapter.execute(job());
  assert.equal(adapter.verify(executed.receipt), true);
  assert.equal(adapter.report(executed.receipt).recorded, 1);
  // An observation has no external effect to reconcile.
  assert.deepEqual(await adapter.reconcile({}), { state: "absent", receipt: { kind: "tenant_wallet_inflow_no_effect" } });
});

test("no receipt or ledger row can carry a secret", async () => {
  const h = harness({
    logs: [transferLog({ block: 1100 })],
    signatures: [SIG],
    transactions: { [SIG]: solanaTransfer({ usdc: 10 }) },
  });
  const { receipt } = await executeWalletInflowJob(job(), h.deps);
  const { assertNoSecret } = require("./earnings-ledger.js");
  assertNoSecret(receipt);
  for (const row of h.recorded) assertNoSecret(row);
  assert.ok(Buffer.byteLength(JSON.stringify(receipt)) < 16_384, "a receipt must fit the runtime limit");
});
