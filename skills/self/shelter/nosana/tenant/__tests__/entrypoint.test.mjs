// node:test — entrypoint.mjs: the full in-job five-step flow (identify, restore, prove, snapshot,
// report), exercised end-to-end with every I/O boundary faked — no real network, no real Solana
// RPC, no real GitHub API. This is the hermetic equivalent of what a real Nosana container would
// run; __tests__/proof.test.mjs separately proves the underlying crypto is real, not mocked away.
import { test } from "node:test";
import assert from "node:assert/strict";
import bs58 from "bs58";
import { Keypair } from "@solana/web3.js";

import { runTenantIncarnation } from "../entrypoint.mjs";
import { TENANT_RUNS_REMOTE_KEY } from "../report-ledger.mjs";
import { verifyChallengeSignature } from "../proof.mjs";

/** A tiny fake GitHub Contents API, same shape as github-contents-store.test.mjs's, inlined here
 * so this test file exercises entrypoint.mjs's actual fetchImpl wiring end-to-end. */
function makeFakeGithubFetch(initialFiles = {}) {
  const files = new Map(Object.entries(initialFiles).map(([k, v]) => [k, { text: v, sha: "sha-0" }]));
  let shaCounter = 0;
  return async function fetchImpl(url, options = {}) {
    const match = url.match(/\/repos\/([^/]+)\/([^/]+)\/contents\/(.+?)(?:\?ref=.*)?$/);
    const key = decodeURIComponent(match[3]);
    if (!options.method || options.method === "GET") {
      const entry = files.get(key);
      if (!entry) return { ok: false, status: 404, json: async () => ({}) };
      return { ok: true, status: 200, json: async () => ({ content: Buffer.from(entry.text, "utf8").toString("base64"), sha: entry.sha }) };
    }
    if (options.method === "PUT") {
      const body = JSON.parse(options.body);
      shaCounter += 1;
      files.set(key, { text: Buffer.from(body.content, "base64").toString("utf8"), sha: `sha-${shaCounter}` });
      return { ok: true, status: 200, json: async () => ({}) };
    }
    throw new Error("unexpected method");
  };
}

function makeFakeConnection({ lamports = 0, nosUiAmount = 0, blockhash = "FakeBlockhash111" } = {}) {
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

test("runTenantIncarnation: first-ever incarnation — no prior state, reports priorRunCount 0 and runNumber 1", async () => {
  const tenantKp = Keypair.generate();
  const env = { NOSANA_TENANT_SECRET_KEY: bs58.encode(tenantKp.secretKey), NOSANA_STATE_GITHUB_TOKEN: "fake-token" };
  const fetchImpl = makeFakeGithubFetch();
  const connectionFactory = () => makeFakeConnection({ lamports: 0, nosUiAmount: 0 });

  const report = await runTenantIncarnation({ env, fetchImpl, connectionFactory, now: () => 1_000_000 });

  assert.equal(report.priorRunCount, 0);
  assert.equal(report.lastRun, null);
  assert.equal(report.runNumber, 1);
  assert.equal(report.tenantAddress, tenantKp.publicKey.toBase58());
  assert.equal(report.solLamports, 0);
  assert.equal(report.nosBalance, 0);
  assert.equal(report.x402Attempted, false);
  assert.match(report.x402Reason, /not attempted/);
});

test("runTenantIncarnation: produces a signature that REALLY verifies against the tenant's own public key over the reported message", async () => {
  const tenantKp = Keypair.generate();
  const env = { NOSANA_TENANT_SECRET_KEY: bs58.encode(tenantKp.secretKey), NOSANA_STATE_GITHUB_TOKEN: "fake-token" };
  const fetchImpl = makeFakeGithubFetch();
  const connectionFactory = () => makeFakeConnection({ lamports: 23_505_190, nosUiAmount: 2.495705, blockhash: "RealisticBlockhash123" });

  const report = await runTenantIncarnation({ env, fetchImpl, connectionFactory, now: () => 2_000_000 });

  const signatureBytes = bs58.decode(report.signature);
  const verified = await verifyChallengeSignature({
    message: report.message,
    signatureBytes,
    publicKeyBytes: tenantKp.publicKey.toBytes(),
  });
  assert.equal(verified, true);
  assert.ok(report.message.includes("RealisticBlockhash123"));
  assert.ok(report.message.includes("23505190"));
});

test("runTenantIncarnation: second incarnation restores the first's history — priorRunCount 1, runNumber 2, lastRun populated", async () => {
  const tenantKp = Keypair.generate();
  const env = { NOSANA_TENANT_SECRET_KEY: bs58.encode(tenantKp.secretKey), NOSANA_STATE_GITHUB_TOKEN: "fake-token" };
  const fetchImpl = makeFakeGithubFetch();
  const connectionFactory = () => makeFakeConnection({ lamports: 1000, nosUiAmount: 0.1 });

  const first = await runTenantIncarnation({ env, fetchImpl, connectionFactory, now: () => 1_000_000 });
  assert.equal(first.runNumber, 1);

  const second = await runTenantIncarnation({ env, fetchImpl, connectionFactory, now: () => 2_000_000 });
  assert.equal(second.priorRunCount, 1);
  assert.equal(second.runNumber, 2);
  assert.equal(second.lastRun.runNumber, 1);
  assert.equal(second.lastRun.ts, 1000, "restored previous run's own timestamp (1_000_000ms/1000)");
});

test("runTenantIncarnation: snapshots the new run back to TENANT_RUNS_REMOTE_KEY before returning", async () => {
  const tenantKp = Keypair.generate();
  const env = { NOSANA_TENANT_SECRET_KEY: bs58.encode(tenantKp.secretKey), NOSANA_STATE_GITHUB_TOKEN: "fake-token" };
  const files = {};
  const fetchImpl = makeFakeGithubFetch(files);
  const connectionFactory = () => makeFakeConnection({});

  await runTenantIncarnation({ env, fetchImpl, connectionFactory, now: () => 1_000_000 });

  // Read back via a second, independent fetchImpl-driven getText to confirm it really persisted
  // (not just returned in-memory) — reuse the same fake store's GET path.
  const readBack = await fetchImpl(`https://api.github.com/repos/Daisuke134/franklin-shelter-state/contents/${TENANT_RUNS_REMOTE_KEY}?ref=main`, {});
  assert.equal(readBack.ok, true);
  const data = await readBack.json();
  const text = Buffer.from(data.content, "base64").toString("utf8");
  assert.ok(text.includes(tenantKp.publicKey.toBase58()));
});

test("runTenantIncarnation: fails closed when NOSANA_TENANT_SECRET_KEY is missing", async () => {
  await assert.rejects(
    () => runTenantIncarnation({ env: { NOSANA_STATE_GITHUB_TOKEN: "t" }, fetchImpl: makeFakeGithubFetch(), connectionFactory: () => makeFakeConnection({}) }),
    /NOSANA_TENANT_SECRET_KEY is not set/,
  );
});

test("runTenantIncarnation: fails closed when NOSANA_STATE_GITHUB_TOKEN is missing", async () => {
  const tenantKp = Keypair.generate();
  await assert.rejects(
    () =>
      runTenantIncarnation({
        env: { NOSANA_TENANT_SECRET_KEY: bs58.encode(tenantKp.secretKey) },
        fetchImpl: makeFakeGithubFetch(),
        connectionFactory: () => makeFakeConnection({}),
      }),
    /NOSANA_STATE_GITHUB_TOKEN is not set/,
  );
});

test("runTenantIncarnation: a failed/zero NOS balance read is honestly reported as 0, never fabricated, and does not crash the run", async () => {
  const tenantKp = Keypair.generate();
  const env = { NOSANA_TENANT_SECRET_KEY: bs58.encode(tenantKp.secretKey), NOSANA_STATE_GITHUB_TOKEN: "fake-token" };
  const fetchImpl = makeFakeGithubFetch();
  const connectionFactory = () => ({
    async getBalance() { return 500; },
    async getParsedTokenAccountsByOwner() { throw new Error("simulated RPC hiccup"); },
    async getLatestBlockhash() { return { blockhash: "BH" }; },
  });

  const report = await runTenantIncarnation({ env, fetchImpl, connectionFactory, now: () => 1_000_000 });
  assert.equal(report.nosBalance, 0);
  assert.equal(report.solLamports, 500);
});
