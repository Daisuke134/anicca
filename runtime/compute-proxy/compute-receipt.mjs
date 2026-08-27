import { createHash, randomUUID } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";
import { authorizeEarnedSpend } from "../../skills/agent-economy/lib/treasury-policy.mjs";

const EVM = /^0x[0-9a-f]{40}$/iu;
const TX = /^0x[0-9a-f]{64}$/iu;
const BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
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
    await fs.appendFile(journalPath, `${JSON.stringify(receipt)}\n`, { encoding: "utf8", mode: 0o600 });
    return { appended: true, duplicate: false, receipt };
  });
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
    if (!transportStarted) {
      await fs.rm(intentLock, { recursive: true, force: true });
      await fs.rm(fundingLock, { recursive: true, force: true });
    }
    else await fs.writeFile(path.join(intentLock, "AMBIGUOUS"), "manual settlement reconciliation required\n", { mode: 0o600 }).catch(() => {});
    throw error;
  }
}
