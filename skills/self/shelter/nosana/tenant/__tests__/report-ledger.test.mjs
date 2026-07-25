// node:test — report-ledger.mjs: tenant-runs.jsonl shaping + restore/append against a fake store.
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  textToLines,
  parseTenantRuns,
  buildTenantRunRecord,
  mergeTenantRunLine,
  restoreTenantRuns,
  appendTenantRun,
  TENANT_RUNS_REMOTE_KEY,
} from "../report-ledger.mjs";

function makeFakeStore(initialText = null) {
  let text = initialText;
  return {
    async getText(key) {
      assert.equal(key, TENANT_RUNS_REMOTE_KEY);
      return text;
    },
    async putTextWithMerge(key, mergeFn) {
      assert.equal(key, TENANT_RUNS_REMOTE_KEY);
      text = await mergeFn(text);
      return text;
    },
    _read: () => text,
  };
}

test("textToLines: trims, filters empty lines, handles null/empty", () => {
  assert.deepEqual(textToLines(null), []);
  assert.deepEqual(textToLines(""), []);
  assert.deepEqual(textToLines("a\n\n  b  \n"), ["a", "b"]);
});

test("parseTenantRuns: skips a malformed line rather than throwing", () => {
  const rows = parseTenantRuns('{"runNumber":1}\nnot-json\n{"runNumber":2}\n');
  assert.deepEqual(rows.map((r) => r.runNumber), [1, 2]);
});

test("buildTenantRunRecord: shapes every field, never includes secret material, defaults optional fields", () => {
  const record = buildTenantRunRecord({
    ts: 100,
    runNumber: 1,
    tenantAddress: "ADDR",
    solLamports: 1000,
    nosBalance: 0.5,
    blockhash: "BH",
    message: "MSG",
    signature: "SIG",
  });
  assert.deepEqual(Object.keys(record).sort(), [
    "blockhash",
    "jobAddress",
    "message",
    "nosBalance",
    "runNumber",
    "signature",
    "solLamports",
    "ts",
    "tenantAddress",
    "x402Attempted",
    "x402Reason",
  ].sort());
  assert.equal(record.x402Attempted, false);
  assert.equal(record.x402Reason, null);
  assert.equal(record.jobAddress, null);
  assert.ok(!JSON.stringify(record).match(/secret/i));
});

test("buildTenantRunRecord: fails closed on a missing required field", () => {
  assert.throws(
    () => buildTenantRunRecord({ runNumber: 1, tenantAddress: "A", blockhash: "B", message: "M", signature: "S" }),
    /ts is required/,
  );
});

test("mergeTenantRunLine: appends a genuinely new runNumber", () => {
  const existing = ['{"runNumber":1}'];
  const { toAppend, merged } = mergeTenantRunLine(existing, '{"runNumber":2}');
  assert.deepEqual(toAppend, ['{"runNumber":2}']);
  assert.deepEqual(merged, ['{"runNumber":1}', '{"runNumber":2}']);
});

test("mergeTenantRunLine: idempotent — re-appending the same runNumber is a no-op, existing lines untouched", () => {
  const existing = ['{"runNumber":1}', '{"runNumber":2}'];
  const { toAppend, merged } = mergeTenantRunLine(existing, '{"runNumber":2}');
  assert.deepEqual(toAppend, []);
  assert.deepEqual(merged, existing);
});

test("mergeTenantRunLine: never drops an unparsable existing line", () => {
  const existing = ["not-json", '{"runNumber":1}'];
  const { merged } = mergeTenantRunLine(existing, '{"runNumber":2}');
  assert.deepEqual(merged, ["not-json", '{"runNumber":1}', '{"runNumber":2}']);
});

test("restoreTenantRuns: brand-new tenant (no remote history) reports priorRunCount 0, lastRun null", async () => {
  const store = makeFakeStore(null);
  const restored = await restoreTenantRuns({ store });
  assert.equal(restored.priorRunCount, 0);
  assert.equal(restored.lastRun, null);
});

test("restoreTenantRuns: reports the correct count and the LAST row as lastRun", async () => {
  const store = makeFakeStore('{"runNumber":1,"ts":10}\n{"runNumber":2,"ts":20}\n');
  const restored = await restoreTenantRuns({ store });
  assert.equal(restored.priorRunCount, 2);
  assert.equal(restored.lastRun.runNumber, 2);
});

test("appendTenantRun then restoreTenantRuns: full round trip through a fake store", async () => {
  const store = makeFakeStore(null);
  const record1 = buildTenantRunRecord({
    ts: 1, runNumber: 1, tenantAddress: "A", solLamports: 0, nosBalance: 0, blockhash: "BH1", message: "M1", signature: "S1",
  });
  await appendTenantRun({ store, record: record1 });

  let restored = await restoreTenantRuns({ store });
  assert.equal(restored.priorRunCount, 1);

  const record2 = buildTenantRunRecord({
    ts: 2, runNumber: 2, tenantAddress: "A", solLamports: 5, nosBalance: 1, blockhash: "BH2", message: "M2", signature: "S2",
  });
  await appendTenantRun({ store, record: record2 });

  restored = await restoreTenantRuns({ store });
  assert.equal(restored.priorRunCount, 2);
  assert.equal(restored.lastRun.runNumber, 2);
  assert.equal(restored.rows[0].runNumber, 1, "row order preserved");
});

test("appendTenantRun: re-appending a run with the same runNumber never duplicates (idempotent snapshot)", async () => {
  const store = makeFakeStore(null);
  const record = buildTenantRunRecord({
    ts: 1, runNumber: 1, tenantAddress: "A", solLamports: 0, nosBalance: 0, blockhash: "BH", message: "M", signature: "S",
  });
  await appendTenantRun({ store, record });
  await appendTenantRun({ store, record });
  const restored = await restoreTenantRuns({ store });
  assert.equal(restored.priorRunCount, 1);
});
