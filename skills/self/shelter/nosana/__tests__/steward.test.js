// node:test — steward: the lease-long loop that turns "posted a job and exited" into "stayed
// alive for the whole lease and can prove it". All I/O is faked: jobs-API fetch returns the REAL
// field shape captured live 2026-07-26 (state/jobStatus/timeStart/timeEnd/timeout), the RPC
// connection is a stub advancing slot+blockhash per cycle, sleep is a no-op, the ledger is an
// in-memory array, and the keypair is a THROWAWAY nacl keypair injected directly (tests never
// touch resolve-identity or Franklin's real secret).
import { test } from "node:test";
import assert from "node:assert/strict";
import nacl from "tweetnacl";
import bs58 from "bs58";
import { verifyHeartbeatEntry } from "../heartbeat.mjs";
import { fetchJobViaApi, computeLeaseEnd, isTerminal, stewardLoop } from "../steward.mjs";

function throwawayKeypair() {
  const kp = nacl.sign.keyPair();
  return { address: bs58.encode(kp.publicKey), secretBytes: kp.secretKey };
}

const JOB_ADDRESS = "CUcMnkzWL8RdNDtGw7pdbqE8xVawuPf2dUigQ3wS5qDs";

// Real captured shape (live GET 2026-07-26), trimmed to the fields the steward reads.
function makeRunningJob(overrides = {}) {
  return {
    address: JOB_ADDRESS,
    payer: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T",
    state: 1,
    jobStatus: "running",
    timeStart: 1_785_000_000,
    timeEnd: null,
    timeout: 900,
    node: "7iHYfu5QLJNF8gU8kdHy6Ruc7mg8cSYpA329CcYeMW3N",
    ...overrides,
  };
}

function fetchImplReturning(bodies) {
  // bodies: array consumed one per call; last one repeats.
  let i = 0;
  return async () => {
    const body = bodies[Math.min(i, bodies.length - 1)];
    i += 1;
    if (body === null) return { ok: false, status: 500, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => body };
  };
}

function fakeConnectionFactory() {
  let slot = 100;
  return () => ({
    getSlot: async () => (slot += 10),
    getLatestBlockhash: async () => ({ blockhash: `hash-${slot}` }),
  });
}

function loopHarness({ jobs, keypair = throwawayKeypair(), ...overrides }) {
  const appended = [];
  const logs = [];
  let t = 1_785_000_060_000; // ms
  return {
    appended,
    logs,
    keypair,
    run: () =>
      stewardLoop({
        jobAddress: JOB_ADDRESS,
        keypair,
        fetchImpl: fetchImplReturning(jobs),
        connectionFactory: fakeConnectionFactory(),
        intervalMs: 0,
        sleep: async () => {},
        now: () => (t += 60_000),
        appendImpl: (entry) => appended.push(entry),
        log: (line) => logs.push(line),
        ...overrides,
      }),
  };
}

test("computeLeaseEnd: timeStart+timeout, recomputed from whatever the API returns now", () => {
  assert.equal(computeLeaseEnd(makeRunningJob()), 1_785_000_000 + 900);
  assert.equal(computeLeaseEnd(makeRunningJob({ timeout: 1800 })), 1_785_000_000 + 1800);
  assert.equal(computeLeaseEnd(makeRunningJob({ timeout: null, timeEnd: 42 })), 42);
  assert.equal(computeLeaseEnd(makeRunningJob({ timeout: null, timeEnd: null })), null);
});

test("isTerminal: done state, terminal jobStatus, or past lease end + grace", () => {
  assert.equal(isTerminal(makeRunningJob(), 1_785_000_100), false);
  assert.equal(isTerminal(makeRunningJob({ state: 2 }), 1_785_000_100), true);
  assert.equal(isTerminal(makeRunningJob({ jobStatus: "success" }), 1_785_000_100), true);
  // Past leaseEnd (1785000900) + default 120s grace:
  assert.equal(isTerminal(makeRunningJob(), 1_785_001_021), true);
  assert.equal(isTerminal(makeRunningJob(), 1_785_001_019), false);
});

test("fetchJobViaApi: returns parsed job, null on HTTP error / throw", async () => {
  const job = makeRunningJob();
  assert.deepEqual(await fetchJobViaApi({ fetchImpl: fetchImplReturning([job]), jobAddress: JOB_ADDRESS }), job);
  assert.equal(await fetchJobViaApi({ fetchImpl: fetchImplReturning([null]), jobAddress: JOB_ADDRESS }), null);
  assert.equal(
    await fetchJobViaApi({ fetchImpl: async () => { throw new Error("network down"); }, jobAddress: JOB_ADDRESS }),
    null,
  );
});

test("loop runs until state becomes terminal, appending one verifiable heartbeat per cycle", async () => {
  const h = loopHarness({ jobs: [makeRunningJob(), makeRunningJob(), makeRunningJob({ state: 2, jobStatus: "success" })] });
  const result = await h.run();
  assert.equal(result.cycles, 3);
  assert.equal(result.heartbeats, 3);
  assert.equal(result.terminal.state, 2);
  assert.equal(h.appended.length, 3);
  for (const entry of h.appended) {
    const verdict = verifyHeartbeatEntry(entry);
    assert.equal(verdict.valid, true, verdict.reason);
    assert.equal(entry.payer, h.keypair.address);
    assert.equal(entry.jobAddress, JOB_ADDRESS);
  }
  // Fresh blockhash per cycle — all distinct.
  assert.equal(new Set(h.appended.map((e) => e.blockhash)).size, 3);
  // Cycles numbered from 1.
  assert.deepEqual(h.appended.map((e) => e.cycle), [1, 2, 3]);
});

test("timeout re-read: lease extension observed mid-lease is picked up and logged", async () => {
  const h = loopHarness({
    jobs: [makeRunningJob(), makeRunningJob({ timeout: 1800 }), makeRunningJob({ timeout: 1800, state: 2 })],
  });
  const result = await h.run();
  assert.equal(result.cycles, 3);
  assert.ok(
    h.logs.some((l) => /lease extended/.test(l)),
    `expected a "lease extended" log line, got: ${JSON.stringify(h.logs)}`,
  );
});

test("consecutive API failures hit the cap and throw (fail-closed), heartbeats continue through the blips", async () => {
  // Design decision: the steward BEATS even on cycles whose API read failed — aliveness evidence
  // must not depend on the indexer's uptime. Cycle 1 succeeds+beats, cycles 2-3 fail+still beat,
  // cycle 4 hits the cap (3 consecutive) and throws BEFORE beating.
  const h = loopHarness({ jobs: [makeRunningJob(), null, null, null], maxConsecutiveFailures: 3 });
  await assert.rejects(h.run(), /consecutive/);
  assert.equal(h.appended.length, 3);
  for (const entry of h.appended) assert.equal(verifyHeartbeatEntry(entry).valid, true);
});

test("maxCycles safety valve stops a lease that never terminates", async () => {
  const h = loopHarness({ jobs: [makeRunningJob()], maxCycles: 5 });
  const result = await h.run();
  assert.equal(result.cycles, 5);
  assert.equal(result.terminal.reason, "max-cycles");
});

test("atomic slot+blockhash: getLatestBlockhashAndContext preferred so slot always matches blockhash", async () => {
  // Regression for a real S8 E2E finding: 2/16 entries failed the verifier's getBlock(slot)
  // cross-check because slot and blockhash came from two separate RPC calls.
  let calls = 0;
  const h = loopHarness({
    jobs: [makeRunningJob({ state: 2, jobStatus: "success" })],
    connectionFactory: () => ({
      getLatestBlockhashAndContext: async () => {
        calls += 1;
        return { context: { slot: 5000 + calls }, value: { blockhash: `atomic-${5000 + calls}` } };
      },
      // The non-atomic pair must NOT be used when the atomic variant exists:
      getSlot: async () => { throw new Error("getSlot must not be called when AndContext exists"); },
      getLatestBlockhash: async () => { throw new Error("getLatestBlockhash must not be called when AndContext exists"); },
    }),
  });
  const result = await h.run();
  assert.equal(result.heartbeats, 1);
  assert.equal(h.appended[0].slot, 5001);
  assert.equal(h.appended[0].blockhash, "atomic-5001");
});
