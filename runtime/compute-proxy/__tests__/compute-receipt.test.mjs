import assert from "node:assert/strict";
import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { normalizeRevenueReceipt } from "../../../skills/agent-economy/lib/revenue-receipt.mjs";
import {
  appendComputeReceipt,
  buildComputeReceipt,
  executeComputeRequest,
} from "../compute-receipt.mjs";
import { publicProxyError, requireInstancePort, selectCappedRequirement } from "../proxy.mjs";

const PAYER = "0x810f6d61f7606deee2657d3083e150a222bc29c5";
const TX = `0x${"ab".repeat(32)}`;
const revenue = [normalizeRevenueReceipt({
  provider: "x402", payer: `0x${"64".repeat(20)}`, recipient: PAYER,
  gross: 0.003, fee: 0, refund: 0, signed_net: 0.003, asset: "USDC",
  terminal_state: "settled", occurred_at: "2026-08-24T01:35:29Z",
  proof: { chain_id: 8453, tx_hash: `0x${"36".repeat(32)}`, log_index: 503, verified: true },
})];
const REVENUE_ID = revenue[0].idempotency_key;

function valid(overrides = {}) {
  return {
    intentId: "compute-1", payer: PAYER, request: { model: "openai/gpt-5-nano" },
    output: { choices: [{ message: { content: "ok" } }] }, costUsdc: 0.001,
    preBalanceUsdc: 1.7, postBalanceUsdc: 1.699,
    fundingReceiptIds: [REVENUE_ID], revenueReceipts: revenue,
    settlement: {
      success: true, transaction: TX, network: "eip155:8453", payer: PAYER, amount: "1000",
      requirement: {
        scheme: "exact", network: "eip155:8453", asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        pay_to: `0x${"22".repeat(20)}`, amount_atomic: "1000",
      },
    },
    ...overrides,
  };
}

test("buildComputeReceipt binds outside revenue, response, balance conservation, and settlement", () => {
  const row = buildComputeReceipt(valid());
  assert.equal(row.receipt_type, "compute");
  assert.equal(row.cost_usdc, 0.001);
  assert.equal(row.settlement.transaction, TX);
  assert.deepEqual(row.funding_receipt_ids, [REVENUE_ID]);
  assert.match(row.idempotency_key, /^compute:/u);
});

test("compute receipt rejects seed funding, payer mismatch, missing output, ambiguous settlement, and balance mismatch", () => {
  assert.throws(() => buildComputeReceipt(valid({ fundingReceiptIds: ["seed:1"] })), /funding/i);
  assert.throws(() => buildComputeReceipt(valid({ settlement: { success: true, transaction: TX, network: "eip155:8453", payer: `0x${"12".repeat(20)}` } })), /payer/i);
  assert.throws(() => buildComputeReceipt(valid({ output: {} })), /output/i);
  assert.throws(() => buildComputeReceipt(valid({ settlement: { success: true, network: "eip155:8453", payer: PAYER } })), /transaction/i);
  assert.throws(() => buildComputeReceipt(valid({ postBalanceUsdc: 1.698 })), /balance/i);
});

test("appendComputeReceipt is append-once under replay", async () => {
  const root = await mkdtemp(join(tmpdir(), "compute-receipt-"));
  const journalPath = join(root, "compute.jsonl");
  const row = buildComputeReceipt(valid());
  assert.deepEqual(await appendComputeReceipt(journalPath, row), { appended: true, duplicate: false, receipt: row });
  assert.deepEqual(await appendComputeReceipt(journalPath, row), { appended: false, duplicate: true, receipt: row });
  assert.equal((await readFile(journalPath, "utf8")).trim().split("\n").length, 1);
});

test("idempotency binds nested prompt content", () => {
  const a = buildComputeReceipt(valid({ request: { model: "openai/gpt-5-nano", messages: [{ role: "user", content: "a" }] } }));
  const b = buildComputeReceipt(valid({ request: { model: "openai/gpt-5-nano", messages: [{ role: "user", content: "b" }] } }));
  assert.notEqual(a.idempotency_key, b.idempotency_key);
});

test("executeComputeRequest authorizes before transport and replay never pays twice", async () => {
  const root = await mkdtemp(join(tmpdir(), "compute-execute-"));
  const journalPath = join(root, "compute.jsonl");
  let calls = 0;
  let balanceCalls = 0;
  const getBalance = async () => (++balanceCalls === 1 ? 1.7 : 1.699);
  const transport = async () => {
    calls += 1;
    return { output: valid().output, costUsdc: 0.001, settlement: valid().settlement };
  };
  const args = {
    journalPath, intentId: "compute-1", payer: PAYER,
    request: valid().request, fundingReceiptIds: [REVENUE_ID], revenueReceipts: revenue,
    maxCostUsdc: 0.001, reserveUsdc: 0.001, sessionCapUsdc: 0.001,
    getBalance, transport,
  };
  const first = await executeComputeRequest(args);
  assert.equal(first.duplicate, false);
  assert.equal(first.output.choices[0].message.content, "ok");
  assert.equal((await executeComputeRequest(args)).duplicate, true);
  assert.equal(calls, 1);
});

test("executeComputeRequest rejects human/seed funding before invoking transport", async () => {
  let calls = 0;
  const root = await mkdtemp(join(tmpdir(), "compute-deny-"));
  await assert.rejects(() => executeComputeRequest({
    journalPath: join(root, "compute.jsonl"),
    intentId: "deny", payer: PAYER, request: valid().request,
    fundingReceiptIds: ["seed:1"], revenueReceipts: revenue,
    maxCostUsdc: 0.001, reserveUsdc: 0, sessionCapUsdc: 0.001,
    getBalance: async () => 1.7, transport: async () => { calls += 1; },
  }), /funding/i);
  assert.equal(calls, 0);
});

test("compute proxy requires a dedicated non-shared port", () => {
  assert.equal(requireInstancePort("8422"), 8422);
  assert.throws(() => requireInstancePort("8402"), /instance-specific/u);
  assert.equal(requireInstancePort("8402", { receiptBacked: false }), 8402);
  assert.throws(() => requireInstancePort(undefined), /instance-specific/u);
});

test("payment requirement selector rejects an over-cap quote before signing", () => {
  const base = { scheme: "exact", network: "eip155:8453", asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", payTo: PAYER };
  assert.equal(selectCappedRequirement(0.001, [{ ...base, amount: "1000" }]).amount, "1000");
  assert.throws(() => selectCappedRequirement(0.001, [{ ...base, amount: "1001" }]), /exceeds authorization/u);
  assert.throws(() => selectCappedRequirement(0.001, [{ ...base, amount: "1000", asset: `0x${"11".repeat(20)}` }]), /unsupported asset/u);
});

test("proxy HTTP errors never reflect provider, journal, or request contents", () => {
  const sentinel = "SECRET_SENTINEL_PRIVATE_MATERIAL";
  const encoded = JSON.stringify(publicProxyError(true));
  assert.doesNotMatch(encoded, new RegExp(sentinel, "u"));
  assert.deepEqual(JSON.parse(encoded), {
    error: { code: "AGENT_ECONOMY_COMPUTE_FAILED", message: "compute request failed" },
  });
});

test("concurrent identical intent invokes payment transport once", async () => {
  const root = await mkdtemp(join(tmpdir(), "compute-race-"));
  let calls = 0;
  let release;
  const pending = new Promise((resolve) => { release = resolve; });
  const args = {
    journalPath: join(root, "compute.jsonl"), intentId: "race", payer: PAYER,
    request: valid().request, fundingReceiptIds: [REVENUE_ID], revenueReceipts: revenue,
    maxCostUsdc: 0.001, reserveUsdc: 0, sessionCapUsdc: 0.001,
    getBalance: async () => 1.7 - calls * 0.001,
    transport: async () => { calls += 1; await pending; return { output: valid().output, costUsdc: 0.001, settlement: valid().settlement }; },
  };
  const first = executeComputeRequest(args);
  await new Promise((resolve) => setTimeout(resolve, 20));
  await assert.rejects(() => executeComputeRequest(args), /already in progress/u);
  release();
  await first;
  assert.equal(calls, 1);
});

test("ambiguous transport failure leaves a durable no-retry intent", async () => {
  const root = await mkdtemp(join(tmpdir(), "compute-ambiguous-"));
  let calls = 0;
  const args = {
    journalPath: join(root, "compute.jsonl"), intentId: "ambiguous", payer: PAYER,
    request: valid().request, fundingReceiptIds: [REVENUE_ID], revenueReceipts: revenue,
    maxCostUsdc: 0.001, reserveUsdc: 0, sessionCapUsdc: 0.001,
    getBalance: async () => 1.7,
    transport: async () => { calls += 1; throw new Error("connection lost after send"); },
  };
  await assert.rejects(() => executeComputeRequest(args), /connection lost/u);
  await assert.rejects(() => executeComputeRequest(args), /requires reconciliation/u);
  assert.equal(calls, 1);
});

test("different intents cannot spend the same earned receipts past cumulative reserve", async () => {
  const root = await mkdtemp(join(tmpdir(), "compute-cumulative-"));
  let calls = 0;
  const common = {
    journalPath: join(root, "compute.jsonl"), payer: PAYER, request: valid().request,
    fundingReceiptIds: [REVENUE_ID], revenueReceipts: revenue,
    maxCostUsdc: 0.001, reserveUsdc: 0.001, sessionCapUsdc: 1,
    getBalance: async () => 1.7 - calls * 0.001,
    transport: async () => { calls += 1; return { output: valid().output, costUsdc: 0.001, settlement: valid().settlement }; },
  };
  await executeComputeRequest({ ...common, intentId: "cumulative-1" });
  await executeComputeRequest({ ...common, intentId: "cumulative-2" });
  await assert.rejects(() => executeComputeRequest({ ...common, intentId: "cumulative-3" }), /reserve-floor/u);
  assert.equal(calls, 2);
});
