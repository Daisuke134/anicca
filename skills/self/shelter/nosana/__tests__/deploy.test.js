// node:test — deploy: the authoritative-reconciliation + payer-address-invariant fix for a real
// incident. A --live run's `nosana job post` crashed (Bug 1: the CLI calls a TTY-only spinner API
// that doesn't exist on piped stdout), and the fallback stdout-guess mechanism produced the PAYER
// WALLET address instead of the real job address, which got recorded straight into the settled-
// cost ledger (Bug 2). These tests prove: (a) the known-fragile stdout parse really would produce
// a wallet address from a realistic crash-shaped stdout — documenting why it can never be trusted
// alone; (b) the new payer-address invariant refuses that exact value regardless of source; (c)
// the new authoritative jobs-API reconciler correctly parses the REAL response shape captured live
// against the real incident's own job (2026-07-25) and fails closed (never throws, returns null)
// on any HTTP/shape problem — matching Bug 2's "job list returns non-JSON on success" discovery.
import { test } from "node:test";
import assert from "node:assert/strict";
import { parseJobAddressFromPostOutput, reconcileNosanaJobViaApi, validateJobAddressIsNotPayer, NOSANA_JOBS_API_BASE_URL } from "../deploy.mjs";

const PAYER_WALLET = "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T";
const REAL_JOB_ADDRESS = "FHAjMnM1q3p5c5qCeFRjZLYEo12FUBesFPW8zvG5heAC";
const REAL_MARKET = "7AtiXMSH6R1jjBxrcYjehCkkSF7zvYWte63gwEDBcGHq";

// ---- Bug 2's root cause, reproduced from the real observed CLI output shape ------------------

// This is the realistic shape of `nosana job post`'s stdout when its own post-post display step
// crashes (Bug 1) before ever printing the actual job's --format json payload: a leading RPC
// warning banner, then a wallet/balance summary object (the SAME shape `job list --format json`
// was verified live to print as its OWN trailing footer — see reconcileNosanaJob's doc comment in
// deploy.mjs), then the crash's stack trace. No valid job address ever gets printed, because
// printing it required the crashed step to succeed first.
const REALISTIC_CRASH_STDOUT = [
  "Using default solana RPC. Some commands might not work, please provide your own with the --rpc option",
  `{"keypair_path":"/Users/anicca/.blockrun/.automaton/nosana_key.json","network":"mainnet","wallet":"${PAYER_WALLET}","balances":{"SOL":"0.021838163 SOL","NOS":"2.707205 NOS"}}`,
  "TypeError: process.stdout.moveCursor is not a function",
  "    at clearLine (@nosana/cli/dist/src/generic/utils.js:44:20)",
  "    at getJob (@nosana/cli/dist/src/cli/job/get/action.js:30:9)",
  "    at async Command.run (@nosana/cli/dist/src/cli/job/post/action.js:241:5)",
].join("\n");

test("REGRESSION: parseJobAddressFromPostOutput really does extract the PAYER WALLET address from realistic crash-shaped stdout — this is exactly why it is never trusted alone", () => {
  const guessed = parseJobAddressFromPostOutput(REALISTIC_CRASH_STDOUT);
  assert.equal(guessed, PAYER_WALLET);
});

test("REGRESSION: even though the stdout guess yields the payer wallet, validateJobAddressIsNotPayer refuses it — the exact confusion that once corrupted the ledger is now structurally rejected", () => {
  const guessed = parseJobAddressFromPostOutput(REALISTIC_CRASH_STDOUT);
  const verdict = validateJobAddressIsNotPayer({ jobAddress: guessed, payerAddress: PAYER_WALLET });
  assert.equal(verdict.valid, false);
  assert.match(verdict.reason, /equals the payer wallet address/);
});

// ---- validateJobAddressIsNotPayer: the cheap, source-independent invariant --------------------

test("validateJobAddressIsNotPayer rejects when jobAddress equals payerAddress", () => {
  const v = validateJobAddressIsNotPayer({ jobAddress: PAYER_WALLET, payerAddress: PAYER_WALLET });
  assert.equal(v.valid, false);
});

test("validateJobAddressIsNotPayer accepts a jobAddress distinct from the payer", () => {
  const v = validateJobAddressIsNotPayer({ jobAddress: REAL_JOB_ADDRESS, payerAddress: PAYER_WALLET });
  assert.equal(v.valid, true);
});

test("validateJobAddressIsNotPayer fails closed on a missing jobAddress rather than treating it as acceptable", () => {
  assert.equal(validateJobAddressIsNotPayer({ jobAddress: null, payerAddress: PAYER_WALLET }).valid, false);
  assert.equal(validateJobAddressIsNotPayer({ jobAddress: "", payerAddress: PAYER_WALLET }).valid, false);
});

// ---- reconcileNosanaJobViaApi: the authoritative source, fully injected ------------------------

// Captured live 2026-07-25 against dashboard.k8s.prd.nos.ci/api/jobs?payer=<wallet> for the real
// incident's own job — verbatim shape (trimmed to the fields this function actually reads).
function makeRealApiResponse(overrides = {}) {
  return {
    jobs: [
      {
        id: 48185994,
        address: REAL_JOB_ADDRESS,
        market: REAL_MARKET,
        payer: PAYER_WALLET,
        project: PAYER_WALLET,
        state: 1,
        timeStart: 1784956456,
        timeEnd: 0,
        ...overrides,
      },
    ],
    totalJobs: 1,
  };
}

function fetchImplReturning(body, { ok = true, status = 200 } = {}) {
  return async () => ({ ok, status, json: async () => body });
}

test("reconcileNosanaJobViaApi parses the real response shape and returns the matching job", async () => {
  const result = await reconcileNosanaJobViaApi({
    fetchImpl: fetchImplReturning(makeRealApiResponse()),
    posterAddress: PAYER_WALLET,
  });
  assert.ok(result);
  assert.equal(result.address, REAL_JOB_ADDRESS);
  assert.equal(result.market, REAL_MARKET);
});

test("reconcileNosanaJobViaApi requests the documented payer-filtered endpoint", async () => {
  let requestedUrl = null;
  await reconcileNosanaJobViaApi({
    fetchImpl: async (url) => {
      requestedUrl = url;
      return { ok: true, status: 200, json: async () => makeRealApiResponse() };
    },
    posterAddress: PAYER_WALLET,
  });
  assert.equal(requestedUrl, `${NOSANA_JOBS_API_BASE_URL}?payer=${PAYER_WALLET}`);
});

test("reconcileNosanaJobViaApi picks the highest-timeStart job among several eligible ones", async () => {
  const body = {
    jobs: [
      { address: "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", market: REAL_MARKET, timeStart: 100 },
      { address: REAL_JOB_ADDRESS, market: REAL_MARKET, timeStart: 300 },
      { address: "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", market: REAL_MARKET, timeStart: 200 },
    ],
    totalJobs: 3,
  };
  const result = await reconcileNosanaJobViaApi({ fetchImpl: fetchImplReturning(body), posterAddress: PAYER_WALLET });
  assert.equal(result.address, REAL_JOB_ADDRESS);
});

test("reconcileNosanaJobViaApi filters out jobs from a different market when marketAddress is given", async () => {
  const result = await reconcileNosanaJobViaApi({
    fetchImpl: fetchImplReturning(makeRealApiResponse({ market: "SomeOtherMarketAddress11111111111111111111" })),
    posterAddress: PAYER_WALLET,
    marketAddress: REAL_MARKET,
  });
  assert.equal(result, null);
});

test("reconcileNosanaJobViaApi filters out jobs started before afterTs", async () => {
  const result = await reconcileNosanaJobViaApi({
    fetchImpl: fetchImplReturning(makeRealApiResponse({ timeStart: 100 })),
    posterAddress: PAYER_WALLET,
    afterTs: 200,
  });
  assert.equal(result, null);
});

test("reconcileNosanaJobViaApi returns null (never throws) on a non-ok HTTP response", async () => {
  const result = await reconcileNosanaJobViaApi({
    fetchImpl: fetchImplReturning({}, { ok: false, status: 500 }),
    posterAddress: PAYER_WALLET,
  });
  assert.equal(result, null);
});

test("reconcileNosanaJobViaApi returns null (never throws) when jobs is missing/empty", async () => {
  assert.equal(await reconcileNosanaJobViaApi({ fetchImpl: fetchImplReturning({ jobs: [] }), posterAddress: PAYER_WALLET }), null);
  assert.equal(await reconcileNosanaJobViaApi({ fetchImpl: fetchImplReturning({}), posterAddress: PAYER_WALLET }), null);
});

test("reconcileNosanaJobViaApi returns null (never throws) when fetchImpl itself throws", async () => {
  const result = await reconcileNosanaJobViaApi({
    fetchImpl: async () => {
      throw new Error("network down");
    },
    posterAddress: PAYER_WALLET,
  });
  assert.equal(result, null);
});

test("reconcileNosanaJobViaApi returns null (never throws) when res.json() rejects (malformed body)", async () => {
  const result = await reconcileNosanaJobViaApi({
    fetchImpl: async () => ({
      ok: true,
      status: 200,
      json: async () => {
        throw new Error("invalid json");
      },
    }),
    posterAddress: PAYER_WALLET,
  });
  assert.equal(result, null);
});

test("reconcileNosanaJobViaApi ignores a job entry with no address field rather than crashing", async () => {
  const result = await reconcileNosanaJobViaApi({
    fetchImpl: fetchImplReturning({ jobs: [{ market: REAL_MARKET, timeStart: 1 }], totalJobs: 1 }),
    posterAddress: PAYER_WALLET,
  });
  assert.equal(result, null);
});
