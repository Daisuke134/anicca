import { createHash, randomUUID } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";
import { authorizeEarnedSpend } from "../../skills/agent-economy/lib/treasury-policy.mjs";
import { verifyEvmReceipt as strictVerifyEvmReceipt } from "../../skills/_shared/lib/verify-tx.mjs";

const EVM = /^0x[0-9a-f]{40}$/iu;
const TX = /^0x[0-9a-f]{64}$/iu;
const BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const FAILED_SETTLEMENT_TX = "0x1b31ef383fae0078a24adcfa1f78fe0eefd390bc2b02fdb25c558498032e2774",
  FAILED_SETTLEMENT_PAYER = "0x810f6d61f7606deee2657d3083e150a222bc29c5",
  FAILED_SETTLEMENT_PAYEE = "0xe9030014f5dae217d0a152f02a043567b16c1abf", FAILED_SETTLEMENT_LOG_INDEX = 29,
  FAILED_SETTLEMENT_AMOUNT_ATOMIC = "2000", FAILED_SETTLEMENT_COST_USDC = 0.002,
  FAILED_SETTLEMENT_RESERVE_USDC = 0.001, STALE_MODEL = "openai/gpt-5-nano", CURRENT_MODEL = "openai/gpt-5.4-nano",
  ORIGINAL_FUNDING_ID = "revenue:v2:9e849219a7c479aa837ab3fedbc3f4f25c2a1e8142ce461888cd0a0b3defeeb3",
  FAILURE_SOURCE_SHA256 = "9c5c9d0393f664c69bea3e470cac21699d8e4d56a55c6b7ddd71bc00484475ee";
const round = (value) => Math.round(Number(value) * 1e6) / 1e6;
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
  }
  return value;
}
const stable = (value) => JSON.stringify(canonical(value));

function content(output) {
  return output?.choices?.[0]?.message?.content
    ?? output?.choices?.[0]?.text
    ?? output?.content?.[0]?.text
    ?? output?.output_text;
}

function keyFor({ intentId, payer, request }) {
  return `compute:${createHash("sha256").update(`${intentId}\n${payer.toLowerCase()}\n${stable(request)}`).digest("hex")}`;
}

function assertFunding({ amountUsdc, fundingReceiptIds, revenueReceipts, recipient }) {
  const result = authorizeEarnedSpend({
    amountUsdc, fundingReceiptIds, revenueReceipts,
    recipient,
    reserveUsdc: 0, sessionSpentUsdc: 0, sessionCapUsdc: amountUsdc,
  });
  if (!result.allowed) throw new Error(`compute receipt funding rejected: ${result.reason}`);
  return result;
}

export function buildComputeReceipt({
  intentId, payer, request, output, costUsdc, preBalanceUsdc, postBalanceUsdc,
  fundingReceiptIds, revenueReceipts, settlement, occurredAt = new Date().toISOString(),
} = {}) {
  if (typeof intentId !== "string" || !intentId || !EVM.test(String(payer || ""))) {
    throw new Error("compute receipt intent and payer are required");
  }
  if (!request || typeof request !== "object" || typeof request.model !== "string") {
    throw new Error("compute receipt request model is required");
  }
  if (typeof content(output) !== "string" || !content(output).trim()) {
    throw new Error("compute receipt output is missing");
  }
  if (!Number.isFinite(Number(costUsdc)) || Number(costUsdc) <= 0) {
    throw new Error("compute receipt settled cost must be positive");
  }
  assertFunding({ amountUsdc: costUsdc, fundingReceiptIds, revenueReceipts, recipient: payer });
  if (settlement?.success !== true || !TX.test(String(settlement?.transaction || ""))) {
    throw new Error("compute receipt settlement transaction is required");
  }
  if (String(settlement?.network || "") !== "eip155:8453") {
    throw new Error("compute receipt settlement network must be Base mainnet");
  }
  if (String(settlement?.payer || "").toLowerCase() !== payer.toLowerCase()) {
    throw new Error("compute receipt settlement payer mismatch");
  }
  const requirement = settlement?.requirement;
  const expectedAtomic = BigInt(Math.round(Number(costUsdc) * 1e6));
  if (requirement?.scheme !== "exact" || requirement?.network !== "eip155:8453"
    || String(requirement?.asset || "").toLowerCase() !== BASE_USDC.toLowerCase()
    || !EVM.test(String(requirement?.pay_to || ""))) {
    throw new Error("compute receipt payment requirement is invalid");
  }
  try {
    if (BigInt(requirement.amount_atomic) !== expectedAtomic
      || (settlement.amount !== undefined && BigInt(settlement.amount) !== expectedAtomic)) {
      throw new Error("mismatch");
    }
  } catch {
    throw new Error("compute receipt settlement amount mismatch");
  }
  const pre = Number(preBalanceUsdc);
  const post = Number(postBalanceUsdc);
  if (!Number.isFinite(pre) || !Number.isFinite(post)
    || Math.abs(round(pre - post) - round(costUsdc)) > 0.000001) {
    throw new Error("compute receipt balance conservation failed");
  }
  return {
    schema_version: 1,
    receipt_type: "compute",
    idempotency_key: keyFor({ intentId, payer, request }),
    intent_id: intentId,
    payer: payer.toLowerCase(),
    request: { model: request.model },
    output_sha256: createHash("sha256").update(stable(output)).digest("hex"),
    cost_usdc: round(costUsdc),
    pre_balance_usdc: round(pre),
    post_balance_usdc: round(post),
    funding_receipt_ids: [...new Set(fundingReceiptIds)],
    settlement: {
      success: true,
      transaction: settlement.transaction.toLowerCase(),
      network: settlement.network,
      payer: payer.toLowerCase(),
      amount_atomic: requirement.amount_atomic,
      asset: BASE_USDC.toLowerCase(),
      pay_to: requirement.pay_to.toLowerCase(),
      scheme: "exact",
    },
    occurred_at: occurredAt,
  };
}

async function rows(file) {
  try {
    return (await fs.readFile(file, "utf8")).split("\n").filter(Boolean).map((line) => JSON.parse(line));
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
}

async function withLock(file, work) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  const lock = `${file}.lock`;
  try { await fs.mkdir(lock); } catch (error) {
    if (error?.code === "EEXIST") throw new Error("compute receipt journal is locked");
    throw error;
  }
  await fs.writeFile(path.join(lock, "owner"), JSON.stringify({ pid: process.pid, id: randomUUID() }));
  try { return await work(); } finally { await fs.rm(lock, { recursive: true, force: true }); }
}

function fundedCost(existing, fundingReceiptIds) {
  const selected = new Set(fundingReceiptIds);
  return round(existing.reduce((total, row) => {
    const linked = Array.isArray(row?.funding_receipt_ids)
      && row.funding_receipt_ids.some((id) => selected.has(id));
    return linked && Number.isFinite(Number(row?.cost_usdc)) && Number(row.cost_usdc) > 0
      ? total + Number(row.cost_usdc) : total;
  }, 0));
}

export async function appendComputeReceipt(journalPath, receipt) {
  return withLock(journalPath, async () => {
    const existing = await rows(journalPath);
    if (existing.some((row) => row?.idempotency_key === receipt.idempotency_key)) {
      return { appended: false, duplicate: true, receipt };
    }
    const transaction = String(receipt?.settlement?.transaction || "").toLowerCase();
    if (transaction && existing.some((row) => String(row?.settlement?.transaction || "").toLowerCase() === transaction)) {
      throw new Error("compute settlement transaction is already recorded");
    }
    await fs.appendFile(journalPath, `${JSON.stringify(receipt)}\n`, { encoding: "utf8", mode: 0o600 });
    return { appended: true, duplicate: false, receipt };
  });
}

function sameStringSet(a, b) {
  const left = Array.isArray(a) ? [...new Set(a)] : [], right = Array.isArray(b) ? [...new Set(b)] : [];
  return left.length === right.length && left.every((value) => right.includes(value));
}

async function readIntent(intentPath) {
  try { return JSON.parse(await fs.readFile(path.join(intentPath, "intent.json"), "utf8")); } catch (error) {
    if (error?.code === "ENOENT") return null;
    throw new Error("compute transport intent is invalid");
  }
}

async function readFailureEvidence(intentPath) {
  let failure;
  try { failure = JSON.parse(await fs.readFile(path.join(intentPath, "failure.json"), "utf8")); }
  catch { throw new Error("compute failure evidence is invalid"); }
  const fields = ["schema_version", "http_status", "provider_code", "output_present", "model", "source_sha256"];
  if (!failure || Array.isArray(failure) || Object.keys(failure).sort().join() !== fields.sort().join()
    || failure.schema_version !== 1 || failure.http_status !== 429
    || failure.provider_code !== "FREE_MODEL_FAILED" || failure.output_present !== false
    || failure.model !== STALE_MODEL || typeof failure.source_sha256 !== "string"
    || !/^[0-9a-f]{64}$/u.test(failure.source_sha256)
    || failure.source_sha256 !== FAILURE_SOURCE_SHA256) throw new Error("compute failure evidence is invalid");
  return failure;
}

function strictProofMatches(proof, expected) {
  const transfer = proof?.transfer;
  return proof?.verified === true && proof.status === "0x1" && Number(proof.chain_id) === 8453
    && String(proof.tx_hash).toLowerCase() === expected.tx_hash
    && String(transfer?.contract || "").toLowerCase() === expected.expected_contract.toLowerCase()
    && String(transfer?.payer || "").toLowerCase() === expected.expected_payer.toLowerCase()
    && String(transfer?.recipient || "").toLowerCase() === expected.expected_recipient.toLowerCase()
    && String(transfer?.amount_atomic) === expected.expected_amount_atomic
    && Number(transfer?.log_index) === expected.expected_log_index;
}

function isFailedSettlementReceipt(row, key, payer, fundingReceiptIds, failure) {
  const settlement = row?.settlement;
  return row?.receipt_type === "compute" && row?.outcome === "failed_output"
    && row?.idempotency_key === key && row?.payer === payer
    && Number(row?.cost_usdc) === FAILED_SETTLEMENT_COST_USDC && row?.http_status === 429
    && row?.provider_code === "FREE_MODEL_FAILED"
    && sameStringSet(row?.funding_receipt_ids, fundingReceiptIds)
    && !Object.hasOwn(row, "request") && !Object.hasOwn(row, "prompt") && !Object.hasOwn(row, "output")
    && settlement?.success === true && settlement?.transaction === FAILED_SETTLEMENT_TX
    && settlement?.network === "eip155:8453" && settlement?.payer === payer
    && settlement?.amount_atomic === FAILED_SETTLEMENT_AMOUNT_ATOMIC && settlement?.asset === BASE_USDC.toLowerCase()
    && settlement?.pay_to === FAILED_SETTLEMENT_PAYEE && settlement?.contract === BASE_USDC.toLowerCase()
    && settlement?.log_index === FAILED_SETTLEMENT_LOG_INDEX && settlement?.scheme === "exact"
    && typeof row?.diagnostic === "string" && row.diagnostic.includes("stale")
    && row?.output_present === false && row?.model === failure.model && row?.source_sha256 === failure.source_sha256;
}

async function clearSettlementLocks(intentPath, fundingLockPath) {
  await fs.rm(fundingLockPath, { recursive: true, force: true });
  await fs.rm(intentPath, { recursive: true, force: true });
}

/** Reconcile a chain-settled failed request without retaining request or output data. */
export async function reconcileFailedComputeSettlement({
  journalPath, intentPath, fundingLockPath, revenueJournalPath,
  verifyEvmReceipt = strictVerifyEvmReceipt,
} = {}) {
  if (!journalPath || !intentPath || !fundingLockPath || !revenueJournalPath
    || typeof verifyEvmReceipt !== "function") throw new Error("compute reconciliation configuration is incomplete");
  const intent = await readIntent(intentPath);
  if (!intent || intent.state !== "transport_started") throw new Error("compute transport intent is not reconcilable");
  if (intentPath !== `${journalPath}.${intent.idempotency_key}.intent`) {
    throw new Error("compute transport intent path is not canonical");
  }
  if (fundingLockPath !== `${journalPath}.funding.lock`) throw new Error("compute funding lock path is not canonical");
  try { await fs.access(path.join(intentPath, "AMBIGUOUS")); }
  catch { throw new Error("compute transport intent is not ambiguous"); }
  const failure = await readFailureEvidence(intentPath);
  const key = intent.idempotency_key;
  const payer = String(intent.payer || "").toLowerCase();
  const ids = intent.funding_receipt_ids;
  if (typeof key !== "string" || !key || payer !== FAILED_SETTLEMENT_PAYER
    || !Array.isArray(ids) || ids.length !== 1 || ids[0] !== ORIGINAL_FUNDING_ID) {
    throw new Error("compute settlement intent is invalid");
  }
  if (typeof intent.ts !== "string" || intent.max_cost_usdc !== FAILED_SETTLEMENT_COST_USDC) {
    throw new Error("compute settlement intent is invalid");
  }
  const fundingReceiptIds = [ORIGINAL_FUNDING_ID];
  const expected = {
    tx_hash: FAILED_SETTLEMENT_TX, expected_chain_id: 8453, expected_contract: BASE_USDC,
    expected_recipient: FAILED_SETTLEMENT_PAYEE, expected_payer: payer,
    expected_amount_atomic: FAILED_SETTLEMENT_AMOUNT_ATOMIC, expected_log_index: FAILED_SETTLEMENT_LOG_INDEX,
  };
  const currentRows = await rows(journalPath);
  const existing = currentRows.find((row) => row?.idempotency_key === key);
  if (currentRows.some((row) => String(row?.settlement?.transaction || "").toLowerCase() === expected.tx_hash
    && row?.idempotency_key !== key)) {
    throw new Error("compute settlement transaction is already bound to another intent");
  }
  let proof;
  try { proof = await verifyEvmReceipt(expected); } catch { throw new Error("compute settlement verification failed"); }
  if (!strictProofMatches(proof, expected)) throw new Error("compute settlement verification failed");
  if (existing) {
    if (!isFailedSettlementReceipt(existing, key, payer, fundingReceiptIds, failure)) {
      throw new Error("compute settlement replay does not match the original proof");
    }
    await clearSettlementLocks(intentPath, fundingLockPath);
    return { appended: false, duplicate: true, receipt: existing };
  }
  const revenueReceipts = await rows(revenueJournalPath);
  const fundingRows = revenueReceipts.filter((row) => row?.idempotency_key === ORIGINAL_FUNDING_ID);
  if (fundingRows.length !== 1 || fundingRows[0].signed_net !== 0.003 || fundingRows[0].recipient !== payer) {
    throw new Error("compute settlement funding provenance rejected");
  }
  const authorization = authorizeEarnedSpend({
    amountUsdc: FAILED_SETTLEMENT_COST_USDC, fundingReceiptIds, revenueReceipts,
    recipient: payer, fundingSpentUsdc: fundedCost(currentRows, fundingReceiptIds),
    reserveUsdc: FAILED_SETTLEMENT_RESERVE_USDC, sessionSpentUsdc: 0,
    sessionCapUsdc: FAILED_SETTLEMENT_COST_USDC,
  });
  if (!authorization.allowed) throw new Error(`compute settlement funding rejected: ${authorization.reason}`);
  const diagnostic = `stale model ${STALE_MODEL}; current catalog model ${CURRENT_MODEL}`;
  const receipt = {
    schema_version: 1, receipt_type: "compute", outcome: "failed_output", idempotency_key: key,
    payer, cost_usdc: FAILED_SETTLEMENT_COST_USDC, funding_receipt_ids: fundingReceiptIds,
    settlement: {
      success: true, transaction: expected.tx_hash, network: "eip155:8453", payer,
      amount_atomic: FAILED_SETTLEMENT_AMOUNT_ATOMIC, asset: BASE_USDC.toLowerCase(),
      pay_to: FAILED_SETTLEMENT_PAYEE, contract: BASE_USDC.toLowerCase(),
      log_index: FAILED_SETTLEMENT_LOG_INDEX, scheme: "exact",
    },
    http_status: failure.http_status, provider_code: failure.provider_code, output_present: failure.output_present,
    stage: "paid_compute", model: failure.model, source_sha256: failure.source_sha256,
    diagnostic, model_diagnostic: { reason: "stale_model", stale_model: STALE_MODEL, current_model: CURRENT_MODEL },
    occurred_at: intent.ts,
  };
  const appended = await appendComputeReceipt(journalPath, receipt);
  const stored = (await rows(journalPath)).find((row) => row?.idempotency_key === key);
  if (!stored || !isFailedSettlementReceipt(stored, key, payer, fundingReceiptIds, failure)) {
    throw new Error("compute settlement append readback failed");
  }
  await clearSettlementLocks(intentPath, fundingLockPath);
  return { appended: appended.appended, duplicate: appended.duplicate, receipt: stored };
}

export async function executeComputeRequest({
  journalPath, intentId, payer, request, fundingReceiptIds, revenueReceipts,
  maxCostUsdc, reserveUsdc = 0, sessionSpentUsdc = 0, sessionCapUsdc,
  getBalance, transport,
} = {}) {
  if (!journalPath || typeof getBalance !== "function" || typeof transport !== "function") {
    throw new Error("compute execution dependencies are required");
  }
  const idempotencyKey = keyFor({ intentId, payer, request });
  const initialRows = await rows(journalPath);
  const existing = initialRows.find((row) => row?.idempotency_key === idempotencyKey);
  if (existing) return { appended: false, duplicate: true, receipt: existing };
  await fs.mkdir(path.dirname(journalPath), { recursive: true });
  const intentLock = `${journalPath}.${idempotencyKey}.intent`;
  const fundingLock = `${journalPath}.funding.lock`;
  try { await fs.mkdir(intentLock); } catch (error) {
    if (error?.code === "EEXIST") throw new Error("compute intent is already in progress or requires reconciliation");
    throw error;
  }
  try { await fs.mkdir(fundingLock); } catch (error) {
    await fs.rm(intentLock, { recursive: true, force: true });
    if (error?.code === "EEXIST") throw new Error("compute funding is already in use or requires reconciliation");
    throw error;
  }
  let transportStarted = false;
  try {
    const currentRows = await rows(journalPath);
    const afterLock = currentRows.find((row) => row?.idempotency_key === idempotencyKey);
    if (afterLock) {
      await fs.rm(intentLock, { recursive: true, force: true });
      await fs.rm(fundingLock, { recursive: true, force: true });
      return { appended: false, duplicate: true, receipt: afterLock };
    }
    const fundingSpentUsdc = fundedCost(currentRows, fundingReceiptIds);
    const authorization = authorizeEarnedSpend({
      amountUsdc: maxCostUsdc, fundingReceiptIds, revenueReceipts, reserveUsdc,
      recipient: payer,
      fundingSpentUsdc,
      sessionSpentUsdc: round(Number(sessionSpentUsdc) + fundingSpentUsdc), sessionCapUsdc,
    });
    if (!authorization.allowed) throw new Error(`compute funding rejected: ${authorization.reason}`);
    const preBalanceUsdc = await getBalance();
    await fs.writeFile(path.join(intentLock, "intent.json"), JSON.stringify({
      idempotency_key: idempotencyKey, payer: String(payer).toLowerCase(),
      max_cost_usdc: maxCostUsdc, funding_receipt_ids: fundingReceiptIds,
      state: "transport_started", ts: new Date().toISOString(),
    }), { mode: 0o600 });
    transportStarted = true;
    const result = await transport({ request, payer, maxCostUsdc });
    const postBalanceUsdc = await getBalance();
    const costUsdc = result?.costUsdc ?? round(Number(preBalanceUsdc) - Number(postBalanceUsdc));
    if (!Number.isFinite(Number(costUsdc)) || Number(costUsdc) > Number(maxCostUsdc)) {
      throw new Error("compute settled cost exceeds authorization");
    }
    const receipt = buildComputeReceipt({
      intentId, payer, request, fundingReceiptIds, revenueReceipts,
      preBalanceUsdc, postBalanceUsdc, ...result, costUsdc,
    });
    const appended = await appendComputeReceipt(journalPath, receipt);
    await fs.rm(intentLock, { recursive: true, force: true });
    await fs.rm(fundingLock, { recursive: true, force: true });
    return { ...appended, output: result.output };
  } catch (error) {
    const safelyUnbroadcast = error?.code === "PAYMENT_REQUIREMENT_REJECTED_BEFORE_SIGNING"
      || error?.code === "PAYMENT_REQUEST_NOT_BROADCAST";
    if (!transportStarted || safelyUnbroadcast) {
      await fs.rm(intentLock, { recursive: true, force: true });
      await fs.rm(fundingLock, { recursive: true, force: true });
    }
    else await fs.writeFile(path.join(intentLock, "AMBIGUOUS"), "manual settlement reconciliation required\n", { mode: 0o600 }).catch(() => {});
    throw error;
  }
}
