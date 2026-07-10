// VCSDD spawn-funding-swap Phase 2a (RED). REQ-004, REQ-005 — planNextLeg (pure leg-scheduling state
// machine) and reconcileLedgerOnResume (pure parse/validation of the on-disk ledger). Written against
// lib/pure/ledger-plan.mjs, which does NOT exist yet — every test below MUST fail at module-load time
// (MODULE_NOT_FOUND) until Phase 2b.
import { test } from "node:test";
import assert from "node:assert/strict";
import fc from "fast-check";
import { planNextLeg, reconcileLedgerOnResume } from "../pure/ledger-plan.mjs";

function ledgerWithLegs(legs) {
  return { legs };
}

// PROP-007
test("PROP-007: planNextLeg returns the FIRST unconfirmed leg index when some legs are confirmed and others are not", () => {
  const route = { txsRequired: 2 };
  const ledgerState = ledgerWithLegs([{ legIndex: 0, status: "confirmed" }]);
  const result = planNextLeg(route, ledgerState);
  assert.equal(result.action, "SUBMIT");
  assert.equal(result.legIndex, 1);
});

test("PROP-007: planNextLeg returns SUBMIT legIndex=0 for a fresh/empty ledger", () => {
  const route = { txsRequired: 2 };
  const result = planNextLeg(route, ledgerWithLegs([]));
  assert.equal(result.action, "SUBMIT");
  assert.equal(result.legIndex, 0);
});

test("PROP-007: planNextLeg returns DONE when every required leg is confirmed and the ledger has no prior completion marker", () => {
  const route = { txsRequired: 2 };
  const ledgerState = { ...ledgerWithLegs([{ legIndex: 0, status: "confirmed" }, { legIndex: 1, status: "confirmed" }]), completedAtMs: null };
  const result = planNextLeg(route, ledgerState);
  assert.equal(result.action, "DONE");
});

test("PROP-007: planNextLeg returns ALREADY_COMPLETE when the ledger already carries a prior completion marker", () => {
  const route = { txsRequired: 2 };
  const ledgerState = { ...ledgerWithLegs([{ legIndex: 0, status: "confirmed" }, { legIndex: 1, status: "confirmed" }]), completedAtMs: 1_700_000_000_000 };
  const result = planNextLeg(route, ledgerState);
  assert.equal(result.action, "ALREADY_COMPLETE");
});

test("PROP-007 (property): planNextLeg NEVER returns a leg index that already has a confirmed entry in the ledger, for arbitrary confirmed-subset ledgers", () => {
  fc.assert(
    fc.property(fc.integer({ min: 1, max: 5 }), fc.array(fc.integer({ min: 0, max: 4 }), { maxLength: 5 }), (txsRequired, confirmedIdxRaw) => {
      const confirmedIdx = new Set(confirmedIdxRaw.filter((i) => i < txsRequired));
      const legs = [...confirmedIdx].map((legIndex) => ({ legIndex, status: "confirmed" }));
      const result = planNextLeg({ txsRequired }, ledgerWithLegs(legs));
      if (result.action === "SUBMIT") {
        assert.ok(!confirmedIdx.has(result.legIndex), `planNextLeg must never resubmit already-confirmed leg ${result.legIndex}`);
        assert.ok(result.legIndex >= 0 && result.legIndex < txsRequired);
      } else {
        assert.equal(confirmedIdx.size, txsRequired, "DONE/ALREADY_COMPLETE only valid when every leg is confirmed");
      }
    }),
    { numRuns: 300 }
  );
});

test("PROP-007: a Leg-2 stall (Leg-1 confirmed, Leg-2 pending, not failed/absent) still resolves to SUBMIT legIndex=1, never re-submits Leg-1", () => {
  const route = { txsRequired: 2 };
  const ledgerState = ledgerWithLegs([{ legIndex: 0, status: "confirmed" }, { legIndex: 1, status: "pending" }]);
  const result = planNextLeg(route, ledgerState);
  assert.equal(result.action, "SUBMIT");
  assert.equal(result.legIndex, 1);
});

// reconcileLedgerOnResume — REQ-005 corrupted-ledger edge case
test("reconcileLedgerOnResume returns 'CORRUPT' for unparseable ledger contents — fail closed, never treated as 'empty/start fresh'", () => {
  assert.equal(reconcileLedgerOnResume("{not valid json"), "CORRUPT");
  assert.equal(reconcileLedgerOnResume(undefined), "CORRUPT");
  assert.equal(reconcileLedgerOnResume(42), "CORRUPT");
});

test("reconcileLedgerOnResume returns a normalized ledger state for a well-formed ledger object/JSON string", () => {
  const raw = JSON.stringify({ legs: [{ legIndex: 0, status: "confirmed" }], completedAtMs: null });
  const result = reconcileLedgerOnResume(raw);
  assert.notEqual(result, "CORRUPT");
  assert.equal(Array.isArray(result.legs), true);
  assert.equal(result.legs[0].legIndex, 0);
});

test("reconcileLedgerOnResume treats a null/absent prior ledger (never-run-before case) as a fresh empty state, distinct from CORRUPT", () => {
  const result = reconcileLedgerOnResume(null);
  assert.notEqual(result, "CORRUPT");
  assert.equal(result.legs.length, 0);
});
