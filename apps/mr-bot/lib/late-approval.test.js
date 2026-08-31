"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const {
  createLateDraft,
  decideLateDraft,
  claimApprovedDelivery,
  recordLateDelivery,
  enqueueLateTelegramReceipt,
  recordLateApprovalCard,
  claimLateTelegramReceipt,
  recordLateTelegramReceipt,
  releaseLateTelegramReceipt,
  createInMemoryLateApprovalStore,
  createSupabaseLateApprovalStore,
  getLateDraft,
  LateApprovalError,
} = require("./late-approval.js");

const NOW = Date.parse("2026-08-08T06:00:00.000Z");

function resolvedInput(overrides = {}) {
  return {
    uid: "lm-user-1",
    eventKey: "calendar:event-1",
    recipientStatus: "resolved",
    recipients: [{
      display_name: "Meeting partner",
      email: "partner@example.invalid",
      source: "calendar",
      evidence_refs: ["calendar:event:event-1:attendee:0"],
      confidence: 1,
      event_role: "attendee",
    }],
    evidenceSnapshot: {
      refs: ["calendar:event:event-1:attendee:0"],
      source: "calendar",
    },
    bodySnapshot: "到着予定が遅れるため、06:20ごろに着く見込みです。",
    etaEvidence: {
      route_eta: "2026-08-08T06:20:00.000Z",
      event_start: "2026-08-08T06:10:00.000Z",
      basis: "route_eta_from_live_location",
    },
    nowMs: NOW,
    ...overrides,
  };
}

function missingInput(status) {
  return resolvedInput({
    eventKey: `calendar:${status}-event`,
    recipientStatus: status,
    recipients: [],
    evidenceSnapshot: { refs: [], status },
  });
}

test("migration defines immutable late approval snapshots, unique event claims, and allowlisted RPCs", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-08-lm-late-approval.sql"), "utf8");
  assert.match(sql, /CREATE TABLE IF NOT EXISTS public\.lm_late_approval_drafts/i);
  assert.match(sql, /UNIQUE\s*\(\s*uid\s*,\s*event_key\s*\)/i);
  assert.match(sql, /recipient_snapshot\s+jsonb/i);
  assert.match(sql, /evidence_snapshot\s+jsonb/i);
  assert.match(sql, /body_snapshot\s+text/i);
  assert.match(sql, /immutable.*snapshot|snapshot.*immutable/i);
  assert.match(sql, /claim_token/i);
  assert.match(sql, /provider_idempotency_key\s+text\s+NOT NULL/i);
  assert.match(sql, /provider_message_id/i);
  assert.match(sql, /telegram_receipt_status\s+text\s+NOT NULL/i);
  assert.match(sql, /telegram_receipt_claim_token/i);
  assert.match(sql, /telegram_receipt_message_id/i);
  assert.match(sql, /telegram_approval_message_id/i);
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.lm_create_late_draft/i);
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.lm_get_late_draft/i);
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.lm_decide_late_draft/i);
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.lm_claim_late_delivery/i);
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.lm_record_late_delivery/i);
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.lm_enqueue_late_telegram_receipt/i);
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.lm_record_late_approval_card/i);
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.lm_claim_late_telegram_receipt/i);
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.lm_record_late_telegram_receipt/i);
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.lm_release_late_telegram_receipt/i);
  assert.match(sql, /FOR UPDATE/i);
  assert.match(sql, /SECURITY DEFINER/i);
  for (const signature of [
    "lm_create_late_draft\\(text,text,text,jsonb,jsonb,text,jsonb,text\\)",
    "lm_get_late_draft\\(text,text\\)",
    "lm_decide_late_draft\\(text,text,text,text\\)",
    "lm_claim_late_delivery\\(text,text,integer\\)",
    "lm_record_late_delivery\\(text,text,text,timestamptz,text,text\\)",
    "lm_enqueue_late_telegram_receipt\\(text,text,text,text\\)",
    "lm_record_late_approval_card\\(text,text,text,text\\)",
    "lm_claim_late_telegram_receipt\\(text,text,text,integer\\)",
    "lm_record_late_telegram_receipt\\(text,text,text,text,text\\)",
    "lm_release_late_telegram_receipt\\(text,text,text,text,text\\)",
  ]) {
    assert.match(
      sql,
      new RegExp(`REVOKE\\s+ALL\\s+ON\\s+FUNCTION\\s+public\\.${signature}\\s+FROM\\s+PUBLIC,\\s*anon,\\s*authenticated;`, "i"),
    );
    assert.match(sql, new RegExp(`GRANT\\s+EXECUTE\\s+ON\\s+FUNCTION\\s+public\\.${signature}\\s+TO\\s+service_role`, "i"));
  }
  assert.match(
    sql,
    /REVOKE\s+ALL\s+ON\s+TABLE\s+public\.lm_late_approval_drafts,\s*public\.lm_late_approval_decisions,\s*public\.lm_late_approval_claims,\s*public\.lm_late_approval_receipts\s+FROM\s+PUBLIC,\s*anon,\s*authenticated;/i,
  );
  assert.match(
    sql,
    /REVOKE\s+ALL\s+ON\s+TABLE\s+public\.lm_late_approval_drafts,\s*public\.lm_late_approval_decisions,\s*public\.lm_late_approval_claims,\s*public\.lm_late_approval_receipts\s+FROM\s+service_role;/i,
  );
});
test("resolved draft stores one immutable evidence/body snapshot and is idempotent by uid and event key", async () => {
  const store = createInMemoryLateApprovalStore({ nowMs: NOW });
  const input = resolvedInput();
  const first = await createLateDraft(input, store);
  input.bodySnapshot = "mutated after the write";
  input.evidenceSnapshot.refs.push("forged-ref");

  assert.equal(first.status, "awaiting_decision");
  assert.equal(first.recipientStatus, "resolved");
  assert.match(first.providerIdempotencyKey, /^[a-f0-9]{64}$/);
  assert.equal(first.bodySnapshot, "到着予定が遅れるため、06:20ごろに着く見込みです。");
  assert.deepEqual(first.evidenceSnapshot.refs, ["calendar:event:event-1:attendee:0"]);

  const retry = await createLateDraft(resolvedInput(), store);
  assert.equal(retry.draftId, first.draftId);
  assert.equal(retry.duplicate, true);
  assert.equal(retry.bodySnapshot, first.bodySnapshot);
  assert.deepEqual(retry.evidenceSnapshot, first.evidenceSnapshot);
  assert.equal(retry.providerIdempotencyKey, first.providerIdempotencyKey);
});

test("recipient missing and ambiguous drafts are terminal and cannot be sent", async () => {
  for (const status of ["recipient_missing", "recipient_ambiguous"]) {
    const store = createInMemoryLateApprovalStore({ nowMs: NOW });
    const draft = await createLateDraft(missingInput(status), store);
    assert.equal(draft.status, status);
    assert.equal(draft.decision, null);

    await assert.rejects(
      decideLateDraft({
        uid: "lm-user-1", draftId: draft.draftId, decision: "send", idempotencyKey: `send-${status}`,
      }, store),
      (error) => error instanceof LateApprovalError && error.code === "recipient_not_sendable",
    );
    const claim = await claimApprovedDelivery({ draftId: draft.draftId, workerId: "worker-1" }, store);
    assert.equal(claim.claimed, false);
    assert.equal(claim.reason, status);
  }
});

test("double-tap send has one durable winner and duplicate same decision returns the original row", async () => {
  const store = createInMemoryLateApprovalStore({ nowMs: NOW });
  const draft = await createLateDraft(resolvedInput(), store);
  const [first, second] = await Promise.all([
    decideLateDraft({ uid: draft.uid, draftId: draft.draftId, decision: "send", idempotencyKey: "tap-1" }, store),
    decideLateDraft({ uid: draft.uid, draftId: draft.draftId, decision: "send", idempotencyKey: "tap-2" }, store),
  ]);

  assert.equal(first.decision, "send");
  assert.equal(second.decision, "send");
  assert.equal([first, second].filter((row) => row.duplicate !== true).length, 1);
  assert.equal(first.draftId, second.draftId);
  assert.equal(first.status, "awaiting_decision");
});

test("conflicting decision loses atomically, while do_not_send is permanent and suppresses claim", async () => {
  const store = createInMemoryLateApprovalStore({ nowMs: NOW });
  const draft = await createLateDraft(resolvedInput({ eventKey: "calendar:event-no-send" }), store);
  const noSend = await decideLateDraft({
    uid: draft.uid, draftId: draft.draftId, decision: "do_not_send", idempotencyKey: "tap-no-send",
  }, store);
  assert.equal(noSend.status, "do_not_send");
  assert.equal(noSend.decision, "do_not_send");

  const duplicate = await decideLateDraft({
    uid: draft.uid, draftId: draft.draftId, decision: "do_not_send", idempotencyKey: "retry-no-send",
  }, store);
  assert.equal(duplicate.duplicate, true);
  assert.equal(duplicate.status, "do_not_send");
  await assert.rejects(
    decideLateDraft({
      uid: draft.uid, draftId: draft.draftId, decision: "send", idempotencyKey: "late-send",
    }, store),
    (error) => error instanceof LateApprovalError && error.code === "decision_conflict",
  );
  const claim = await claimApprovedDelivery({ draftId: draft.draftId, workerId: "worker-1" }, store);
  assert.equal(claim.claimed, false);
  assert.equal(claim.reason, "do_not_send");
});

test("only one worker owns an approved delivery claim and the receipt makes it sent exactly once", async () => {
  const store = createInMemoryLateApprovalStore({ nowMs: NOW });
  const draft = await createLateDraft(resolvedInput({ eventKey: "calendar:event-claim" }), store);
  await decideLateDraft({ uid: draft.uid, draftId: draft.draftId, decision: "send", idempotencyKey: "tap-send" }, store);

  const first = await claimApprovedDelivery({ draftId: draft.draftId, workerId: "worker-a" }, store);
  const second = await claimApprovedDelivery({ draftId: draft.draftId, workerId: "worker-b" }, store);
  assert.equal(first.claimed, true);
  assert.ok(first.claimToken);
  assert.equal(first.status, "send_claimed");
  assert.equal(second.claimed, false);
  assert.equal(second.reason, "claimed_by_other_worker");

  const sent = await recordLateDelivery({
    uid: draft.uid,
    draftId: draft.draftId,
    providerMessageId: "resend-msg-1",
    deliveredAt: "2026-08-08T06:01:00.000Z",
    claimToken: first.claimToken,
    workerId: "worker-a",
  }, store);
  assert.equal(sent.status, "sent");
  assert.equal(sent.providerMessageId, "resend-msg-1");

  const retry = await recordLateDelivery({
    uid: draft.uid,
    draftId: draft.draftId,
    providerMessageId: "resend-msg-1",
    deliveredAt: "2026-08-08T06:01:00.000Z",
    claimToken: first.claimToken,
    workerId: "worker-a",
  }, store);
  assert.equal(retry.duplicate, true);
  await assert.rejects(
    recordLateDelivery({
      uid: draft.uid,
      draftId: draft.draftId,
      providerMessageId: "resend-msg-2",
      deliveredAt: "2026-08-08T06:02:00.000Z",
      claimToken: first.claimToken,
      workerId: "worker-a",
    }, store),
    (error) => error instanceof LateApprovalError && error.code === "receipt_conflict",
  );
});

test("receipt requires the draft uid and the current claim token and worker", async () => {
  const store = createInMemoryLateApprovalStore({ nowMs: NOW });
  const draft = await createLateDraft(resolvedInput({ eventKey: "calendar:event-receipt-scope" }), store);
  await decideLateDraft({ uid: draft.uid, draftId: draft.draftId, decision: "send", idempotencyKey: "tap-scope" }, store);
  const claim = await claimApprovedDelivery({ draftId: draft.draftId, workerId: "worker-scope" }, store);
  const base = {
    draftId: draft.draftId,
    providerMessageId: "scope-msg",
    deliveredAt: "2026-08-08T06:01:00.000Z",
    claimToken: claim.claimToken,
    workerId: "worker-scope",
  };

  for (const [label, input] of [
    ["uid", { ...base }],
    ["claim token", { ...base, uid: draft.uid, claimToken: undefined }],
    ["worker", { ...base, uid: draft.uid, workerId: undefined }],
  ]) {
    await assert.rejects(
      recordLateDelivery(input, store),
      (error) => error instanceof LateApprovalError && error.code === "invalid_input" && error.message.includes(label),
    );
  }
  await assert.rejects(
    recordLateDelivery({ ...base, uid: "another-user" }, store),
    (error) => error instanceof LateApprovalError && error.code === "scope_mismatch",
  );
  await assert.rejects(
    recordLateDelivery({ ...base, uid: draft.uid, claimToken: "wrong-token" }, store),
    (error) => error instanceof LateApprovalError && error.code === "claim_token_mismatch",
  );
  await assert.rejects(
    recordLateDelivery({ ...base, uid: draft.uid, workerId: "another-worker" }, store),
    (error) => error instanceof LateApprovalError && error.code === "claim_worker_mismatch",
  );
  const sent = await recordLateDelivery({ ...base, uid: draft.uid }, store);
  assert.equal(sent.status, "sent");
});

test("an interrupted worker can retry its claim, and an expired claim can be recovered by another worker", async () => {
  const store = createInMemoryLateApprovalStore({ nowMs: NOW, leaseMs: 1_000 });
  const draft = await createLateDraft(resolvedInput({ eventKey: "calendar:event-retry" }), store);
  await decideLateDraft({ uid: draft.uid, draftId: draft.draftId, decision: "send", idempotencyKey: "tap-retry" }, store);

  const first = await claimApprovedDelivery({ draftId: draft.draftId, workerId: "worker-a", nowMs: NOW }, store);
  const retry = await claimApprovedDelivery({ draftId: draft.draftId, workerId: "worker-a", nowMs: NOW + 500 }, store);
  assert.equal(retry.claimed, true);
  assert.equal(retry.claimToken, first.claimToken);
  assert.equal(retry.retry, true);

  const takeover = await claimApprovedDelivery({ draftId: draft.draftId, workerId: "worker-b", nowMs: NOW + 2_000 }, store);
  assert.equal(takeover.claimed, true);
  assert.notEqual(takeover.claimToken, first.claimToken);
  assert.equal(takeover.providerIdempotencyKey, first.providerIdempotencyKey);
  assert.equal(takeover.workerId, "worker-b");
  assert.equal(takeover.status, "send_claimed");
});

test("the approval card message id is durable and idempotent before receipt edits", async () => {
  const store = createInMemoryLateApprovalStore({ nowMs: NOW });
  const draft = await createLateDraft(resolvedInput({ eventKey: "calendar:event-telegram-card" }), store);
  const recorded = await recordLateApprovalCard({
    uid: draft.uid, draftId: draft.draftId, chatId: "100", telegramMessageId: "777", nowMs: NOW,
  }, store);
  const duplicate = await recordLateApprovalCard({
    uid: draft.uid, draftId: draft.draftId, chatId: "100", telegramMessageId: "777", nowMs: NOW,
  }, store);
  assert.equal(recorded.telegramApprovalMessageId, "777");
  assert.equal(recorded.telegramApprovalChatId, "100");
  assert.equal(duplicate.duplicate, true);
  await assert.rejects(
    () => recordLateApprovalCard({
      uid: draft.uid, draftId: draft.draftId, chatId: "100", telegramMessageId: "778", nowMs: NOW,
    }, store),
    (error) => error && error.code === "approval_card_collision",
  );
});

test("Telegram receipt outbox has one active claimant and releases a failed attempt for retry", async () => {
  const store = createInMemoryLateApprovalStore({ nowMs: NOW, leaseMs: 1_000 });
  const draft = await createLateDraft(resolvedInput({ eventKey: "calendar:event-telegram-outbox" }), store);
  await decideLateDraft({ uid: draft.uid, draftId: draft.draftId, decision: "send", idempotencyKey: "tap-outbox" }, store);
  const providerClaim = await claimApprovedDelivery({ draftId: draft.draftId, workerId: "provider-worker" }, store);
  await recordLateDelivery({
    uid: draft.uid, draftId: draft.draftId, providerMessageId: "resend-outbox-1",
    deliveredAt: "2026-08-08T06:01:00.000Z", claimToken: providerClaim.claimToken,
    workerId: "provider-worker",
  }, store);
  await enqueueLateTelegramReceipt({
    uid: draft.uid, draftId: draft.draftId, chatId: "100", receiptText: "receipt body",
  }, store);

  const first = await claimLateTelegramReceipt({
    uid: draft.uid, draftId: draft.draftId, workerId: "telegram-a", nowMs: NOW,
  }, store);
  const concurrent = await claimLateTelegramReceipt({
    uid: draft.uid, draftId: draft.draftId, workerId: "telegram-b", nowMs: NOW,
  }, store);
  assert.equal(first.claimed, true);
  assert.equal(concurrent.claimed, false);
  assert.equal(concurrent.reason, "receipt_claimed_by_other_worker");

  await releaseLateTelegramReceipt({
    uid: draft.uid, draftId: draft.draftId, claimToken: first.telegramReceiptClaimToken,
    workerId: "telegram-a", error: "telegram unavailable", nowMs: NOW,
  }, store);
  const retry = await claimLateTelegramReceipt({
    uid: draft.uid, draftId: draft.draftId, workerId: "telegram-b", nowMs: NOW + 1,
  }, store);
  assert.equal(retry.claimed, true);
  const sent = await recordLateTelegramReceipt({
    uid: draft.uid, draftId: draft.draftId, claimToken: retry.telegramReceiptClaimToken,
    workerId: "telegram-b", telegramMessageId: "701", nowMs: NOW + 1,
  }, store);
  assert.equal(sent.telegramReceiptStatus, "sent");
  const duplicate = await recordLateTelegramReceipt({
    uid: draft.uid, draftId: draft.draftId, claimToken: retry.telegramReceiptClaimToken,
    workerId: "telegram-b", telegramMessageId: "701", nowMs: NOW + 1,
  }, store);
  assert.equal(duplicate.duplicate, true);
});

test("Supabase store calls only the named RPCs and preserves a non-2xx failure", async () => {
  const calls = [];
  const replies = [{
    ok: true,
    status: 200,
    json: async () => ({
      draft_id: "draft-1", uid: "lm-user-1", event_key: "calendar:event-rpc",
      status: "awaiting_decision", recipient_status: "resolved", decision: null,
      recipient_snapshot: resolvedInput().recipients, evidence_snapshot: resolvedInput().evidenceSnapshot,
      body_snapshot: resolvedInput().bodySnapshot, eta_evidence_snapshot: resolvedInput().etaEvidence,
    }),
  }];
  const store = createSupabaseLateApprovalStore({
    supaUrl: "https://staging.supabase.test",
    supaKey: "service-role-test",
    fetchImpl: async (url, init) => { calls.push({ url, init }); return replies.shift(); },
  });
  const row = await createLateDraft(resolvedInput({ eventKey: "calendar:event-rpc" }), store);
  assert.equal(row.draftId, "draft-1");
  assert.match(calls[0].url, /\/rest\/v1\/rpc\/lm_create_late_draft$/);
  assert.equal(JSON.parse(calls[0].init.body).p_event_key, "calendar:event-rpc");

  const failingStore = createSupabaseLateApprovalStore({
    supaUrl: "https://staging.supabase.test", supaKey: "service-role-test",
    fetchImpl: async () => ({ ok: false, status: 409, json: async () => ({ message: "decision_conflict" }) }),
  });
  await assert.rejects(
    decideLateDraft({ uid: "lm-user-1", draftId: "draft-1", decision: "send", idempotencyKey: "tap" }, failingStore),
    (error) => error instanceof LateApprovalError && error.code === "storage_error" && error.status === 409,
  );
});

test("Supabase draft lookup uses the allowlisted read RPC instead of revoked table access", async () => {
  const calls = [];
  const store = createSupabaseLateApprovalStore({
    supaUrl: "https://staging.supabase.test",
    supaKey: "service-role-test",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return {
        ok: true,
        status: 200,
        json: async () => ({
          draft_id: "draft-read",
          uid: "lm-user-1",
          event_key: "calendar:event-read",
          status: "awaiting_decision",
          recipient_status: "resolved",
          recipient_snapshot: resolvedInput().recipients,
          evidence_snapshot: resolvedInput().evidenceSnapshot,
          body_snapshot: resolvedInput().bodySnapshot,
          eta_evidence_snapshot: resolvedInput().etaEvidence,
          provider_idempotency_key: "b".repeat(64),
        }),
      };
    },
  });

  const row = await getLateDraft({ uid: "lm-user-1", draftId: "draft-read" }, store);
  assert.equal(row.draftId, "draft-read");
  assert.match(calls[0].url, /\/rest\/v1\/rpc\/lm_get_late_draft$/);
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    p_uid: "lm-user-1",
    p_draft_id: "draft-read",
  });
});

test("Supabase Telegram receipt outbox uses durable queue, claim, record, and release RPCs", async () => {
  const calls = [];
  const base = {
    draft_id: "draft-telegram-rpc",
    uid: "lm-user-1",
    event_key: "calendar:event-telegram-rpc",
    status: "sent",
    recipient_status: "resolved",
    recipient_snapshot: resolvedInput().recipients,
    evidence_snapshot: resolvedInput().evidenceSnapshot,
    body_snapshot: resolvedInput().bodySnapshot,
    eta_evidence_snapshot: resolvedInput().etaEvidence,
    provider_message_id: "resend-rpc-1",
    delivered_at: "2026-08-08T06:01:00.000Z",
    telegram_receipt_status: "pending",
    telegram_receipt_chat_id: "100",
    telegram_receipt_text: "receipt body",
    telegram_receipt_attempts: 0,
  };
  const store = createSupabaseLateApprovalStore({
    supaUrl: "https://staging.supabase.test",
    supaKey: "service-role-test",
    fetchImpl: async (url, init) => {
      const rpc = String(url).split("/").pop();
      const body = JSON.parse(init.body || "{}");
      calls.push({ rpc, body });
      if (rpc === "lm_record_late_approval_card") return {
        ok: true, status: 200,
        json: async () => ({ ...base, telegram_approval_chat_id: body.p_chat_id, telegram_approval_message_id: body.p_telegram_message_id }),
      };
      if (rpc === "lm_enqueue_late_telegram_receipt") return { ok: true, status: 200, json: async () => base };
      if (rpc === "lm_claim_late_telegram_receipt") return {
        ok: true, status: 200,
        json: async () => ({ ...base, telegram_receipt_status: "send_claimed", telegram_receipt_claim_token: "claim-telegram-rpc", telegram_receipt_worker_id: body.p_worker_id }),
      };
      if (rpc === "lm_record_late_telegram_receipt") return {
        ok: true, status: 200,
        json: async () => ({ ...base, telegram_receipt_status: "sent", telegram_receipt_message_id: body.p_telegram_message_id }),
      };
      if (rpc === "lm_release_late_telegram_receipt") return {
        ok: true, status: 200,
        json: async () => base,
      };
      throw new Error(`unexpected rpc ${rpc}`);
    },
  });

  const card = await recordLateApprovalCard({ uid: "lm-user-1", draftId: base.draft_id, chatId: "100", telegramMessageId: "777" }, store);
  const queued = await enqueueLateTelegramReceipt({ uid: "lm-user-1", draftId: base.draft_id, chatId: "100", receiptText: "receipt body" }, store);
  const claimed = await claimLateTelegramReceipt({ uid: "lm-user-1", draftId: base.draft_id, workerId: "telegram-rpc-worker" }, store);
  const recorded = await recordLateTelegramReceipt({ uid: "lm-user-1", draftId: base.draft_id, claimToken: "claim-telegram-rpc", workerId: "telegram-rpc-worker", telegramMessageId: "702" }, store);
  const released = await releaseLateTelegramReceipt({ uid: "lm-user-1", draftId: base.draft_id, claimToken: "claim-telegram-rpc", workerId: "telegram-rpc-worker", error: "retry" }, store);

  assert.equal(card.telegramApprovalMessageId, "777");
  assert.equal(queued.draftId, base.draft_id);
  assert.equal(claimed.claimed, true);
  assert.equal(recorded.telegramReceiptStatus, "sent");
  assert.equal(released.telegramReceiptStatus, "pending");
  assert.deepEqual(calls.map((call) => call.rpc), [
    "lm_record_late_approval_card",
    "lm_enqueue_late_telegram_receipt",
    "lm_claim_late_telegram_receipt",
    "lm_record_late_telegram_receipt",
    "lm_release_late_telegram_receipt",
  ]);
});
