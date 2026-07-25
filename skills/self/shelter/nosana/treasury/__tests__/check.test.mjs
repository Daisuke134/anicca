// node:test — check.mjs: the full solvency-check orchestration. Every I/O dependency is injected
// (no real network, no real signing, no real state dir outside a throwaway temp dir) so these tests
// are deterministic. Mirrors renew/__tests__/executor.test.mjs's own fixture style
// (ANICCA_SOLANA_PRIVATE_KEY + ANICCA_STATE_DIR + a fake connectionFactory/publicKeyCtor).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import bs58 from "bs58";
import { Keypair } from "@solana/web3.js";

import { checkShelterSolvency } from "../check.mjs";
import { appendChild } from "../../../../spawn/lib/ledger.js";

const FIXED_NOS_USD_PRICE = 0.25;

function makeTestEnv() {
  const keypair = Keypair.generate();
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "citizen-solvency-test-"));
  return {
    address: keypair.publicKey.toBase58(),
    env: { ANICCA_SOLANA_PRIVATE_KEY: bs58.encode(keypair.secretKey), ANICCA_STATE_DIR: stateDir },
    stateDir,
    cleanup: () => fs.rmSync(stateDir, { recursive: true, force: true }),
  };
}

function makeConnectionFactory({ solBalanceLamports = 1_000_000_000, nosUiAmount = 5 }) {
  return () => ({
    getBalance: async () => solBalanceLamports,
    getParsedTokenAccountsByOwner: async () => ({
      value: [{ account: { data: { parsed: { info: { tokenAmount: { uiAmount: nosUiAmount } } } } } }],
    }),
  });
}

class FakePublicKey {
  constructor(v) {
    this.value = v;
  }
}

function fakeRenewShelterImpl(overrides = {}) {
  return async () => ({
    nosPerHour: 0.1728,
    runwayHours: 24,
    runway: { days: 1, hours: 0, totalHours: 24 },
    survivalSignal: { level: "warning", promoteEarning: true, reason: "test" },
    ...overrides,
  });
}

function callRecorder(result) {
  const calls = [];
  const fn = async (...args) => {
    calls.push(args);
    return typeof result === "function" ? result(...args) : result;
  };
  fn.calls = calls;
  return fn;
}

const baseDeps = () => ({
  connectionFactory: makeConnectionFactory({}),
  publicKeyCtor: FakePublicKey,
  fetchNosUsdPriceImpl: async () => FIXED_NOS_USD_PRICE,
  renewShelterImpl: fakeRenewShelterImpl(),
  now: () => 1_800_000_000_000, // fixed clock: 1_800_000_000 seconds
});

test("checkShelterSolvency: real seeded cost ledger + no revenue file -> honest $0 revenue, correct burn rate, no throw", async () => {
  const t = makeTestEnv();
  try {
    const costFile = path.join(t.stateDir, "shelter-cost.jsonl");
    appendChild(costFile, { ts: 1_800_000_000 - 3600, settledLeaseCostUsd: 0.012 });
    appendChild(costFile, { ts: 1_800_000_000 - 1800, settledLeaseCostUsd: 0.012 });

    const result = await checkShelterSolvency({ env: t.env, live: false, ...baseDeps() });

    assert.equal(result.address, t.address);
    assert.equal(result.ledger.totalExternalRevenueUsd, 0);
    assert.equal(result.solvencyReport.revenueIsZero, true);
    assert.equal(result.ledger.noRevenueData, true); // revenue file never created
    assert.equal(result.ledger.costEventCount, 2);
    assert.ok(result.ledger.burnUsdPerHour > 0);
    assert.equal(result.topupExecuted, false); // --dry never executes
  } finally {
    t.cleanup();
  }
});

test("checkShelterSolvency: a real correction row is honored — no double-count in the live orchestration path", async () => {
  const t = makeTestEnv();
  try {
    const costFile = path.join(t.stateDir, "shelter-cost.jsonl");
    appendChild(costFile, { ts: 1_800_000_000 - 3600, settledLeaseCostUsd: 0.01199, jobAddress: "WRONG_ADDR" });
    appendChild(costFile, { ts: 1_800_000_000 - 3599, correction: true, correctsTs: 1_800_000_000 - 3600, correctedField: "jobAddress", correctedJobAddress: "REAL_ADDR" });

    const result = await checkShelterSolvency({ env: t.env, live: false, ...baseDeps() });

    assert.equal(result.ledger.costEventCount, 1); // NOT 2 — the correction row is not a second spend
    assert.ok(Math.abs(result.ledger.totalCostUsd - 0.01199) < 1e-9);
    const costEvent = result.ledger.events.find((e) => e.type === "cost");
    assert.equal(costEvent.jobAddress, "REAL_ADDR");
  } finally {
    t.cleanup();
  }
});

test("checkShelterSolvency: revenue events are classified — self-pay excluded, external counted", async () => {
  const t = makeTestEnv();
  try {
    const costFile = path.join(t.stateDir, "shelter-cost.jsonl");
    appendChild(costFile, { ts: 1_800_000_000 - 3600, settledLeaseCostUsd: 0.01 });
    const revenueFile = path.join(t.stateDir, "shelter-revenue.jsonl");
    appendChild(revenueFile, { ts: 1_800_000_000 - 1800, amountUsd: 0.5, from: t.address, chain: "solana" }); // self-pay: own address
    appendChild(revenueFile, { ts: 1_800_000_000 - 900, amountUsd: 2.0, from: "0x000000000000000000000000000000deadbeef", chain: "base" });

    const result = await checkShelterSolvency({ env: t.env, live: false, ...baseDeps() });

    assert.equal(result.ledger.totalExternalRevenueUsd, 2.0);
    assert.equal(result.ledger.totalSelfPayUsd, 0.5);
    assert.equal(result.solvencyReport.revenueIsZero, false);
  } finally {
    t.cleanup();
  }
});

test("checkShelterSolvency: --live executes acquireNos only when the top-up decision allows it", async () => {
  const t = makeTestEnv();
  try {
    // Force a "critical" survival level: tiny nosBalance, real burn -> top-up recommended.
    const costFile = path.join(t.stateDir, "shelter-cost.jsonl");
    appendChild(costFile, { ts: 1_800_000_000 - 3600, settledLeaseCostUsd: 1 }); // huge burn -> critical
    const acquireNosCalls = callRecorder({ gate: { allowed: true }, posted: false });

    const result = await checkShelterSolvency({
      env: t.env,
      live: true,
      ...baseDeps(),
      connectionFactory: makeConnectionFactory({ solBalanceLamports: 5_000_000_000, nosUiAmount: 0.001 }),
      acquireNosImpl: acquireNosCalls,
    });

    assert.equal(result.topupDecision.allowed, true);
    assert.equal(result.topupExecuted, true);
    assert.equal(acquireNosCalls.calls.length, 1);
    assert.equal(acquireNosCalls.calls[0][0].live, true);
    assert.equal(acquireNosCalls.calls[0][0].requestedSol, result.topupDecision.recommendedSpendSol);
  } finally {
    t.cleanup();
  }
});

test("checkShelterSolvency: --live never calls acquireNos when the top-up decision does not recommend one", async () => {
  const t = makeTestEnv();
  try {
    // No cost data at all in this window -> noCostData -> survival level 'unknown' -> topup IS
    // recommended by decideShelterTopUp (unknown is a dangerous level)... so instead prove the
    // negative case with a healthy (nominal) runway: tiny burn, huge balance.
    const costFile = path.join(t.stateDir, "shelter-cost.jsonl");
    appendChild(costFile, { ts: 1_800_000_000 - 3600, settledLeaseCostUsd: 0.00001 }); // negligible burn
    const acquireNosCalls = callRecorder({ gate: { allowed: true }, posted: false });

    const result = await checkShelterSolvency({
      env: t.env,
      live: true,
      ...baseDeps(),
      connectionFactory: makeConnectionFactory({ solBalanceLamports: 5_000_000_000, nosUiAmount: 10_000 }),
      acquireNosImpl: acquireNosCalls,
    });

    assert.equal(result.solvencyReport.survivalSignal.level, "nominal");
    assert.equal(result.topupDecision.allowed, false);
    assert.equal(result.topupExecuted, false);
    assert.equal(acquireNosCalls.calls.length, 0);
  } finally {
    t.cleanup();
  }
});

test("checkShelterSolvency: fails closed (throws) when no Solana secret can be resolved", async () => {
  await assert.rejects(
    () => checkShelterSolvency({ env: { ANICCA_STATE_DIR: fs.mkdtempSync(path.join(os.tmpdir(), "no-secret-")) }, ...baseDeps() }),
    /no Solana secret resolved/,
  );
});

test("checkShelterSolvency: fails closed (throws, never a fabricated report) when the NOS/USD price fetch fails", async () => {
  const t = makeTestEnv();
  try {
    await assert.rejects(
      () =>
        checkShelterSolvency({
          env: t.env,
          ...baseDeps(),
          fetchNosUsdPriceImpl: async () => {
            throw new Error("fetchNosUsdPriceLive: could not obtain a valid NOS/USD price — refusing to treat as free");
          },
        }),
      /could not obtain a valid NOS\/USD price/,
    );
  } finally {
    t.cleanup();
  }
});

test("checkShelterSolvency: survival-drive cross-check failure is non-fatal to the rest of the report", async () => {
  const t = makeTestEnv();
  try {
    const costFile = path.join(t.stateDir, "shelter-cost.jsonl");
    appendChild(costFile, { ts: 1_800_000_000 - 3600, settledLeaseCostUsd: 0.01 });
    const result = await checkShelterSolvency({
      env: t.env,
      ...baseDeps(),
      renewShelterImpl: async () => {
        throw new Error("simulated jobs-API outage");
      },
    });
    assert.equal(result.survivalDriveComparison.error, "simulated jobs-API outage");
    assert.ok(result.solvencyReport); // the rest of the report still computed
  } finally {
    t.cleanup();
  }
});
