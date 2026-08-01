"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { buildFunderSubmissionReceipt } = require("./funder-submission-receipt.js");
const { makeFunderGogThreadReader } = require("./funder-gog-thread-reader.js");
const {
  normalizeFunderApplicationThread,
  buildFunderConfirmationResult,
  buildFunderReplyResult,
} = require("./funder-thread-result.js");
const { appendOutboundResult } = require("./outbound-result-store.js");
const { syncFunderThreadResults, loadFunderSubmissionReceipt } = require("./funder-thread-result-sync.js");
const {
  buildJobHunterConfirmationResult,
  verifyJobHunterConfirmationResultSource,
  makeJobHunterSqliteQuery,
  readJobHunterConfirmationReceipts,
} = require("./job-hunter-outbound-result.js");

const SQL = fs.readFileSync(path.join(__dirname,
  "../migrations/2026-08-02-lm-outbound-result-ledger.sql"), "utf8");

function submission() {
  return buildFunderSubmissionReceipt({
    tenantId: "dais-local",
    funderId: "yc-fall-2026",
    draftId: "0b61fe42-e383-490d-b60e-04f1ad7ec5df",
    applicationUrl: "https://apply.ycombinator.com/home",
    home: { status: "in_review", observedAt: "2026-08-01T17:32:00.000Z" },
    mail: {
      messageId: "19fbe6135cf98bd4",
      threadId: "19fbe6135cf98bd4",
      internalDateMs: 1785605465000,
      from: "apply@ycombinator.com",
      subject: "YC Fall 2026 Application Submitted",
      body: "Your application to the Fall 2026 batch for Anicca has been submitted.",
      dkimPass: true, spfPass: true, dmarcPass: true,
    },
  });
}

function wrapped(id, text) {
  return `<<<EXTERNAL_UNTRUSTED_CONTENT id="${id}">>>\nSource: google_api\n---\n${text}\n<<<END_EXTERNAL_UNTRUSTED_CONTENT id="${id}">>>`;
}

function rawThread(messages = []) {
  return { thread: { id: "19fbe6135cf98bd4", messages: [
    {
      id: "19fbe6135cf98bd4", threadId: "19fbe6135cf98bd4",
      internalDate: 1785605465000,
      headers: {
        from: wrapped("from-1", "apply@ycombinator.com"),
        subject: wrapped("subject-1", "YC Fall 2026 Application Submitted"),
      },
      body: wrapped("body-1", "Your application to the Fall 2026 batch for Anicca has been submitted."),
    },
    ...messages,
  ] } };
}

async function trusted(payload) {
  const reader = makeFunderGogThreadReader({
    account: "keiodaisuke@gmail.com", run: async () => JSON.stringify(payload),
  });
  return reader.getThread(payload.thread.id);
}

function reply(overrides = {}) {
  return {
    id: "19fc000000000001", threadId: "19fbe6135cf98bd4",
    internalDate: Date.parse("2026-08-02T01:00:00.000Z"),
    headers: {
      from: wrapped("from-2", "YC Partner <partner@ycombinator.com>"),
      subject: wrapped("subject-2", "Re: YC Fall 2026 Application Submitted"),
    },
    body: wrapped("body-2", "We reviewed Anicca. Can we meet Tuesday at 10:00 PT?"),
    ...overrides,
  };
}

test("reader invokes only exact read-only gog thread command and validates returned identity", async () => {
  const calls = [];
  const reader = makeFunderGogThreadReader({ account: "keiodaisuke@gmail.com", run: async (args) => {
    calls.push(args);
    return JSON.stringify(rawThread());
  } });
  const value = await reader.getThread("19fbe6135cf98bd4");
  assert.equal(value.thread.id, "19fbe6135cf98bd4");
  assert.deepEqual(calls, [[
    "--gmail-no-send", "--no-input", "gmail", "thread", "get",
    "--account=keiodaisuke@gmail.com", "--json", "--wrap-untrusted", "--full",
    "--sanitize-content", "19fbe6135cf98bd4",
  ]]);
  await assert.rejects(() => reader.getThread("--help"), /thread reader/i);

  const mismatch = makeFunderGogThreadReader({ account: "keiodaisuke@gmail.com",
    run: async () => JSON.stringify({ thread: { id: "19fc000000000099", messages: [] } }) });
  await assert.rejects(() => mismatch.getThread("19fbe6135cf98bd4"), /thread reader/i);
});

test("exact source confirmation and later inbound reply normalize without trusting wrapper text", async () => {
  const normalized = normalizeFunderApplicationThread(await trusted(rawThread([reply()])), {
    submissionReceipt: submission(), ownerEmail: "keiodaisuke@gmail.com",
  });
  assert.equal(normalized.confirmation.provider_message_id, "19fbe6135cf98bd4");
  assert.equal(normalized.replies.length, 1);
  assert.equal(normalized.replies[0].sender, "partner@ycombinator.com");
  assert.equal(normalized.replies[0].body,
    "We reviewed Anicca. Can we meet Tuesday at 10:00 PT?");
});

test("sanitizer-added confirmation display text cannot replace immutable receipt identity", async () => {
  const payload = rawThread();
  payload.thread.messages[0].body = wrapped("body-live",
    "Your application to the Fall 2026 batch for Anicca has been submitted.\nView your application in the portal.");
  const normalized = normalizeFunderApplicationThread(await trusted(payload), {
    submissionReceipt: submission(), ownerEmail: "keiodaisuke@gmail.com",
  });
  const result = buildFunderConfirmationResult({ submissionReceipt: submission(),
    message: normalized.confirmation });
  assert.equal(result.status, "confirmed");
  assert.match(result.body_sha256, /^[0-9a-f]{64}$/);
  assert.equal("body" in result, false);
});

test("cross-thread, duplicate ID, forged confirmation, pre-submit, and owner outbound fail closed", async () => {
  const opts = { submissionReceipt: submission(), ownerEmail: "keiodaisuke@gmail.com" };
  const other = await trusted({ thread: {
    id: "19fc000000000099", messages: [],
  } });
  assert.throws(() => normalizeFunderApplicationThread(other, opts), /thread result/i);
  const cross = await trusted(rawThread([
    reply(), reply({ threadId: "19fc000000000099" }),
  ]));
  assert.throws(() => normalizeFunderApplicationThread(cross, opts), /thread result/i);
  const duplicate = await trusted(rawThread([
    reply(), reply({ internalDate: Date.parse("2026-08-02T01:01:00.000Z") }),
  ]));
  assert.throws(() => normalizeFunderApplicationThread(duplicate, opts), /thread result/i);
  const forged = rawThread();
  forged.thread.messages[0].headers.subject = wrapped("subject-x", "Application accepted");
  const trustedForged = await trusted(forged);
  assert.throws(() => normalizeFunderApplicationThread(trustedForged, opts), /thread result/i);
  const preSubmit = await trusted(rawThread([
    reply({ internalDate: Date.parse("2026-08-01T17:30:00.000Z") }),
  ]));
  assert.throws(() => normalizeFunderApplicationThread(preSubmit, opts), /thread result/i);
  const outboundOnly = normalizeFunderApplicationThread(await trusted(rawThread([
    reply({ headers: { from: "Dais <keiodaisuke@gmail.com>", subject: "Re" } }),
  ])), opts);
  assert.deepEqual(outboundOnly.replies, []);
});

test("confirmation is deterministic while reply meaning requires exact agent evidence", async () => {
  const receipt = submission();
  const normalized = normalizeFunderApplicationThread(await trusted(rawThread([reply()])), {
    submissionReceipt: receipt, ownerEmail: "keiodaisuke@gmail.com",
  });
  const confirmation = buildFunderConfirmationResult({ submissionReceipt: receipt,
    message: normalized.confirmation });
  assert.equal(confirmation.organ, "fundraising");
  assert.equal(confirmation.result_type, "confirmation");
  assert.equal(confirmation.status, "confirmed");
  assert.equal(confirmation.source_fence, 1);

  const result = buildFunderReplyResult({ submissionReceipt: receipt,
    message: normalized.replies[0], judgment: {
      kind: "agent_judgment", status: "meeting_requested",
      rationale: "The partner asks for a specific meeting.",
      evidence_quotes: ["Can we meet Tuesday at 10:00 PT?"],
    } });
  assert.equal(result.result_type, "reply");
  assert.equal(result.status, "meeting_requested");
  assert.equal("body" in result, false);
  assert.equal("sender" in result, false);
  assert.equal(JSON.stringify(result).includes("partner@ycombinator.com"), false);
  assert.equal(JSON.stringify(result).includes("Can we meet"), false);

  for (const judgment of [
    { kind: "keyword_rule", status: "meeting_requested", rationale: "x", evidence_quotes: ["Can we meet"] },
    { kind: "agent_judgment", status: "positive", rationale: "x", evidence_quotes: ["Can we meet"] },
    { kind: "agent_judgment", status: "meeting_requested", rationale: "x", evidence_quotes: ["invented quote"] },
  ]) assert.throws(() => buildFunderReplyResult({ submissionReceipt: receipt,
    message: normalized.replies[0], judgment }), /thread result/i);
  assert.throws(() => buildFunderReplyResult({ submissionReceipt: receipt,
    message: { ...normalized.replies[0] }, judgment: {
      kind: "agent_judgment", status: "meeting_requested", rationale: "copied",
      evidence_quotes: ["Can we meet Tuesday at 10:00 PT?"],
    } }), /thread result/i);
});

test("common ledger is source-bound, fenced, append-only, RLS protected, and exact-replay only", async () => {
  assert.match(SQL, /CREATE TABLE IF NOT EXISTS public\.lm_outbound_result_ledger/i);
  assert.match(SQL, /organ IN \('job_hunter', 'fundraising'\)/i);
  assert.match(SQL, /source_fence integer NOT NULL/i);
  assert.match(SQL, /UNIQUE \(tenant_id, provider_message_id\)/i);
  assert.match(SQL, /BEFORE UPDATE OR DELETE/i);
  assert.match(SQL, /BEFORE TRUNCATE/i);
  assert.match(SQL, /ENABLE ROW LEVEL SECURITY/i);
  assert.match(SQL, /CREATE OR REPLACE VIEW public\.lm_outbound_current_result/i);
  assert.doesNotMatch(SQL, /UPDATE public\.lm_outbound_result_ledger/i);

  const receipt = submission();
  const normalized = normalizeFunderApplicationThread(await trusted(rawThread()), {
    submissionReceipt: receipt, ownerEmail: "keiodaisuke@gmail.com",
  });
  const result = buildFunderConfirmationResult({ submissionReceipt: receipt,
    message: normalized.confirmation });
  const calls = [];
  const saved = await appendOutboundResult(result, { query: async (sql, params) => {
    calls.push({ sql, params });
    return { rows: [{ result_id: params[1], inserted: true }] };
  } });
  assert.equal(saved.result_id, result.result_id);
  assert.match(calls[0].sql, /FROM public\.lm_funder_submission_ledger/i);
  assert.match(calls[0].sql, /ON CONFLICT DO NOTHING/i);
  assert.doesNotMatch(calls[0].sql, /UPDATE/i);
  assert.equal(calls[0].params.some((value) => String(value).includes("Your application")), false);
  await assert.rejects(() => appendOutboundResult({ ...result, status: "rejected" }, {
    query: async () => ({ rows: [] }),
  }), /outbound result store/i);
  await assert.rejects(() => appendOutboundResult({ ...result, body: "raw secret" }, {
    query: async () => ({ rows: [{ result_id: result.result_id }] }),
  }), /outbound result store/i);
  await assert.rejects(() => appendOutboundResult({ ...result }, {
    query: async () => ({ rows: [{ result_id: result.result_id }] }),
  }), /outbound result store/i);
});

test("sync appends confirmation and judged replies while leaving unjudged messages pending", async () => {
  const receipt = submission();
  const appended = [];
  const result = await syncFunderThreadResults({
    submissionReceipt: receipt,
    ownerEmail: "keiodaisuke@gmail.com",
    reader: makeFunderGogThreadReader({ account: "keiodaisuke@gmail.com", run: async (args) => {
      const threadId = args[args.length - 1];
      assert.equal(threadId, receipt.mail_thread_id);
      return JSON.stringify(rawThread([reply(), reply({
        id: "19fc000000000002",
        internalDate: Date.parse("2026-08-02T02:00:00.000Z"),
        body: wrapped("body-3", "Thank you. We will review and get back to you."),
      })]));
    } }),
    judgments: {
      "19fc000000000001": {
        kind: "agent_judgment", status: "meeting_requested",
        rationale: "A concrete meeting is requested.",
        evidence_quotes: ["Can we meet Tuesday at 10:00 PT?"],
      },
    },
    append: async (entry) => {
      appended.push(entry);
      return { result_id: entry.result_id, inserted: true };
    },
  });
  assert.deepEqual(appended.map((entry) => entry.result_type), ["confirmation", "reply"]);
  assert.deepEqual(result.pending_judgment_message_ids, ["19fc000000000002"]);
  assert.equal(JSON.stringify(result).includes("Thank you"), false);
  await assert.rejects(() => syncFunderThreadResults({
    submissionReceipt: receipt, ownerEmail: "keiodaisuke@gmail.com",
    reader: makeFunderGogThreadReader({ account: "keiodaisuke@gmail.com",
      run: async () => JSON.stringify(rawThread()) }),
    judgments: { "19fc000000000099": { kind: "agent_judgment" } },
    append: async () => ({ inserted: true }),
  }), /unused judgment/i);
});

test("sync source loader requires one exact tenant-bound ledger ID instead of latest-by-funder", async () => {
  const receipt = submission();
  const calls = [];
  const loaded = await loadFunderSubmissionReceipt({
    tenantId: receipt.tenant_id, sourceId: receipt.ledger_id,
    query: async (sql, params) => {
      calls.push({ sql, params });
      return { rows: [{
        tenant_id: receipt.tenant_id, ledger_id: receipt.ledger_id,
        funder_id: receipt.funder_id, draft_id: receipt.draft_id,
        application_url: receipt.application_url, status: receipt.status,
        provider_status: receipt.provider_status, submitted_at: receipt.submitted_at,
        home_observed_at: receipt.home_observed_at,
        mail_message_id: receipt.mail_message_id, mail_thread_id: receipt.mail_thread_id,
        mail_sender: receipt.mail_sender, mail_subject: receipt.mail_subject,
        mail_auth: receipt.mail_auth, evidence_digest: receipt.evidence_digest,
      }] };
    },
  });
  assert.equal(loaded.ledger_id, receipt.ledger_id);
  assert.deepEqual(calls[0].params, [receipt.tenant_id, receipt.ledger_id]);
  assert.match(calls[0].sql, /WHERE tenant_id=\$1 AND ledger_id=\$2/i);
  assert.doesNotMatch(calls[0].sql, /ORDER BY|LIMIT/i);
  await assert.rejects(() => loadFunderSubmissionReceipt({
    tenantId: receipt.tenant_id, sourceId: receipt.ledger_id,
    query: async () => ({ rows: [] }),
  }), /sync source/i);
});

test("Job Hunter confirmation receipt writes the same common ledger through exact SQLite source verification", async () => {
  const sourceReceipt = {
    intent_id: "899cdc72936541f3b03606d998fe2f51", fence: 2,
    application_id: "2db0cefdf284774c93e0abeee8a72526e345efd8171a2485fd668955a59f53d8",
    message_id: "19fc000000000010", thread_id: "19fc000000000011",
    evidence_sha256: "9".repeat(64), received_at: "2026-08-02T03:00:00+00:00",
  };
  const entry = buildJobHunterConfirmationResult({
    tenantId: "dais-local", sourceReceipt,
  });
  assert.equal(entry.organ, "job_hunter");
  assert.equal(entry.source_fence, 2);
  assert.equal(entry.sender_sha256, null);
  assert.equal(entry.result_type, "confirmation");
  assert.equal(entry.occurred_at, "2026-08-02T03:00:00.000Z");

  const sourceCalls = [];
  const verified = await verifyJobHunterConfirmationResultSource(entry, {
    query: async (sql, params) => {
      sourceCalls.push({ sql, params });
      return { rows: [{ verified: 1 }] };
    },
  });
  assert.equal(verified, true);
  assert.match(sourceCalls[0].sql, /JOIN submit_intents/i);
  assert.deepEqual(sourceCalls[0].params, [
    sourceReceipt.message_id, sourceReceipt.thread_id, sourceReceipt.intent_id,
    sourceReceipt.fence, sourceReceipt.application_id, sourceReceipt.evidence_sha256,
    sourceReceipt.received_at,
  ]);

  const pgCalls = [];
  const saved = await appendOutboundResult(entry, {
    verifyJobHunterSource: (candidate) =>
      verifyJobHunterConfirmationResultSource(candidate, {
        query: async () => ({ rows: [{ verified: 1 }] }),
      }),
    query: async (sql, params) => {
      pgCalls.push({ sql, params });
      return { rows: [{ result_id: entry.result_id, inserted: true }] };
    },
  });
  assert.equal(saved.result_id, entry.result_id);
  assert.doesNotMatch(pgCalls[0].sql, /lm_funder_submission_ledger/i);
  await assert.rejects(() => appendOutboundResult(entry, {
    verifyJobHunterSource: async () => false,
    query: async () => ({ rows: [{ result_id: entry.result_id }] }),
  }), /source verification/i);
});

test("Job Hunter production reader opens one exact SQLite ledger read-only and returns source receipts", async () => {
  const calls = [];
  const query = makeJobHunterSqliteQuery({
    ledgerPath: "/private/job-search/ledger.sqlite3",
    run: async (args) => {
      calls.push(args);
      return JSON.stringify([{
        message_id: "19fc000000000010", thread_id: "19fc000000000011",
        intent_id: "899cdc72936541f3b03606d998fe2f51", fence: 2,
        application_id: "2db0cefdf284774c93e0abeee8a72526e345efd8171a2485fd668955a59f53d8",
        evidence_sha256: "9".repeat(64), received_at: "2026-08-02T03:00:00+00:00",
      }]);
    },
  });
  const receipts = await readJobHunterConfirmationReceipts({ query });
  assert.equal(receipts.length, 1);
  assert.equal(receipts[0].fence, 2);
  assert.deepEqual(calls[0].slice(0, 3), [
    "-readonly", "-json", "/private/job-search/ledger.sqlite3",
  ]);
  assert.match(calls[0][3], /FROM submission_confirmations/i);
});
