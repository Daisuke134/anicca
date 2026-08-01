"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const { appendTalkApplicationLedgerEntry } = require("./event-talk-application-ledger-store.js");
const { buildTalkApplicationLedgerEntry } = require("./event-talk-application-ledger.js");

const migration = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-02-lm-event-talk-application-ledger.sql"), "utf8");
const entry = buildTalkApplicationLedgerEntry({
  entity: { schema_version: 1, entity_id: `event-entity:${"e".repeat(64)}`, tenant_id: "tenant-a", kind: "talk_application", event_ref: "luma-event://event/ledger", canonical_url: "https://luma.com/ledger", status: "submitted", payload: {}, version: 3 },
  transition: { entity_id: `event-entity:${"e".repeat(64)}`, tenant_id: "tenant-a", kind: "talk_application", from_status: "drafted", to_status: "submitted", version: 3, occurred_at: "2026-08-03T00:00:00Z", receipt_ref: "receipt://talk/submitted" },
});

test("migrationは4 statusのappend-only tenant ledgerを作る", () => {
  assert.match(migration, /CREATE TABLE IF NOT EXISTS public\.lm_event_talk_application_ledger/i);
  assert.match(migration, /status IN \('submitted', 'accepted', 'rejected', 'presented'\)/i);
  assert.match(migration, /UNIQUE \(tenant_id, talk_entity_id, status\)/i);
  assert.match(migration, /UNIQUE \(tenant_id, receipt_ref\)/i);
  assert.match(migration, /ENABLE ROW LEVEL SECURITY/i);
  assert.match(migration, /GRANT SELECT, INSERT.*service_role/is);
  assert.doesNotMatch(migration, /GRANT[^;]*UPDATE[^;]*service_role/is);
});

test("exact replayだけを同じledger rowとして返す", async () => {
  let seen;
  const result = await appendTalkApplicationLedgerEntry(entry, { query: async (sql, params) => {
    seen = { sql, params };
    return { rows: [{ ledger_id: entry.ledger_id, inserted: false }] };
  }});
  assert.equal(result.ledger_id, entry.ledger_id);
  assert.match(seen.sql, /ON CONFLICT DO NOTHING/i);
  assert.match(seen.sql, /UNION ALL/i);
  assert.equal(seen.params[6], entry.receipt_ref);
});

test("不正entryとcollision 0行を成功扱いしない", async () => {
  await assert.rejects(appendTalkApplicationLedgerEntry({ ...entry, status: "drafted" }, { query: async () => ({ rows: [] }) }), /invalid/i);
  await assert.rejects(appendTalkApplicationLedgerEntry(entry, { query: async () => ({ rows: [] }) }), /conflict/i);
});
