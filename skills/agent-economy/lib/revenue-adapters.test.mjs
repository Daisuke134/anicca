import assert from "node:assert/strict";
import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

import {
  adaptCoconala,
  adaptLancers,
  adaptTaskMarket,
  adaptX402,
  adaptWriterStripe,
  projectRevenueReceipts,
} from "./revenue-adapters.mjs";

const RECIPIENT = "acct_life_manager_instance_01";
const PAYER = "customer_external_01";
const NOW = "2026-08-27T00:00:00.000Z";

function providerProof(id) {
  return { provider_receipt_id: id, verified: true };
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
  }));
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
    proposal_id: "lancers-project-1",
    status: "paid",
    gross_jpy: 20000,
    fee_jpy: 2000,
    payer: "lancers-client-1",
    recipient: RECIPIENT,
    payment_receipt_id: "lancers-payment-1",
    payment_proof_verified: true,
    occurred_at: NOW,
  }));
  assert.equal(receipt.provider, "lancers");
  assert.equal(receipt.signed_net, 18000);
  rejected(adaptLancers({
    provider_id: "lancers-project-2", status: "working", gross_jpy: 20000,
    fee_jpy: 2000, payer: "lancers-client-2", recipient: RECIPIENT, occurred_at: NOW,
  }), "settlement|proof");
});

test("TaskMarket never treats submitTxHash as payment proof", () => {
  rejected(adaptTaskMarket({
    taskId: "0x" + "1".repeat(64), submissionId: "submission-1",
    submitTxHash: "0x" + "2".repeat(64), status: "submitted",
    netReward: "5000000", payer: PAYER, recipient: RECIPIENT, occurred_at: NOW,
  }), "award|settlement|proof");

  const receipt = accepted(adaptTaskMarket({
    taskId: "0x" + "3".repeat(64), submissionId: "submission-2", status: "awarded",
    gross_atomic: "5000000", fee_atomic: "250000", asset: "USDC", decimals: 6,
    payer: PAYER, recipient: RECIPIENT, award_receipt_id: "taskmarket-award-1",
    award_proof_verified: true, occurred_at: NOW,
  }));
  assert.equal(receipt.provider, "taskmarket");
  assert.equal(receipt.gross, 5);
  assert.equal(receipt.fee, 0.25);
  assert.equal(receipt.signed_net, 4.75);
});

test("x402 requires a successful settlement readback, valid currency, and external payer", () => {
  const receipt = accepted(adaptX402({
    route: "/research", settled: true, success: true,
    amount: "$0.003", currency: "USDC", payer: PAYER, recipient: RECIPIENT,
    transaction: "0x" + "4".repeat(64), chain_id: 8453, log_index: 0,
    settlement_verified: true, ts: NOW,
  }));
  assert.equal(receipt.provider, "x402");
  assert.equal(receipt.gross, 0.003);
  assert.equal(receipt.asset, "USDC");
  assert.deepEqual(receipt.proof, { chain_id: 8453, tx_hash: "0x" + "4".repeat(64), log_index: 0, verified: true });
  rejected(adaptX402({
    route: "/research", settled: true, success: true, amount: "$0.003", currency: "USDC",
    payer: PAYER, recipient: RECIPIENT, ts: NOW,
  }), "proof");
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
  const result = adaptWriterStripe(rows, { payer: PAYER, recipient: RECIPIENT });
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
});

test("projectRevenueReceipts appends accepted rows once and persists rejection rows", async () => {
  const root = await mkdtemp(join(tmpdir(), "revenue-adapters-"));
  const journalPath = join(root, "revenue-receipts.jsonl");
  const rejectionPath = join(root, "revenue-rejections.jsonl");
  const rows = [{
    provider: "x402", route: "/research", settled: true, success: true,
    amount: "$0.003", currency: "USDC", payer: PAYER, recipient: RECIPIENT,
    transaction: "0x" + "7".repeat(64), chain_id: 8453, log_index: 0,
    settlement_verified: true, ts: NOW,
  }, {
    provider: "x402", route: "/research", settled: false, success: false,
    amount: "$0.003", currency: "USDC", payer: PAYER, recipient: RECIPIENT, ts: NOW,
  }];
  const first = await projectRevenueReceipts({ journalPath, rejectionPath, provider: "x402", rows });
  assert.equal(first.accepted, 1);
  assert.equal(first.rejected, 1);
  assert.equal(first.duplicates, 0);
  const second = await projectRevenueReceipts({ journalPath, rejectionPath, provider: "x402", rows });
  assert.equal(second.accepted, 0);
  assert.equal(second.duplicates, 1);
  assert.equal(second.rejected, 1);
  assert.equal((await readFile(journalPath, "utf8")).trim().split("\n").length, 1);
  assert.equal((await readFile(rejectionPath, "utf8")).trim().split("\n").length, 1);
});
