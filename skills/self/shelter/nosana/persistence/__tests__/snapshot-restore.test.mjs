// node:test — snapshot.mjs + restore.mjs: the full "house gets rebuilt" round trip, exercised
// end-to-end against createLocalFsStore (no network — see store.test.mjs/github-store.test.mjs
// for the store layer's own tests). This is the same shape of proof the S4 report's real round
// trip runs against the real GitHub store, just hermetic and fast for `node --test`.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import bs58 from "bs58";
import { Keypair } from "@solana/web3.js";

import { createLocalFsStore } from "../store.mjs";
import { snapshotState } from "../snapshot.mjs";
import { restoreState } from "../restore.mjs";
import { LEDGER_SPECS } from "../ledger-files.mjs";

function makeTestEnv() {
  const keypair = Keypair.generate();
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "citizen-state-test-"));
  const remoteDir = fs.mkdtempSync(path.join(os.tmpdir(), "citizen-state-remote-"));
  return {
    address: keypair.publicKey.toBase58(),
    env: { ANICCA_SOLANA_PRIVATE_KEY: bs58.encode(keypair.secretKey), ANICCA_STATE_DIR: stateDir },
    stateDir,
    store: createLocalFsStore({ rootDir: remoteDir }),
    cleanup: () => {
      fs.rmSync(stateDir, { recursive: true, force: true });
      fs.rmSync(remoteDir, { recursive: true, force: true });
    },
  };
}

function writeLedger(stateDir, fileName, rows) {
  const file = path.join(stateDir, fileName);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, rows.map((r) => JSON.stringify(r)).join("\n") + "\n");
}

function readRawFile(file) {
  try {
    return fs.readFileSync(file, "utf8");
  } catch (e) {
    if (e && e.code === "ENOENT") return null;
    throw e;
  }
}

// ---- dry run never writes -----------------------------------------------------------------

test("snapshotState --dry (default) never calls store.putText/putTextWithMerge", async () => {
  const t = makeTestEnv();
  try {
    writeLedger(t.stateDir, "shelter-cost.jsonl", [{ ts: 1, settledLeaseCostUsd: 0.01, jobAddress: "JOB1" }]);
    let wrote = false;
    const spyStore = {
      ...t.store,
      putText: async (...a) => { wrote = true; return t.store.putText(...a); },
      putTextWithMerge: async (...a) => { wrote = true; return t.store.putTextWithMerge(...a); },
    };
    const result = await snapshotState({ store: spyStore, stateDir: t.stateDir, env: t.env, dryRun: true });
    assert.equal(wrote, false);
    assert.equal(result.dryRun, true);
    assert.equal(result.manifest.solanaAddress, t.address);
  } finally {
    t.cleanup();
  }
});

// ---- the real round trip: snapshot -> destroy -> restore into a clean dir -----------------

test("REGRESSION: snapshot then restore-into-a-clean-dir reproduces every ledger byte-for-byte, in order, with no duplicates, and the wallet address matches", async () => {
  const t = makeTestEnv();
  try {
    const originalContents = {};
    for (const spec of LEDGER_SPECS) {
      const rows =
        spec.localFileName === "shelter-cost.jsonl"
          ? [
              { ts: 1000, settledLeaseCostUsd: 0.01199, jobAddress: "JOB1" },
              { ts: 2000, correction: true, correctsTs: 1000, correctedField: "jobAddress", correctedJobAddress: "JOB1-FIXED", reason: "test" },
              { ts: 3000, settledLeaseCostUsd: 0.0107, jobAddress: "JOB2" },
            ]
          : [
              { ts: 1000, intentId: "I1", status: "intent" },
              { ts: 1001, intentId: "I1", status: "settled", signature: "SIG1" },
            ];
      writeLedger(t.stateDir, spec.localFileName, rows);
      originalContents[spec.localFileName] = readRawFile(path.join(t.stateDir, spec.localFileName));
    }

    const snap = await snapshotState({ store: t.store, stateDir: t.stateDir, env: t.env, dryRun: false });
    assert.equal(snap.manifestError, null);
    assert.equal(snap.manifest.solanaAddress, t.address);

    // "Simulate the house being destroyed": restore into a CLEAN, different directory — the
    // original stateDir is left untouched (mirrors the real verification bar's rename-aside, not
    // delete).
    const cleanDir = fs.mkdtempSync(path.join(os.tmpdir(), "citizen-state-clean-"));
    const restore = await restoreState({ store: t.store, stateDir: t.stateDir, targetStateDir: cleanDir, env: t.env, dryRun: false });

    assert.equal(restore.addressesMatch, true, "restored manifest's address must match this environment's own locally-resolved address");
    assert.equal(restore.remoteManifest.solanaAddress, t.address);

    for (const spec of LEDGER_SPECS) {
      const restoredFile = path.join(cleanDir, spec.localFileName);
      const restoredContent = readRawFile(restoredFile);
      assert.equal(restoredContent, originalContents[spec.localFileName], `${spec.localFileName} must be byte-identical after restore`);
    }

    // Restoring a SECOND time must be a no-op (idempotent) — no duplicate rows, no growth.
    const restoreAgain = await restoreState({ store: t.store, stateDir: t.stateDir, targetStateDir: cleanDir, env: t.env, dryRun: false });
    for (const r of restoreAgain.ledgerResults) {
      assert.equal(r.appended, 0, `${r.localFileName} must append 0 rows on a second restore`);
    }
    for (const spec of LEDGER_SPECS) {
      const restoredContent = readRawFile(path.join(cleanDir, spec.localFileName));
      assert.equal(restoredContent, originalContents[spec.localFileName], `${spec.localFileName} must still be byte-identical after a second restore`);
    }

    fs.rmSync(cleanDir, { recursive: true, force: true });
  } finally {
    t.cleanup();
  }
});

test("restoreState: two jobs each wrote rows the other never saw — restore merges both, drops neither, appends the missing row after the existing ones", async () => {
  const t = makeTestEnv();
  try {
    const spec = LEDGER_SPECS[0];
    // "Remote" (what a prior job already snapshotted) has row ts=1 only.
    writeLedger(t.stateDir, spec.localFileName, [{ ts: 1, settledLeaseCostUsd: 0.01, jobAddress: "JOB1" }]);
    await snapshotState({ store: t.store, stateDir: t.stateDir, env: t.env, dryRun: false });

    // A second job died mid-write, locally, with a row (ts=2) the remote never received.
    const secondJobDir = fs.mkdtempSync(path.join(os.tmpdir(), "citizen-state-second-job-"));
    writeLedger(secondJobDir, spec.localFileName, [
      { ts: 1, settledLeaseCostUsd: 0.01, jobAddress: "JOB1" },
      { ts: 2, settledLeaseCostUsd: 0.02, jobAddress: "JOB2" },
    ]);

    const restore = await restoreState({ store: t.store, stateDir: t.stateDir, targetStateDir: secondJobDir, env: t.env, dryRun: false });
    assert.equal(restore.ledgerResults[0].appended, 0, "ts=1 already present locally — must not be duplicated");

    const finalRows = readRawFile(path.join(secondJobDir, spec.localFileName))
      .trim()
      .split("\n")
      .map((l) => JSON.parse(l));
    assert.equal(finalRows.length, 2, "no row from either side is lost, and none is duplicated");
    assert.deepEqual(finalRows.map((r) => r.ts).sort(), [1, 2]);

    fs.rmSync(secondJobDir, { recursive: true, force: true });
  } finally {
    t.cleanup();
  }
});

test("snapshotState: manifestError is reported (not thrown) when no Solana secret is resolvable in this environment", async () => {
  const t = makeTestEnv();
  try {
    const result = await snapshotState({ store: t.store, stateDir: t.stateDir, env: {}, dryRun: true });
    assert.match(result.manifestError, /no Solana secret resolved/);
    assert.equal(result.manifest, null);
  } finally {
    t.cleanup();
  }
});
