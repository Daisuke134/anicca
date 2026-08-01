"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const {
  normalizeFunderInboundMessage,
  classifyFunderInbound,
} = require("./funder-inbound-status.js");
const { appendFunderInboundStatus } = require("./funder-inbound-status-store.js");

const OUTREACH = Object.freeze({
  schema_version: 1,
  tenant_id: "dais-local",
  outreach_id: "funder-outreach:" + "a".repeat(64),
  candidate_id: "yeetvc",
  sent_at: "2026-08-01T17:50:10.812Z",
  provider_message_id: "19fbe729f4bfc3f2",
  provider_thread_id: "19fbe729f4bfc3f2",
});

function message(overrides = {}) {
  return {
    id: "19fbe72a5b2cc4e7",
    threadId: OUTREACH.provider_thread_id,
    internalDate: Date.parse("2026-08-01T17:50:11.000Z"),
    body: "メールを pitch@example.com に配信できませんでした。リモート サーバーからの応答: 554 5.7.1 Relay access denied",
    headers: {
      from: "Mail Delivery Subsystem <mailer-daemon@googlemail.com>",
      subject: "Delivery Status Notification (Failure)",
    },
    ...overrides,
  };
}

function judgment(status, quote) {
  return {
    kind: "agent_judgment",
    status,
    rationale: "The exact inbound evidence supports this lifecycle status.",
    evidence_quotes: [quote],
  };
}

test("agent judgment maps exact inbound evidence to each allowed typed status without raw text", () => {
  const cases = [
    ["delivery_failed", message(), "Relay access denied"],
    ["reply_received", message({ id: "19fc000000000001", body: "Thanks, I will review this with the team.", headers: { from: "Partner <partner@example.com>", subject: "Re: Anicca" } }), "review this with the team"],
    ["rejected", message({ id: "19fc000000000002", body: "Thanks, but this is not a fit for our fund.", headers: { from: "Partner <partner@example.com>", subject: "Re: Anicca" } }), "not a fit"],
    ["meeting_requested", message({ id: "19fc000000000003", body: "This is interesting. Can we meet Tuesday at 10:00 JST?", headers: { from: "Partner <partner@example.com>", subject: "Re: Anicca" } }), "meet Tuesday"],
  ];
  for (const [status, raw, quote] of cases) {
    const normalized = normalizeFunderInboundMessage(raw, { ownerEmail: "keiodaisuke@gmail.com", outreachReceipt: OUTREACH });
    const result = classifyFunderInbound({ outreachReceipt: OUTREACH, message: normalized, judgment: judgment(status, quote) });
    assert.equal(result.status, status);
    assert.equal(result.provider_message_id, raw.id);
    assert.match(result.body_sha256, /^[0-9a-f]{64}$/);
    assert.match(result.evidence_sha256, /^[0-9a-f]{64}$/);
    assert.equal("body" in result, false);
    assert.equal("sender" in result, false);
    assert.equal(JSON.stringify(result).includes("partner@example.com"), false);
    assert.equal(JSON.stringify(result).includes(quote), false);
  }
});

test("cross-thread, owner outbound, pre-send, fabricated quote, and unknown status fail closed", () => {
  const opts = { ownerEmail: "keiodaisuke@gmail.com", outreachReceipt: OUTREACH };
  assert.throws(() => normalizeFunderInboundMessage(message({ threadId: "19fc000000000099" }), opts), /inbound status/i);
  assert.throws(() => normalizeFunderInboundMessage(message({ headers: { from: "Daisuke Narita <keiodaisuke@gmail.com>", subject: "Re" } }), opts), /inbound status/i);
  assert.throws(() => normalizeFunderInboundMessage(message({ internalDate: Date.parse("2026-08-01T17:00:00Z") }), opts), /inbound status/i);
  const normalized = normalizeFunderInboundMessage(message(), opts);
  assert.throws(() => classifyFunderInbound({ outreachReceipt: OUTREACH, message: normalized, judgment: judgment("meeting_requested", "invented Tuesday") }), /inbound status/i);
  assert.throws(() => classifyFunderInbound({ outreachReceipt: OUTREACH, message: normalized, judgment: judgment("positive", "Relay access denied") }), /inbound status/i);
  assert.throws(() => classifyFunderInbound({ outreachReceipt: OUTREACH, message: normalized, judgment: { ...judgment("delivery_failed", "Relay access denied"), kind: "keyword_rule" } }), /inbound status/i);
});

test("status migration/store are append-only exact-replay and expose a derived latest view", async () => {
  const migration = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-02-lm-funder-inbound-status-ledger.sql"), "utf8");
  assert.match(migration, /CREATE TABLE IF NOT EXISTS public\.lm_funder_inbound_status_ledger/i);
  assert.match(migration, /CREATE OR REPLACE VIEW public\.lm_funder_current_status/i);
  assert.match(migration, /DISTINCT ON \(tenant_id, outreach_id\)/i);
  assert.match(migration, /ENABLE ROW LEVEL SECURITY/i);
  assert.match(migration, /UNIQUE \(tenant_id, provider_message_id\)/i);
  assert.doesNotMatch(migration, /UPDATE public\.lm_funder_inbound_status_ledger/i);

  const normalized = normalizeFunderInboundMessage(message(), { ownerEmail: "keiodaisuke@gmail.com", outreachReceipt: OUTREACH });
  const observation = classifyFunderInbound({ outreachReceipt: OUTREACH, message: normalized, judgment: judgment("delivery_failed", "Relay access denied") });
  const calls = [];
  const saved = await appendFunderInboundStatus(observation, { query: async (sql, params) => {
    calls.push({ sql, params });
    return { rows: [{ observation_id: params[1], inserted: true }] };
  } });
  assert.equal(saved.observation_id, observation.observation_id);
  assert.match(calls[0].sql, /ON CONFLICT DO NOTHING/i);
  assert.doesNotMatch(calls[0].sql, /UPDATE/i);
  assert.equal(calls[0].params.includes(message().body), false);
});
