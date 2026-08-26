"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { validateEventTalkOpportunity } = require("./event-talk-opportunity.js");
const { validateGroundedTalkPack } = require("./grounded-talk-pack.js");
const { createTalkEvidenceChain } = require("./connector-talk-evidence.js");

function fixture() {
  const source = { canonicalUrl: "https://luma.com/talk", title: "AI LT", body: "Open LT: https://forms.example.com/talk", now: "2026-08-07T00:00:00.000Z" };
  const opportunity = validateEventTalkOpportunity({ participation_kind: "both", talk_format: "lightning_talk", application_status: "open", should_create_talk_application: true, application_url: "https://forms.example.com/talk", evidence_excerpt: source.body, reason: "Open LT." }, source);
  const input = { event: source, facts: [{ evidence_ref: "evidence://connector/bio", fact: "Life Manager Connectorを開発しています。" }] };
  const talkPack = validateGroundedTalkPack({ title: "Life Manager LT", abstract: "Life Manager Connectorの証拠設計を紹介します。", bio: input.facts[0].fact, application_reason: "実装知見を共有します。", product_demo_summary: "Life Manager Connectorを紹介します。", outline: [
    { start_second: 0, end_second: 75, heading: "1", content: "設計", evidence_refs: [input.facts[0].evidence_ref] },
    { start_second: 75, end_second: 150, heading: "2", content: "実装", evidence_refs: [input.facts[0].evidence_ref] },
    { start_second: 150, end_second: 225, heading: "3", content: "検証", evidence_refs: [input.facts[0].evidence_ref] },
    { start_second: 225, end_second: 300, heading: "4", content: "結論", evidence_refs: [input.facts[0].evidence_ref] },
  ] }, input);
  return Object.freeze({ provider: "luma", event_ref: "luma-event://event/talk", priority_class: "open_talk", preference_reason: "Open LT first.", talk_opportunity: opportunity, talk_pack: talkPack });
}

test("verified talk readback creates one reference-only durable bundle and exact retry reuses it", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-talk-evidence-"));
  try {
    const chain = createTalkEvidenceChain({ stateDir, now: () => new Date("2026-08-07T01:00:00.000Z") });
    const input = { candidate: fixture(), providerState: { status: "provider_verified", receipt_ref: "provider-receipt://connector/talk/abc" } };
    const first = await chain.completeTalkEvidence(input);
    const second = await chain.completeTalkEvidence(input);
    assert.equal(first.status, "applied_bundle");
    assert.equal(first.completion_disposition, "created");
    assert.equal(second.completion_disposition, "reused");
    assert.equal(second.bundle_id, first.bundle_id);
    const files = fs.readdirSync(path.join(stateDir, "talk-applied-bundles"));
    assert.equal(files.length, 1);
    const file = path.join(stateDir, "talk-applied-bundles", files[0]);
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    const stored = JSON.parse(fs.readFileSync(file, "utf8"));
    assert.equal(stored.talk_state, "provider_verified");
    assert.equal(stored.priority_class, "open_talk");
    assert.equal(stored.preference_reason, "Open LT first.");
    assert.match(stored.talk_pack_sha256, /^[0-9a-f]{64}$/);
    assert.doesNotMatch(JSON.stringify(stored), /abstract|outline|bio|Life Manager LT/);
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});

test("unverified opportunity, pack, or provider state never writes a talk bundle", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-talk-evidence-"));
  try {
    const chain = createTalkEvidenceChain({ stateDir });
    const candidate = fixture();
    for (const input of [
      { candidate: { ...candidate, talk_pack: structuredClone(candidate.talk_pack) }, providerState: { status: "provider_verified", receipt_ref: "provider-receipt://connector/talk/abc" } },
      { candidate, providerState: { status: "submitted", receipt_ref: "provider-receipt://connector/talk/abc" } },
    ]) await assert.rejects(chain.completeTalkEvidence(input), /talk evidence unavailable/i);
    assert.equal(fs.existsSync(path.join(stateDir, "talk-applied-bundles")), false);
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});
