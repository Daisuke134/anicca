import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { promisify } from "node:util";

import {
  adaptCoconala,
  adaptLancers,
  adaptTaskMarket,
  adaptX402,
  adaptX402WithEvmVerifier,
  adaptWriterStripe,
  projectRevenueReceipts,
} from "./revenue-adapters.mjs";
import * as AdapterModule from "./revenue-adapters.mjs";
import { runTaskMarketPass } from "../../earn/taskmarket/taskmarket-work.mjs";

const RECIPIENT = "acct_life_manager_instance_01";
const PAYER = "customer_external_01";
const NOW = "2026-08-27T00:00:00.000Z";
const execFileAsync = promisify(execFile);

test("adapter does not export a forgeable trusted-proof wrapper", () => {
  assert.equal("createTrustedReadbackVerifier" in AdapterModule, false);
});

function squarePng() {
  const png = Buffer.alloc(33);
  Buffer.from("89504e470d0a1a0a", "hex").copy(png, 0);
  png.writeUInt32BE(13, 8); Buffer.from("IHDR").copy(png, 12);
  png.writeUInt32BE(1024, 16); png.writeUInt32BE(1024, 20); png[24] = 8; png[25] = 2;
  return png;
}

function providerProof(id) {
  return { provider_receipt_id: id, verified: true };
}

function trustedProofs(entries) {
  return (row, expected) => {
    const proof = entries[String(row.source_record_id || row.requestId || row.proposal_id || row.taskId || row.external_receipt_id || row.provider_receipt_id || row.transaction || row.id || "")];
    return proof ? { verified: true, ...expected, proof } : null;
  };
}

function accepted(result) {
  assert.equal(result.ok, true, JSON.stringify(result));
  assert.equal(result.rejection, undefined);
  return result.receipt;
}

function rejected(result, reason) {
  assert.equal(result.ok, false, JSON.stringify(result));
  assert.equal(result.receipt, undefined);
  assert.match(`${result.rejection.reason} ${result.rejection.code}`, new RegExp(reason, "i"));
  assert.equal(result.rejection.kind, "revenue_rejection");
  return result.rejection;
}

test("Coconala accepts only a settled provider payout proof and preserves fee/net", () => {
  const receipt = accepted(adaptCoconala({
    source_record_id: "coconala-payout-1",
    requestId: "90000001",
    status: "検収完了",
    gross_jpy: 10000,
    fee_jpy: 2200,
    payout_jpy: 7800,
    payer: PAYER,
    recipient: RECIPIENT,
    payout_status: "paid",
    payout_receipt_id: "coconala-payout-1",
    payout_proof_verified: true,
    ts: NOW,
  }, { readbackVerifier: trustedProofs({ "coconala-payout-1": providerProof("coconala-payout-1") }) }));
  assert.equal(receipt.provider, "coconala");
  assert.equal(receipt.gross, 10000);
  assert.equal(receipt.fee, 2200);
  assert.equal(receipt.signed_net, 7800);
  assert.equal(receipt.asset, "JPY");
  assert.deepEqual(receipt.proof, providerProof("coconala-payout-1"));
});

test("Coconala net-only sales and payout-requested UI are durable rejections", () => {
  rejected(adaptCoconala({
    requestId: "90000002", status: "検収完了", jpy: 7800, net_of_fee: true,
    payout_requested: true, evidence: "https://coconala.example/revenue", ts: NOW,
    payer: PAYER, recipient: RECIPIENT,
  }), "settlement|gross|payout");
});

test("Lancers accepts a paid finance readback and rejects a contract or pending balance", () => {
  const receipt = accepted(adaptLancers({
    source_record_id: "lancers-payment-1",
    proposal_id: "lancers-project-1",
    status: "paid",
    gross_jpy: 20000,
    fee_jpy: 2000,
    payer: "lancers-client-1",
    recipient: RECIPIENT,
    payment_receipt_id: "lancers-payment-1",
    payment_proof_verified: true,
    occurred_at: NOW,
  }, { readbackVerifier: trustedProofs({ "lancers-payment-1": providerProof("lancers-payment-1") }) }));
  assert.equal(receipt.provider, "lancers");
  assert.equal(receipt.signed_net, 18000);
  rejected(adaptLancers({
    provider_id: "lancers-project-2", status: "working", gross_jpy: 20000,
    fee_jpy: 2000, payer: "lancers-client-2", recipient: RECIPIENT, occurred_at: NOW,
  }), "settlement|proof|trusted");
});

test("TaskMarket never treats submitTxHash or an unverified award id as payment proof", () => {
  rejected(adaptTaskMarket({
    taskId: "0x" + "1".repeat(64), submissionId: "submission-1",
    submitTxHash: "0x" + "2".repeat(64), status: "submitted",
    netReward: "5000000", payer: PAYER, recipient: RECIPIENT, occurred_at: NOW,
  }), "award|settlement|proof");

  const award = adaptTaskMarket({
    source_record_id: "taskmarket-award-1",
    taskId: "0x" + "3".repeat(64), submissionId: "submission-2", status: "awarded",
    gross_atomic: "5000000", fee_atomic: "250000", asset: "USDC", decimals: 6,
    payer: PAYER, recipient: RECIPIENT, award_receipt_id: "taskmarket-award-1",
    award_proof_verified: true, occurred_at: NOW,
  });
  assert.equal(award.ok, false);
  assert.match(award.rejection.code + award.rejection.reason, /VERIFIER|non-revenue/i);
});

test("x402 requires a successful settlement readback, valid currency, and external payer", () => {
  const receipt = accepted(adaptX402({
    source_record_id: "x402-tx-1",
    route: "/research", settled: true, success: true,
    amount: "$0.003", currency: "USDC", payer: PAYER, recipient: RECIPIENT,
    transaction: "0x" + "4".repeat(64), chain_id: 8453, log_index: 0,
    settlement_verified: true, ts: NOW,
    amount_atomic: "3000", decimals: 6,
  }, { readbackVerifier: trustedProofs({ "x402-tx-1": { chain_id: 8453, tx_hash: "0x" + "4".repeat(64), log_index: 0, verified: true } }) }));
  assert.equal(receipt.provider, "x402");
  assert.equal(receipt.gross, 0.003);
  assert.equal(receipt.asset, "USDC");
  assert.deepEqual(receipt.proof, { chain_id: 8453, tx_hash: "0x" + "4".repeat(64), log_index: 0, verified: true });
  rejected(adaptX402({
    route: "/research", settled: true, success: true, amount: "$0.003", currency: "USDC",
    payer: PAYER, recipient: RECIPIENT, ts: NOW,
  }), "proof|decimals");
  rejected(adaptX402({
    route: "/research", settled: true, success: true, amount: "$0.003", currency: "USD!",
    payer: PAYER, recipient: RECIPIENT, transaction: "0x" + "5".repeat(64), chain_id: 8453,
    log_index: 0, settlement_verified: true, ts: NOW,
  }), "currency");
  rejected(adaptX402({
    route: "/research", settled: true, success: true, amount: "$0.003", currency: "USDC",
    payer: RECIPIENT, recipient: RECIPIENT, transaction: "0x" + "6".repeat(64), chain_id: 8453,
    log_index: 0, settlement_verified: true, ts: NOW,
  }), "self");
});

test("Writer/Stripe joins settled money with its fee, emits refund correction, and rejects tests/pending/unjoined rows", () => {
  const rows = [
    { receipt_type: "money", kind: "sale", amount: 10, currency: "USD", status: "verified_received", test: false, external_receipt_id: "pi_1", payer: PAYER, recipient: RECIPIENT, occurred_at: NOW, provider_receipt_id: "pi_1", proof_verified: true },
    { receipt_type: "fee", amount: 0.3, currency: "USD", status: "verified", test: false, money_external_receipt_id: "pi_1", external_receipt_id: "txn_1", provider_receipt_id: "txn_1", proof_verified: true, occurred_at: NOW },
    { receipt_type: "refund", amount: 2, currency: "USD", status: "refunded", test: false, external_receipt_id: "re_1", money_external_receipt_id: "pi_1", provider_receipt_id: "re_1", proof_verified: true, occurred_at: NOW },
  ];
  const result = adaptWriterStripe(rows, {
    payer: PAYER,
    recipient: RECIPIENT,
    readbackVerifier: trustedProofs({
      pi_1: providerProof("pi_1"),
      re_1: providerProof("re_1"),
      txn_1: providerProof("txn_1"),
    }),
  });
  assert.equal(result.accepted.length, 2);
  assert.equal(result.rejected.length, 0);
  assert.equal(result.accepted[0].receipt.signed_net, 9.7);
  assert.equal(result.accepted[1].receipt.signed_net, -2);
  assert.equal(result.accepted[1].receipt.terminal_state, "refunded");

  const pending = adaptWriterStripe([
    { receipt_type: "money", kind: "sale", amount: 10, currency: "USD", status: "observed", test: false, external_receipt_id: "pi_pending", occurred_at: NOW },
  ], { payer: PAYER, recipient: RECIPIENT });
  assert.equal(pending.accepted.length, 0);
  assert.equal(pending.rejected.length, 1);
  assert.match(pending.rejected[0].reason, /settled|pending/i);

  const wrongLineage = adaptWriterStripe([
    { receipt_type: "money", kind: "sale", amount: 10, currency: "USD", status: "verified_received", test: false, external_receipt_id: "pi_exact", payer: PAYER, recipient: RECIPIENT, occurred_at: NOW },
    { receipt_type: "fee", amount: 0.3, currency: "USD", status: "verified", test: false, money_external_receipt_id: "pi_exact", external_receipt_id: "txn_exact", occurred_at: NOW },
    { receipt_type: "refund", amount: 2, currency: "USD", status: "refunded", test: false, money_external_receipt_id: "pi_other", artifact_id: "same-artifact", run_id: "same-run", external_receipt_id: "re_wrong", occurred_at: NOW },
  ], {
    payer: PAYER,
    recipient: RECIPIENT,
    readbackVerifier: trustedProofs({ pi_exact: providerProof("pi_exact"), txn_exact: providerProof("txn_exact"), re_wrong: providerProof("re_wrong") }),
  });
  assert.equal(wrongLineage.accepted.length, 1);
  assert.match(wrongLineage.rejected[0].code + wrongLineage.rejected[0].reason, /UNJOINED|lineage/i);
});

test("projectRevenueReceipts appends accepted rows once and persists rejection rows", async () => {
  const root = await mkdtemp(join(tmpdir(), "revenue-adapters-"));
  const journalPath = join(root, "revenue-receipts.jsonl");
  const rejectionPath = join(root, "revenue-rejections.jsonl");
  const rows = [{
    provider: "x402", route: "/research", settled: true, success: true,
    amount_atomic: "3000", decimals: 6, currency: "USDC", payer: PAYER, recipient: RECIPIENT,
    transaction: "0x" + "7".repeat(64), chain_id: 8453, log_index: 0,
    settlement_verified: true, ts: NOW,
  }, {
    provider: "x402", route: "/research", settled: false, success: false,
    amount: "$0.003", currency: "USDC", payer: PAYER, recipient: RECIPIENT, ts: NOW,
  }];
  const verifier = trustedProofs({ ["0x" + "7".repeat(64)]: { chain_id: 8453, tx_hash: "0x" + "7".repeat(64), log_index: 0, verified: true } });
  const first = await projectRevenueReceipts({ journalPath, rejectionPath, provider: "x402", rows, options: { readbackVerifier: verifier } });
  assert.equal(first.accepted, 1);
  assert.equal(first.rejected, 1);
  assert.equal(first.duplicates, 0);
  const second = await projectRevenueReceipts({ journalPath, rejectionPath, provider: "x402", rows, options: { readbackVerifier: verifier } });
  assert.equal(second.accepted, 0);
  assert.equal(second.duplicates, 1);
  assert.equal(second.rejected, 1);
  assert.equal((await readFile(journalPath, "utf8")).trim().split("\n").length, 1);
  assert.equal((await readFile(rejectionPath, "utf8")).trim().split("\n").length, 1);
});

test("raw proof ids and verification booleans cannot bypass the trusted readback boundary", () => {
  const forged = adaptX402({
    source_record_id: "forged-1", route: "/research", settled: true, success: true,
    amount_atomic: "3000", decimals: 6, currency: "USDC", payer: PAYER, recipient: RECIPIENT,
    transaction: "0x" + "8".repeat(64), chain_id: 8453, log_index: 0,
    proof: providerProof("fake-provider-receipt"), settlement_verified: true, ts: NOW,
  });
  rejected(forged, "trusted|proof");
});

test("a Stripe dashboard URL and external id are not trusted proof", () => {
  const result = adaptWriterStripe([
    { receipt_type: "money", kind: "sale", amount: 10, currency: "USD", status: "verified_received", test: false, external_receipt_id: "pi_fake", source_url: "https://dashboard.stripe.com/payments/pi_fake", payer: PAYER, recipient: RECIPIENT, occurred_at: NOW },
    { receipt_type: "fee", amount: 0.3, currency: "USD", status: "verified", test: false, money_external_receipt_id: "pi_fake", external_receipt_id: "txn_fake", source_url: "https://dashboard.stripe.com/balance/txn_fake", occurred_at: NOW },
  ], { payer: PAYER, recipient: RECIPIENT });
  assert.equal(result.accepted.length, 0);
  assert.equal(result.rejected.length, 1);
  assert.match(result.rejected[0].reason + result.rejected[0].code, /trusted|proof/i);
});

test("x402 atomic amount 3000 at six decimals is 0.003 and needs chain proof", () => {
  const result = adaptX402({
    source_record_id: "x402-atomic", route: "/research", settled: true, success: true,
    amount_atomic: "3000", decimals: 6, currency: "USDC", payer: PAYER, recipient: RECIPIENT,
    transaction: "0x" + "9".repeat(64), chain_id: 8453, log_index: 0, ts: NOW,
  }, { readbackVerifier: trustedProofs({ "x402-atomic": { chain_id: 8453, tx_hash: "0x" + "9".repeat(64), log_index: 0, verified: true } }) });
  const receipt = accepted(result);
  assert.equal(receipt.gross, 0.003);
  assert.equal(receipt.proof.provider_receipt_id, undefined);
  assert.deepEqual(receipt.proof, { chain_id: 8453, tx_hash: "0x" + "9".repeat(64), log_index: 0, verified: true });
});

test("provider verifier must echo the full expected tuple", () => {
  const base = {
    source_record_id: "tuple-1", requestId: "tuple-1", status: "paid", gross: "10", fee: "1", refund: "0",
    asset: "USD", payer: PAYER, recipient: RECIPIENT, occurred_at: NOW,
  };
  for (const field of ["gross", "fee", "refund", "payer", "recipient", "asset", "terminal_state"]) {
    const result = adaptCoconala(base, {
      readbackVerifier: (_row, expected) => ({
        verified: true,
        ...expected,
        [field]: field === "terminal_state" ? "pending" : field === "asset" ? "EUR" : field === "payer" ? "other" : field === "recipient" ? "other" : "999",
        proof: providerProof("tuple-1"),
      }),
    });
    assert.equal(result.ok, false, field);
    assert.match(result.rejection.code, /PROOF_BINDING_MISMATCH|MALFORMED_CURRENCY|NON_TERMINAL/);
  }
});

test("x402 production adapter calls strict EVM verifier with exact transfer tuple", async () => {
  const payer = "0x1111111111111111111111111111111111111111";
  const recipient = "0x2222222222222222222222222222222222222222";
  const tx = "0x" + "d".repeat(64);
  let captured;
  const result = await adaptX402WithEvmVerifier({
    source_record_id: "x402-strict", settled: true, success: true, amount_atomic: "3000", decimals: 6,
    currency: "USDC", payer, recipient, transaction: tx, chain_id: 8453, log_index: 4, ts: NOW,
  }, {
    evmVerifier: async (expected) => {
      captured = expected;
      return {
        verified: true, chain_id: 8453, tx_hash: tx,
        transfer: { contract: "0x833589fcd6edb6e08f4c7c32d4f71b54bdA02913".toLowerCase(), payer, recipient, amount_atomic: "3000", log_index: 4 },
      };
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.receipt.gross, 0.003);
  assert.equal(result.receipt.proof.log_index, 4);
  assert.equal(captured.expected_contract.toLowerCase(), "0x833589fcd6edb6e08f4c7c32d4f71b54bdA02913".toLowerCase());
  assert.equal(captured.expected_amount_atomic, "3000");
  assert.equal(captured.expected_payer, payer);
  assert.equal(captured.expected_recipient, recipient);
  assert.equal(captured.expected_log_index, 4);
});

test("twenty concurrent projections append one receipt and one rejection", async () => {
  const root = await mkdtemp(join(tmpdir(), "revenue-adapters-concurrent-"));
  const journalPath = join(root, "journal.jsonl");
  const rejectionPath = join(root, "rejections.jsonl");
  const tx = "0x" + "a".repeat(64);
  const rows = [{ source_record_id: "concurrent-1", provider: "x402", settled: true, success: true, amount_atomic: "3000", decimals: 6, currency: "USDC", payer: PAYER, recipient: RECIPIENT, transaction: tx, chain_id: 8453, log_index: 0, ts: NOW }, { source_record_id: "concurrent-bad", provider: "x402", settled: false, success: false, amount_atomic: "3000", decimals: 6, currency: "USDC", payer: PAYER, recipient: RECIPIENT, ts: NOW }];
  const verifier = trustedProofs({ "concurrent-1": { chain_id: 8453, tx_hash: tx, log_index: 0, verified: true } });
  await Promise.all(Array.from({ length: 20 }, () => projectRevenueReceipts({ journalPath, rejectionPath, provider: "x402", rows, options: { readbackVerifier: verifier } })));
  assert.equal((await readFile(journalPath, "utf8")).trim().split("\n").length, 1);
  assert.equal((await readFile(rejectionPath, "utf8")).trim().split("\n").length, 1);
});

test("deterministic CLI projection of a raw lane outbox records rejection without a verifier", async () => {
  const root = await mkdtemp(join(tmpdir(), "revenue-adapters-cli-"));
  const source = join(root, "x402-sales.jsonl");
  const journalPath = join(root, "journal.jsonl");
  const rejectionPath = join(root, "rejections.jsonl");
  await writeFile(source, `${JSON.stringify({
    source_record_id: "cli-raw", settled: true, success: true, amount_atomic: "3000", decimals: 6,
    currency: "USDC", payer: PAYER, recipient: RECIPIENT,
    transaction: "0x" + "b".repeat(64), chain_id: 8453, log_index: 0,
    proof: providerProof("forged-by-outbox"), proof_verified: true, ts: NOW,
  })}\n`);
  const { stdout } = await execFileAsync(process.execPath, [
    "skills/agent-economy/lib/revenue-adapters.mjs", "--provider", "x402", "--rows", source,
    "--journal", journalPath, "--rejections", rejectionPath,
  ], { cwd: process.cwd(), timeout: 5000 });
  const result = JSON.parse(stdout);
  assert.equal(result.accepted, 0);
  assert.equal(result.rejected, 1);
  await assert.rejects(() => readFile(journalPath, "utf8"), { code: "ENOENT" });
  assert.equal((await readFile(rejectionPath, "utf8")).trim().split("\n").length, 1);
});

test("TaskMarket natural owner projects an official award as rejection until an official verifier exists", async () => {
  const root = await mkdtemp(join(tmpdir(), "revenue-adapters-taskmarket-owner-"));
  const taskId = "0x" + "c".repeat(64);
  const awardId = "taskmarket-award-owner";
  const selected = {
    id: taskId, status: "open", phase: "active", submissionWindowOpen: true, stakeRequired: false,
    description: "Make one still image, 1:1 square. Use GPT Image 2. Deliver one finished hero image.",
    reward: "5000000", netReward: "5000000", submissionCount: 1,
    expiryTime: "2026-08-28T00:00:00Z",
  };
  const recorded = {
    id: "submission-owner", taskId, status: "awarded", gross_atomic: "5000000", fee_atomic: "0",
    asset: "USDC", decimals: 6, payer: PAYER, recipient: RECIPIENT,
    award_receipt_id: awardId, occurred_at: NOW,
  };
  let submissionReads = 0;
  const result = await runTaskMarketPass({
    action: "execute", aniccaHome: root, earnLedgerPath: join(root, "earn.jsonl"), now: Date.parse(NOW),
    revenueJournalPath: join(root, "revenue.jsonl"), revenueRejectionPath: join(root, "rejections.jsonl"),
  }, {
    listTasks: async () => [selected],
    listSubmissions: async () => { submissionReads += 1; return submissionReads < 2 ? [] : [recorded]; },
    loadWalletKey: () => "0x" + "1".repeat(64),
    generateImage: async () => ({ url: "https://cdn.example/hero.png", model: "fixture", costUsd: 0.01 }),
    downloadImage: async () => squarePng(),
    submitTask: async () => ({ ok: true }),
  });
  assert.equal(result.revenue_candidate.ok, false);
  assert.equal(result.revenue_projection.accepted, 0);
  await assert.rejects(() => readFile(join(root, "revenue.jsonl"), "utf8"), { code: "ENOENT" });
  assert.equal((await readFile(join(root, "rejections.jsonl"), "utf8")).trim().split("\n").length, 1);
});
