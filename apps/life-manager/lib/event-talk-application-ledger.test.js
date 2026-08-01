"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { buildTalkApplicationLedgerEntry } = require("./event-talk-application-ledger.js");

const BASE = Object.freeze({
  entity_id: `event-entity:${"d".repeat(64)}`,
  tenant_id: "tenant-a",
  kind: "talk_application",
  event_ref: "luma-event://event/talk-ledger",
});

function change(from, to, version, receipt = `receipt://talk/${to}`) {
  return {
    entity: { ...BASE, schema_version: 1, canonical_url: "https://luma.com/talk-ledger", status: to, payload: {}, version },
    transition: { ...BASE, from_status: from, to_status: to, version, occurred_at: `2026-08-0${version}T00:00:00.000Z`, receipt_ref: receipt },
  };
}

test("4つの外部statusをreceipt-bound append-only entryへ変換する", () => {
  for (const [from, to, version] of [
    ["drafted", "submitted", 3], ["submitted", "accepted", 4],
    ["submitted", "rejected", 4], ["accepted", "presented", 5],
  ]) {
    const actual = buildTalkApplicationLedgerEntry(change(from, to, version));
    assert.equal(actual.status, to);
    assert.equal(actual.from_status, from);
    assert.match(actual.ledger_id, /^talk-ledger:[0-9a-f]{64}$/);
    assert.equal(buildTalkApplicationLedgerEntry(change(from, to, version)).ledger_id, actual.ledger_id);
    assert.equal(Object.isFrozen(actual), true);
  }
});

test("receiptなし、非talk、非正規遷移、entity/transition不一致を拒否する", () => {
  assert.throws(() => buildTalkApplicationLedgerEntry(change("drafted", "submitted", 3, null)), /receipt/i);
  assert.throws(() => buildTalkApplicationLedgerEntry({ ...change("drafted", "submitted", 3), entity: { ...change("drafted", "submitted", 3).entity, kind: "audience_registration" } }), /transition/i);
  assert.throws(() => buildTalkApplicationLedgerEntry(change("drafted", "accepted", 3)), /transition/i);
  const mismatch = change("submitted", "accepted", 4);
  mismatch.transition.tenant_id = "tenant-b";
  assert.throws(() => buildTalkApplicationLedgerEntry(mismatch), /transition/i);
});
