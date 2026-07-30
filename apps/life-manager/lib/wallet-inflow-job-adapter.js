#!/usr/bin/env node
"use strict";
// AE-ZERO-START-1 §4.5 — the incoming-payment watch.
//
// A tenant's agent starts at zero and does not require a seed, but money may still arrive. When it does,
// it is capital, not revenue, and it has to be recorded exactly once.
//
// Exactly-once lives in the database, not here: `entry_key` is `inflow:<chain>:<tx>` and
// lm_agent_earnings carries UNIQUE (wallet_address, entry_key), so a replayed window makes the second
// write a refused duplicate rather than a second deposit. That is why re-scanning a block is safe and why
// the cursor is allowed to be conservative.
//
// Revenue 0 lives in the kind: every row is `financial_deposit`, a member of EXCLUDED_KINDS, which
// `rollUpMonth` skips before any arithmetic. `capital_in` is the program-SSOT name for this and is NOT a
// ledger kind — `normaliseEntry` and the table's CHECK both reject it — so it travels as the receipt
// label `capital_class`.
//
// Amounts are recorded in the unit the chain used. Base USDC and Solana SPL-USDC are exact USD atomic
// amounts. A native SOL amount is stored as lamports with currency SOL, because turning lamports into
// dollars needs a price feed, and a price nobody measured is exactly the invented number a ledger may
// never carry.
//
// The cursor is persisted in this job's own receipt (`next_cursor`) and read back from the last completed
// receipt — the pattern `scripts/runtime-up.js` already uses for marketing video history. No new table,
// append-only, and auditable next to the evidence it describes.
//
// Every wake is bounded: a bounded block window, a bounded signature page, and a bounded number of ledger
// rows. A three-day outage must produce a slow catch-up, never a request for the whole chain.

const { createHash } = require("node:crypto");

const { buildRuntimeJob, enqueueJob } = require("./runtime-job-store.js");
const { EXCLUDED_KINDS, assertNoSecret } = require("./earnings-ledger.js");
const { recordEarnLoopRevenue } = require("./earnings-runtime.js");
const { isSolanaAddress } = require("./agent-wallet-solana.js");
const { BASE_USDC } = require("./base-usdc-payout.js");

const CAPABILITY = "wallet.inflow.watch";
const LOOP_ID = "agent.inflow.watch";
const RECEIPT_KIND = "tenant_wallet_inflow";
// The semantic label from the program SSOT. Deliberately not a ledger kind.
const CAPITAL_CLASS = "capital_in";
const LEDGER_KIND = "financial_deposit";

const TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
const SOLANA_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
// §10 MAJOR-6: `confirmed` can still be rolled back. An append-only money ledger may only read what
// is irreversible, so both Solana calls use `finalized`.
const SOLANA_COMMITMENT = "finalized";
const USDC_DECIMALS = 6;
const LAMPORT_DECIMALS = 9;

// Base produces a block every ~2s. Four hours of catch-up on a cold start, 50k blocks (~28h) per wake
// after that, in the 10k chunks a public RPC will actually serve.
const BASE_DEFAULT_LOOKBACK_BLOCKS = 7_200;
const BASE_MAX_BLOCKS_PER_WAKE = 50_000;
const BASE_LOG_CHUNK = 10_000;
const SOLANA_MAX_SIGNATURES = 25;
// A cap on ledger rows per wake, so one receipt stays inside the runtime's 16 KB limit and one wake
// cannot turn into an unbounded write burst. The cursor never advances past unprocessed work.
const MAX_ENTRIES_PER_WAKE = 25;

const EVM_ADDRESS = /^0x[0-9a-fA-F]{40}$/;
const EVM_TX = /^0x[0-9a-fA-F]{64}$/;
const WHOLE = /^\d+$/;

function fail(message) {
  throw new Error(`zero-start inflow watch: ${message}`);
}

function requiredText(value, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text) fail(`${label} is required`);
  return text;
}

function buildWalletInflowJob(input = {}) {
  const tenantId = requiredText(input.tenantId, "tenant");
  const instant = Number(input.nowMs);
  if (!Number.isFinite(instant)) fail("wake instant is invalid");
  const digest = createHash("sha256")
    .update(`${tenantId}\n${new Date(instant).toISOString()}`, "utf8")
    .digest("hex");
  return buildRuntimeJob({
    jobId: `wallet-inflow:${digest}`,
    tenantId,
    loopId: LOOP_ID,
    capability: CAPABILITY,
    // Observing a chain changes nothing outside this process. The money is made exactly-once by the
    // ledger's unique entry_key, and the schema requires effect_key to be null for the 'none' class.
    effectClass: "none",
    effectKey: null,
    inputRefs: { wallet_inflow_window_ref: `wallet-inflow://${encodeURIComponent(tenantId)}/${new Date(instant).toISOString()}` },
    maxAttempts: 3,
  });
}

// Nodes are inconsistent about hex casing, so every comparison is made on a lowered copy. A
// case-sensitive compare here would silently drop real money.
function lower(value) {
  return String(value == null ? "" : value).trim().toLowerCase();
}

function topicAddress(address) {
  return `0x${address.slice(2).toLowerCase().padStart(64, "0")}`;
}

function fromTopic(topic) {
  return `0x${String(topic || "").slice(-40)}`;
}

function hexNumber(value, label) {
  const raw = String(value == null ? "" : value).trim();
  // Emptiness is checked BEFORE BigInt, because `BigInt("")` is 0n — so an omitted quantity would
  // silently become zero, which for a log index means every transfer in a tx collapses onto index 0.
  if (!raw) fail(`${label} is not a usable number`);
  let parsed = NaN;
  try {
    // A quantity the node garbled must fail closed with a message that names WHICH quantity; letting
    // BigInt throw its own TypeError would say nothing useful in a worker log.
    parsed = Number(BigInt(raw));
  } catch {
    fail(`${label} is not a usable number`);
  }
  if (!Number.isSafeInteger(parsed) || parsed < 0) fail(`${label} is not a usable number`);
  return parsed;
}

// Two rails, one shape. `null` self-wallet knowledge stays null in the label: claiming an inflow is
// external when we never had the list to check against would be a guess.
function selfLabel(selfWallets, address) {
  if (!selfWallets || typeof selfWallets.has !== "function") return null;
  return selfWallets.has(String(address).toLowerCase());
}

async function baseBlockTimestamps(baseRpc, blocks) {
  const timestamps = new Map();
  for (const block of blocks) {
    let header = null;
    try {
      header = await baseRpc("eth_getBlockByNumber", [`0x${block.toString(16)}`, false]);
    } catch {
      // A missing header is not a reason to drop a confirmed inflow; the row is recorded with the
      // observation time and says so in its meta.
      header = null;
    }
    const seconds = header && header.timestamp ? Number(BigInt(header.timestamp)) : NaN;
    if (Number.isSafeInteger(seconds) && seconds > 0) {
      timestamps.set(block, new Date(seconds * 1000).toISOString());
    }
  }
  return timestamps;
}

// §10 MAJOR-6 — the ledger is append-only, so a reorg it already booked can never be taken back. The
// scan is therefore bounded by the FINALIZED head, not by `latest`. `eth_blockNumber` is deliberately not
// used: it answers `latest`, and using it is the silent downgrade this rule exists to prevent. A node that
// can answer neither `finalized` nor `safe` cannot tell us what is irreversible, so the wake fails closed.
async function baseFinalizedHead(baseRpc) {
  for (const tag of ["finalized", "safe"]) {
    let header = null;
    try {
      header = await baseRpc("eth_getBlockByNumber", [tag, false]);
    } catch {
      header = null;
    }
    if (header && header.number != null) {
      return { head: hexNumber(header.number, `Base ${tag} head`), finality: tag };
    }
  }
  fail("no finalized Base head is available — refusing to book unfinalized chain data");
  return null;
}

async function scanBaseInflows({ baseRpc, address, cursor, limit }) {
  const { head, finality } = await baseFinalizedHead(baseRpc);
  const cursorBlock = cursor && Number.isSafeInteger(cursor.base_next_block) && cursor.base_next_block >= 0
    ? cursor.base_next_block
    : null;
  const fromBlock = cursorBlock == null
    ? Math.max(0, head - BASE_DEFAULT_LOOKBACK_BLOCKS)
    : Math.min(cursorBlock, head);
  const toBlock = Math.min(head, fromBlock + BASE_MAX_BLOCKS_PER_WAKE - 1);

  const logs = [];
  for (let start = fromBlock; start <= toBlock; start += BASE_LOG_CHUNK) {
    const end = Math.min(start + BASE_LOG_CHUNK - 1, toBlock);
    const page = await baseRpc("eth_getLogs", [{
      address: BASE_USDC,
      fromBlock: `0x${start.toString(16)}`,
      toBlock: `0x${end.toString(16)}`,
      topics: [TRANSFER_TOPIC, null, topicAddress(address)],
    }]);
    if (!Array.isArray(page)) fail("Base log page was not a list");
    logs.push(...page);
  }

  const recipientTopic = topicAddress(address);
  const ordered = logs
    // §10 MAJOR-4 — re-derive, never trust. `eth_getLogs` filters are a REQUEST; a buggy, cached,
    // load-balanced or hostile node can answer with logs that do not match them, and this writes to an
    // append-only money ledger. So the token contract, the event signature and above all the RECIPIENT
    // are read back out of the payload and compared, and anything that does not match is dropped.
    .filter((log) => (
      Boolean(log)
      && Array.isArray(log.topics)
      && log.topics.length >= 3
      && lower(log.address) === lower(BASE_USDC)
      && lower(log.topics[0]) === lower(TRANSFER_TOPIC)
      && lower(log.topics[2]) === recipientTopic
      // §10 MAJOR-6: a log the node has already retracted is not money.
      && log.removed !== true
    ))
    .map((log) => ({
      tx: String(log.transactionHash || ""),
      block: hexNumber(log.blockNumber, "Base log block"),
      // §10 MAJOR-2: the identity of a transfer is (tx, logIndex), not tx. One transaction can carry
      // several transfers to the same wallet — a batch payout, a router, an invoice paid in tranches —
      // and a tx-only key made the second one a refused duplicate, silently unbooking real money.
      // Absent or unparseable = fail closed: without an index there is no way to distinguish a second
      // transfer from a replay of the first, and guessing one would invent an identity.
      logIndex: hexNumber(log.logIndex, "Base log index"),
      from: fromTopic(log.topics[1]),
      atomic: BigInt(String(log.data || "0x0")).toString(),
    }))
    .filter((log) => EVM_TX.test(log.tx) && log.atomic !== "0")
    .sort((left, right) => (
      left.block - right.block
      || left.tx.localeCompare(right.tx)
      || left.logIndex - right.logIndex
    ));

  const taken = ordered.slice(0, Math.max(0, limit));
  const truncated = taken.length < ordered.length;
  // A truncated wake rewinds the cursor to the last block it actually processed and re-scans it next
  // time; the unique entry_key turns the overlap into refused duplicates rather than double counting.
  const nextBlock = truncated ? taken[taken.length - 1].block : toBlock + 1;
  const timestamps = await baseBlockTimestamps(baseRpc, [...new Set(taken.map((log) => log.block))]);

  return {
    scanned_from_block: fromBlock,
    scanned_to_block: toBlock,
    finality,
    inflows: taken.map((log) => ({ ...log, occurred_at: timestamps.get(log.block) || null })),
    truncated,
    next_block: nextBlock,
  };
}

// §10 MAJOR-7 — `preTokenBalances` and `postTokenBalances` are two INDEPENDENT arrays. Nothing in the RPC
// contract says they share an order, or that either one lists every account. The previous code took the
// first owner+mint match from each and subtracted them, so a pure reordering of two unchanged accounts
// produced a deposit that never happened (T16b), and its mirror hid a real one. `accountIndex` is the only
// value that identifies an account across the two arrays, so pairing is done on it and on nothing else.
//
// A balance entry with no `accountIndex` cannot be paired at all. It fails the wake closed: dropping it
// would lose money and pairing it positionally would invent money, and neither belongs in a ledger.
function solanaTokenDeltas(meta, address, mint) {
  const indexed = (list, label) => {
    const map = new Map();
    for (const item of Array.isArray(list) ? list : []) {
      if (!item || item.owner !== address || item.mint !== mint) continue;
      if (!Number.isSafeInteger(item.accountIndex)) {
        fail(`a Solana ${label} token balance has no usable account index`);
      }
      map.set(item.accountIndex, BigInt(String((item.uiTokenAmount || {}).amount || "0")));
    }
    return map;
  };
  const pre = indexed(meta.preTokenBalances, "pre");
  const post = indexed(meta.postTokenBalances, "post");
  // The union, not the intersection: a first-ever payment CREATES the token account, so it appears only
  // in post. Requiring a pre entry would drop the first deposit a tenant ever receives.
  return [...new Set([...pre.keys(), ...post.keys()])]
    .sort((left, right) => left - right)
    .map((accountIndex) => ({
      accountIndex,
      delta: (post.get(accountIndex) || 0n) - (pre.get(accountIndex) || 0n),
    }));
}

function solanaDeltas(transaction, address) {
  const keys = ((transaction.transaction || {}).message || {}).accountKeys || [];
  const index = keys.findIndex((key) => String(key && key.pubkey ? key.pubkey : key) === address);
  const meta = transaction.meta || {};
  let lamports = 0n;
  if (index >= 0) {
    // `preBalances[i]` and `postBalances[i]` correspond to `accountKeys[i]` BY DEFINITION, so position is
    // the right pairing here — but only if both arrays actually reach that position. A ragged array cannot
    // be read as "no movement"; that is the same silent zero this module exists to refuse.
    if (!Array.isArray(meta.preBalances) || !Array.isArray(meta.postBalances)) {
      fail("a Solana transaction is missing its lamport balance arrays");
    }
    if (meta.preBalances.length <= index || meta.postBalances.length <= index) {
      fail("a Solana lamport balance array is shorter than the account it must describe");
    }
    lamports = BigInt(meta.postBalances[index] || 0) - BigInt(meta.preBalances[index] || 0);
  }

  const tokenDeltas = solanaTokenDeltas(meta, address, SOLANA_USDC_MINT);
  const blockTime = Number(transaction.blockTime);
  return {
    lamports,
    tokenDeltas,
    // The net across every one of the owner's accounts for this mint. Recorded on the receipt so an
    // internal shuffle between two of the tenant's own accounts is visible to a reader.
    usdcNet: tokenDeltas.reduce((total, entry) => total + entry.delta, 0n),
    occurred_at: Number.isSafeInteger(blockTime) && blockTime > 0
      ? new Date(blockTime * 1000).toISOString()
      : null,
  };
}

async function scanSolanaInflows({ solanaRpc, address, cursor, limit }) {
  const until = cursor && typeof cursor.solana_last_signature === "string" && cursor.solana_last_signature
    ? cursor.solana_last_signature
    : null;
  const page = await solanaRpc("getSignaturesForAddress", [
    address,
    { limit: SOLANA_MAX_SIGNATURES, commitment: SOLANA_COMMITMENT, ...(until ? { until } : {}) },
  ]);
  if (!Array.isArray(page)) fail("Solana signature page was not a list");

  // getSignaturesForAddress answers newest-first; a cursor has to advance oldest-first so an interrupted
  // wake never leaves a gap behind the marker.
  const confirmed = page
    .map((entry) => (typeof entry === "string" ? { signature: entry, err: null } : entry))
    .filter((entry) => entry && entry.err == null && typeof entry.signature === "string")
    .reverse();

  const inflows = [];
  let scanned = 0;
  let lastSignature = until;
  let truncated = false;
  let usdcNet = 0n;
  for (const entry of confirmed) {
    const transaction = await solanaRpc("getTransaction", [
      entry.signature,
      { commitment: SOLANA_COMMITMENT, encoding: "jsonParsed", maxSupportedTransactionVersion: 0 },
    ]);
    scanned += 1;
    if (!transaction || (transaction.meta && transaction.meta.err != null)) {
      lastSignature = entry.signature;
      continue;
    }
    const delta = solanaDeltas(transaction, address);
    usdcNet += delta.usdcNet;
    const rows = [];
    // One row per token account that gained, keyed by its accountIndex (§4.5). Accounts that lost are
    // reflected in usdcNet on the receipt but are not deposits.
    for (const token of delta.tokenDeltas) {
      if (token.delta <= 0n) continue;
      rows.push({
        unit: "usdc",
        accountIndex: token.accountIndex,
        amount: token.delta.toString(),
        occurred_at: delta.occurred_at,
      });
    }
    if (delta.lamports > 0n) rows.push({ unit: "sol", amount: delta.lamports.toString(), occurred_at: delta.occurred_at });
    if (inflows.length + rows.length > Math.max(0, limit)) {
      // Stop BEFORE this signature and leave the cursor behind it, so nothing is skipped.
      truncated = true;
      scanned -= 1;
      break;
    }
    for (const row of rows) inflows.push({ signature: entry.signature, ...row });
    lastSignature = entry.signature;
  }

  return {
    scanned_signatures: scanned,
    inflows,
    truncated,
    last_signature: lastSignature,
    usdc_net_atomic: usdcNet.toString(),
  };
}

function baseEntry({ inflow, address, nowIso, selfWallets }) {
  const fromIsSelf = selfLabel(selfWallets, inflow.from);
  return {
    entry: {
      // §4.5: one transfer event, not one transaction.
      entry_key: `inflow:base:${inflow.tx}:${inflow.logIndex}`,
      wallet_address: address,
      kind: LEDGER_KIND,
      amount_atomic: inflow.atomic,
      amount_decimals: USDC_DECIMALS,
      currency: "USD",
      occurred_at: inflow.occurred_at || nowIso,
      tx_hash: inflow.tx,
      source: "wallet.inflow.watch",
      meta: {
        capital_class: CAPITAL_CLASS,
        chain: "base",
        asset: "USDC",
        block: inflow.block,
        log_index: inflow.logIndex,
        from: inflow.from,
        ...(fromIsSelf == null ? {} : { from_is_self: fromIsSelf }),
        occurred_at_source: inflow.occurred_at ? "chain" : "observed",
      },
    },
    view: {
      chain: "base",
      tx: inflow.tx,
      currency: "USD",
      amount: inflow.atomic,
      amount_unit: `atomic:${USDC_DECIMALS}`,
      from_is_self: fromIsSelf,
    },
  };
}

function solanaEntry({ inflow, address, nowIso }) {
  const isUsdc = inflow.unit === "usdc";
  return {
    entry: {
      // §4.5: a single transfer event. An SPL inflow is per token account, so the account index is part
      // of its identity; a native SOL delta is per transaction and has no sub-identity.
      entry_key: isUsdc
        ? `inflow:solana:${inflow.signature}:${inflow.accountIndex}`
        : `inflow:solana-sol:${inflow.signature}`,
      wallet_address: address,
      kind: LEDGER_KIND,
      ...(isUsdc
        ? { amount_atomic: inflow.amount, amount_decimals: USDC_DECIMALS, currency: "USD" }
        : { amount_minor: inflow.amount, currency: "SOL" }),
      occurred_at: inflow.occurred_at || nowIso,
      tx_hash: inflow.signature,
      source: "wallet.inflow.watch",
      meta: isUsdc
        ? {
          capital_class: CAPITAL_CLASS,
          chain: "solana",
          asset: "USDC",
          account_index: inflow.accountIndex,
          occurred_at_source: inflow.occurred_at ? "chain" : "observed",
        }
        // Lamports as themselves. A USD figure here would need a price feed nobody measured.
        : { unit: "lamports", decimals: LAMPORT_DECIMALS, capital_class: CAPITAL_CLASS },
    },
    view: {
      chain: "solana",
      tx: inflow.signature,
      currency: isUsdc ? "USD" : "SOL",
      amount: inflow.amount,
      amount_unit: isUsdc ? `atomic:${USDC_DECIMALS}` : "lamports",
      from_is_self: null,
    },
  };
}

// A scan that failed must never be indistinguishable from a scan that found nothing, and the failure has
// to say WHICH rail it was: a bare "rpc down" in a worker log tells the next reader nothing.
async function scanRail(label, run) {
  try {
    return await run();
  } catch (error) {
    fail(`${label} scan failed: ${error && error.message ? error.message : error}`);
  }
  return null;
}

async function executeWalletInflowJob(job, deps = {}) {
  if (!job || job.capability !== CAPABILITY || job.effect_class !== "none") {
    fail("job contract mismatch");
  }
  const uid = requiredText(job.tenant_id, "tenant");
  const nowIso = typeof deps.now === "function" ? String(deps.now()) : new Date().toISOString();
  const readTenant = deps.readTenant;
  if (typeof readTenant !== "function") fail("a tenant reader is required");
  const recordEarning = deps.recordEarning || ((entry) => recordEarnLoopRevenue(entry, deps));
  // Wired by scripts/runtime-up.js to the last completed receipt for this capability. Absent = cold start.
  const readCursor = typeof deps.readCursor === "function" ? deps.readCursor : async () => null;
  const selfWallets = deps.selfWallets === undefined ? null : deps.selfWallets;

  const row = await readTenant(uid);
  if (!row || String(row.uid || uid) !== uid) fail("tenant scope mismatch");

  const baseAddress = String(row.agent_wallet_address || "").trim();
  const solanaAddress = String(row.agent_wallet_solana_address || "").trim();
  const hasBase = EVM_ADDRESS.test(baseAddress);
  const hasSolana = isSolanaAddress(solanaAddress);
  if (!hasBase && !hasSolana) {
    const receipt = {
      schema_version: 1,
      kind: RECEIPT_KIND,
      status: "skipped",
      reason: "no_wallets",
      capital_class: CAPITAL_CLASS,
      ledger_kind: LEDGER_KIND,
      checked_at: nowIso,
    };
    return { receipt, result: { status: "skipped", recorded: 0 } };
  }

  const cursor = (await readCursor({ tenantId: uid })) || null;
  let remaining = MAX_ENTRIES_PER_WAKE;
  let truncated = false;
  const pending = [];
  let baseSummary = null;
  let solanaSummary = null;
  let nextBaseBlock = cursor && Number.isSafeInteger(cursor.base_next_block) ? cursor.base_next_block : null;
  let nextSolanaSignature = cursor && cursor.solana_last_signature ? cursor.solana_last_signature : null;

  if (hasBase) {
    const scan = await scanRail(
      "Base",
      () => scanBaseInflows({ baseRpc: deps.baseRpc, address: baseAddress, cursor, limit: remaining }),
    );
    for (const inflow of scan.inflows) {
      pending.push(baseEntry({ inflow, address: baseAddress, nowIso, selfWallets }));
    }
    remaining -= scan.inflows.length;
    truncated = truncated || scan.truncated;
    nextBaseBlock = scan.next_block;
    baseSummary = {
      address: baseAddress,
      scanned_from_block: scan.scanned_from_block,
      scanned_to_block: scan.scanned_to_block,
      finality: scan.finality,
      found: scan.inflows.length,
    };
  }

  if (hasSolana) {
    const scan = await scanRail("Solana", () => scanSolanaInflows({
      solanaRpc: deps.solanaRpc,
      address: solanaAddress,
      cursor,
      limit: remaining,
    }));
    for (const inflow of scan.inflows) {
      pending.push(solanaEntry({ inflow, address: solanaAddress, nowIso }));
    }
    remaining -= scan.inflows.length;
    truncated = truncated || scan.truncated;
    nextSolanaSignature = scan.last_signature;
    solanaSummary = {
      address: solanaAddress,
      scanned_signatures: scan.scanned_signatures,
      commitment: SOLANA_COMMITMENT,
      usdc_net_atomic: scan.usdc_net_atomic,
      found: scan.inflows.length,
    };
  }

  const entries = [];
  for (const { entry, view } of pending) {
    assertNoSecret(entry);
    const written = await recordEarning(entry);
    entries.push({
      entry_key: entry.entry_key,
      ...view,
      kind: entry.kind,
      recorded: written.duplicate !== true,
    });
  }

  const recorded = entries.filter((entry) => entry.recorded).length;
  const receipt = {
    schema_version: 1,
    kind: RECEIPT_KIND,
    status: "checked",
    outcome: entries.length === 0 ? "none" : (recorded > 0 ? "recorded" : "duplicate"),
    capital_class: CAPITAL_CLASS,
    ledger_kind: LEDGER_KIND,
    checked_at: nowIso,
    found: entries.length,
    recorded,
    duplicates: entries.length - recorded,
    truncated,
    self_wallets_known: Boolean(selfWallets && typeof selfWallets.has === "function"),
    base: baseSummary,
    solana: solanaSummary,
    entries,
    next_cursor: {
      schema_version: 1,
      base_next_block: nextBaseBlock,
      solana_last_signature: nextSolanaSignature || null,
    },
  };
  assertNoSecret(receipt);
  return { receipt, result: { status: "checked", recorded, duplicates: receipt.duplicates, uid } };
}

function validIso(value) {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}

function validRailSummary(summary, addressOk, counterKey) {
  if (summary === null) return true;
  if (!summary || typeof summary !== "object" || Array.isArray(summary)) return false;
  if (!addressOk(String(summary.address || ""))) return false;
  if (!Number.isSafeInteger(summary[counterKey]) || summary[counterKey] < 0) return false;
  if (!Number.isSafeInteger(summary.found) || summary.found < 0) return false;
  return true;
}

function validEntry(entry) {
  return Boolean(entry)
    && typeof entry === "object"
    && !Array.isArray(entry)
    // A revenue kind here would mean a deposit was booked as income.
    && entry.kind === LEDGER_KIND
    && EXCLUDED_KINDS.has(entry.kind)
    && ["base", "solana"].includes(entry.chain)
    && typeof entry.entry_key === "string"
    && entry.entry_key.startsWith("inflow:")
    && typeof entry.tx === "string"
    && entry.tx.length > 0
    && /^[A-Z]{3}$/.test(String(entry.currency || ""))
    && WHOLE.test(String(entry.amount == null ? "" : entry.amount))
    && typeof entry.amount_unit === "string"
    && typeof entry.recorded === "boolean"
    && (entry.from_is_self === null || typeof entry.from_is_self === "boolean");
}

function verifyWalletInflowReceipt(receipt) {
  if (
    !receipt
    || typeof receipt !== "object"
    || Array.isArray(receipt)
    || receipt.schema_version !== 1
    || receipt.kind !== RECEIPT_KIND
    || receipt.capital_class !== CAPITAL_CLASS
    || receipt.ledger_kind !== LEDGER_KIND
    || !validIso(receipt.checked_at)
  ) {
    return false;
  }
  if (receipt.status === "skipped") return receipt.reason === "no_wallets";
  if (receipt.status !== "checked") return false;
  if (!Array.isArray(receipt.entries) || !receipt.entries.every(validEntry)) return false;
  const recorded = receipt.entries.filter((entry) => entry.recorded).length;
  if (
    receipt.found !== receipt.entries.length
    || receipt.recorded !== recorded
    || receipt.duplicates !== receipt.entries.length - recorded
  ) {
    return false;
  }
  const expectedOutcome = receipt.entries.length === 0 ? "none" : (recorded > 0 ? "recorded" : "duplicate");
  if (receipt.outcome !== expectedOutcome) return false;
  if (typeof receipt.truncated !== "boolean" || typeof receipt.self_wallets_known !== "boolean") return false;
  if (!validRailSummary(receipt.base, (value) => EVM_ADDRESS.test(value), "scanned_to_block")) return false;
  if (receipt.base && !Number.isSafeInteger(receipt.base.scanned_from_block)) return false;
  // §10 MAJOR-6: a receipt that does not state which finality it read cannot be audited for reorg safety,
  // and `latest` is never an acceptable answer.
  if (receipt.base && !["finalized", "safe"].includes(receipt.base.finality)) return false;
  if (!validRailSummary(receipt.solana, isSolanaAddress, "scanned_signatures")) return false;
  if (receipt.solana && receipt.solana.commitment !== SOLANA_COMMITMENT) return false;
  const cursor = receipt.next_cursor;
  if (!cursor || typeof cursor !== "object" || Array.isArray(cursor) || cursor.schema_version !== 1) return false;
  if (cursor.base_next_block !== null && !Number.isSafeInteger(cursor.base_next_block)) return false;
  if (cursor.solana_last_signature !== null && typeof cursor.solana_last_signature !== "string") return false;
  return true;
}

function safeWalletInflowSummary(receipt) {
  if (!verifyWalletInflowReceipt(receipt)) {
    throw new Error("zero-start inflow receipt verification failed");
  }
  if (receipt.status === "skipped") {
    return { status: "skipped", reason: receipt.reason, outcome: "none", recorded: 0, duplicates: 0 };
  }
  return {
    status: receipt.status,
    outcome: receipt.outcome,
    capital_class: receipt.capital_class,
    found: receipt.found,
    recorded: receipt.recorded,
    duplicates: receipt.duplicates,
    truncated: receipt.truncated,
    next_cursor: { ...receipt.next_cursor },
  };
}

function createWalletInflowLoopAdapter(deps = {}) {
  return Object.freeze({
    async plan(context = {}) {
      return [buildWalletInflowJob({
        tenantId: context.tenantId,
        nowMs: context.nowMs == null ? Date.now() : context.nowMs,
      })];
    },
    execute(job, services = {}) {
      return executeWalletInflowJob(job, { ...deps, ...services });
    },
    async reconcile() {
      // There is nothing outside this process to reconcile: the effect class is 'none' and the ledger's
      // unique entry_key already makes the write idempotent.
      return { state: "absent", receipt: { kind: "tenant_wallet_inflow_no_effect" } };
    },
    verify: verifyWalletInflowReceipt,
    report: safeWalletInflowSummary,
  });
}

function parseEnqueueArgs(argv) {
  const args = Array.isArray(argv) ? argv : [];
  if (args[0] !== "enqueue") throw new Error("usage: wallet-inflow-job-adapter.js enqueue --uid <tenant>");
  const uidIndex = args.indexOf("--uid");
  const tenantId = uidIndex >= 0 ? String(args[uidIndex + 1] || "").trim() : "";
  if (!tenantId || tenantId.startsWith("--")) throw new Error("--uid <tenant> is required");
  return { tenantId };
}

async function enqueueWalletInflowJob(argv, env = process.env, deps = {}) {
  const { tenantId } = parseEnqueueArgs(argv);
  const job = buildWalletInflowJob({
    tenantId,
    nowMs: deps.nowMs == null ? Date.now() : Number(deps.nowMs),
  });
  const enqueue = deps.enqueueJob || enqueueJob;
  const queued = await enqueue({
    jobId: job.job_id,
    tenantId: job.tenant_id,
    loopId: job.loop_id,
    capability: job.capability,
    effectClass: job.effect_class,
    effectKey: job.effect_key,
    inputRefs: job.input_refs,
    maxAttempts: job.max_attempts,
  });
  const result = { created: queued.created === true, job_id: job.job_id, tenant_id: job.tenant_id };
  (deps.stdout || process.stdout).write(`${JSON.stringify(result)}\n`);
  return result;
}

if (require.main === module) {
  enqueueWalletInflowJob(process.argv.slice(2)).catch((error) => {
    process.stderr.write(`[wallet-inflow-enqueue] ${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  BASE_DEFAULT_LOOKBACK_BLOCKS,
  BASE_LOG_CHUNK,
  BASE_MAX_BLOCKS_PER_WAKE,
  BASE_USDC,
  CAPABILITY,
  CAPITAL_CLASS,
  LEDGER_KIND,
  LOOP_ID,
  MAX_ENTRIES_PER_WAKE,
  RECEIPT_KIND,
  SOLANA_COMMITMENT,
  SOLANA_MAX_SIGNATURES,
  SOLANA_USDC_MINT,
  TRANSFER_TOPIC,
  buildWalletInflowJob,
  createWalletInflowLoopAdapter,
  enqueueWalletInflowJob,
  executeWalletInflowJob,
  parseEnqueueArgs,
  safeWalletInflowSummary,
  scanBaseInflows,
  scanSolanaInflows,
  verifyWalletInflowReceipt,
};
