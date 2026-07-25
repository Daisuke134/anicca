// node:test — fund-tenant.mjs: the treasury -> tenant funding gate (pure) + the dry/live
// orchestration (I/O fully injected — no real network, no real signing, matching this skill's
// existing acquire-nos.mjs/deploy.mjs test conventions).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import bs58 from "bs58";
import { Keypair, PublicKey } from "@solana/web3.js";

import {
  evaluateTenantFundingGate,
  fundTenant,
  DEFAULT_TENANT_FUND_SOL,
  DEFAULT_TENANT_FUND_NOS,
  MAX_TENANT_FUND_SOL,
  MAX_TENANT_FUND_NOS,
} from "../fund-tenant.mjs";

// ---- evaluateTenantFundingGate (pure) --------------------------------------------------------

test("evaluateTenantFundingGate: allows a well-within-ceiling, well-funded request", () => {
  const gate = evaluateTenantFundingGate({
    solToSend: DEFAULT_TENANT_FUND_SOL,
    nosToSend: DEFAULT_TENANT_FUND_NOS,
    treasurySolBalance: 1,
    treasuryNosBalance: 5,
  });
  assert.equal(gate.allowed, true);
});

test("evaluateTenantFundingGate: refuses above the absolute SOL ceiling regardless of treasury balance", () => {
  const gate = evaluateTenantFundingGate({
    solToSend: MAX_TENANT_FUND_SOL + 0.001,
    nosToSend: 0.01,
    treasurySolBalance: 1000,
    treasuryNosBalance: 1000,
  });
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /exceeds the absolute ceiling/);
});

test("evaluateTenantFundingGate: refuses above the absolute NOS ceiling regardless of treasury balance", () => {
  const gate = evaluateTenantFundingGate({
    solToSend: 0.001,
    nosToSend: MAX_TENANT_FUND_NOS + 0.01,
    treasurySolBalance: 1000,
    treasuryNosBalance: 1000,
  });
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /exceeds the absolute ceiling/);
});

test("evaluateTenantFundingGate: refuses when treasury NOS balance is insufficient (within the ceiling, but the treasury itself is short)", () => {
  const gate = evaluateTenantFundingGate({ solToSend: 0.001, nosToSend: 0.4, treasurySolBalance: 1, treasuryNosBalance: 0.2 });
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /treasury NOS balance/);
});

test("evaluateTenantFundingGate: refuses when sending would breach the treasury's own SOL fee floor (within the ceiling, but the treasury can't spare it)", () => {
  const gate = evaluateTenantFundingGate({
    solToSend: 0.009,
    nosToSend: 0.01,
    treasurySolBalance: 0.015,
    treasuryNosBalance: 5,
    solFeeFloor: 0.01,
  });
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /fee floor/);
});

test("evaluateTenantFundingGate: fails closed on non-finite/zero/negative amounts", () => {
  assert.equal(evaluateTenantFundingGate({ solToSend: 0, nosToSend: 0.01, treasurySolBalance: 1, treasuryNosBalance: 1 }).allowed, false);
  assert.equal(evaluateTenantFundingGate({ solToSend: NaN, nosToSend: 0.01, treasurySolBalance: 1, treasuryNosBalance: 1 }).allowed, false);
  assert.equal(evaluateTenantFundingGate({ solToSend: 0.001, nosToSend: -1, treasurySolBalance: 1, treasuryNosBalance: 1 }).allowed, false);
});

test("evaluateTenantFundingGate: fails closed when treasury balances are unavailable", () => {
  assert.equal(evaluateTenantFundingGate({ solToSend: 0.001, nosToSend: 0.01, treasurySolBalance: NaN, treasuryNosBalance: 1 }).allowed, false);
  assert.equal(evaluateTenantFundingGate({ solToSend: 0.001, nosToSend: 0.01, treasurySolBalance: 1, treasuryNosBalance: undefined }).allowed, false);
});

// ---- fundTenant orchestration (I/O injected) -----------------------------------------------

function makeFakeConnection({ lamports, nosUiAmount, ataExists = true }) {
  return {
    async getBalance() {
      return lamports;
    },
    async getParsedTokenAccountsByOwner() {
      if (nosUiAmount == null) return { value: [] };
      return { value: [{ account: { data: { parsed: { info: { tokenAmount: { uiAmount: nosUiAmount } } } } } }] };
    },
    async getAccountInfo() {
      return ataExists ? { data: Buffer.alloc(0) } : null;
    },
  };
}

test("fundTenant: throws when tenantAddress is missing", async () => {
  await assert.rejects(() => fundTenant({ env: {} }), /tenantAddress is required/);
});

test("fundTenant: throws when no treasury secret is resolvable", async () => {
  await assert.rejects(
    () => fundTenant({ env: {}, tenantAddress: Keypair.generate().publicKey.toBase58() }),
    /no Solana secret resolved/,
  );
});

test("fundTenant: --dry (default) reads real-shaped balances, evaluates the gate, and stops before any signing", async () => {
  const treasury = Keypair.generate();
  const tenantAddress = Keypair.generate().publicKey.toBase58();
  const env = { ANICCA_SOLANA_PRIVATE_KEY: bs58.encode(treasury.secretKey) };
  const connectionFactory = () => makeFakeConnection({ lamports: 1_000_000_000, nosUiAmount: 5 });

  let keypairCtorCalled = false;
  const result = await fundTenant({
    env,
    live: false,
    tenantAddress,
    connectionFactory,
    publicKeyCtor: PublicKey,
    keypairCtor: { fromSecretKey: () => { keypairCtorCalled = true; } },
  });

  assert.equal(result.sent, false);
  assert.equal(result.gate.allowed, true);
  assert.equal(result.treasuryAddress, treasury.publicKey.toBase58());
  assert.equal(result.tenantAddress, tenantAddress);
  assert.equal(keypairCtorCalled, false, "dry mode must never construct a signing Keypair");
});

test("fundTenant: --dry reports a REFUSED gate honestly rather than pretending it would send", async () => {
  const treasury = Keypair.generate();
  const tenantAddress = Keypair.generate().publicKey.toBase58();
  const env = { ANICCA_SOLANA_PRIVATE_KEY: bs58.encode(treasury.secretKey) };
  // Treasury has almost no NOS at all.
  const connectionFactory = () => makeFakeConnection({ lamports: 1_000_000_000, nosUiAmount: 0.001 });

  const result = await fundTenant({ env, live: false, tenantAddress, connectionFactory, publicKeyCtor: PublicKey });
  assert.equal(result.gate.allowed, false);
  assert.equal(result.sent, false);
});

test("fundTenant: --live refuses to build/send a transaction when the gate denies it", async () => {
  const treasury = Keypair.generate();
  const tenantAddress = Keypair.generate().publicKey.toBase58();
  const env = { ANICCA_SOLANA_PRIVATE_KEY: bs58.encode(treasury.secretKey) };
  const connectionFactory = () => makeFakeConnection({ lamports: 1_000_000_000, nosUiAmount: 0 });

  let sendCalled = false;
  const result = await fundTenant({
    env,
    live: true,
    tenantAddress,
    connectionFactory,
    publicKeyCtor: PublicKey,
    sendAndConfirmImpl: async () => { sendCalled = true; return "SIG"; },
  });
  assert.equal(result.gate.allowed, false);
  assert.equal(result.sent, false);
  assert.equal(sendCalled, false);
});

test("fundTenant: --live builds a transfer + token-transfer transaction, signs once, sends once, and ledgers intent+settled", async () => {
  const treasury = Keypair.generate();
  const tenantKp = Keypair.generate();
  const tenantAddress = tenantKp.publicKey.toBase58();
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "tenant-fund-test-"));
  const env = { ANICCA_SOLANA_PRIVATE_KEY: bs58.encode(treasury.secretKey), ANICCA_STATE_DIR: stateDir };
  const connectionFactory = () => makeFakeConnection({ lamports: 1_000_000_000, nosUiAmount: 5, ataExists: false });

  const addedInstructions = [];
  class FakeTransaction {
    add(ix) {
      addedInstructions.push(ix);
      return this;
    }
  }
  let sendCalledWith = null;

  const fakeSplToken = {
    getAssociatedTokenAddressSync: (mint, owner) => new PublicKey("11111111111111111111111111111112"),
    createAssociatedTokenAccountInstruction: () => ({ kind: "create-ata" }),
    createTransferInstruction: (from, to, owner, amount) => ({ kind: "transfer", amount }),
  };

  try {
    const result = await fundTenant({
      env,
      live: true,
      tenantAddress,
      connectionFactory,
      publicKeyCtor: PublicKey,
      keypairCtor: Keypair,
      splToken: fakeSplToken,
      systemProgramCtor: { transfer: (args) => ({ kind: "sol-transfer", ...args }) },
      transactionCtor: FakeTransaction,
      sendAndConfirmImpl: async (connection, tx, signers) => {
        sendCalledWith = { tx, signers };
        return "FAKE_SIGNATURE";
      },
    });

    assert.equal(result.sent, true);
    assert.equal(result.signature, "FAKE_SIGNATURE");
    assert.equal(sendCalledWith.signers.length, 1);
    assert.equal(sendCalledWith.signers[0].publicKey.toBase58(), treasury.publicKey.toBase58());

    // sol-transfer, create-ata (since ataExists:false), transfer — in that order.
    assert.equal(addedInstructions.length, 3);
    assert.equal(addedInstructions[0].kind, "sol-transfer");
    assert.equal(addedInstructions[1].kind, "create-ata");
    assert.equal(addedInstructions[2].kind, "transfer");

    const ledgerFile = path.join(stateDir, "nosana-tenant-funding.jsonl");
    const rows = fs.readFileSync(ledgerFile, "utf8").trim().split("\n").map((l) => JSON.parse(l));
    assert.equal(rows.length, 2);
    assert.equal(rows[0].status, "intent");
    assert.equal(rows[1].status, "settled");
    assert.equal(rows[1].signature, "FAKE_SIGNATURE");
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});

test("fundTenant: --live SKIPS the create-ata instruction when the tenant's NOS account already exists", async () => {
  const treasury = Keypair.generate();
  const tenantAddress = Keypair.generate().publicKey.toBase58();
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "tenant-fund-test2-"));
  const env = { ANICCA_SOLANA_PRIVATE_KEY: bs58.encode(treasury.secretKey), ANICCA_STATE_DIR: stateDir };
  const connectionFactory = () => makeFakeConnection({ lamports: 1_000_000_000, nosUiAmount: 5, ataExists: true });

  const addedInstructions = [];
  class FakeTransaction {
    add(ix) {
      addedInstructions.push(ix);
      return this;
    }
  }
  const fakeSplToken = {
    getAssociatedTokenAddressSync: () => new PublicKey("11111111111111111111111111111112"),
    createAssociatedTokenAccountInstruction: () => ({ kind: "create-ata" }),
    createTransferInstruction: () => ({ kind: "transfer" }),
  };

  try {
    await fundTenant({
      env,
      live: true,
      tenantAddress,
      connectionFactory,
      publicKeyCtor: PublicKey,
      keypairCtor: Keypair,
      splToken: fakeSplToken,
      systemProgramCtor: { transfer: (args) => ({ kind: "sol-transfer", ...args }) },
      transactionCtor: FakeTransaction,
      sendAndConfirmImpl: async () => "SIG",
    });
    assert.equal(addedInstructions.length, 2);
    assert.deepEqual(addedInstructions.map((i) => i.kind), ["sol-transfer", "transfer"]);
  } finally {
    fs.rmSync(stateDir, { recursive: true, force: true });
  }
});
