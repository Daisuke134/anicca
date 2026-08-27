import assert from "node:assert/strict";
import { access, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { normalizeRevenueReceipt } from "../../../skills/agent-economy/lib/revenue-receipt.mjs";
import { appendComputeReceipt, reconcileFailedComputeSettlement } from "../compute-receipt.mjs";

const PAYER = "0x810f6d61f7606deee2657d3083e150a222bc29c5";
const PAYEE = "0xe9030014f5dae217d0a152f02a043567b16c1abf";
const TX = "0x1b31ef383fae0078a24adcfa1f78fe0eefd390bc2b02fdb25c558498032e2774";
const CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const REVENUE_ID = "revenue:v2:9e849219a7c479aa837ab3fedbc3f4f25c2a1e8142ce461888cd0a0b3defeeb3";
const FAILURE_SOURCE_SHA256 = "9c5c9d0393f664c69bea3e470cac21699d8e4d56a55c6b7ddd71bc00484475ee";

const revenue = normalizeRevenueReceipt({
  provider: "x402",
  payer: "0x644678ad37833c0d52f0170f1f73a5e62bc3e6d5",
  recipient: PAYER,
  gross: 0.003,
  fee: 0,
  refund: 0,
  asset: "USDC",
  terminal_state: "settled",
  occurred_at: "2026-08-24T01:35:29.000Z",
  proof: {
    chain_id: 8453,
    tx_hash: "0x36deb1f3921a399d2b2b1d8db90821ac5d6d785a74689b056f6d12d5ec06135c",
    log_index: 503,
    verified: true,
  },
});
assert.equal(revenue.idempotency_key, REVENUE_ID);

async function seedIntent(root, {
  key = "compute:failed-settlement-1", payer = PAYER, fundingReceiptIds = [REVENUE_ID],
  maxCostUsdc = 0.002, ambiguous = true,
} = {}) {
  const journalPath = join(root, "compute.jsonl");
  const intentPath = `${journalPath}.${key}.intent`;
  const fundingLockPath = `${journalPath}.funding.lock`;
  await mkdir(intentPath, { recursive: true });
  await mkdir(fundingLockPath, { recursive: true });
  await writeFile(join(intentPath, "intent.json"), JSON.stringify({
    idempotency_key: key,
    intent_id: "failed-blockrun-attempt",
    payer,
    max_cost_usdc: maxCostUsdc,
    funding_receipt_ids: fundingReceiptIds,
    state: "transport_started",
    ts: "2026-08-27T17:00:00.000Z",
  }));
  if (ambiguous) await writeFile(join(intentPath, "AMBIGUOUS"), "manual settlement reconciliation required\n");
  await writeFile(join(intentPath, "failure.json"), JSON.stringify({
    schema_version: 1,
    http_status: 429,
    provider_code: "FREE_MODEL_FAILED",
    output_present: false,
    model: "openai/gpt-5-nano",
    source_sha256: FAILURE_SOURCE_SHA256,
  }));
  return { journalPath, intentPath, fundingLockPath };
}

function strictProof(expected) {
  return {
    verified: true,
    status: "0x1",
    chain_id: expected.expected_chain_id,
    tx_hash: expected.tx_hash,
    transfer: {
      contract: expected.expected_contract.toLowerCase(),
      payer: expected.expected_payer.toLowerCase(),
      recipient: expected.expected_recipient.toLowerCase(),
      amount_atomic: expected.expected_amount_atomic,
      log_index: expected.expected_log_index,
    },
  };
}

test("reconciles one settled failed output, consumes funding, and clears locks only after append", async () => {
  const root = await mkdtemp(join(tmpdir(), "failed-settlement-reconcile-"));
  const revenueJournalPath = join(root, "revenue.jsonl");
  await writeFile(revenueJournalPath, `${JSON.stringify(revenue)}\n`);
  const paths = await seedIntent(root);
  const seen = [];

  const first = await reconcileFailedComputeSettlement({
    ...paths,
    revenueJournalPath,
    verifyEvmReceipt: async (expected) => {
      seen.push(expected);
      return strictProof(expected);
    },
  });

  assert.equal(first.appended, true);
  assert.equal(first.duplicate, false);
  assert.equal(seen[0].expected_chain_id, 8453);
  assert.equal(seen[0].expected_contract.toLowerCase(), CONTRACT.toLowerCase());
  assert.equal(seen[0].expected_payer, PAYER);
  assert.equal(seen[0].expected_recipient, PAYEE);
  assert.equal(seen[0].expected_amount_atomic, "2000");
  assert.equal(seen[0].expected_log_index, 29);

  const rows = (await readFile(paths.journalPath, "utf8")).trim().split("\n").map(JSON.parse);
  assert.equal(rows.length, 1);
  const row = rows[0];
  assert.equal(row.receipt_type, "compute");
  assert.equal(row.outcome, "failed_output");
  assert.equal(row.idempotency_key, "compute:failed-settlement-1");
  assert.equal(row.cost_usdc, 0.002);
  assert.deepEqual(row.funding_receipt_ids, [REVENUE_ID]);
  assert.equal(row.http_status, 429);
  assert.equal(row.provider_code, "FREE_MODEL_FAILED");
  assert.match(JSON.stringify(row.model_diagnostic), /stale/u);
  assert.equal(row.settlement.transaction, TX);
  assert.equal(row.settlement.amount_atomic, "2000");
  assert.equal(row.settlement.pay_to, PAYEE);
  assert.equal("request" in row, false);
  assert.equal("prompt" in row, false);
  assert.equal("output" in row, false);
  await assert.rejects(() => access(paths.intentPath));
  await assert.rejects(() => access(paths.fundingLockPath));

  await seedIntent(root);
  const replay = await reconcileFailedComputeSettlement({
    ...paths,
    revenueJournalPath,
    verifyEvmReceipt: async (expected) => strictProof(expected),
  });
  assert.equal(replay.appended, false);
  assert.equal(replay.duplicate, true);
  assert.equal((await readFile(paths.journalPath, "utf8")).trim().split("\n").length, 1);
  await assert.rejects(() => access(paths.intentPath));
  await assert.rejects(() => access(paths.fundingLockPath));

  const second = await seedIntent(root, { key: "compute:failed-settlement-2" });
  await assert.rejects(() => reconcileFailedComputeSettlement({
    ...second,
    revenueJournalPath,
    verifyEvmReceipt: async (expected) => strictProof(expected),
  }), /funding|transaction|intent/u);
  await access(second.intentPath);
  await access(second.fundingLockPath);
});

test("failed settlement reconciliation leaves both locks when strict proof verification fails", async () => {
  const root = await mkdtemp(join(tmpdir(), "failed-settlement-reconcile-reject-"));
  const revenueJournalPath = join(root, "revenue.jsonl");
  await writeFile(revenueJournalPath, `${JSON.stringify(revenue)}\n`);
  const paths = await seedIntent(root, { key: "compute:failed-settlement-reject" });

  await assert.rejects(() => reconcileFailedComputeSettlement({
    ...paths,
    revenueJournalPath,
    verifyEvmReceipt: async () => ({ verified: false, reason: "wrong_transaction" }),
  }), /verification|settlement|proof/u);
  await access(paths.intentPath);
  await access(paths.fundingLockPath);
  await assert.rejects(() => access(paths.journalPath));
});

test("strict proof mutations for every settlement tuple field remain rejected", async () => {
  const mutations = [
    (proof) => ({ ...proof, status: "0x0" }),
    (proof) => ({ ...proof, chain_id: 1 }),
    (proof) => ({ ...proof, tx_hash: `0x${"aa".repeat(32)}` }),
    (proof) => ({ ...proof, transfer: { ...proof.transfer, contract: `0x${"11".repeat(20)}` } }),
    (proof) => ({ ...proof, transfer: { ...proof.transfer, payer: `0x${"12".repeat(20)}` } }),
    (proof) => ({ ...proof, transfer: { ...proof.transfer, recipient: `0x${"13".repeat(20)}` } }),
    (proof) => ({ ...proof, transfer: { ...proof.transfer, amount_atomic: "2001" } }),
    (proof) => ({ ...proof, transfer: { ...proof.transfer, log_index: 30 } }),
  ];
  for (const [index, mutate] of mutations.entries()) {
    const root = await mkdtemp(join(tmpdir(), `failed-settlement-proof-${index}-`));
    const revenueJournalPath = join(root, "revenue.jsonl");
    await writeFile(revenueJournalPath, `${JSON.stringify(revenue)}\n`);
    const paths = await seedIntent(root, { key: `compute:failed-proof-${index}` });
    await assert.rejects(() => reconcileFailedComputeSettlement({
      ...paths,
      revenueJournalPath,
      verifyEvmReceipt: async (expected) => mutate(strictProof(expected)),
    }), /verification/u);
    await access(paths.intentPath);
    await access(paths.fundingLockPath);
  }
});

test("reconciliation rejects a second spend that would consume the funding reserve", async () => {
  const root = await mkdtemp(join(tmpdir(), "failed-settlement-reserve-"));
  const revenueJournalPath = join(root, "revenue.jsonl");
  await writeFile(revenueJournalPath, `${JSON.stringify(revenue)}\n`);
  const paths = await seedIntent(root, { key: "compute:failed-reserve" });
  await writeFile(paths.journalPath, `${JSON.stringify({
    receipt_type: "compute",
    cost_usdc: 0.002,
    funding_receipt_ids: [revenue.idempotency_key],
    settlement: { transaction: `0x${"aa".repeat(32)}` },
  })}\n`);
  await assert.rejects(() => reconcileFailedComputeSettlement({
    ...paths,
    revenueJournalPath,
    verifyEvmReceipt: async (expected) => strictProof(expected),
  }), /reserve-floor/u);
  await access(paths.intentPath);
  await access(paths.fundingLockPath);
});

test("reconciliation requires the exact ambiguous intent path and marker", async () => {
  const root = await mkdtemp(join(tmpdir(), "failed-settlement-intent-fence-"));
  const revenueJournalPath = join(root, "revenue.jsonl");
  await writeFile(revenueJournalPath, `${JSON.stringify(revenue)}\n`);
  const missingMarker = await seedIntent(root, { key: "compute:missing-ambiguous", ambiguous: false });
  await assert.rejects(() => reconcileFailedComputeSettlement({
    ...missingMarker, revenueJournalPath, verifyEvmReceipt: async (expected) => strictProof(expected),
  }), /ambiguous|marker|intent/u);
  await access(missingMarker.intentPath);
  await access(missingMarker.fundingLockPath);

  const wrong = await seedIntent(root, { key: "compute:exact-intent" });
  const wrongPath = `${wrong.journalPath}.compute:other.intent`;
  await mkdir(wrongPath, { recursive: true });
  await writeFile(join(wrongPath, "intent.json"), await readFile(join(wrong.intentPath, "intent.json")));
  await writeFile(join(wrongPath, "AMBIGUOUS"), "manual settlement reconciliation required\n");
  await writeFile(join(wrongPath, "failure.json"), await readFile(join(wrong.intentPath, "failure.json")));
  await assert.rejects(() => reconcileFailedComputeSettlement({
    journalPath: wrong.journalPath, intentPath: wrongPath, fundingLockPath: wrong.fundingLockPath,
    revenueJournalPath, verifyEvmReceipt: async (expected) => strictProof(expected),
  }), /path|intent/u);
  await access(wrongPath);
  await access(wrong.fundingLockPath);
});

test("reconciliation accepts only the sanitized durable failure evidence", async () => {
  const variants = [
    ["missing", (path) => rm(path)],
    ["extra", async (path) => writeFile(path, JSON.stringify({
      schema_version: 1, http_status: 429, provider_code: "FREE_MODEL_FAILED", output_present: false,
      model: "openai/gpt-5-nano", source_sha256: FAILURE_SOURCE_SHA256, prompt: "secret",
    }))],
    ["bad-hash", async (path) => writeFile(path, JSON.stringify({
      schema_version: 1, http_status: 429, provider_code: "FREE_MODEL_FAILED", output_present: false,
      model: "openai/gpt-5-nano", source_sha256: "A".repeat(64),
    }))],
    ["different-valid-hash", async (path) => writeFile(path, JSON.stringify({
      schema_version: 1, http_status: 429, provider_code: "FREE_MODEL_FAILED", output_present: false,
      model: "openai/gpt-5-nano", source_sha256: "b".repeat(64),
    }))],
  ];
  for (const [name, mutate] of variants) {
    const root = await mkdtemp(join(tmpdir(), `failed-settlement-failure-${name}-`));
    const revenueJournalPath = join(root, "revenue.jsonl");
    await writeFile(revenueJournalPath, `${JSON.stringify(revenue)}\n`);
    const paths = await seedIntent(root, { key: `compute:failure-${name}` });
    await mutate(join(paths.intentPath, "failure.json"));
    await assert.rejects(() => reconcileFailedComputeSettlement({
      ...paths, revenueJournalPath, verifyEvmReceipt: async (expected) => strictProof(expected),
    }), /failure|evidence/u);
    await access(paths.intentPath);
    await access(paths.fundingLockPath);
  }
});

test("reconciliation binds exactly the original canonical funding receipt and max cost", async () => {
  const root = await mkdtemp(join(tmpdir(), "failed-settlement-funding-fence-"));
  const revenueJournalPath = join(root, "revenue.jsonl");
  const alternate = normalizeRevenueReceipt({
    ...revenue,
    gross: 0.004,
    signed_net: undefined,
    proof: { ...revenue.proof, tx_hash: `0x${"77".repeat(32)}` },
    idempotency_key: undefined,
  });
  await writeFile(revenueJournalPath, `${JSON.stringify(alternate)}\n`);
  const alternatePaths = await seedIntent(root, { key: "compute:alternate-funding", fundingReceiptIds: [alternate.idempotency_key] });
  await assert.rejects(() => reconcileFailedComputeSettlement({
    ...alternatePaths, revenueJournalPath, verifyEvmReceipt: async (expected) => strictProof(expected),
  }), /funding|canonical|provenance|intent/u);
  await access(alternatePaths.intentPath);
  await access(alternatePaths.fundingLockPath);

  const splitPaths = await seedIntent(root, {
    key: "compute:split-funding", fundingReceiptIds: [REVENUE_ID, alternate.idempotency_key],
  });
  await writeFile(revenueJournalPath, `${JSON.stringify(revenue)}\n${JSON.stringify(alternate)}\n`);
  await assert.rejects(() => reconcileFailedComputeSettlement({
    ...splitPaths, revenueJournalPath, verifyEvmReceipt: async (expected) => strictProof(expected),
  }), /funding|canonical|provenance|intent/u);
  await access(splitPaths.intentPath);
  await access(splitPaths.fundingLockPath);

  const maxPaths = await seedIntent(root, { key: "compute:max-cost", maxCostUsdc: 0.003 });
  await assert.rejects(() => reconcileFailedComputeSettlement({
    ...maxPaths, revenueJournalPath, verifyEvmReceipt: async (expected) => strictProof(expected),
  }), /max_cost|authorization|exact|intent/u);
  await access(maxPaths.intentPath);
  await access(maxPaths.fundingLockPath);
});

test("reconciliation requires the canonical funding lock path", async () => {
  const root = await mkdtemp(join(tmpdir(), "failed-settlement-lock-path-"));
  const revenueJournalPath = join(root, "revenue.jsonl");
  await writeFile(revenueJournalPath, `${JSON.stringify(revenue)}\n`);
  const paths = await seedIntent(root, { key: "compute:alternate-funding-lock" });
  const alternateFundingLockPath = join(root, "alternate-funding.lock");
  await mkdir(alternateFundingLockPath, { recursive: true });
  await assert.rejects(() => reconcileFailedComputeSettlement({
    journalPath: paths.journalPath,
    intentPath: paths.intentPath,
    fundingLockPath: alternateFundingLockPath,
    revenueJournalPath,
    verifyEvmReceipt: async (expected) => strictProof(expected),
  }), /canonical|funding.*lock|path/u);
  await access(paths.intentPath);
  await access(paths.fundingLockPath);
  await access(alternateFundingLockPath);
});

test("appendComputeReceipt rejects a settlement transaction under a different idempotency key", async () => {
  const root = await mkdtemp(join(tmpdir(), "compute-receipt-tx-identity-"));
  const journalPath = join(root, "compute.jsonl");
  const first = { idempotency_key: "compute:tx-owner", settlement: { transaction: TX } };
  const second = { idempotency_key: "compute:tx-reuse", settlement: { transaction: TX } };
  assert.deepEqual((await appendComputeReceipt(journalPath, first)).appended, true);
  await assert.rejects(() => appendComputeReceipt(journalPath, second), /transaction.*already/u);
  assert.equal((await readFile(journalPath, "utf8")).trim().split("\n").length, 1);
});
