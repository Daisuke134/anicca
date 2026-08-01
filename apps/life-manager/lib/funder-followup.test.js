"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const { normalizeFunderThread, planFunderFollowup } = require("./funder-followup.js");
const { deliverFunderFollowup } = require("./funder-followup-gmail.js");
const { appendFunderFollowupDecision, appendFunderFollowupReceipt } = require("./funder-followup-store.js");

function outreach() {
  return {
    schema_version: 1,
    outreach_id: "funder-outreach:d37c2a948785d12998cd46dbb8c01d4e0ee8a9818b97c2a0c316a9ed03bf4d3d",
    batch_id: "funder-outreach-batch:74ac51016258c8afc85ffe3f4ba3b351aa6dadb8a4dd04635b3e7ce43f4dc822",
    tenant_id: "dais-local",
    tokyo_date: "2026-08-02",
    candidate_id: "evio",
    funder_name: "Evio VC",
    recipient_sha256: "bb65126db9fa84a9b2040ad05d6418a1e2ea8d7b0e7d98fbbad997e1c381d1a4",
    source_url: "https://evio.vc/",
    source_observed_at: "2026-08-01T17:47:00.000Z",
    source_digest: "4e41a8e085bf7bab245fa651a1f8a7a4c95391a6ae4592bb79ac2bd0416a5ff6",
    fit_summary_sha256: "aec3f3373aacfb38e2f5bfad9fd135c5ecb908220b49d16170683cf4072d7fd0",
    subject_sha256: "4e2967f566a9684df3aa64dfd5a819d4a1a6849ea4b1ffc4a0971972ba5fc8af",
    body_sha256: "8de7af79ceafb63df6d86555a6cebd21e2a2ae39a53d45e887b890766ffae80c",
    sent_at: "2026-08-01T17:50:09.839Z",
    provider_message_id: "19fbe729ab0133d6",
    provider_thread_id: "19fbe729ab0133d6",
  };
}

function gmailMessage(id, internalDate, from, labels = []) {
  return {
    id,
    internalDate: String(Date.parse(internalDate)),
    labelIds: labels,
    payload: { headers: [
      { name: "From", value: from },
      { name: "Subject", value: "Anicca × Evio — behavioral health AI" },
    ] },
  };
}

function rawThread(messages) {
  return { downloaded: [], thread: { id: outreach().provider_thread_id, messages } };
}

function initialOnly() {
  return normalizeFunderThread(rawThread([
    gmailMessage(outreach().provider_message_id, outreach().sent_at, "Daisuke Narita <keiodaisuke@gmail.com>", ["SENT"]),
  ]), { ownerEmail: "keiodaisuke@gmail.com", expectedThreadId: outreach().provider_thread_id });
}

function draft(number) {
  return {
    kind: "agent_judgment",
    rationale: `Follow-up ${number} adds one relevant proof point without repeating the first email.`,
    subject: "Re: Anicca × Evio — behavioral health AI",
    body: number === 1
      ? "Hi Saki,\n\nOne useful detail: Anicca’s behavior-change work is grounded in attention-lapse research, not a generic wellness chatbot. Would a 15-minute fit check next week be useful?\n\n— Dais\nhttps://aniccaai.com"
      : "Hi Saki,\n\nClosing the loop here. If autonomous behavioral-health infrastructure is relevant to Evio, would a 15-minute fit check be useful? If not, I won’t follow up again.\n\n— Dais\nhttps://aniccaai.com",
  };
}

test("real Gmail envelope schedules follow-up one exactly 72 hours after initial send", () => {
  const thread = initialOnly();
  const result = planFunderFollowup({ outreachReceipt: outreach(), thread, priorFollowups: [], now: "2026-08-02T00:00:00Z" });
  assert.deepEqual(result, {
    status: "scheduled",
    followup_number: 1,
    due_at: "2026-08-04T17:50:09.839Z",
    outreach_id: outreach().outreach_id,
    provider_thread_id: outreach().provider_thread_id,
  });
});

test("day-three due plan sends one threaded reply and requires positive Gmail IDs", async () => {
  const plan = planFunderFollowup({ outreachReceipt: outreach(), thread: initialOnly(), priorFollowups: [], now: "2026-08-04T17:50:09.839Z", draft: draft(1) });
  assert.equal(plan.status, "due");
  let calls = 0;
  const receipt = await deliverFunderFollowup(plan, { send: async (message) => {
    calls += 1;
    assert.equal(message.thread_id, outreach().provider_thread_id);
    assert.equal(message.reply_to_message_id, outreach().provider_message_id);
    return { message_id: "19fc000000000001", thread_id: outreach().provider_thread_id };
  }, observedAt: () => "2026-08-04T17:50:10Z" });
  assert.equal(calls, 1);
  assert.equal(receipt.followup_number, 1);
  assert.equal(receipt.provider_message_id, "19fc000000000001");
  await assert.rejects(() => deliverFunderFollowup(plan, { send: async () => ({ ok: true }) }), /Gmail message\/thread ID/i);
});

test("any inbound including bounce suppresses follow-up and malformed binding fails closed", () => {
  const inbound = normalizeFunderThread(rawThread([
    gmailMessage(outreach().provider_message_id, outreach().sent_at, "Daisuke Narita <keiodaisuke@gmail.com>", ["SENT"]),
    gmailMessage("19fbe72a5b2cc4e7", "2026-08-01T17:50:11Z", "Mail Delivery Subsystem <mailer-daemon@googlemail.com>", ["INBOX"]),
  ]), { ownerEmail: "keiodaisuke@gmail.com", expectedThreadId: outreach().provider_thread_id });
  const result = planFunderFollowup({ outreachReceipt: outreach(), thread: inbound, priorFollowups: [], now: "2026-08-10T00:00:00Z", draft: draft(1) });
  assert.equal(result.status, "suppressed_inbound");
  assert.equal(result.inbound_message_id, "19fbe72a5b2cc4e7");
  assert.throws(() => normalizeFunderThread({ thread: { id: "different", messages: [] } }, { ownerEmail: "keiodaisuke@gmail.com", expectedThreadId: outreach().provider_thread_id }), /funder follow-up/i);
  assert.throws(() => planFunderFollowup({ outreachReceipt: outreach(), thread: { ...initialOnly(), thread_id: "different" }, priorFollowups: [], now: "2026-08-10T00:00:00Z", draft: draft(1) }), /funder follow-up/i);
});

test("second follow-up waits 96 hours after verified first and a third can never be planned", () => {
  const first = {
    schema_version: 1,
    followup_id: "funder-followup:" + "1".repeat(64),
    outreach_id: outreach().outreach_id,
    batch_id: outreach().batch_id,
    tenant_id: outreach().tenant_id,
    candidate_id: outreach().candidate_id,
    followup_number: 1,
    due_at: "2026-08-04T17:50:09.839Z",
    sent_at: "2026-08-04T17:50:10.000Z",
    provider_message_id: "19fc000000000001",
    provider_thread_id: outreach().provider_thread_id,
    rationale_sha256: "a".repeat(64),
    subject_sha256: "b".repeat(64),
    body_sha256: "c".repeat(64),
  };
  const thread = normalizeFunderThread(rawThread([
    gmailMessage(outreach().provider_message_id, outreach().sent_at, "Daisuke Narita <keiodaisuke@gmail.com>", ["SENT"]),
    gmailMessage(first.provider_message_id, first.sent_at, "Daisuke Narita <keiodaisuke@gmail.com>", ["SENT"]),
  ]), { ownerEmail: "keiodaisuke@gmail.com", expectedThreadId: outreach().provider_thread_id });
  const scheduled = planFunderFollowup({ outreachReceipt: outreach(), thread, priorFollowups: [first], now: "2026-08-05T00:00:00Z" });
  assert.equal(scheduled.status, "scheduled");
  assert.equal(scheduled.followup_number, 2);
  assert.equal(scheduled.due_at, "2026-08-08T17:50:10.000Z");
  const second = { ...first, followup_id: "funder-followup:" + "2".repeat(64), followup_number: 2, due_at: scheduled.due_at, sent_at: "2026-08-08T17:50:11.000Z", provider_message_id: "19fc000000000002" };
  const completeThread = normalizeFunderThread(rawThread([
    ...rawThread([
      gmailMessage(outreach().provider_message_id, outreach().sent_at, "Daisuke Narita <keiodaisuke@gmail.com>", ["SENT"]),
      gmailMessage(first.provider_message_id, first.sent_at, "Daisuke Narita <keiodaisuke@gmail.com>", ["SENT"]),
    ]).thread.messages,
    gmailMessage(second.provider_message_id, second.sent_at, "Daisuke Narita <keiodaisuke@gmail.com>", ["SENT"]),
  ]), { ownerEmail: "keiodaisuke@gmail.com", expectedThreadId: outreach().provider_thread_id });
  const complete = planFunderFollowup({ outreachReceipt: outreach(), thread: completeThread, priorFollowups: [first, second], now: "2026-08-20T00:00:00Z", draft: draft(2) });
  assert.equal(complete.status, "complete");
  assert.equal(complete.followup_count, 2);
});

test("follow-up migration and store permit append or exact replay but never update", async () => {
  const migration = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-02-lm-funder-followup-ledger.sql"), "utf8");
  assert.match(migration, /CREATE TABLE IF NOT EXISTS public\.lm_funder_followup_decisions/i);
  assert.match(migration, /CREATE TABLE IF NOT EXISTS public\.lm_funder_followup_ledger/i);
  assert.match(migration, /ENABLE ROW LEVEL SECURITY/i);
  assert.doesNotMatch(migration, /UPDATE public\.lm_funder_followup_decisions/i);
  assert.doesNotMatch(migration, /UPDATE public\.lm_funder_followup_ledger/i);
  const scheduled = planFunderFollowup({ outreachReceipt: outreach(), thread: initialOnly(), priorFollowups: [], now: "2026-08-02T00:00:00Z" });
  const decisionCalls = [];
  const decision = await appendFunderFollowupDecision({ ...scheduled, tenant_id: outreach().tenant_id, candidate_id: outreach().candidate_id, observed_at: "2026-08-02T00:00:00Z" }, { query: async (sql, params) => (decisionCalls.push({ sql, params }), { rows: [{ decision_id: params[1], inserted: true }] }) });
  assert.match(decision.decision_id, /^funder-followup-decision:[0-9a-f]{64}$/);
  assert.match(decisionCalls[0].sql, /ON CONFLICT DO NOTHING/i);
  assert.doesNotMatch(decisionCalls[0].sql, /UPDATE/i);
  const due = planFunderFollowup({ outreachReceipt: outreach(), thread: initialOnly(), priorFollowups: [], now: "2026-08-04T17:50:09.839Z", draft: draft(1) });
  const receipt = await deliverFunderFollowup(due, { send: async () => ({ message_id: "19fc000000000001", thread_id: outreach().provider_thread_id }), observedAt: () => "2026-08-04T17:50:10Z" });
  const calls = [];
  const saved = await appendFunderFollowupReceipt(receipt, { query: async (sql, params) => (calls.push({ sql, params }), { rows: [{ followup_id: params[1], inserted: true }] }) });
  assert.equal(saved.followup_id, receipt.followup_id);
  assert.match(calls[0].sql, /ON CONFLICT DO NOTHING/i);
  assert.doesNotMatch(calls[0].sql, /UPDATE/i);
});
