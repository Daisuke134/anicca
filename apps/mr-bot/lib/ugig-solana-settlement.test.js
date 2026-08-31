"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  verifyUgigSolanaInvoice,
  ugigSolanaLedgerEntry,
  processUgigPaidInvoice,
} = require("./ugig-solana-settlement.js");

const RECIPIENT = "71FfqFniYoMsWZb1qFeQDb1fk2xqvajzivpsnMb44gTf";
const PAYER = "9xQeWvG816bUx9EPfEz3Tq9FZzY5hNhWZQpLJQhY7G6e";
const SIGNATURE = "4".repeat(88);
const DELIVERY = {
  application_id: "5e315cfd-33fc-433b-a5f0-3cfcdc27a9a4",
  gig_id: "2b410cad-7cc9-44fd-b2f1-843d9eae6c24",
  amount_usd: 1,
  payment_currency: "sol",
  merchant_wallet_address: RECIPIENT,
};
const INVOICE = {
  id: "inv-paid-1",
  application_id: DELIVERY.application_id,
  amount_usd: 1,
  currency: "USD",
  status: "paid",
  metadata: {
    merchant_tx_hash: SIGNATURE,
    paid_at: "2026-07-28T10:00:00.000Z",
    settlement_chain: "solana",
    payment_currency: "USD",
    receiver_payment_currency: "sol",
    merchant_wallet_address: RECIPIENT,
    amount_crypto: "0.005",
  },
};

function rpcFixture(overrides = {}) {
  const status = overrides.status || {
    slot: 351000000,
    confirmations: null,
    err: null,
    confirmationStatus: "finalized",
  };
  const transaction = overrides.transaction || {
    slot: 351000000,
    blockTime: 1785232800,
    transaction: {
      signatures: [SIGNATURE],
      message: { accountKeys: [PAYER, RECIPIENT] },
    },
    meta: {
      err: null,
      preBalances: [1_000_000_000, 10_000_000],
      postBalances: [994_995_000, 15_000_000],
    },
  };
  return async (method, params) => {
    if (method === "getSignatureStatuses") {
      assert.deepEqual(params, [[SIGNATURE], { searchTransactionHistory: true }]);
      return { value: [status] };
    }
    if (method === "getTransaction") {
      assert.equal(params[0], SIGNATURE);
      assert.equal(params[1].commitment, "finalized");
      return transaction;
    }
    throw new Error(`unexpected RPC method ${method}`);
  };
}

test("a paid uGig invoice is accepted only after its recipient delta is finalized on Solana", async () => {
  const proof = await verifyUgigSolanaInvoice(DELIVERY, INVOICE, {
    rpcCall: rpcFixture(),
    ownedWalletAddresses: [RECIPIENT],
  });

  assert.equal(proof.signature, SIGNATURE);
  assert.equal(proof.recipient, RECIPIENT);
  assert.equal(proof.received_lamports, "5000000");
  assert.equal(proof.expected_lamports, "5000000");
  assert.equal(proof.slot, 351000000);
  assert.equal(proof.finalized, true);
});

test("unpaid, mismatched, unfinalized, self-funded, failed, and underpaid claims fail closed", async () => {
  await assert.rejects(
    () => verifyUgigSolanaInvoice(DELIVERY, { ...INVOICE, status: "sent" }, { rpcCall: rpcFixture() }),
    /paid/i,
  );
  await assert.rejects(
    () => verifyUgigSolanaInvoice(DELIVERY, { ...INVOICE, amount_usd: 2 }, { rpcCall: rpcFixture() }),
    /amount/i,
  );
  await assert.rejects(
    () => verifyUgigSolanaInvoice(DELIVERY, INVOICE, {
      rpcCall: rpcFixture({ status: { err: null, confirmationStatus: "confirmed" } }),
    }),
    /finalized/i,
  );
  await assert.rejects(
    () => verifyUgigSolanaInvoice(DELIVERY, INVOICE, {
      rpcCall: rpcFixture({
        transaction: {
          slot: 1,
          blockTime: 1785232800,
          transaction: { signatures: [SIGNATURE], message: { accountKeys: [RECIPIENT] } },
          meta: { err: null, preBalances: [10_000_000], postBalances: [15_000_000] },
        },
      }),
      ownedWalletAddresses: [RECIPIENT],
    }),
    /self-funded|payer/i,
  );
  await assert.rejects(
    () => verifyUgigSolanaInvoice(DELIVERY, INVOICE, {
      rpcCall: rpcFixture({
        transaction: {
          slot: 1,
          blockTime: 1785232800,
          transaction: { signatures: [SIGNATURE], message: { accountKeys: [PAYER, RECIPIENT] } },
          meta: { err: { InstructionError: [0, "Custom"] }, preBalances: [1, 1], postBalances: [1, 1] },
        },
      }),
    }),
    /failed/i,
  );
  await assert.rejects(
    () => verifyUgigSolanaInvoice(DELIVERY, INVOICE, {
      rpcCall: rpcFixture({
        transaction: {
          slot: 1,
          blockTime: 1785232800,
          transaction: { signatures: [SIGNATURE], message: { accountKeys: [PAYER, RECIPIENT] } },
          meta: {
            err: null,
            preBalances: [1_000_000_000, 10_000_000],
            postBalances: [999_000_000, 10_999_999],
          },
        },
      }),
    }),
    /underpaid/i,
  );
});

test("the verified receipt becomes one exact USD-micro ledger row with chain evidence", async () => {
  const proof = await verifyUgigSolanaInvoice(DELIVERY, INVOICE, { rpcCall: rpcFixture() });
  const row = ugigSolanaLedgerEntry(DELIVERY, INVOICE, proof);

  assert.equal(row.entry_key, `ugig:invoice:${INVOICE.id}:merchant-payout`);
  assert.equal(row.wallet_address, RECIPIENT);
  assert.equal(row.kind, "financial_external_income");
  assert.equal(row.amount_atomic, "1000000");
  assert.equal(row.amount_decimals, 6);
  assert.equal(row.currency, "USD");
  assert.equal(row.occurred_at, "2026-07-28T10:00:00.000Z");
  assert.equal(row.tx_hash, SIGNATURE);
  assert.equal(row.source, "ugig_work");
  assert.equal(row.meta.chain, "solana:mainnet");
  assert.equal(row.meta.finalized, true);
  assert.equal(row.meta.received_lamports, "5000000");
});

test("the settlement bridge verifies before writing and preserves database idempotency", async () => {
  const writes = [];
  const result = await processUgigPaidInvoice(DELIVERY, INVOICE, {
    rpcCall: rpcFixture(),
    recordEntry: async (row) => {
      writes.push(row);
      return { ok: true, duplicate: true, entry_key: row.entry_key };
    },
  });

  assert.equal(writes.length, 1);
  assert.equal(result.duplicate, true);
  assert.equal(result.entry_key, `ugig:invoice:${INVOICE.id}:merchant-payout`);
});
