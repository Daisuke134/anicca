"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const test = require("node:test");

const { verifyOutboundEvidence } = require("./outbound-evidence.js");
const {
  buildVerifiedOutboundReceipt,
  assertVerifiedOutboundReceipt,
} = require("./outbound-success.js");

const TENANT = "dais";
const JOB_ID = `outbound-event:${"b".repeat(64)}`;
const ATTEMPT = 2;
const ATTEMPT_REF = `runtime-attempt://${TENANT}/${JOB_ID}/${ATTEMPT}`;

async function evidence(options = {}) {
  const bytes = Buffer.alloc(5000, 0x61);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(bytes);
  const digest = createHash("sha256").update(bytes).digest("hex");
  return verifyOutboundEvidence({
    tenantId: TENANT,
    attemptRef: ATTEMPT_REF,
    externalReceiptRef: "gmail-message://dais/msg-501",
    artifactRef: `object://sha256/${digest}`,
    canonicalUrl: "https://lu.ma/tokyo-agent-night",
  }, {
    readExternalReceipt: async () => options.missingE1 ? null : ({
      kind: "confirmation_mail",
      provider_id: "msg-501",
      observed_at: "2026-08-01T09:00:00.000Z",
    }),
    readArtifact: async () => bytes,
    fetchImpl: async () => ({ status: 200 }),
  });
}

function job(overrides = {}) {
  return {
    tenant_id: TENANT,
    job_id: JOB_ID,
    attempt: ATTEMPT,
    capability: "outbound.event.apply",
    ...overrides,
  };
}

test("実verifier由来のE1/E2/E3だけが同じattemptのsuccess receiptになる", async () => {
  const verified = await evidence();
  const receipt = buildVerifiedOutboundReceipt({
    tenantId: TENANT,
    jobId: JOB_ID,
    attempt: ATTEMPT,
    verifiedAt: "2026-08-01T09:00:01.000Z",
  }, verified);
  assert.equal(assertVerifiedOutboundReceipt(receipt, job()), receipt);
  assert.deepEqual(receipt, {
    kind: "outbound_event_application",
    status: "verified",
    attempt_ref: ATTEMPT_REF,
    external_receipt_ref: "gmail-message://dais/msg-501",
    artifact_ref: verified.evidence.e2.ref,
    canonical_url: "https://lu.ma/tokyo-agent-night",
    evidence_hash: verified.evidence_hash,
    verified_at: "2026-08-01T09:00:01.000Z",
  });
  assert.equal(Object.isFrozen(receipt), true);
});

test("missing tierとverifier結果のplain copyはreceiptを作れない", async () => {
  const failed = await evidence({ missingE1: true });
  assert.throws(() => buildVerifiedOutboundReceipt({
    tenantId: TENANT, jobId: JOB_ID, attempt: ATTEMPT,
  }, failed), /verified evidence/);

  const verified = await evidence();
  const copied = JSON.parse(JSON.stringify(verified));
  assert.throws(() => buildVerifiedOutboundReceipt({
    tenantId: TENANT, jobId: JOB_ID, attempt: ATTEMPT,
  }, copied), /verifier provenance/);
});

test("bare success、receipt copy、別attemptはruntime completionを通れない", async () => {
  assert.throws(() => assertVerifiedOutboundReceipt(
    { status: "success" },
    job(),
  ), /verified receipt/);

  const verified = await evidence();
  const receipt = buildVerifiedOutboundReceipt({
    tenantId: TENANT, jobId: JOB_ID, attempt: ATTEMPT,
  }, verified);
  assert.throws(() => assertVerifiedOutboundReceipt(
    JSON.parse(JSON.stringify(receipt)),
    job(),
  ), /receipt provenance/);
  assert.throws(() => assertVerifiedOutboundReceipt(
    receipt,
    job({ attempt: 3 }),
  ), /attempt mismatch/);
});

