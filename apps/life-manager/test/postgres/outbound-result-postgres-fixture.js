"use strict";

const assert = require("node:assert/strict");
const { Client } = require("pg");
const { buildFunderSubmissionReceipt } = require("../../lib/funder-submission-receipt.js");
const { makeFunderGogThreadReader } = require("../../lib/funder-gog-thread-reader.js");
const {
  normalizeFunderApplicationThread,
  buildFunderConfirmationResult,
} = require("../../lib/funder-thread-result.js");
const { buildJobHunterConfirmationResult } = require("../../lib/job-hunter-outbound-result.js");
const { appendOutboundResult } = require("../../lib/outbound-result-store.js");

const wrapped = (id, text) => `<<<EXTERNAL_UNTRUSTED_CONTENT id="${id}">>>\nSource: google_api\n---\n${text}\n<<<END_EXTERNAL_UNTRUSTED_CONTENT id="${id}">>>`;

function receipt() {
  return buildFunderSubmissionReceipt({
    tenantId: "tenant-a", funderId: "yc-fall-2026",
    draftId: "0b61fe42-e383-490d-b60e-04f1ad7ec5df",
    applicationUrl: "https://apply.ycombinator.com/home",
    home: { status: "in_review", observedAt: "2026-08-01T17:32:00Z" },
    mail: {
      messageId: "19fbe6135cf98bd4", threadId: "19fbe6135cf98bd4",
      internalDateMs: Date.parse("2026-08-01T17:31:05Z"),
      from: "apply@ycombinator.com", subject: "YC Fall 2026 Application Submitted",
      body: "Your application to the Fall 2026 batch for Anicca has been submitted.",
      dkimPass: true, spfPass: true, dmarcPass: true,
    },
  });
}

async function funderResult(body) {
  const source = receipt();
  const raw = { thread: { id: source.mail_thread_id, messages: [{
    id: source.mail_message_id, threadId: source.mail_thread_id,
    internalDate: Date.parse(source.submitted_at),
    headers: {
      from: wrapped("from", source.mail_sender),
      subject: wrapped("subject", source.mail_subject),
    },
    body: wrapped("body", body),
  }] } };
  const reader = makeFunderGogThreadReader({
    account: "fixture@example.com", run: async () => JSON.stringify(raw),
  });
  const normalized = normalizeFunderApplicationThread(
    await reader.getThread(source.mail_thread_id),
    { submissionReceipt: source, ownerEmail: "owner@example.com" },
  );
  return buildFunderConfirmationResult({
    submissionReceipt: source, message: normalized.confirmation,
  });
}

async function main() {
  const client = new Client({ connectionString: process.env.DATABASE_URL });
  await client.connect();
  const query = (sql, params) => client.query(sql, params);
  try {
    const source = receipt();
    await client.query(`
      INSERT INTO public.lm_funder_submission_ledger (
        tenant_id,ledger_id,funder_id,draft_id,application_url,status,provider_status,
        submitted_at,home_observed_at,mail_message_id,mail_thread_id,mail_sender,
        mail_subject,mail_auth,evidence_digest
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14::jsonb,$15)
    `, [source.tenant_id, source.ledger_id, source.funder_id, source.draft_id,
      source.application_url, source.status, source.provider_status, source.submitted_at,
      source.home_observed_at, source.mail_message_id, source.mail_thread_id,
      source.mail_sender, source.mail_subject, JSON.stringify(source.mail_auth),
      source.evidence_digest]);
    const standardBody = "Your application to the Fall 2026 batch for Anicca has been submitted.";
    const confirmation = await funderResult(standardBody);
    assert.equal((await appendOutboundResult(confirmation, { query })).inserted, true);
    assert.equal((await appendOutboundResult(confirmation, { query })).inserted, false);

    const collision = await funderResult(`${standardBody}\nView it in the portal.`);
    await assert.rejects(() => appendOutboundResult(collision, { query }), /conflict/);

    const job = buildJobHunterConfirmationResult({ tenantId: "tenant-a", sourceReceipt: {
      intent_id: "899cdc72936541f3b03606d998fe2f51", fence: 2,
      application_id: "2db0cefdf284774c93e0abeee8a72526e345efd8171a2485fd668955a59f53d8",
      message_id: "19fc000000000010", thread_id: "19fc000000000011",
      evidence_sha256: "9".repeat(64), received_at: "2026-08-02T03:00:00+00:00",
    } });
    const verified = async () => true;
    assert.equal((await appendOutboundResult(job, { query, verifyJobHunterSource: verified })).inserted, true);
    assert.equal((await appendOutboundResult(job, { query, verifyJobHunterSource: verified })).inserted, false);
    await assert.rejects(() => appendOutboundResult(job, {
      query, verifyJobHunterSource: async () => false,
    }), /source verification/);
    process.stdout.write("store_fixture=PASS insert=2 replay=2 conflict=1 source_reject=1\n");
  } finally {
    await client.end();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
