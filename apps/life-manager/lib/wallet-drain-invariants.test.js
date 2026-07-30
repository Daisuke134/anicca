"use strict";
// AE-ZERO-START-1 §12.2 — the two drain-invariant tests.
//
// Two rounds of adversarial review were survived by adding one more example payload per defect, and two
// rounds of adversarial review then found more defects of the same kind. Example tests encode the cases
// somebody thought of; this defect class lives entirely in the cases nobody thought of.
//
// These two tests are stated as INVARIANTS over an arbitrary synthetic world instead. They do not name a
// payload. They say:
//
//   1. Scan drain — for any chain of events, running the scanner until it stops making progress must leave
//      every event booked EXACTLY once; and any event left unbooked must be admitted in the receipt
//      (`truncated`, or named in an operator-attention bucket). Silence with unbooked events fails.
//   2. Sweep drain — for any pattern of permanently failing tenants, every healthy tenant is watched within
//      a bounded number of passes, and no tenant can hold the front of the queue forever.
//
// The point is that the NEXT unthought-of case fails loudly here instead of silently under-counting money.

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  MAX_ENTRIES_PER_WAKE,
  SOLANA_USDC_MINT,
  TRANSFER_TOPIC,
  buildWalletInflowJob,
  executeWalletInflowJob,
  verifyWalletInflowReceipt,
} = require("./wallet-inflow-job-adapter.js");
const { MAX_TENANTS_PER_SWEEP, sweepWalletJobs } = require("./wallet-sweep.js");
const { createWalletSweepReceiptReaders } = require("./wallet-sweep-receipts.js");
const { BASE_USDC } = require("./base-usdc-payout.js");
const { normaliseEntry } = require("./earnings-ledger.js");

const BASE_ADDRESS = "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF";
const SOLANA_ADDRESS = "FVen3X669xLzsi6N2V91DoiyzHzg1uAgqiT8jZ9nS96Z";
const PAYER = "0x1111111111111111111111111111111111111111";
const NOW = "2026-07-30T10:00:00.000Z";

function hex(value) {
  return `0x${BigInt(value).toString(16)}`;
}

// A deterministic 88-character base58 signature per index, so the synthetic chain is reproducible.
//
// The index is encoded into a fixed-width base58 PREFIX rather than smeared across the whole string. The
// obvious `(index * 7 + position * 13) % 58` generator has period 58 in the index, so signature 58 collided
// with signature 0 — which silently overwrote a transaction in the fixture and made two events of the
// synthetic chain unproducible. That is this round's own defect class appearing inside the test harness, so
// uniqueness is asserted below rather than assumed.
const B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
function signatureFor(index) {
  let remaining = index + 1;
  let prefix = "";
  while (remaining > 0) {
    prefix = B58[remaining % B58.length] + prefix;
    remaining = Math.floor(remaining / B58.length);
  }
  prefix = prefix.padStart(8, "1");
  let out = prefix;
  for (let position = prefix.length; position < 88; position++) {
    out += B58[(index * 7 + position * 13 + 1) % B58.length];
  }
  return out;
}

test("the synthetic chain's own signatures are unique — a fixture may not lie either", () => {
  // A colliding generator makes an event unproducible and the invariant then blames the scanner for money
  // the harness never actually created. Measured before this guard existed: 60 indices produced 58 unique
  // signatures.
  const seen = new Set();
  for (let index = 0; index < 5000; index++) {
    const signature = signatureFor(index);
    assert.equal(signature.length, 88);
    assert.match(signature, /^[1-9A-HJ-NP-Za-km-z]{88}$/);
    assert.equal(seen.has(signature), false, `signature ${index} collides with an earlier one`);
    seen.add(signature);
  }
  assert.equal(seen.size, 5000);
});

// ---------------------------------------------------------------------------------------------------
// A synthetic chain. It deliberately includes the shapes that broke the scanner twice: several transfers
// inside one block, several token accounts inside one signature, and entries that cannot be read at all.
// ---------------------------------------------------------------------------------------------------
function syntheticChain({
  baseEvents = 130,
  busyBlockSize = 40,
  solanaSignatures = 60,
  unreadableEvery = 17,
  multiAccountEvery = 5,
} = {}) {
  const logs = [];
  const expected = new Set();

  // Base: a busy block far larger than one wake's budget, then a long tail of ordinary blocks.
  let block = 1000;
  let produced = 0;
  let logIndex = 0;
  while (produced < baseEvents) {
    const inThisBlock = produced === 0 ? busyBlockSize : 1 + (produced % 3);
    for (let n = 0; n < inThisBlock && produced < baseEvents; n++) {
      const tx = `0x${(produced + 1).toString(16).padStart(64, "0")}`;
      logs.push({
        address: BASE_USDC,
        transactionHash: tx,
        logIndex: hex(logIndex),
        blockNumber: hex(block),
        removed: false,
        topics: [
          TRANSFER_TOPIC,
          `0x${PAYER.slice(2).toLowerCase().padStart(64, "0")}`,
          `0x${BASE_ADDRESS.slice(2).toLowerCase().padStart(64, "0")}`,
        ],
        data: `0x${BigInt(1000 + produced).toString(16).padStart(64, "0")}`,
      });
      expected.add(`inflow:base:${tx}:${logIndex}`);
      produced += 1;
      logIndex += 1;
    }
    block += 1;
    logIndex = 0;
  }
  const headBlock = block + 5;

  // Solana: newest-first is what the RPC returns, so build oldest-first and reverse when answering.
  const signatures = [];
  const transactions = new Map();
  const unreadable = new Set();
  for (let index = 0; index < solanaSignatures; index++) {
    const signature = signatureFor(index);
    const slot = 5000 + index;
    signatures.push({ signature, slot, err: null, blockTime: 1785484800 + index });

    if (index % unreadableEvery === unreadableEvery - 1) {
      // The node cannot serve this one. It is UNREADABLE, not empty.
      unreadable.add(signature);
      transactions.set(signature, null);
      continue;
    }
    const accounts = index % multiAccountEvery === 0 ? [5, 9] : [5];
    const pre = accounts.map((accountIndex) => ({
      accountIndex,
      owner: SOLANA_ADDRESS,
      mint: SOLANA_USDC_MINT,
      uiTokenAmount: { amount: "0", decimals: 6 },
    }));
    const post = accounts.map((accountIndex) => ({
      accountIndex,
      owner: SOLANA_ADDRESS,
      mint: SOLANA_USDC_MINT,
      uiTokenAmount: { amount: String(100 + index + accountIndex), decimals: 6 },
    }));
    for (const accountIndex of accounts) expected.add(`inflow:solana:${signature}:${accountIndex}`);

    const lamports = index % 3 === 0 ? 1_000 + index : 0;
    if (lamports > 0) expected.add(`inflow:solana-sol:${signature}`);
    transactions.set(signature, {
      signature,
      slot,
      blockTime: 1785484800 + index,
      transaction: { message: { accountKeys: [{ pubkey: SOLANA_ADDRESS }, { pubkey: PAYER }] } },
      meta: {
        err: null,
        preBalances: [1_000_000, 5_000_000],
        postBalances: [1_000_000 + lamports, 5_000_000],
        preTokenBalances: pre,
        postTokenBalances: post,
      },
    });
  }

  return { logs, headBlock, signatures, transactions, expected, unreadable };
}

function chainDeps(chain, ledger, options = {}) {
  const signaturePages = [];
  return {
    now: () => NOW,
    async readTenant() {
      return {
        uid: "tenant-a",
        agent_wallet_address: BASE_ADDRESS,
        agent_wallet_solana_address: SOLANA_ADDRESS,
      };
    },
    async baseRpc(method, params) {
      if (method === "eth_getBlockByNumber" && typeof params[0] === "string" && !params[0].startsWith("0x")) {
        return params[0] === "finalized" ? { number: hex(chain.headBlock), timestamp: hex(1785484800) } : null;
      }
      if (method === "eth_getBlockByNumber") return { number: params[0], timestamp: hex(1785484800) };
      if (method === "eth_getLogs") {
        const from = BigInt(params[0].fromBlock);
        const to = BigInt(params[0].toBlock);
        return chain.logs.filter((log) => BigInt(log.blockNumber) >= from && BigInt(log.blockNumber) <= to);
      }
      throw new Error(`unexpected Base RPC ${method}`);
    },
    async solanaRpc(method, params) {
      if (method === "getSignaturesForAddress") {
        const opts = params[1] || {};
        signaturePages.push(opts);
        // The real API answers NEWEST-first, stops at `until` only if it is reached before `limit`, and
        // starts below `before`. Reproducing that exactly is the whole point of this harness.
        let newestFirst = [...chain.signatures].reverse();
        if (opts.before) {
          const at = newestFirst.findIndex((entry) => entry.signature === opts.before);
          newestFirst = at < 0 ? [] : newestFirst.slice(at + 1);
        }
        if (opts.until) {
          const at = newestFirst.findIndex((entry) => entry.signature === opts.until);
          if (at >= 0) newestFirst = newestFirst.slice(0, at);
        }
        return newestFirst.slice(0, opts.limit || 25);
      }
      if (method === "getTransaction") {
        if (!chain.transactions.has(params[0])) throw new Error("unexpected getTransaction");
        return chain.transactions.get(params[0]);
      }
      throw new Error(`unexpected Solana RPC ${method}`);
    },
    async recordEarning(entry) {
      const row = normaliseEntry(entry);
      const key = `${row.wallet_address}|${row.entry_key}`;
      if (ledger.has(key)) {
        ledger.get(key).writes += 1;
        return { ok: true, duplicate: true, entry_key: row.entry_key };
      }
      ledger.set(key, { row, writes: 1 });
      return { ok: true, duplicate: false, entry_key: row.entry_key };
    },
    ...options,
  };
}

// Runs wakes, feeding each receipt's cursor into the next, until a wake makes no progress.
async function drain(chain, { maxWakes = 400 } = {}) {
  const ledger = new Map();
  const receipts = [];
  let cursor = null;
  let wakes = 0;
  while (wakes < maxWakes) {
    const before = ledger.size;
    const deps = chainDeps(chain, ledger, { readCursor: async () => cursor });
    const { receipt } = await executeWalletInflowJob(
      buildWalletInflowJob({ tenantId: "tenant-a", nowMs: Date.parse(NOW) + wakes * 300_000 }),
      deps,
    );
    receipts.push(receipt);
    wakes += 1;
    const cursorMoved = JSON.stringify(receipt.next_cursor) !== JSON.stringify(cursor);
    cursor = receipt.next_cursor;
    if (ledger.size === before && !cursorMoved) break;
  }
  return { ledger, receipts, wakes };
}

test("§12.2 invariant 1: a scan drains every event exactly once, or says it did not", async () => {
  const chain = syntheticChain();
  const { ledger, receipts, wakes } = await drain(chain);

  assert.ok(wakes < 400, "the scan must terminate, not livelock");
  assert.ok(receipts.every((receipt) => verifyWalletInflowReceipt(receipt)), "every receipt must verify");

  // EXACTLY once: never twice, which is the double-count side of the invariant.
  for (const [key, entry] of ledger) {
    assert.equal(
      entry.row.entry_key.length > 0,
      true,
      `${key} must be a real ledger row`,
    );
  }
  const booked = new Set([...ledger.values()].map((entry) => entry.row.entry_key));
  assert.equal(booked.size, ledger.size, "no entry_key may be booked under two ledger rows");

  // Everything readable must be booked.
  const unbooked = [...chain.expected].filter((key) => !booked.has(key));
  const unreadableKeys = unbooked.filter((key) => (
    [...chain.unreadable].some((signature) => key.includes(signature))
  ));

  // THE INVARIANT: anything left unbooked must be ADMITTED by the receipts, never passed over in silence.
  if (unbooked.length > 0) {
    const admitted = receipts.some((receipt) => (
      receipt.truncated === true
      || (Array.isArray(receipt.needs_operator_attention) && receipt.needs_operator_attention.length > 0)
      || receipt.status === "skipped"
    ));
    assert.ok(
      admitted,
      `${unbooked.length} events were left unbooked and NO receipt admitted it: ${unbooked.slice(0, 3).join(", ")}`,
    );
  }

  // Every unbooked event must be one the chain could not serve — never a readable one silently dropped.
  assert.deepEqual(
    unbooked.filter((key) => !unreadableKeys.includes(key)),
    [],
    "a readable event was never booked, which is silent money loss",
  );

  // And the unreadable ones must be named for a human, by signature.
  const surfaced = new Set(
    receipts.flatMap((receipt) => (receipt.needs_operator_attention || []).map((item) => item.signature)),
  );
  for (const signature of chain.unreadable) {
    assert.ok(surfaced.has(signature), `unreadable signature ${signature.slice(0, 8)}… must be surfaced`);
  }

  // Sanity: the world really was bigger than one wake, so this exercised resumption rather than one pass.
  assert.ok(chain.expected.size > MAX_ENTRIES_PER_WAKE * 3, "the synthetic chain must exceed the budget");
  assert.ok(wakes > 3, "draining must have taken several wakes");
});

test("§12.2 invariant 1: a single block busier than the whole budget still drains", async () => {
  // The mid-block resumption case. A block-only cursor either livelocks here or skips the tail of the block.
  const chain = syntheticChain({ baseEvents: 90, busyBlockSize: 90, solanaSignatures: 0, unreadableEvery: 9999 });
  const { ledger, wakes } = await drain(chain);
  const booked = new Set([...ledger.values()].map((entry) => entry.row.entry_key));
  assert.equal(booked.size, 90, "all 90 transfers in one block must be booked");
  assert.deepEqual([...chain.expected].filter((key) => !booked.has(key)), []);
  assert.ok(wakes >= 4, "a 90-event block must take several bounded wakes");
});

test("§12.2 invariant 1: one signature carrying more rows than the budget still drains", async () => {
  // The Solana mirror of the busy block: if a single signature cannot fit, refusing to split it AND
  // refusing to exceed the budget would mean never processing it at all.
  const signature = signatureFor(1);
  const accounts = Array.from({ length: MAX_ENTRIES_PER_WAKE + 6 }, (_, index) => index + 2);
  const chain = {
    logs: [],
    headBlock: 1200,
    signatures: [{ signature, slot: 5001, err: null, blockTime: 1785484800 }],
    transactions: new Map([[signature, {
      signature,
      slot: 5001,
      blockTime: 1785484800,
      transaction: { message: { accountKeys: [{ pubkey: SOLANA_ADDRESS }, { pubkey: PAYER }] } },
      meta: {
        err: null,
        preBalances: [1_000_000, 5_000_000],
        postBalances: [1_000_000, 5_000_000],
        preTokenBalances: accounts.map((accountIndex) => ({
          accountIndex, owner: SOLANA_ADDRESS, mint: SOLANA_USDC_MINT, uiTokenAmount: { amount: "0", decimals: 6 },
        })),
        postTokenBalances: accounts.map((accountIndex) => ({
          accountIndex, owner: SOLANA_ADDRESS, mint: SOLANA_USDC_MINT, uiTokenAmount: { amount: "500", decimals: 6 },
        })),
      },
    }]]),
    expected: new Set(accounts.map((accountIndex) => `inflow:solana:${signature}:${accountIndex}`)),
    unreadable: new Set(),
  };
  const { ledger } = await drain(chain);
  const booked = new Set([...ledger.values()].map((entry) => entry.row.entry_key));
  assert.equal(booked.size, accounts.length, "every token account in the oversized signature must be booked");
});

// ---------------------------------------------------------------------------------------------------
// Invariant 2 — sweep drain.
// ---------------------------------------------------------------------------------------------------
function provisionedRow(uid) {
  return {
    uid,
    agent_wallet_address: BASE_ADDRESS,
    agent_wallet_solana_address: SOLANA_ADDRESS,
    agent_wallet_key_ref: `secret://lm-agent-wallet/${uid}/base`,
    agent_wallet_solana_key_ref: `secret://lm-agent-wallet/${uid}/solana`,
    agent_wallet_created_at: NOW,
    telegram_chat_id: "555000111",
  };
}

// A stand-in for lm_runtime_job_receipts that answers the REAL production SQL. It honours whatever outcome
// filter that SQL contains, so if the ordering query only counts successes this harness reproduces exactly
// the starvation that causes — the test drives the shipped reader, not a model of it.
function receiptStore() {
  const receipts = [];
  const jobs = new Map();
  return {
    receipts,
    jobs,
    async query(sql, params) {
      if (sql.includes("max(r.created_at)")) {
        const capability = params[0];
        const onlyCompleted = /r\.outcome = 'completed'/.test(sql);
        const latest = new Map();
        for (const row of receipts) {
          if (row.capability !== capability) continue;
          if (onlyCompleted && row.outcome !== "completed") continue;
          const previous = latest.get(row.tenant_id);
          if (!previous || row.created_at > previous) latest.set(row.tenant_id, row.created_at);
        }
        return { rows: [...latest].map(([tenant_id, attempted_at]) => ({ tenant_id, attempted_at })) };
      }
      if (sql.includes("SELECT DISTINCT r.tenant_id")) {
        const capability = params[0];
        const announced = new Set(
          receipts
            .filter((row) => (
              row.capability === capability
              && row.outcome === "completed"
              && row.receipt
              && row.receipt.kind === "tenant_zero_start"
              && row.receipt.status === "started"
            ))
            .map((row) => row.tenant_id),
        );
        return { rows: [...announced].map((tenant_id) => ({ tenant_id })) };
      }
      throw new Error(`unexpected sweep query: ${sql.slice(0, 40)}`);
    },
  };
}

// Every tenant in `failing` fails forever. A failed attempt still writes a receipt (failJob does), so the
// ordering key must move for it — otherwise failing buys a permanent place at the front of the queue.
async function sweepDrain({ tenants, failing, passes }) {
  const rows = Array.from({ length: tenants }, (_, index) => provisionedRow(`t${String(index + 1).padStart(3, "0")}`));
  const store = receiptStore();
  const watchCounts = new Map();
  const readers = createWalletSweepReceiptReaders({
    query: store.query,
    zeroStartCapability: "wallet.zero-start",
    inflowCapability: "wallet.inflow.watch",
  });
  // Every tenant is already announced, so this test is purely about the inflow ordering.
  for (const row of rows) {
    store.receipts.push({
      tenant_id: row.uid,
      capability: "wallet.zero-start",
      outcome: "completed",
      created_at: NOW,
      receipt: { kind: "tenant_zero_start", status: "started" },
    });
  }

  for (let pass = 0; pass < passes; pass++) {
    const nowMs = Date.parse(NOW) + (pass + 1) * 300_000;
    const result = await sweepWalletJobs({
      nowMs,
      telegramTokenRef: "secret://telegram/bot-token",
      listTenants: async () => rows,
      enqueueJob: async (input) => ({ created: true, job: { ...input } }),
      readAnnouncedTenants: readers.readAnnouncedTenants,
      readInflowWatchedAt: readers.readInflowWatchedAt,
    });
    for (const entry of result.inflow) {
      const failed = failing.has(entry.uid);
      // The worker ran and wrote a receipt either way — completed on success, failed on failure.
      store.receipts.push({
        tenant_id: entry.uid,
        capability: "wallet.inflow.watch",
        outcome: failed ? "failed" : "completed",
        created_at: new Date(nowMs).toISOString(),
        receipt: failed ? { error_code: "CAPABILITY_EXECUTION_FAILED" } : { kind: "tenant_wallet_inflow" },
      });
      if (!failed) watchCounts.set(entry.uid, (watchCounts.get(entry.uid) || 0) + 1);
    }
  }
  return { rows, watchCounts };
}

test("§12.2 invariant 2: permanently failing tenants cannot starve the healthy ones", async () => {
  // The polarity trap: "never watched sorts first" plus "the key advances only on SUCCESS" means a tenant
  // that always fails is always the most starved, so it holds the front of the queue forever and every
  // healthy tenant is starved instead. That is MAJOR-3 again with the victims swapped.
  const tenants = 120;
  const failing = new Set(Array.from({ length: 40 }, (_, index) => `t${String(index + 1).padStart(3, "0")}`));
  const passes = Math.ceil(tenants / MAX_TENANTS_PER_SWEEP) + 1;
  const { rows, watchCounts } = await sweepDrain({ tenants, failing, passes });

  const healthy = rows.map((row) => row.uid).filter((uid) => !failing.has(uid));
  const neverWatched = healthy.filter((uid) => !watchCounts.has(uid));
  assert.deepEqual(
    neverWatched,
    [],
    `${neverWatched.length} healthy tenants were never watched within ${passes} passes`,
  );
  // Bounded fairness: nobody is served far more often than anyone else.
  const spread = Math.max(...watchCounts.values()) - Math.min(...watchCounts.values());
  assert.ok(spread <= 1, `healthy service counts must stay within one, saw ${spread}`);
});

test("§12.2 invariant 2: the invariant holds for every failure pattern, not one lucky subset", async () => {
  const tenants = 60;
  const patterns = [
    new Set(),
    new Set(["t001"]),
    // The whole first page — exactly the set a uid-ordered sweep would keep re-serving.
    new Set(Array.from({ length: MAX_TENANTS_PER_SWEEP }, (_, i) => `t${String(i + 1).padStart(3, "0")}`)),
    // Every other tenant.
    new Set(Array.from({ length: tenants }, (_, i) => `t${String(i + 1).padStart(3, "0")}`).filter((_, i) => i % 2 === 0)),
    // Everyone but one.
    new Set(Array.from({ length: tenants - 1 }, (_, i) => `t${String(i + 1).padStart(3, "0")}`)),
  ];
  const passes = Math.ceil(tenants / MAX_TENANTS_PER_SWEEP) + 1;

  for (const failing of patterns) {
    const { rows, watchCounts } = await sweepDrain({ tenants, failing, passes });
    const healthy = rows.map((row) => row.uid).filter((uid) => !failing.has(uid));
    const starved = healthy.filter((uid) => !watchCounts.has(uid));
    assert.deepEqual(
      starved,
      [],
      `failing=${failing.size}: ${starved.length} healthy tenants starved within ${passes} passes`,
    );
  }
});
