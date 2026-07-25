// node:test — entrypoint.mjs: the full in-job flow (identify, restore, prove, report), exercised
// end-to-end with every I/O boundary faked — no real network, no real Solana RPC, no real Nosana
// jobs API, no real Jupiter/markets API. This is the hermetic equivalent of what a real Nosana
// container would run; __tests__/proof.test.mjs separately proves the underlying crypto is real,
// not mocked away, and this repo's own real dry runs (see the implementation report) exercise the
// REAL bundled artifact against REAL public endpoints.
import { test } from "node:test";
import assert from "node:assert/strict";
import { Keypair, PublicKey } from "@solana/web3.js";

import { runTenantIncarnation } from "../entrypoint.mjs";
import { verifyChallengeSignature } from "../proof.mjs";
import { NOSANA_JOBS_API_BASE_URL } from "../public-job-state.mjs";
import { MARKETS_PRICE_URL } from "../../market.mjs";

const TREASURY_ADDRESS = "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T";

// Standard fetch(url)-shaped fake, for the jobs API + markets-price API (both real GET-a-url
// endpoints). Deliberately does NOT also serve the NOS/USD price call — see
// makeNosUsdPriceFetchImpl below for why that is a SEPARATE, differently-shaped fake (a real bug
// this project found live: conflating the two conventions silently breaks production — see
// entrypoint.mjs's resolveNosPerHour doc comment).
function makeFetchImpl({ jobs = [], markets = null } = {}) {
  return async (url) => {
    if (url.startsWith(NOSANA_JOBS_API_BASE_URL)) {
      return { ok: true, status: 200, json: async () => ({ jobs, totalJobs: jobs.length }) };
    }
    if (url === MARKETS_PRICE_URL) {
      if (markets === null) {
        throw new Error(`unexpected markets fetch in a test that didn't configure any: ${url}`);
      }
      return { ok: true, status: 200, json: async () => markets };
    }
    throw new Error(`makeFetchImpl: unexpected URL ${url}`);
  };
}

// ../market.mjs's fetchNosUsdPriceLive (via ../../spawn/lib/cloud-target.mjs) calls its fetchImpl
// with ZERO arguments and expects `{json: async () => ({price})}` directly — a different contract
// than the standard `fetch(url)` above. entrypoint.mjs's `nosUsdPriceFetchImpl` param exists
// specifically so a test can supply this distinctly-shaped fake without it ever being confused
// with the standard one.
function makeNosUsdPriceFetchImpl(price) {
  return async () => ({ ok: true, status: 200, json: async () => ({ price }) });
}

function makeConnection({ lamports = 0, nosUiAmount = 0, blockhash = "FakeBlockhash111" } = {}) {
  return {
    async getBalance() {
      return lamports;
    },
    async getParsedTokenAccountsByOwner() {
      if (nosUiAmount == null) return { value: [] };
      return { value: [{ account: { data: { parsed: { info: { tokenAmount: { uiAmount: nosUiAmount } } } } } }] };
    },
    async getLatestBlockhash() {
      return { blockhash };
    },
  };
}

test("runTenantIncarnation: fails closed when NOSANA_TREASURY_ADDRESS is missing", async () => {
  await assert.rejects(
    () => runTenantIncarnation({ env: {}, fetchImpl: makeFetchImpl({}), connectionFactory: () => makeConnection({}) }),
    /NOSANA_TREASURY_ADDRESS is not set/,
  );
});

test("runTenantIncarnation: active job present — uses the active job's own price, never touches the market fallback (and never even needs nosUsdPriceFetchImpl)", async () => {
  const env = { NOSANA_TREASURY_ADDRESS: TREASURY_ADDRESS };
  const activeJob = { address: "JOB_ACTIVE", state: 1, timeStart: 1000, timeout: 900, price: 47 };
  const fetchImpl = makeFetchImpl({ jobs: [activeJob] }); // markets: null -> throws if ever touched
  const connectionFactory = () => makeConnection({ lamports: 26066471, nosUiAmount: 2.495705 });

  const report = await runTenantIncarnation({ env, fetchImpl, connectionFactory, now: () => 1500 * 1000 });

  assert.equal(report.activeJobAddress, "JOB_ACTIVE");
  assert.equal(report.rateSource, "active-job:JOB_ACTIVE");
  assert.ok(Math.abs(report.nosPerHour - 0.1692) < 1e-9);
  assert.ok(report.runwayHours > 0);
});

test("runTenantIncarnation: no alive job — falls back to the live cheapest-market estimate, matching ../renew/executor.mjs's own fallback branch", async () => {
  const env = { NOSANA_TREASURY_ADDRESS: TREASURY_ADDRESS };
  const deadJob = { address: "JOB_DEAD", state: 2, timeStart: 100, timeout: 50, price: 47 };
  const markets = [{ address: "MKT1", name: "NVIDIA 3060", usd_reward_per_hour: 0.04796 }];
  const fetchImpl = makeFetchImpl({ jobs: [deadJob], markets });
  const nosUsdPriceFetchImpl = makeNosUsdPriceFetchImpl(0.25383035377762303);
  const connectionFactory = () => makeConnection({ lamports: 26066471, nosUiAmount: 2.495705 });

  const report = await runTenantIncarnation({ env, fetchImpl, nosUsdPriceFetchImpl, connectionFactory, now: () => 1000000 * 1000 });

  assert.equal(report.activeJobAddress, null);
  assert.equal(report.mostRecentJobAddress, "JOB_DEAD");
  assert.match(report.rateSource, /^market-fallback:MKT1/);
  assert.ok(report.nosPerHour > 0);
  assert.ok(report.runwayHours > 0);
});

test("runTenantIncarnation: no job history AND no eligible market — reports rate/runway as null, never fabricates one (never even needs nosUsdPriceFetchImpl)", async () => {
  const env = { NOSANA_TREASURY_ADDRESS: TREASURY_ADDRESS };
  const fetchImpl = makeFetchImpl({ jobs: [], markets: [] }); // no markets at all -> selectCheapestMarket returns null
  const connectionFactory = () => makeConnection({ lamports: 0, nosUiAmount: 0 });

  const report = await runTenantIncarnation({ env, fetchImpl, connectionFactory, now: () => 1000000 * 1000 });

  assert.equal(report.nosPerHour, null);
  assert.equal(report.runwayHours, null);
  assert.match(report.rateSource, /unavailable/);
});

test("runTenantIncarnation: generates a fresh ephemeral identity every call — never the same address twice, never persisted", async () => {
  const env = { NOSANA_TREASURY_ADDRESS: TREASURY_ADDRESS };
  const fetchImpl = makeFetchImpl({ jobs: [], markets: [] });
  const connectionFactory = () => makeConnection({});

  const first = await runTenantIncarnation({ env, fetchImpl, connectionFactory, now: () => 1 });
  const second = await runTenantIncarnation({ env, fetchImpl, connectionFactory, now: () => 2 });
  assert.notEqual(first.ephemeralAddress, second.ephemeralAddress);
});

test("runTenantIncarnation: the reported signature REALLY verifies against the reported ephemeral public key over the reported message", async () => {
  const env = { NOSANA_TREASURY_ADDRESS: TREASURY_ADDRESS };
  const activeJob = { address: "JOB1", state: 1, timeStart: 1000, timeout: 900, price: 47 };
  const fetchImpl = makeFetchImpl({ jobs: [activeJob] });
  const connectionFactory = () => makeConnection({ lamports: 26066471, nosUiAmount: 2.495705, blockhash: "RealisticBlockhash123" });

  const report = await runTenantIncarnation({ env, fetchImpl, connectionFactory, now: () => 1500 * 1000 });

  const bs58 = (await import("bs58")).default;
  const signatureBytes = bs58.decode(report.signature);
  const publicKeyBytes = bs58.decode(report.ephemeralAddress);
  const verified = await verifyChallengeSignature({ message: report.message, signatureBytes, publicKeyBytes });
  assert.equal(verified, true);
  assert.ok(report.message.includes("RealisticBlockhash123"));
  assert.ok(report.message.includes(String(report.treasurySolLamports)));
});

test("runTenantIncarnation: a failed NOS balance read is honestly reported as 0, never fabricated, and does not crash the run", async () => {
  const env = { NOSANA_TREASURY_ADDRESS: TREASURY_ADDRESS };
  const activeJob = { address: "JOB1", state: 1, timeStart: 1000, timeout: 900, price: 47 };
  const fetchImpl = makeFetchImpl({ jobs: [activeJob] });
  const connectionFactory = () => ({
    async getBalance() { return 500; },
    async getParsedTokenAccountsByOwner() { throw new Error("simulated RPC hiccup"); },
    async getLatestBlockhash() { return { blockhash: "BH" }; },
  });

  const report = await runTenantIncarnation({ env, fetchImpl, connectionFactory, now: () => 1500 * 1000 });
  assert.equal(report.treasuryNosBalance, 0);
  assert.equal(report.treasurySolLamports, 500);
});

test("runTenantIncarnation: the ephemeral identity is a genuine, valid Solana address (round-trips through PublicKey)", async () => {
  const env = { NOSANA_TREASURY_ADDRESS: TREASURY_ADDRESS };
  const fetchImpl = makeFetchImpl({ jobs: [], markets: [] });
  const connectionFactory = () => makeConnection({});
  const report = await runTenantIncarnation({ env, fetchImpl, connectionFactory, now: () => 1 });
  assert.doesNotThrow(() => new PublicKey(report.ephemeralAddress));
  assert.notEqual(report.ephemeralAddress, TREASURY_ADDRESS);
});

test("runTenantIncarnation: honors an injected keypairCtor (for deterministic orchestration tests)", async () => {
  const fixedKp = Keypair.generate();
  const env = { NOSANA_TREASURY_ADDRESS: TREASURY_ADDRESS };
  const fetchImpl = makeFetchImpl({ jobs: [], markets: [] });
  const connectionFactory = () => makeConnection({});
  const report = await runTenantIncarnation({
    env,
    fetchImpl,
    connectionFactory,
    now: () => 1,
    keypairCtor: { generate: () => fixedKp },
  });
  assert.equal(report.ephemeralAddress, fixedKp.publicKey.toBase58());
});
