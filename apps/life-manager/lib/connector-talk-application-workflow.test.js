"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { validateEventTalkOpportunity } = require("./event-talk-opportunity.js");
const { validateGroundedTalkPack } = require("./grounded-talk-pack.js");
const { createTalkApplicationWorkflow } = require("./connector-talk-application-workflow.js");

const source = Object.freeze({
  canonicalUrl: "https://luma.com/ai-lt", title: "AI LT",
  body: "5 minute LT applications are open at https://forms.example.com/ai-lt",
  now: "2026-08-07T00:00:00.000Z",
});
const opportunity = validateEventTalkOpportunity({
  participation_kind: "both", talk_format: "lightning_talk", application_status: "open",
  should_create_talk_application: true, application_url: "https://forms.example.com/ai-lt",
  evidence_excerpt: source.body, reason: "Public LT application.",
}, source);
const packInput = Object.freeze({
  event: source,
  facts: [{ evidence_ref: "evidence://connector/bio", fact: "Life Manager Connectorを開発しています。" }],
});
const pack = validateGroundedTalkPack({
  title: "Life Manager Connectorの証拠設計", abstract: "Life Manager Connectorの申込と確認を証拠で結ぶ設計を紹介します。",
  bio: "Life Manager Connectorを開発しています。", application_reason: "AI LTで実装知見を共有するためです。",
  product_demo_summary: "Life Manager Connectorの申込からreadbackまでを紹介します。",
  outline: [
    { start_second: 0, end_second: 60, heading: "課題", content: "申込の完了を証明します。", evidence_refs: ["evidence://connector/bio"] },
    { start_second: 60, end_second: 150, heading: "設計", content: "証拠境界を説明します。", evidence_refs: ["evidence://connector/bio"] },
    { start_second: 150, end_second: 240, heading: "デモ", content: "readbackを示します。", evidence_refs: ["evidence://connector/bio"] },
    { start_second: 240, end_second: 300, heading: "結論", content: "安全な自動化で締めます。", evidence_refs: ["evidence://connector/bio"] },
  ],
}, packInput);

function candidate() {
  return Object.freeze({ provider: "luma", event_ref: "luma-event://event/ai-lt", talk_opportunity: opportunity, talk_pack: pack });
}

test("ordinary verified fields submit once and official readback advances to provider_verified", async () => {
  const calls = [];
  const workflow = createTalkApplicationWorkflow({
    async inspectForm() { return { required_fields: ["title", "abstract", "bio"], blocking_flags: [] }; },
    async fillFields(input) { calls.push(["fill", input.values]); },
    async clickSubmit() { calls.push(["submit"]); },
    async readProviderState() { return { status: "provider_verified", receipt_ref: "provider-receipt://connector/talk/1" }; },
  });
  const result = await workflow.run({ page: {}, candidate: candidate() });
  assert.equal(result.status, "provider_verified");
  assert.equal(result.receipt_ref, "provider-receipt://connector/talk/1");
  assert.deepEqual(calls.map(([name]) => name), ["fill", "submit"]);
  assert.deepEqual(Object.keys(calls[0][1]).sort(), ["abstract", "bio", "title"]);
});

test("payment, CAPTCHA, identity verification, and unknown required fields never fill or submit", async () => {
  for (const inspection of [
    { required_fields: ["title"], blocking_flags: ["payment"] },
    { required_fields: ["title"], blocking_flags: ["captcha"] },
    { required_fields: ["title"], blocking_flags: ["identity_verification"] },
    { required_fields: ["title", "employer_legal_attestation"], blocking_flags: [] },
  ]) {
    let effects = 0;
    const workflow = createTalkApplicationWorkflow({
      async inspectForm() { return inspection; },
      async fillFields() { effects += 1; }, async clickSubmit() { effects += 1; },
      async readProviderState() { effects += 1; },
    });
    assert.deepEqual(await workflow.run({ page: {}, candidate: candidate() }), {
      status: "human_action_required", safe_reason: inspection.blocking_flags[0] || "unknown_required_field",
    });
    assert.equal(effects, 0);
  }
});

test("submit without official readback stops at submitted and never claims provider verification", async () => {
  let submits = 0;
  const workflow = createTalkApplicationWorkflow({
    async inspectForm() { return { required_fields: ["title"], blocking_flags: [] }; },
    async fillFields() {}, async clickSubmit() { submits += 1; },
    async readProviderState() { return { status: "unavailable" }; },
  });
  assert.deepEqual(await workflow.run({ page: {}, candidate: candidate() }), { status: "submitted", safe_reason: "provider_readback_unavailable" });
  assert.equal(submits, 1);
});
