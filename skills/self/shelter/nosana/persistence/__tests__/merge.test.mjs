// node:test — merge.mjs: the dedupe key + the one append-only merge rule shared by snapshot and
// restore. These are pure functions — no filesystem, no network.
import { test } from "node:test";
import assert from "node:assert/strict";

import { dedupeKeyForRow, mergeAppendOnly } from "../merge.mjs";

const line = (obj) => JSON.stringify(obj);

// ---- dedupeKeyForRow ------------------------------------------------------------------------

test("dedupeKeyForRow: two rows with identical ts+jobAddress+signature+intentId collide", () => {
  const a = { ts: 100, jobAddress: "JOB1", signature: "SIG1", intentId: "I1" };
  const b = { ts: 100, jobAddress: "JOB1", signature: "SIG1", intentId: "I1", extraNoise: "whatever" };
  assert.equal(dedupeKeyForRow(a), dedupeKeyForRow(b));
});

test("dedupeKeyForRow: rows differing only in ts are distinct", () => {
  const a = { ts: 100, jobAddress: "JOB1" };
  const b = { ts: 101, jobAddress: "JOB1" };
  assert.notEqual(dedupeKeyForRow(a), dedupeKeyForRow(b));
});

test("dedupeKeyForRow: falls back guessedAddress -> address when jobAddress is absent", () => {
  const a = { ts: 100, guessedAddress: "GUESS1" };
  const b = { ts: 100, address: "GUESS1" };
  // Different field names but same effective identity value collapse — this documents the
  // intentional fallback chain, not an accident.
  assert.equal(dedupeKeyForRow(a), dedupeKeyForRow(b));
});

test("dedupeKeyForRow: a correction row is keyed by what it corrects, not by its own ts — two independent fixes of the same mistake collide", () => {
  const fix1 = { ts: 5000, correction: true, correctsTs: 1000, correctedField: "jobAddress", correctedJobAddress: "REAL" };
  const fix2 = { ts: 6000, correction: true, correctsTs: 1000, correctedField: "jobAddress", correctedJobAddress: "REAL" };
  assert.equal(dedupeKeyForRow(fix1), dedupeKeyForRow(fix2));
});

test("dedupeKeyForRow: a correction row never collides with an ordinary row, even at the same ts", () => {
  const ordinary = { ts: 1000, jobAddress: "JOB1" };
  const correction = { ts: 1000, correction: true, correctsTs: 1000, correctedField: "jobAddress", correctedJobAddress: "JOB2" };
  assert.notEqual(dedupeKeyForRow(ordinary), dedupeKeyForRow(correction));
});

test("dedupeKeyForRow: fails closed on a non-object row", () => {
  assert.throws(() => dedupeKeyForRow(null), /must be a non-null object/);
  assert.throws(() => dedupeKeyForRow("not an object"), /must be a non-null object/);
});

// ---- mergeAppendOnly -------------------------------------------------------------------------

test("mergeAppendOnly: existing lines are never reordered or dropped", () => {
  const existing = [line({ ts: 1, jobAddress: "A" }), line({ ts: 2, jobAddress: "B" })];
  const { merged } = mergeAppendOnly(existing, []);
  assert.deepEqual(merged, existing);
});

test("mergeAppendOnly: a genuinely new incoming row is appended verbatim at the tail", () => {
  const existing = [line({ ts: 1, jobAddress: "A" })];
  const incoming = [line({ ts: 2, jobAddress: "B" })];
  const { toAppend, merged } = mergeAppendOnly(existing, incoming);
  assert.deepEqual(toAppend, incoming);
  assert.deepEqual(merged, existing.concat(incoming));
});

test("mergeAppendOnly: a duplicate incoming row (same dedupe key) is dropped, not appended", () => {
  const row = { ts: 1, jobAddress: "A" };
  const existing = [line(row)];
  const incoming = [line(row)];
  const { toAppend, merged } = mergeAppendOnly(existing, incoming);
  assert.deepEqual(toAppend, []);
  assert.deepEqual(merged, existing);
});

test("mergeAppendOnly: appended lines preserve their EXACT original bytes (no re-serialization)", () => {
  // A hand-written line with different key order / spacing than JSON.stringify would produce.
  const oddlyFormattedLine = '{"jobAddress":"B", "ts":2}';
  const existing = [line({ ts: 1, jobAddress: "A" })];
  const { toAppend, merged } = mergeAppendOnly(existing, [oddlyFormattedLine]);
  assert.equal(toAppend[0], oddlyFormattedLine); // byte-identical, not JSON.stringify(JSON.parse(...))
  assert.equal(merged[1], oddlyFormattedLine);
});

test("mergeAppendOnly: idempotent — merging the same incoming lines twice appends nothing the second time", () => {
  const existing = [line({ ts: 1, jobAddress: "A" })];
  const incoming = [line({ ts: 2, jobAddress: "B" }), line({ ts: 3, jobAddress: "C" })];
  const first = mergeAppendOnly(existing, incoming);
  const second = mergeAppendOnly(first.merged, incoming);
  assert.deepEqual(second.toAppend, []);
  assert.deepEqual(second.merged, first.merged);
});

test("mergeAppendOnly: mixed case — some incoming rows are new, some are duplicates, order preserved", () => {
  const rowA = { ts: 1, jobAddress: "A" };
  const rowB = { ts: 2, jobAddress: "B" };
  const rowC = { ts: 3, jobAddress: "C" };
  const existing = [line(rowA), line(rowB)];
  const incoming = [line(rowB), line(rowC)]; // B is a duplicate, C is new
  const { toAppend, merged } = mergeAppendOnly(existing, incoming);
  assert.deepEqual(toAppend, [line(rowC)]);
  assert.deepEqual(merged, [line(rowA), line(rowB), line(rowC)]);
});

test("mergeAppendOnly: empty existing + incoming reproduces incoming verbatim in order (the from-empty restore case)", () => {
  const incoming = [line({ ts: 1, jobAddress: "A" }), line({ ts: 2, jobAddress: "B" }), line({ ts: 3, jobAddress: "C" })];
  const { toAppend, merged } = mergeAppendOnly([], incoming);
  assert.deepEqual(toAppend, incoming);
  assert.deepEqual(merged, incoming);
});
