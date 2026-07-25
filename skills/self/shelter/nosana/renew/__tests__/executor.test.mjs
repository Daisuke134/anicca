// node:test — executor: the full renewal orchestration. Every I/O dependency is injected (no
// real network, no real filesystem outside a throwaway per-test state dir, no real signing) so
// these tests exercise the at-most-once / never-blind-retry / honest-death logic deterministically.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import bs58 from "bs58";
import { Keypair } from "@solana/web3.js";

import { renewShelter, findWindowRecord, reconcileExtendFromJobs, reconcileRepostFromJobs } from "../executor.mjs";
import { NOSANA_JOBS_API_BASE_URL, JOB_STATE_RUNNING, JOB_STATE_COMPLETED } from "../job-lookup.mjs";
import { MARKETS_PRICE_URL } from "../../market.mjs";

// ---- shared fixtures -----------------------------------------------------------------------

const MARKET = "7AtiXMSH6R1jjBxrcYjehCkkSF7zvYWte63gwEDBcGHq";

function makeTestEnv() {
  const keypair = Keypair.generate();
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "citizen-rent-test-"));
  return {
    address: keypair.publicKey.toBase58(),
    env: {
      ANICCA_SOLANA_PRIVATE_KEY: bs58.encode(keypair.secretKey),
      ANICCA_STATE_DIR: stateDir,
    },
    stateDir,
    cleanup: () => fs.rmSync(stateDir, { recursive: true, force: true }),
  };
}

function makeRunningJob({ address, timeStart, timeout = 900, price = 48 }) {
  return { id: 1, address, market: MARKET, price, state: JOB_STATE_RUNNING, timeStart, timeout, usdRewardPerHour: 0.0437 };
}

function makeCompletedJob({ address, timeStart, timeout = 900, price = 48 }) {
  return { id: 1, address, market: MARKET, price, state: JOB_STATE_COMPLETED, timeStart, timeout, usdRewardPerHour: 0.0437 };
}

/** A fetchImpl that answers the jobs API from a mutable `jobsBox.jobs` array (so a test can
 * mutate it mid-run, e.g. from inside a sendSignedExtend fake, to simulate "the tx actually landed
 * on-chain even though the client-side confirmation failed") and the markets-price API from a
 * fixed list (only reached on the no-active-job/repost branch). */
function makeFetchImpl(jobsBox) {
  return async (url) => {
    if (url.startsWith(NOSANA_JOBS_API_BASE_URL)) {
      return { ok: true, status: 200, json: async () => ({ jobs: jobsBox.jobs, totalJobs: jobsBox.jobs.length }) };
    }
    if (url.startsWith(MARKETS_PRICE_URL)) {
      return {
        ok: true,
        status: 200,
        json: async () => [{ address: MARKET, name: "NVIDIA RTX3060", usd_reward_per_hour: 0.04796 }],
      };
    }
    throw new Error(`unexpected fetchImpl url in test: ${url}`);
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

function callCounter() {
  const calls = [];
  const fn = async (...args) => {
    calls.push(args);
    return fn.__result ? fn.__result(...args) : undefined;
  };
  fn.calls = calls;
  return fn;
}

// ---- pure helper tests ----------------------------------------------------------------------

test("findWindowRecord: no rows for the window => 'none'", () => {
  assert.equal(findWindowRecord([], "W1").state, "none");
  assert.equal(findWindowRecord([{ windowId: "OTHER", status: "settled" }], "W1").state, "none");
});

test("findWindowRecord: a settled/posted row => 'done'", () => {
  assert.equal(findWindowRecord([{ windowId: "W1", status: "settled" }], "W1").state, "done");
  assert.equal(findWindowRecord([{ windowId: "W1", status: "posted" }], "W1").state, "done");
});

test("findWindowRecord: an unresolved intent row => 'pending-reconciliation'", () => {
  assert.equal(findWindowRecord([{ windowId: "W1", status: "intent" }], "W1").state, "pending-reconciliation");
});

test("findWindowRecord: only refused/failed rows (nothing was ever spent) => 'none', free to retry", () => {
  const rows = [
    { windowId: "W1", status: "refused" },
    { windowId: "W1", status: "failed-onchain" },
  ];
  assert.equal(findWindowRecord(rows, "W1").state, "none");
});

test("reconcileExtendFromJobs: settled once the real timeout reflects the extension", () => {
  const jobs = [{ address: "J1", timeout: 1800 }];
  const r = reconcileExtendFromJobs(jobs, { jobAddress: "J1", minTimeout: 1800 });
  assert.equal(r.outcome, "settled");
});

test("reconcileExtendFromJobs: unknown when the real timeout has not moved — never treats it as settled", () => {
  const jobs = [{ address: "J1", timeout: 900 }];
  const r = reconcileExtendFromJobs(jobs, { jobAddress: "J1", minTimeout: 1800 });
  assert.equal(r.outcome, "unknown");
});

test("reconcileExtendFromJobs: unknown when the job is missing entirely from the fresh read", () => {
  const r = reconcileExtendFromJobs([], { jobAddress: "J1", minTimeout: 1800 });
  assert.equal(r.outcome, "unknown");
});

test("reconcileRepostFromJobs: settled when an alive job started at/after the attempt", () => {
  const jobs = [makeRunningJob({ address: "NEW", timeStart: 1000 })];
  const r = reconcileRepostFromJobs(jobs, { attemptTs: 995, nowTs: 1100 });
  assert.equal(r.outcome, "settled");
  assert.equal(r.jobAddress, "NEW");
});

test("reconcileRepostFromJobs: unknown when nothing alive started after the attempt", () => {
  const jobs = [makeCompletedJob({ address: "OLD", timeStart: 100 })];
  const r = reconcileRepostFromJobs(jobs, { attemptTs: 995, nowTs: 1100 });
  assert.equal(r.outcome, "unknown");
});

// ---- renewShelter: not due yet ---------------------------------------------------------------

test("renewShelter: far from expiry is not due, and never touches the on-chain seams", async () => {
  const { env, address, cleanup } = makeTestEnv();
  try {
    const job = makeRunningJob({ address: "JOBALIVE", timeStart: 1_000_000 });
    const jobsBox = { jobs: [job] };
    const buildAndSignExtend = callCounter();
    const nowTs = job.timeStart + 100; // 900s timeout, 800s remaining — way outside the 180s lead.
    const result = await renewShelter({
      env,
      live: true,
      now: () => nowTs * 1000,
      fetchImpl: makeFetchImpl(jobsBox),
      connectionFactory: makeConnectionFactory({}),
      publicKeyCtor: FakePublicKey,
      fetchNosUsdPriceImpl: async () => 0.254,
      buildAndSignExtend,
    });
    assert.equal(result.decision, "not-due");
    assert.equal(result.address, address);
    assert.equal(buildAndSignExtend.calls.length, 0);
    assert.ok(result.survivalSignal, "survival signal is always computed, even when not due");
    assert.equal(result.rentClock.dueForRenewal, false);
  } finally {
    cleanup();
  }
});

// ---- renewShelter: due, dry mode ---------------------------------------------------------------

test("renewShelter: due + dry + gate allowed => 'would-extend', and touches NO ledger file", async () => {
  const { env, cleanup, stateDir } = makeTestEnv();
  try {
    const job = makeRunningJob({ address: "JOBALIVE", timeStart: 1_000_000 });
    const jobsBox = { jobs: [job] };
    const nowTs = job.timeStart + 900 - 60; // 60s left, inside the default 180s lead.
    const result = await renewShelter({
      env,
      live: false,
      now: () => nowTs * 1000,
      fetchImpl: makeFetchImpl(jobsBox),
      connectionFactory: makeConnectionFactory({ nosUiAmount: 5 }),
      publicKeyCtor: FakePublicKey,
      fetchNosUsdPriceImpl: async () => 0.254,
    });
    assert.equal(result.decision, "would-extend");
    assert.equal(result.posted, false);
    assert.equal(fs.existsSync(path.join(stateDir, "nosana-renewal-intents.jsonl")), false);
  } finally {
    cleanup();
  }
});

test("renewShelter: due + dry + insufficient NOS => 'refused' (honest, not a silent skip)", async () => {
  const { env, cleanup } = makeTestEnv();
  try {
    const job = makeRunningJob({ address: "JOBALIVE", timeStart: 1_000_000 });
    const jobsBox = { jobs: [job] };
    const nowTs = job.timeStart + 900 - 60;
    const result = await renewShelter({
      env,
      live: false,
      now: () => nowTs * 1000,
      fetchImpl: makeFetchImpl(jobsBox),
      connectionFactory: makeConnectionFactory({ nosUiAmount: 0 }),
      publicKeyCtor: FakePublicKey,
      fetchNosUsdPriceImpl: async () => 0.254,
    });
    assert.equal(result.decision, "refused");
    assert.match(result.gate.reason, /insufficient NOS balance/);
    assert.equal(result.survivalSignal.level, "insolvent");
    assert.equal(result.survivalSignal.promoteEarning, true);
  } finally {
    cleanup();
  }
});

// ---- renewShelter: due, live, extend succeeds --------------------------------------------------

test("renewShelter: due + live + send succeeds => 'extended', records intent+settled+shelter-cost", async () => {
  const { env, cleanup, stateDir } = makeTestEnv();
  try {
    const job = makeRunningJob({ address: "JOBALIVE", timeStart: 1_000_000 });
    const jobsBox = { jobs: [job] };
    const nowTs = job.timeStart + 900 - 60;
    const buildAndSignExtend = callCounter();
    buildAndSignExtend.__result = async () => ({ signature: "SIG1", sendable: { ok: true } });
    const sendSignedExtend = callCounter();
    sendSignedExtend.__result = async () => {};

    const result = await renewShelter({
      env,
      live: true,
      now: () => nowTs * 1000,
      fetchImpl: makeFetchImpl(jobsBox),
      connectionFactory: makeConnectionFactory({ nosUiAmount: 5 }),
      publicKeyCtor: FakePublicKey,
      fetchNosUsdPriceImpl: async () => 0.254,
      buildAndSignExtend,
      sendSignedExtend,
    });

    assert.equal(result.decision, "extended");
    assert.equal(result.posted, true);
    assert.equal(result.signature, "SIG1");
    assert.equal(buildAndSignExtend.calls.length, 1);
    assert.equal(sendSignedExtend.calls.length, 1);

    const intentRows = fs
      .readFileSync(path.join(stateDir, "nosana-renewal-intents.jsonl"), "utf8")
      .trim()
      .split("\n")
      .map((l) => JSON.parse(l));
    assert.equal(intentRows.length, 2);
    assert.equal(intentRows[0].status, "intent");
    assert.equal(intentRows[1].status, "settled");
    assert.equal(intentRows[0].windowId, intentRows[1].windowId);

    const costRows = fs
      .readFileSync(path.join(stateDir, "shelter-cost.jsonl"), "utf8")
      .trim()
      .split("\n")
      .map((l) => JSON.parse(l));
    assert.equal(costRows.length, 1);
    assert.equal(costRows[0].jobAddress, "JOBALIVE");
  } finally {
    cleanup();
  }
});

// ---- renewShelter: unknown-outcome RECONCILES rather than retries -----------------------------

test("renewShelter: send throws but real state confirms it landed => reconciles SETTLED, never re-signs/re-sends", async () => {
  const { env, cleanup } = makeTestEnv();
  try {
    const job = makeRunningJob({ address: "JOBALIVE", timeStart: 1_000_000 });
    const jobsBox = { jobs: [job] };
    const nowTs = job.timeStart + 900 - 60;
    const buildAndSignExtend = callCounter();
    buildAndSignExtend.__result = async () => ({ signature: "SIG2", sendable: {} });
    const sendSignedExtend = callCounter();
    // Simulate: the transaction actually confirmed on-chain, but OUR client-side wait threw
    // (e.g. an RPC hiccup right after broadcast) — mutate the "real" job state the SAME way a
    // real confirmed extend would, then throw, exactly like acquire-nos.mjs's own documented
    // "sendRawTransaction threw — outcome unknown, proceeding to reconcile" scenario.
    sendSignedExtend.__result = async () => {
      jobsBox.jobs = [{ ...job, timeout: job.timeout + 900 }];
      throw new Error("simulated confirmation timeout");
    };

    const result = await renewShelter({
      env,
      live: true,
      now: () => nowTs * 1000,
      fetchImpl: makeFetchImpl(jobsBox),
      connectionFactory: makeConnectionFactory({ nosUiAmount: 5 }),
      publicKeyCtor: FakePublicKey,
      fetchNosUsdPriceImpl: async () => 0.254,
      buildAndSignExtend,
      sendSignedExtend,
    });

    assert.equal(result.decision, "extended");
    assert.equal(result.posted, true);
    assert.equal(result.reconciliation.outcome, "settled");
    // The critical assertion: reconciliation must NEVER cause a second build/sign/send attempt.
    assert.equal(buildAndSignExtend.calls.length, 1);
    assert.equal(sendSignedExtend.calls.length, 1);
  } finally {
    cleanup();
  }
});

test("renewShelter: send throws and real state still shows the OLD timeout => throws UNKNOWN, never retries", async () => {
  const { env, cleanup } = makeTestEnv();
  try {
    const job = makeRunningJob({ address: "JOBALIVE", timeStart: 1_000_000 });
    const jobsBox = { jobs: [job] }; // left unchanged — the extend truly did not land.
    const nowTs = job.timeStart + 900 - 60;
    const buildAndSignExtend = callCounter();
    buildAndSignExtend.__result = async () => ({ signature: "SIG3", sendable: {} });
    const sendSignedExtend = callCounter();
    sendSignedExtend.__result = async () => {
      throw new Error("simulated hard send failure");
    };

    await assert.rejects(
      () =>
        renewShelter({
          env,
          live: true,
          now: () => nowTs * 1000,
          fetchImpl: makeFetchImpl(jobsBox),
          connectionFactory: makeConnectionFactory({ nosUiAmount: 5 }),
          publicKeyCtor: FakePublicKey,
          fetchNosUsdPriceImpl: async () => 0.254,
          buildAndSignExtend,
          sendSignedExtend,
        }),
      /UNKNOWN after reconciliation/,
    );
    assert.equal(buildAndSignExtend.calls.length, 1);
    assert.equal(sendSignedExtend.calls.length, 1);
  } finally {
    cleanup();
  }
});

// ---- renewShelter: ONE window can NEVER produce TWO payments ----------------------------------

test("renewShelter: a second invocation for the SAME window (stale/lagging real state) refuses — cannot pay twice", async () => {
  const { env, cleanup } = makeTestEnv();
  try {
    const job = makeRunningJob({ address: "JOBALIVE", timeStart: 1_000_000 });
    // jobsBox is deliberately left STALE (still the pre-extension timeout) across both calls —
    // this is the exact indexer-lag scenario the intent ledger (not the API) must catch.
    const jobsBox = { jobs: [job] };
    const nowTs = job.timeStart + 900 - 60;
    const buildAndSignExtend = callCounter();
    buildAndSignExtend.__result = async () => ({ signature: "SIG4", sendable: {} });
    const sendSignedExtend = callCounter();
    sendSignedExtend.__result = async () => {};

    const commonArgs = {
      env,
      live: true,
      now: () => nowTs * 1000,
      fetchImpl: makeFetchImpl(jobsBox),
      connectionFactory: makeConnectionFactory({ nosUiAmount: 5 }),
      publicKeyCtor: FakePublicKey,
      fetchNosUsdPriceImpl: async () => 0.254,
      buildAndSignExtend,
      sendSignedExtend,
    };

    const first = await renewShelter(commonArgs);
    assert.equal(first.decision, "extended");

    const second = await renewShelter(commonArgs);
    assert.equal(second.decision, "already-done");
    assert.equal(second.posted, false);

    // The whole point: across BOTH invocations, exactly one build+sign and one send ever happened.
    assert.equal(buildAndSignExtend.calls.length, 1);
    assert.equal(sendSignedExtend.calls.length, 1);
  } finally {
    cleanup();
  }
});

// ---- renewShelter: repost fallback (no alive job) ----------------------------------------------

test("renewShelter: no alive job => delegates to deployNosanaJobImpl (repost), dry relays its gate", async () => {
  const { env, cleanup } = makeTestEnv();
  try {
    const deadJob = makeCompletedJob({ address: "OLDJOB", timeStart: 1_000_000 });
    const jobsBox = { jobs: [deadJob] };
    const nowTs = deadJob.timeStart + 100000; // long dead
    const deployNosanaJobImpl = callCounter();
    deployNosanaJobImpl.__result = async () => ({ posted: false, gate: { allowed: false, reason: "simulated refusal" } });

    const result = await renewShelter({
      env,
      live: false,
      now: () => nowTs * 1000,
      fetchImpl: makeFetchImpl(jobsBox),
      connectionFactory: makeConnectionFactory({ nosUiAmount: 5 }),
      publicKeyCtor: FakePublicKey,
      fetchNosUsdPriceImpl: async () => 0.254,
      deployNosanaJobImpl,
    });

    assert.equal(result.action, "repost");
    assert.equal(result.decision, "refused");
    assert.equal(deployNosanaJobImpl.calls.length, 1);
  } finally {
    cleanup();
  }
});

test("renewShelter: repost live success records settled, and a stale-state repeat call cannot repost twice", async () => {
  const { env, cleanup, stateDir } = makeTestEnv();
  try {
    const deadJob = makeCompletedJob({ address: "OLDJOB", timeStart: 1_000_000 });
    const jobsBox = { jobs: [deadJob] }; // deliberately never updated — simulates indexer lag.
    const nowTs = deadJob.timeStart + 100000;
    const deployNosanaJobImpl = callCounter();
    deployNosanaJobImpl.__result = async () => ({ posted: true, jobAddress: "NEWJOB1", gate: { allowed: true, reason: "ok" } });

    const commonArgs = {
      env,
      live: true,
      now: () => nowTs * 1000,
      fetchImpl: makeFetchImpl(jobsBox),
      connectionFactory: makeConnectionFactory({ nosUiAmount: 5 }),
      publicKeyCtor: FakePublicKey,
      fetchNosUsdPriceImpl: async () => 0.254,
      deployNosanaJobImpl,
    };

    const first = await renewShelter(commonArgs);
    assert.equal(first.decision, "reposted");
    assert.equal(first.jobAddress, "NEWJOB1");

    const second = await renewShelter(commonArgs);
    assert.equal(second.decision, "already-done");

    assert.equal(deployNosanaJobImpl.calls.length, 1, "deployNosanaJob must never be invoked twice for the same window");

    const intentRows = fs
      .readFileSync(path.join(stateDir, "nosana-renewal-intents.jsonl"), "utf8")
      .trim()
      .split("\n")
      .map((l) => JSON.parse(l));
    const statuses = intentRows.map((r) => r.status);
    assert.deepEqual(statuses, ["intent", "settled"]);
  } finally {
    cleanup();
  }
});
