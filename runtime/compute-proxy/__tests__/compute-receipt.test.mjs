import assert from "node:assert/strict";
import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { privateKeyToAccount } from "viem/accounts";
import { normalizeRevenueReceipt } from "../../../skills/agent-economy/lib/revenue-receipt.mjs";
import {
  appendComputeReceipt,
  buildComputeReceipt,
  executeComputeRequest,
} from "../compute-receipt.mjs";
import {
  createComputeProxy,
  paidTransport,
  publicProxyError,
  requireInstancePort,
  resolveFrontierModel,
  selectCappedRequirement,
} from "../proxy.mjs";

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

test("frontier model resolver trims explicit values and defaults to the current catalog model", () => {
  assert.equal(resolveFrontierModel(" openai/custom-model "), "openai/custom-model");
  assert.equal(resolveFrontierModel(" \t"), "openai/gpt-5.4-nano");
  assert.equal(resolveFrontierModel(undefined), "openai/gpt-5.4-nano");
  assert.notEqual(resolveFrontierModel(undefined), "openai/gpt-5-nano");
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

test("typed pre-sign payment requirement rejection releases intent and funding locks", async () => {
  const root = await mkdtemp(join(tmpdir(), "compute-presign-reject-"));
  let calls = 0;
  const error = new Error("quote over cap");
  error.code = "PAYMENT_REQUIREMENT_REJECTED_BEFORE_SIGNING";
  const args = {
    journalPath: join(root, "compute.jsonl"), intentId: "pre-sign-reject", payer: PAYER,
    request: valid().request, fundingReceiptIds: [REVENUE_ID], revenueReceipts: revenue,
    maxCostUsdc: 0.001, reserveUsdc: 0, sessionCapUsdc: 0.001,
    getBalance: async () => 1.7,
    transport: async () => { calls += 1; throw error; },
  };
  await assert.rejects(() => executeComputeRequest(args), /quote over cap/u);
  await assert.rejects(() => executeComputeRequest(args), /quote over cap/u);
  assert.equal(calls, 2, "retry reaches the pre-sign selector instead of a stale ambiguity lock");
});

test("installed x402 wrapper preserves pre-sign rejection through paidTransport and retries without signing", async () => {
  const root = await mkdtemp(join(tmpdir(), "compute-x402-presign-"));
  let fetchCalls = 0;
  let signatures = 0;
  const requirement = {
    scheme: "exact", network: "eip155:8453", asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    amount: "1001", payTo: `0x${"22".repeat(20)}`, maxTimeoutSeconds: 60,
    extra: { name: "USD Coin", version: "2" },
  };
  const paymentRequired = {
    x402Version: 2, accepts: [requirement],
    resource: { url: "https://blockrun.ai/api/v1/chat/completions", description: "test", mimeType: "application/json" },
  };
  const encoded = Buffer.from(JSON.stringify(paymentRequired), "utf8").toString("base64url");
  const transport = paidTransport({
    address: PAYER,
    signTypedData: async () => { signatures += 1; throw new Error("must not sign"); },
  }, async () => {
    fetchCalls += 1;
    return new Response("", { status: 402, headers: { "PAYMENT-REQUIRED": encoded } });
  });
  const args = {
    journalPath: join(root, "compute.jsonl"), intentId: "x402-pre-sign", payer: PAYER,
    request: valid().request, fundingReceiptIds: [REVENUE_ID], revenueReceipts: revenue,
    maxCostUsdc: 0.001, reserveUsdc: 0, sessionCapUsdc: 0.001,
    getBalance: async () => 1.7, transport,
  };
  for (let attempt = 0; attempt < 2; attempt += 1) {
    await assert.rejects(() => executeComputeRequest(args), (error) => error?.code === "PAYMENT_REQUIREMENT_REJECTED_BEFORE_SIGNING");
  }
  assert.equal(fetchCalls, 2, "each retry reaches only the initial unsigned 402 quote");
  assert.equal(signatures, 0);
});

test("installed x402 wrapper marks signer failure as unbroadcast and releases locks", async () => {
  const root = await mkdtemp(join(tmpdir(), "compute-x402-sign-fail-"));
  let fetchCalls = 0;
  let signatures = 0;
  const requirement = {
    scheme: "exact", network: "eip155:8453", asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    amount: "1000", payTo: `0x${"22".repeat(20)}`, maxTimeoutSeconds: 60,
    extra: { name: "USD Coin", version: "2" },
  };
  const encoded = Buffer.from(JSON.stringify({
    x402Version: 2, accepts: [requirement],
    resource: { url: "https://blockrun.ai/api/v1/chat/completions", description: "test", mimeType: "application/json" },
  }), "utf8").toString("base64url");
  const transport = paidTransport({
    address: PAYER,
    signTypedData: async () => { signatures += 1; throw new Error("local signer failed"); },
  }, async () => {
    fetchCalls += 1;
    return new Response("", { status: 402, headers: { "PAYMENT-REQUIRED": encoded } });
  });
  const args = {
    journalPath: join(root, "compute.jsonl"), intentId: "x402-sign-fail", payer: PAYER,
    request: valid().request, fundingReceiptIds: [REVENUE_ID], revenueReceipts: revenue,
    maxCostUsdc: 0.001, reserveUsdc: 0, sessionCapUsdc: 0.001,
    getBalance: async () => 1.7, transport,
  };
  for (let attempt = 0; attempt < 2; attempt += 1) {
    await assert.rejects(() => executeComputeRequest(args), (error) => error?.code === "PAYMENT_REQUEST_NOT_BROADCAST");
  }
  assert.equal(fetchCalls, 2);
  assert.equal(signatures, 2);
});

test("paidTransport projects only validated status and provider code for non-OK responses", async () => {
  const sentinel = "SECRET_PROVIDER_BODY_AND_MESSAGE";
  const transport = paidTransport({ address: PAYER }, async () => new Response(JSON.stringify({
    error: { message: sentinel, code: "FREE_MODEL_FAILED" }, prompt: sentinel, apiKey: sentinel,
  }), { status: 503, headers: { "content-type": "application/json" } }));
  await assert.rejects(() => transport({ request: valid().request, maxCostUsdc: 0.001 }), (error) => {
    assert.equal(error.message, "BlockRun request failed");
    assert.equal(error.httpStatus, 503);
    assert.equal(error.providerCode, "FREE_MODEL_FAILED");
    assert.doesNotMatch(error.message, new RegExp(sentinel, "u"));
    assert.equal(Object.keys(error).sort().join(","), "httpStatus,providerCode");
    return true;
  });
});

test("unknown provider codes are dropped before they reach the proxy diagnostic sink", async () => {
  const root = await mkdtemp(join(tmpdir(), "compute-unknown-provider-code-"));
  const sentinel = "SECRET_TOKEN_PATH_RAW_MESSAGE";
  const diagnostics = [];
  const transport = paidTransport({ address: PAYER }, async () => new Response(JSON.stringify({
    error: { message: sentinel, code: sentinel }, path: `/private/${sentinel}`,
  }), { status: 503, headers: { "content-type": "application/json" } }));
  const server = createComputeProxy({
    payer: PAYER,
    revenueJournalPath: join(root, "revenue.jsonl"),
    computeJournalPath: join(root, "compute.jsonl"),
    fundingReceiptIds: [REVENUE_ID], maxCostUsdc: 0.001, reserveUsdc: 0, sessionCapUsdc: 0.001,
    getBalance: async () => 1.7, transport, frontierModel: "openai/gpt-5.4-nano",
    diagnosticSink: (diagnostic) => diagnostics.push(diagnostic),
  });
  await import("node:fs/promises").then(({ writeFile }) => writeFile(join(root, "revenue.jsonl"), `${JSON.stringify(revenue[0])}\n`));
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const { port } = server.address();
    const response = await fetch(`http://127.0.0.1:${port}/v1/chat/completions`, {
      method: "POST", headers: { "content-type": "application/json", "idempotency-key": "unknown-provider-code" },
      body: JSON.stringify({ model: "free/glm-4.7", messages: [{ role: "user", content: "hello" }] }),
    });
    assert.equal(response.status, 502);
    assert.deepEqual(await response.json(), publicProxyError(true));
    assert.deepEqual(diagnostics, [{
      event: "compute_execution_failed", stage: "paid_compute", model: "openai/gpt-5.4-nano",
      httpStatus: 503, providerCode: null,
    }]);
    assert.doesNotMatch(JSON.stringify(diagnostics), new RegExp(sentinel, "u"));
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});

test("signed fetch overwrites misleading safe code and remains durably ambiguous", async () => {
  const root = await mkdtemp(join(tmpdir(), "compute-x402-broadcast-"));
  let initialFetches = 0;
  let signedFetches = 0;
  const requirement = {
    scheme: "exact", network: "eip155:8453", asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    amount: "1000", payTo: `0x${"22".repeat(20)}`, maxTimeoutSeconds: 60,
    extra: { name: "USD Coin", version: "2" },
  };
  const encoded = Buffer.from(JSON.stringify({
    x402Version: 2, accepts: [requirement],
    resource: { url: "https://blockrun.ai/api/v1/chat/completions", description: "test", mimeType: "application/json" },
  }), "utf8").toString("base64url");
  const transport = paidTransport(privateKeyToAccount(`0x${"11".repeat(32)}`), async (input) => {
    const request = input instanceof Request ? input : new Request(input);
    if (request.headers.has("PAYMENT-SIGNATURE") || request.headers.has("X-PAYMENT")) {
      signedFetches += 1;
      const error = new Error("connection lost after signed request");
      error.code = "PAYMENT_REQUEST_NOT_BROADCAST";
      throw error;
    }
    initialFetches += 1;
    return new Response("", { status: 402, headers: { "PAYMENT-REQUIRED": encoded } });
  });
  const args = {
    journalPath: join(root, "compute.jsonl"), intentId: "x402-broadcast", payer: PAYER,
    request: valid().request, fundingReceiptIds: [REVENUE_ID], revenueReceipts: revenue,
    maxCostUsdc: 0.001, reserveUsdc: 0, sessionCapUsdc: 0.001,
    getBalance: async () => 1.7, transport,
  };
  await assert.rejects(() => executeComputeRequest(args), (error) => error?.code === "PAYMENT_REQUEST_BROADCAST_AMBIGUOUS");
  await assert.rejects(() => executeComputeRequest(args), /requires reconciliation/u);
  assert.equal(initialFetches, 1);
  assert.equal(signedFetches, 1);
});

test("receipt-backed proxy forces the configured paid model regardless of resident free tier", async () => {
  const root = await mkdtemp(join(tmpdir(), "compute-model-force-"));
  let seenModel;
  let balanceCalls = 0;
  const server = createComputeProxy({
    payer: PAYER,
    revenueJournalPath: join(root, "revenue.jsonl"),
    computeJournalPath: join(root, "compute.jsonl"),
    fundingReceiptIds: [REVENUE_ID], maxCostUsdc: 0.001, reserveUsdc: 0, sessionCapUsdc: 0.001,
    getBalance: async () => (++balanceCalls === 1 ? 1.7 : 1.699),
    transport: async ({ request }) => {
      seenModel = request.model;
      return { output: valid().output, costUsdc: 0.001, settlement: valid().settlement };
    },
    frontierModel: " openai/gpt-5.4-nano ",
  });
  await import("node:fs/promises").then(({ writeFile }) => writeFile(join(root, "revenue.jsonl"), `${JSON.stringify(revenue[0])}\n`));
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const { port } = server.address();
    const response = await fetch(`http://127.0.0.1:${port}/v1/chat/completions`, {
      method: "POST", headers: { "content-type": "application/json", "idempotency-key": "force-paid-model" },
      body: JSON.stringify({ model: "free/glm-4.7", messages: [{ role: "user", content: "hello" }] }),
    });
    assert.equal(response.status, 200);
    assert.equal(seenModel, "openai/gpt-5.4-nano");
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});

test("receipt-backed proxy keeps a generic HTTP error and sends an allowlisted diagnostic", async () => {
  const root = await mkdtemp(join(tmpdir(), "compute-diagnostic-"));
  const sentinel = "SECRET_SENTINEL_PRIVATE_MATERIAL";
  const diagnostics = [];
  const server = createComputeProxy({
    payer: PAYER,
    revenueJournalPath: join(root, "revenue.jsonl"),
    computeJournalPath: join(root, "compute.jsonl"),
    fundingReceiptIds: [REVENUE_ID], maxCostUsdc: 0.001, reserveUsdc: 0, sessionCapUsdc: 0.001,
    getBalance: async () => 1.7,
    transport: async () => {
      const error = new Error(sentinel);
      Object.assign(error, {
        httpStatus: 503, providerCode: "FREE_MODEL_FAILED", prompt: sentinel, request: { token: sentinel },
        response: { body: sentinel }, output: sentinel, key: sentinel, path: `/private/${sentinel}`,
        settlement: { body: sentinel }, unknown: sentinel,
      });
      throw error;
    },
    frontierModel: " openai/gpt-5.4-nano ",
    diagnosticSink: (diagnostic) => diagnostics.push(diagnostic),
  });
  await import("node:fs/promises").then(({ writeFile }) => writeFile(join(root, "revenue.jsonl"), `${JSON.stringify(revenue[0])}\n`));
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const { port } = server.address();
    const response = await fetch(`http://127.0.0.1:${port}/v1/chat/completions`, {
      method: "POST", headers: { "content-type": "application/json", "idempotency-key": "diagnostic" },
      body: JSON.stringify({ model: "free/glm-4.7", messages: [{ role: "user", content: sentinel }] }),
    });
    assert.equal(response.status, 502);
    assert.deepEqual(await response.json(), publicProxyError(true));
    assert.deepEqual(diagnostics, [{
      event: "compute_execution_failed",
      stage: "paid_compute",
      model: "openai/gpt-5.4-nano",
      httpStatus: 503,
      providerCode: "FREE_MODEL_FAILED",
    }]);
    assert.doesNotMatch(JSON.stringify(diagnostics), new RegExp(sentinel, "u"));
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});

test("async diagnostic sink rejection does not change the generic HTTP error or become unhandled", async () => {
  const root = await mkdtemp(join(tmpdir(), "compute-async-diagnostic-"));
  const diagnostics = [];
  const unhandled = [];
  const onUnhandled = (reason) => unhandled.push(reason);
  process.on("unhandledRejection", onUnhandled);
  const server = createComputeProxy({
    payer: PAYER,
    revenueJournalPath: join(root, "revenue.jsonl"),
    computeJournalPath: join(root, "compute.jsonl"),
    fundingReceiptIds: [REVENUE_ID], maxCostUsdc: 0.001, reserveUsdc: 0, sessionCapUsdc: 0.001,
    getBalance: async () => 1.7,
    transport: async () => {
      const error = new Error("transport failure");
      error.httpStatus = 503;
      error.providerCode = "FREE_MODEL_FAILED";
      throw error;
    },
    frontierModel: "openai/gpt-5.4-nano",
    diagnosticSink: async () => { throw new Error("DIAGNOSTIC_SINK_SENTINEL"); },
  });
  await import("node:fs/promises").then(({ writeFile }) => writeFile(join(root, "revenue.jsonl"), `${JSON.stringify(revenue[0])}\n`));
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const { port } = server.address();
    const response = await fetch(`http://127.0.0.1:${port}/v1/chat/completions`, {
      method: "POST", headers: { "content-type": "application/json", "idempotency-key": "async-diagnostic" },
      body: JSON.stringify({ model: "free/glm-4.7", messages: [{ role: "user", content: "hello" }] }),
    });
    assert.equal(response.status, 502);
    assert.deepEqual(await response.json(), publicProxyError(true));
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(unhandled, []);
    assert.deepEqual(diagnostics, []);
  } finally {
    process.off("unhandledRejection", onUnhandled);
    await new Promise((resolve) => server.close(resolve));
  }
});

test("different intents cannot spend the same earned receipts past cumulative reserve", async () => {
  const root = await mkdtemp(join(tmpdir(), "compute-cumulative-"));
  let calls = 0;
  const common = {
    journalPath: join(root, "compute.jsonl"), payer: PAYER, request: valid().request,
    fundingReceiptIds: [REVENUE_ID], revenueReceipts: revenue,
    maxCostUsdc: 0.001, reserveUsdc: 0.001, sessionCapUsdc: 1,
    getBalance: async () => 1.7 - calls * 0.001,
    transport: async () => {
      calls += 1;
      return {
        output: valid().output,
        costUsdc: 0.001,
        settlement: { ...valid().settlement, transaction: `0x${String(calls).padStart(64, "0")}` },
      };
    },
  };
  await executeComputeRequest({ ...common, intentId: "cumulative-1" });
  await executeComputeRequest({ ...common, intentId: "cumulative-2" });
  await assert.rejects(() => executeComputeRequest({ ...common, intentId: "cumulative-3" }), /reserve-floor/u);
  assert.equal(calls, 2);
});
