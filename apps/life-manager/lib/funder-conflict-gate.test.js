"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { judgeFunderRelationships, evaluateFunderConflict } = require("./funder-conflict-gate.js");

const NOW = "2026-08-02T01:00:00.000Z";

function observation(overrides = {}) {
  return {
    schema_version: 1,
    observed_at: "2026-08-02T00:30:00.000Z",
    partner_roster_status: "complete",
    sources: [{ source_id: "official", url: "https://example.org/program", fetched_at: "2026-08-02T00:00:00.000Z" }],
    relationships: [],
    ...overrides,
  };
}

function rel(entityId, role) {
  const conflictGroup = ["mufg", "mufg-bank", "muit", "mucap", "muip"].includes(entityId) ? "mufg_family" : "other";
  return { entity_id: entityId, entity_name: entityId, conflict_group: conflictGroup, role, source_refs: ["official"], rationale: "official relationship" };
}

test("MUFG-family operator and CVC relationships are denied", () => {
  for (const relationship of [rel("mucap", "operator"), rel("muip", "cvc"), rel("muit", "operator")]) {
    const result = evaluateFunderConflict({ tenantId: "dais-local", programId: "program", evaluatedAt: NOW, observation: observation({ relationships: [relationship] }) });
    assert.equal(result.decision, "deny_conflict");
    assert.equal(result.submit_allowed, false);
    assert.equal(result.blocking_relationships.length, 1);
  }
});

test("a restricted corporate partner is denied even when it is not the operator", () => {
  const result = evaluateFunderConflict({ tenantId: "dais-local", programId: "program", evaluatedAt: NOW, observation: observation({ relationships: [rel("mufg-bank", "corporate_partner")] }) });
  assert.equal(result.decision, "deny_conflict");
  assert.match(result.reason, /corporate_partner/);
});

test("LP-only involvement does not deny after a complete current partner check", () => {
  const result = evaluateFunderConflict({ tenantId: "dais-local", programId: "program", evaluatedAt: NOW, observation: observation({ relationships: [rel("mufg", "lp_only")] }) });
  assert.equal(result.decision, "allow");
  assert.equal(result.submit_allowed, true);
});

test("incomplete roster, stale source, unknown role, and non-HTTPS source fail closed", () => {
  const cases = [
    observation({ partner_roster_status: "incomplete" }),
    observation({ sources: [{ source_id: "official", url: "https://example.org", fetched_at: "2026-07-31T00:00:00.000Z" }] }),
    observation({ relationships: [rel("other", "unknown")] }),
    observation({ sources: [{ source_id: "official", url: "http://example.org", fetched_at: "2026-08-02T00:00:00.000Z" }] }),
  ];
  for (const item of cases) {
    const result = evaluateFunderConflict({ tenantId: "dais-local", programId: "program", evaluatedAt: NOW, observation: item });
    assert.equal(result.decision, "research_required");
    assert.equal(result.submit_allowed, false);
  }
});

test("relationship classification is an explicit model judgment over official source content", async () => {
  let received;
  const judged = await judgeFunderRelationships({
    programId: "1stround",
    observedAt: "2026-08-02T00:30:00.000Z",
    officialPages: [{ sourceId: "partners", url: "https://www.1stround.jp/", fetchedAt: "2026-08-02T00:00:00.000Z", content: "official partner links" }],
  }, { judge: async (request) => {
    received = request;
    return { partner_roster_status: "complete", relationships: [] };
  } });
  assert.match(received.instructions, /meaning/i);
  assert.doesNotMatch(received.instructions, /substring/i);
  assert.equal(judged.partner_roster_status, "complete");
  assert.match(judged.sources[0].content_digest, /^[0-9a-f]{64}$/);
  await assert.rejects(() => judgeFunderRelationships({ programId: "x", observedAt: NOW, officialPages: [] }, {}), /model judgment/i);
});
